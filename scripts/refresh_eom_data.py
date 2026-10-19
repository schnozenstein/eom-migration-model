"""Incremental, auditable EOM source refresh.

Networked sources are best-effort: failures are recorded, never treated as zero values.
Historical snapshots and retrieval vintages are retained. This script does not calibrate
or publish a new ranking automatically; it only refreshes evidence and freshness reports.
"""
from __future__ import annotations
import argparse, hashlib, json, os, socket, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
WB_BASE = "https://api.worldbank.org/v2"
# Current identifiers for revised World Bank Worldwide Governance Indicators.
# Keep canonical feature keys stable for downstream EOM data.
WB_API_CODE_OVERRIDES = {"GE.EST": "GOV_WGI_GE_EST", "PV.EST": "GOV_WGI_PV_EST", "RQ.EST": "GOV_WGI_RQ_EST"}
WB_INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "GDP per capita, PPP (constant 2021 international $)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force, ILO modeled estimate)",
    "PA.NUS.PPPC.RF": "GDP price level ratio of PPP to market exchange rate (US=1)",
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
]


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
            if not (host.endswith(".gov.uk") or host.endswith(".gov.au") or host.endswith(".govt.nz") or host.endswith(".gov.sg") or host.endswith(".gov.hk") or host.endswith(".admin.ch") or host.endswith(".go.jp") or host.endswith(".canada.ca") or host.endswith(".gov.ie") or host.endswith(".mom.gov.sg") or host.endswith(".immd.gov.hk") or host.endswith(".moj.go.jp") or host.endswith(".sem.admin.ch") or host in {"www.canada.ca", "enterprise.gov.ie", "www.mom.gov.sg", "www.immd.gov.hk", "www.moj.go.jp", "www.sem.admin.ch"}):
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
        policy = []
    else:
        fresh, statuses = fetch_world_bank(session, run_id, args.start_year, args.end_year)
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
    status_df = pd.DataFrame(statuses)
    policy_df = pd.DataFrame(policy)
    atomic_csv(status_df, ROOT / "metadata" / "live_source_status.csv")
    if policy:
        atomic_csv(policy_df, ROOT / "metadata" / "policy_page_watch_status.csv")
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
        "world_bank_rows_fetched": int(len(fresh)), "policy_pages_successful": int((policy_df["status"] == "SUCCESS").sum()) if not policy_df.empty else 0,
        "policy_pages_failed": int((policy_df["status"] == "FAILED").sum()) if not policy_df.empty else 0,
        "ranking_recomputed": False, "forecast_issued": False,
        "note": "This is a source refresh, not model calibration. Failed sources preserve the prior canonical data; a new ranking requires a separate validated run."}
    out_dir = ROOT / "metadata" / "refresh_runs"; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if args.offline_audit or summary["world_bank_indicators_successful"] > 0 or policy_df.get("status", pd.Series(dtype=str)).eq("SUCCESS").any() else 2

if __name__ == "__main__":
    raise SystemExit(main())
