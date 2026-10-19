"""Incremental, auditable EOM source refresh.

Networked sources are best-effort: failures are recorded, never treated as zero values.
Historical snapshots and retrieval vintages are retained. This script does not calibrate
or publish a new ranking automatically; it only refreshes evidence and freshness reports.
"""
from __future__ import annotations
import argparse, hashlib, json, os, socket, sys, time, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eom_empirical.eurostat_api import fetch_spain_migration_flows

WB_BASE = "https://api.worldbank.org/v2"
# Current identifiers for revised World Bank Worldwide Governance Indicators.
# Keep canonical feature keys stable for downstream EOM data.
WB_API_CODE_OVERRIDES = {"GE.EST": "GOV_WGI_GE_EST", "PV.EST": "GOV_WGI_PV_EST", "RQ.EST": "GOV_WGI_RQ_EST"}
WB_INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "GDP per capita, PPP (constant 2021 international $)",
    "NY.GDP.MKTP.PP.CD": "GDP, PPP (current international $)",
    "PA.NUS.PPP": "PPP conversion factor, GDP (LCU per international $)",
    "PA.NUS.PRVT.PP": "PPP conversion factor, household/private consumption (LCU per international $)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force, ILO modeled estimate)",
    "RQ.EST": "Regulatory quality estimate",
    "GE.EST": "Government effectiveness estimate",
    "PV.EST": "Political stability and absence of violence/terrorism estimate",
    "SP.POP.TOTL": "Population, total",
    "SM.POP.NETM": "Net migration",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "SL.EMP.TOTL.SP.ZS": "Employment to population ratio, 15+, total (%)",
    "SL.TLF.CACT.ZS": "Labor force participation rate, total (%)",
    "SP.DYN.LE00.IN": "Life expectancy at birth, total (years)",
    "SP.POP.1564.TO.ZS": "Population ages 15-64 (% of total)",
    "BX.TRF.PWKR.CD.DT": "Personal remittances, received (current US$)",
}
POLICY_URLS = [
    ("Canada", "IRCC Express Entry news", "https://www.canada.ca/en/immigration-refugees-citizenship/news.html"),
    ("United Kingdom", "UK immigration policy news", "https://www.gov.uk/government/organisations/uk-visas-and-immigration"),
    ("Australia", "Department of Home Affairs immigration news", "https://immi.homeaffairs.gov.au/news-media/archive"),
    ("New Zealand", "Immigration New Zealand news", "https://www.immigration.govt.nz/about-us/news-centre/"),
    ("Ireland", "Employment permits current processing dates", "https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/current-application-processing-dates/"),
    ("Singapore", "Ministry of Manpower work passes", "https://www.mom.gov.sg/passes-and-permits"),
    ("Hong Kong", "Immigration Department news", "https://www.immd.gov.hk/eng/press/"),
    ("Japan", "Immigration Services Agency", "https://www.moj.go.jp/isa/"),
    ("Switzerland", "State Secretariat for Migration news", "https://www.sem.admin.ch/sem/en/home/aktuell.html"),
    ("Austria", "Austrian Federal Government migration portal", "https://www.migration.gv.at/en/welcome/"),
    ("Spain", "Spanish State Secretariat for Migration", "https://www.inclusion.gob.es/en/web/migraciones/home"),
]

OBMIGRA_URL = "https://www.gov.br/mj/pt-br/assuntos/seus-direitos/migracoes/portal-de-imigracao-laboral/obmigra-1/relatorios-obmigra/dados-consolidados/2025"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def session_with_retries() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "EOM-Research-ETL/2.1 (+reproducible academic research)"})
    retry = Retry(total=2, connect=2, read=2, backoff_factor=0.4,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def resolve_host_with_retries(url: str, attempts: int = 3, base_delay: float = 1.0) -> None:
    """Preflight DNS resolution and retry transient resolver failures with backoff.

    This does not replace the system resolver; it prevents a transient DNS failure
    from immediately failing an entire source fetch and leaves useful diagnostics.
    """
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError(f"URL has no hostname: {url!r}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    last_error = None
    for attempt in range(attempts):
        try:
            socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            return
        except socket.gaierror as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(base_delay * (2 ** attempt))
    raise socket.gaierror(f"DNS lookup failed for {host} after {attempts} attempts: {last_error}") from last_error


def request_with_dns_retries(session: requests.Session, url: str, *, attempts: int = 3, base_delay: float = 1.0, **kwargs):
    """Retry transient DNS resolution errors around an HTTP GET."""
    last_error = None
    for attempt in range(attempts):
        try:
            resolve_host_with_retries(url, attempts=2, base_delay=base_delay)
            return session.get(url, **kwargs)
        except (socket.gaierror, requests.exceptions.ConnectionError) as exc:
            message = str(exc).lower()
            is_dns_error = isinstance(exc, socket.gaierror) or any(
                token in message for token in ("name or service not known", "temporary failure in name resolution",
                                                "getaddrinfo failed", "nodename nor servname", "failed to resolve"))
            if not is_dns_error:
                raise
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(base_delay * (2 ** attempt))
    raise requests.exceptions.ConnectionError(
        f"DNS resolution/request failed for {url} after {attempts} attempts: {last_error}"
    ) from last_error


def atomic_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def fetch_one_indicator(code: str, label: str, run_id: str, start: int, end: int) -> tuple[list[dict], dict]:
    session = session_with_retries()
    rows, statuses = [], []
    snapshot_dir = ROOT / "data" / "raw" / "snapshots" / "world_bank" / run_id
    api_code = WB_API_CODE_OVERRIDES.get(code, code)
    url = f"{WB_BASE}/country/all/indicator/{api_code}"
    page, pages, count, per_page = 1, 1, 0, 20000
    try:
        while page <= pages:
            last_error = None
            parsed = None
            for candidate_per_page in dict.fromkeys([per_page, 1000]):
                try:
                    r = request_with_dns_retries(session, url, params={"date": f"{start}:{end}", "format": "json", "per_page": candidate_per_page, "page": page}, timeout=(8, 30))
                    r.raise_for_status()
                    payload = r.json()
                    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict) or not (payload[1] is None or isinstance(payload[1], list)):
                        preview = (r.text or "").replace("\n", " ")[:400]
                        raise ValueError(f"Unexpected World Bank API response for {code}: HTTP {r.status_code}, content-type={r.headers.get('Content-Type')}, payload_type={type(payload).__name__}, body_preview={preview!r}")
                    parsed = (r, payload, payload[0], payload[1] or [], candidate_per_page)
                    break
                except Exception as exc:
                    last_error = exc
            if parsed is None:
                raise last_error or ValueError(f"No valid World Bank response for {code}")
            r, payload, meta, observations, per_page = parsed
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            (snapshot_dir / f"{code.replace('.', '_')}_page_{page}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            for item in observations:
                c = item.get("country") or {}; im = item.get("indicator") or {}
                year = item.get("date")
                if not year: continue
                rows.append({"country_code": (item.get("countryiso3code") or "").upper(), "country_name_api": c.get("value"),
                    "indicator_code": code, "indicator_api_code": im.get("id", api_code), "indicator_name_api": im.get("value") or label, "year": int(year),
                    "value": item.get("value"), "source": "World Bank Indicators API", "source_url": r.url,
                    "retrieved_utc": utc_now().isoformat(), "run_id": run_id,
                    "status": "observed" if item.get("value") is not None else "missing"})
            count += len(observations); pages = int(meta.get("pages", 1) or 1); page += 1
        status = {"source_id": f"WDI_{code}", "source": "World Bank Indicators API", "url": url, "status": "SUCCESS",
            "rows_fetched": count, "indicator": code, "observation_start": start, "observation_end_requested": end, "error": ""}
    except Exception as e:
        status = {"source_id": f"WDI_{code}", "source": "World Bank Indicators API", "url": url, "status": "FAILED",
            "rows_fetched": count, "indicator": code, "observation_start": start, "observation_end_requested": end, "error": f"{type(e).__name__}: {e}"}
    return rows, status


def fetch_world_bank(session: requests.Session, run_id: str, start: int, end: int) -> tuple[pd.DataFrame, list[dict]]:
    rows, statuses = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_one_indicator, code, label, run_id, start, end) for code, label in WB_INDICATORS.items()]
        for future in as_completed(futures):
            got_rows, status = future.result()
            rows.extend(got_rows); statuses.append(status)
    statuses.sort(key=lambda item: item["indicator"])
    return pd.DataFrame(rows), statuses



def check_policy_sources(session: requests.Session, run_id: str) -> list[dict]:
    out, snap_dir = [], ROOT / "data" / "raw" / "snapshots" / "policy_pages" / run_id
    snap_dir.mkdir(parents=True, exist_ok=True)
    state_path = ROOT / "data" / "policy_page_state.json"
    try: previous = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception: previous = {}
    new_state = dict(previous)
    for country, label, url in POLICY_URLS:
        row = {"country": country, "source_label": label, "url": url, "checked_at_utc": utc_now().isoformat(), "status": "FAILED", "http_status": None, "content_sha256": "", "changed_since_previous_check": "unknown", "error": ""}
        try:
            host = (urlparse(url).hostname or "").lower()
            if not (host.endswith(".gov.uk") or host.endswith(".gov.au") or host.endswith(".govt.nz") or host.endswith(".gov.sg") or host.endswith(".gov.hk") or host.endswith(".admin.ch") or host.endswith(".go.jp") or host.endswith(".canada.ca") or host.endswith(".gov.ie") or host.endswith(".mom.gov.sg") or host.endswith(".immd.gov.hk") or host.endswith(".moj.go.jp") or host.endswith(".sem.admin.ch") or host.endswith(".gv.at") or host.endswith(".gob.es") or host in {"www.canada.ca", "enterprise.gov.ie", "www.mom.gov.sg", "www.immd.gov.hk", "www.moj.go.jp", "www.sem.admin.ch"}):
                raise ValueError(f"Host not on official-domain allowlist: {host}")
            r = request_with_dns_retries(session, url, timeout=(8, 20), allow_redirects=True)
            r.raise_for_status()
            body = r.text
            digest = hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()
            key = hashlib.sha256(url.encode()).hexdigest()[:16]
            (snap_dir / f"{key}.html").write_text(body, encoding="utf-8", errors="replace")
            old = previous.get(url, {}).get("content_sha256")
            row.update({"status": "SUCCESS", "http_status": r.status_code, "content_sha256": digest,
                        "changed_since_previous_check": str(old != digest).lower() if old else "first_seen"})
            new_state[url] = {"content_sha256": digest, "last_checked_utc": row["checked_at_utc"], "country": country, "label": label, "final_url": r.url}
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        out.append(row)
    state_path.write_text(json.dumps(new_state, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def check_obmigra_source(session: requests.Session, run_id: str) -> dict:
    """Monitor the official Brazil OBMigra catalogue page.

    This is a source-page/change monitor only. It does not claim to parse PDF tables
    or turn the report into numeric observations.
    """
    row = {
        "source_id": "BRAZIL_OBMIGRA_CATALOG",
        "source": "Brazil OBMigra consolidated migration statistics",
        "url": OBMIGRA_URL,
        "checked_at_utc": utc_now().isoformat(),
        "status": "FAILED",
        "http_status": None,
        "content_sha256": "",
        "linked_data_assets": "",
        "linked_data_asset_count": 0,
        "error": "",
        "numeric_data_ingested": False,
    }
    try:
        response = request_with_dns_retries(session, OBMIGRA_URL, timeout=(8, 25))
        response.raise_for_status()
        final_host = (urlparse(response.url).hostname or "").lower()
        if not (final_host == "gov.br" or final_host.endswith(".gov.br")):
            raise ValueError(f"Unexpected redirect away from official gov.br domain: {final_host}")
        body = response.text
        digest = hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()
        snapshot = ROOT / "data" / "raw" / "snapshots" / "obmigra" / run_id / "catalog.html"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(body, encoding="utf-8", errors="replace")
        hrefs = re.findall(r"""href=["']([^"']+)["']""", body, flags=re.IGNORECASE)
        assets = sorted({
            urljoin(response.url, href)
            for href in hrefs
            if urlparse(urljoin(response.url, href)).path.lower().endswith(
                (".pdf", ".xlsx", ".xls", ".csv", ".zip", ".ods")
            )
        })
        row.update({
            "status": "SUCCESS",
            "http_status": response.status_code,
            "content_sha256": digest,
            "linked_data_assets": ";".join(assets),
            "linked_data_asset_count": len(assets),
        })
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def integrate_eurostat_panel(rows: list[dict]) -> None:
    """Merge Spain's refreshed total flows into the historical panel where years exist."""
    panel_path = ROOT / "data" / "historical_destination_year_panel.csv"
    if not rows or not panel_path.exists():
        return
    panel = pd.read_csv(panel_path)
    if "eurostat_immigration_total_flow_persons" not in panel.columns:
        panel["eurostat_immigration_total_flow_persons"] = pd.NA
        panel["missing_eurostat_immigration_total_flow_persons"] = True
    column_map = {
        "emigration_total": (
            "eurostat_emigration_total_flow_persons",
            "missing_eurostat_emigration_total_flow_persons",
        ),
        "immigration_total": (
            "eurostat_immigration_total_flow_persons",
            "missing_eurostat_immigration_total_flow_persons",
        ),
    }
    for item in rows:
        destination = item.get("destination")
        if destination != "Spain":
            continue
        try:
            year = int(item["year"])
        except (TypeError, ValueError):
            continue
        mask = (panel["destination"] == destination) & (pd.to_numeric(panel["year"], errors="coerce") == year)
        if not mask.any():
            continue
        columns = column_map.get(item.get("indicator"))
        if not columns:
            continue
        value_column, missing_column = columns
        if value_column not in panel.columns:
            panel[value_column] = pd.NA
        if missing_column not in panel.columns:
            panel[missing_column] = True
        value = item.get("value")
        if value is None or pd.isna(value):
            panel.loc[mask, value_column] = pd.NA
            panel.loc[mask, missing_column] = True
        else:
            panel.loc[mask, value_column] = float(value)
            panel.loc[mask, missing_column] = False
    atomic_csv(panel, panel_path)


def update_brazil_macro_extract(
    fresh: pd.DataFrame, output_path: Path | None = None
) -> int:
    """Persist a compact BRA-only extract from the global World Bank refresh.

    Returns the number of Brazil indicator-year rows fetched in this run. If no
    Brazil rows arrive, existing output is left untouched rather than erased.
    """
    if fresh.empty or "country_code" not in fresh.columns:
        return 0
    brazil = fresh[fresh["country_code"].astype(str).str.upper().eq("BRA")].copy()
    if brazil.empty:
        return 0
    path = output_path or ROOT / "data" / "raw" / "brazil_world_bank_macro.csv"
    existing = pd.read_csv(path) if path.exists() else pd.DataFrame()
    combined = pd.concat([existing, brazil], ignore_index=True, sort=False)
    combined["_retrieved_sort"] = pd.to_datetime(
        combined.get("retrieved_utc"), errors="coerce", utc=True
    )
    combined = (
        combined.sort_values("_retrieved_sort")
        .drop_duplicates(["country_code", "indicator_code", "year"], keep="last")
        .drop(columns=["_retrieved_sort"])
    )
    atomic_csv(combined, path)
    return int(len(brazil))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start-year", type=int, default=2010)
    ap.add_argument("--end-year", type=int, default=utc_now().year)
    ap.add_argument("--skip-policy-watch", action="store_true")
    ap.add_argument("--offline-audit", action="store_true", help="Build freshness/status reports from cached data without network calls")
    args = ap.parse_args()
    if args.start_year > args.end_year: ap.error("start-year must be <= end-year")
    run_dt = utc_now(); run_id = run_dt.strftime("%Y-%m-%dT%H%M%SZ")
    session = session_with_retries()
    if args.offline_audit:
        fresh = pd.DataFrame()
        statuses = [{"source_id": f"WDI_{code}", "source": "World Bank Indicators API", "url": f"{WB_BASE}/country/all/indicator/{code}", "status": "SKIPPED_OFFLINE", "rows_fetched": 0, "indicator": code, "observation_start": args.start_year, "observation_end_requested": args.end_year, "error": "Offline audit requested; no network call made"} for code in WB_INDICATORS]
        eurostat_rows = []
        eurostat_status = [{"source_id": f"EUROSTAT_{dataset}", "source": "Eurostat Statistics API", "dataset": dataset, "url": f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}", "status": "SKIPPED_OFFLINE", "rows_fetched": 0, "observed_rows": 0, "observation_start": args.start_year, "observation_end_requested": args.end_year, "error": "Offline audit requested; no network call made"} for _indicator, dataset in (("emigration_total", "migr_emi2"), ("immigration_total", "migr_imm8"))]
        obmigra = {"source_id": "BRAZIL_OBMIGRA_CATALOG", "source": "Brazil OBMigra consolidated migration statistics", "url": OBMIGRA_URL, "checked_at_utc": utc_now().isoformat(), "status": "SKIPPED_OFFLINE", "http_status": None, "content_sha256": "", "linked_data_assets": "", "linked_data_asset_count": 0, "error": "Offline audit requested; no network call made", "numeric_data_ingested": False}
        policy = []
    else:
        fresh, statuses = fetch_world_bank(session, run_id, args.start_year, args.end_year)
        eurostat_rows, eurostat_status = fetch_spain_migration_flows(
            session,
            run_id=run_id,
            start_year=args.start_year,
            end_year=args.end_year,
            snapshot_dir=ROOT / "data" / "raw" / "snapshots" / "eurostat" / run_id,
        )
        obmigra = check_obmigra_source(session, run_id)
        policy = [] if args.skip_policy_watch else check_policy_sources(session, run_id)
    raw_path = ROOT / "data" / "raw" / "world_bank_long.csv"
    history_path = ROOT / "data" / "observations_history" / "world_bank_observations.csv"
    if not fresh.empty:
        # Immutable-ish retrieval history: one record per retrieved vintage/run.
        history = pd.concat([pd.read_csv(history_path) if history_path.exists() else pd.DataFrame(), fresh], ignore_index=True, sort=False)
        if not history.empty:
            history = history.drop_duplicates(subset=["run_id", "country_code", "indicator_code", "year"], keep="last")
        atomic_csv(history, history_path)
        # Canonical latest-observation table, retaining older records and never erasing on failure.
        existing = pd.read_csv(raw_path) if raw_path.exists() else pd.DataFrame()
        merged = pd.concat([existing, fresh], ignore_index=True, sort=False)
        if not merged.empty:
            merged["year"] = pd.to_numeric(merged["year"], errors="coerce")
            merged["_retrieved_sort"] = pd.to_datetime(merged.get("retrieved_utc"), errors="coerce", utc=True)
            merged = merged.sort_values("_retrieved_sort").drop_duplicates(["country_code", "indicator_code", "year"], keep="last").drop(columns=["_retrieved_sort"])
            atomic_csv(merged, raw_path)
    brazil_macro_rows = update_brazil_macro_extract(fresh)
    status_df = pd.DataFrame(statuses)
    policy_df = pd.DataFrame(policy)
    eurostat_status_df = pd.DataFrame(eurostat_status)
    obmigra_df = pd.DataFrame([obmigra])
    atomic_csv(status_df, ROOT / "metadata" / "live_source_status.csv")
    atomic_csv(eurostat_status_df, ROOT / "metadata" / "eurostat_source_status.csv")
    atomic_csv(obmigra_df, ROOT / "metadata" / "obmigra_source_status.csv")
    if policy:
        atomic_csv(policy_df, ROOT / "metadata" / "policy_page_watch_status.csv")

    if eurostat_rows:
        eurostat_path = ROOT / "data" / "raw" / "eurostat_migration_flows.csv"
        existing_eurostat = pd.read_csv(eurostat_path) if eurostat_path.exists() else pd.DataFrame()
        combined_eurostat = pd.concat(
            [existing_eurostat, pd.DataFrame(eurostat_rows)], ignore_index=True, sort=False
        )
        combined_eurostat["_retrieved_sort"] = pd.to_datetime(
            combined_eurostat.get("retrieved_utc"), errors="coerce", utc=True
        )
        combined_eurostat = (
            combined_eurostat.sort_values("_retrieved_sort")
            .drop_duplicates(["geo_code", "indicator", "year"], keep="last")
            .drop(columns=["_retrieved_sort"])
        )
        atomic_csv(combined_eurostat, eurostat_path)
        integrate_eurostat_panel(eurostat_rows)
    # Freshness dashboard by indicator: last nonmissing observation year and destination coverage.
    dashboard = []
    canonical = pd.read_csv(raw_path) if raw_path.exists() else pd.DataFrame()
    if not canonical.empty:
        canonical["year"] = pd.to_numeric(canonical["year"], errors="coerce")
        for code, group in canonical.groupby("indicator_code", dropna=False):
            obs = group[group["value"].notna()]
            latest = int(obs["year"].max()) if not obs.empty else None
            name_col = "indicator_name_api" if "indicator_name_api" in group.columns else "indicator_name"
            retrieval_col = "retrieved_utc" if "retrieved_utc" in group.columns else None
            names = group[name_col].dropna() if name_col in group.columns else pd.Series(dtype=str)
            retrievals = group[retrieval_col].dropna() if retrieval_col else pd.Series(dtype=str)
            dashboard.append({"indicator_code": code, "indicator_name": names.iloc[-1] if not names.empty else "",
                "latest_observation_year": latest, "countries_with_latest_year": int(obs.loc[obs["year"] == latest, "country_code"].nunique()) if latest else 0,
                "observed_rows": int(len(obs)), "last_retrieval_utc": retrievals.max() if not retrievals.empty else "unknown_for_legacy_snapshot",
                "freshness_status": "NO_OBSERVATIONS" if latest is None else ("CURRENT_YEAR" if latest >= run_dt.year else ("RECENT" if latest >= run_dt.year - 2 else "STALE_OR_SLOW_RELEASE"))})
    atomic_csv(pd.DataFrame(dashboard), ROOT / "outputs" / "data_freshness_dashboard.csv")
    summary = {"run_id": run_id, "run_at_utc": run_dt.isoformat(), "requested_year_range": [args.start_year, args.end_year],
        "world_bank_indicators_successful": int((status_df["status"] == "SUCCESS").sum()) if not status_df.empty else 0,
        "world_bank_indicators_failed": int((status_df["status"] == "FAILED").sum()) if not status_df.empty else 0,
        "offline_audit": bool(args.offline_audit),
        "world_bank_rows_fetched": int(len(fresh)), "brazil_macro_rows_fetched": int(brazil_macro_rows), "policy_pages_successful": int((policy_df["status"] == "SUCCESS").sum()) if not policy_df.empty else 0,
        "policy_pages_failed": int((policy_df["status"] == "FAILED").sum()) if not policy_df.empty else 0,
        "eurostat_series_successful": int((eurostat_status_df["status"] == "SUCCESS").sum()) if not eurostat_status_df.empty else 0,
        "eurostat_series_failed": int((eurostat_status_df["status"] == "FAILED").sum()) if not eurostat_status_df.empty else 0,
        "eurostat_observed_rows": int(eurostat_status_df["observed_rows"].sum()) if not eurostat_status_df.empty else 0,
        "obmigra_source_status": obmigra.get("status", "Not reported"),
        "obmigra_numeric_data_ingested": False,
        "ranking_recomputed": False, "forecast_issued": False,
        "note": "This is a source refresh, not model calibration. Eurostat total flows are kept separate from subgroup-specific series; OBMigra is source-page monitored only and is not numerically parsed. Failed sources preserve prior canonical data; a new ranking requires a separate validated run."}
    out_dir = ROOT / "metadata" / "refresh_runs"; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    any_eurostat_success = not eurostat_status_df.empty and eurostat_status_df["status"].eq("SUCCESS").any()
    obmigra_success = obmigra.get("status") == "SUCCESS"
    return 0 if args.offline_audit or summary["world_bank_indicators_successful"] > 0 or policy_df.get("status", pd.Series(dtype=str)).eq("SUCCESS").any() or any_eurostat_success or obmigra_success else 2

if __name__ == "__main__":
    raise SystemExit(main())
