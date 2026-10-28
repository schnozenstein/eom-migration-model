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
from eom_empirical.eurostat_api import fetch_eurostat_total_flows_all_geographies, merge_eurostat_history
from eom_empirical.research_datasets import (
    ILOSTAT_MIGRATION_INDICATORS,
    fetch_ilostat_migration_focus,
    fetch_oecd_migration_slice,
    fetch_undesa_migrant_stock,
    fetch_unhcr_focus,
)

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
    "SE.TER.ENRR": "School enrollment, tertiary (% gross)",
    "SE.SEC.ENRR": "School enrollment, secondary (% gross)",
    "SE.XPD.TOTL.GD.ZS": "Government expenditure on education, total (% of GDP)",
    "IT.NET.USER.ZS": "Individuals using the Internet (% of population)",
    "SI.POV.GINI": "Gini index",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total population)",
    "SP.POP.GROW": "Population growth (annual %)",
    "SP.DYN.TFRT.IN": "Fertility rate, total (births per woman)",
    "SP.DYN.IMRT.IN": "Mortality rate, infant (per 1,000 live births)",
    "SP.DYN.LE00.FE.IN": "Life expectancy at birth, female (years)",
    "SP.DYN.LE00.MA.IN": "Life expectancy at birth, male (years)",
    "SH.XPD.CHEX.GD.ZS": "Current health expenditure (% of GDP)",
    "SL.UEM.1524.ZS": "Unemployment, youth total (% of total labor force ages 15-24)",
    "SL.TLF.CACT.FE.ZS": "Labor force participation rate, female (% of female population ages 15+)",
    "SL.TLF.CACT.MA.ZS": "Labor force participation rate, male (% of male population ages 15+)",
    "BX.KLT.DINV.WD.GD.ZS": "Foreign direct investment, net inflows (% of GDP)",
    "NE.TRD.GNFS.ZS": "Trade (% of GDP)",
    "NY.GDP.TOTL.RT.ZS": "Total natural resources rents (% of GDP)",
    "GC.DOD.TOTL.GD.ZS": "Central government debt, total (% of GDP)",
    "SP.DYN.CBRT.IN": "Birth rate, crude (per 1,000 people)",
    "SP.DYN.CDRT.IN": "Death rate, crude (per 1,000 people)",
}
POLICY_URLS = [
    ("Canada", "IRCC Express Entry news", "https://www.canada.ca/en/immigration-refugees-citizenship/news.html"),
    ("United Kingdom", "UK immigration policy news", "https://www.gov.uk/government/organisations/uk-visas-and-immigration"),
    ("Australia", "Department of Home Affairs immigration news", "https://immi.homeaffairs.gov.au/news-media/archive"),
    ("New Zealand", "Immigration New Zealand news", "https://www.immigration.govt.nz/about-us/news-centre/"),
    ("Ireland", "Employment permits current processing dates", "https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/current-application-processing-dates/"),
    ("Singapore", "Ministry of Manpower work passes", "https://www.mom.gov.sg/passes-and-permits"),
    ("Hong Kong", "Immigration Department press releases", "https://www.immd.gov.hk/eng/press/press_releases.html"),
    ("Japan", "Immigration Services Agency", "https://www.moj.go.jp/isa/"),
    ("Switzerland", "State Secretariat for Migration latest news", "https://www.sem.admin.ch/sem/en/home/sem/aktuell.html"),
    ("Austria", "Austrian Federal Government migration portal", "https://www.migration.gv.at/en/welcome/"),
    ("Spain", "Ministry of Inclusion, Social Security and Migration news", "https://www.inclusion.gob.es/es/web/guest/comunicacion/noticias"),
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


def atomic_csv(df, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    compression = "gzip" if path.suffix == ".gz" else None
    df.to_csv(tmp, index=False, compression=compression)
    tmp.replace(path)


def stable_wdi_country_key(country_iso3, source_geo_id, region_id=None, country_name=None):
    """Return a stable key for WDI country and aggregate entities."""
    iso3 = str(country_iso3 or "").strip().upper()
    source_id = str(source_geo_id or "").strip().upper()
    region = str(region_id or "").strip().upper()
    if len(iso3) == 3:
        return iso3, ("WDI_AGGREGATE_CODE" if region == "NA" else "ISO3")
    if source_id:
        return f"WB_{source_id}", "WB_SOURCE_ID"
    name = str(country_name or "unknown").strip().upper()
    slug = re.sub(r"[^A-Z0-9]+", "_", name).strip("_") or "UNKNOWN"
    return f"WB_NAME_{slug}", "WB_SOURCE_NAME"


_WDI_LEGACY_AGGREGATE_IDS = {
    "high income": "XD",
    "low income": "XM",
    "lower middle income": "XN",
    "not classified": "XY",
    "upper middle income": "XT",
}
_WDI_HISTORY_KEYS = ["country_code", "indicator_code", "year"]


def _normalise_wdi_history_geo_keys(frame):
    df = frame.copy()
    required = [
        "country_code", "country_code_type", "source_geo_id", "country_name_api",
        "country_region_id", "country_region_name", "income_level_id", "income_level_name",
        "lending_type_id", "lending_type_name", "indicator_code", "indicator_api_code",
        "indicator_name_api", "year", "value", "source", "source_url", "retrieved_utc",
        "run_id", "status", "api_lastupdated",
    ]
    for column in required:
        if column not in df.columns:
            df[column] = pd.Series(dtype="object") if df.empty else pd.NA
    if df.empty:
        return df, 0
    codes = df["country_code"].fillna("").astype(str).str.strip()
    blank = codes.eq("")
    repaired = int(blank.sum())
    for idx in df.index[blank]:
        name_value = df.at[idx, "country_name_api"]
        name = "" if pd.isna(name_value) else str(name_value).strip()
        source_value = df.at[idx, "source_geo_id"]
        source_id = "" if pd.isna(source_value) else str(source_value).strip().upper()
        if not source_id:
            source_id = _WDI_LEGACY_AGGREGATE_IDS.get(name.lower(), "")
        if source_id:
            df.at[idx, "country_code"] = f"WB_{source_id}"
            df.at[idx, "source_geo_id"] = source_id
            df.at[idx, "country_code_type"] = "WB_SOURCE_ID"
        else:
            slug = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_") or "UNKNOWN"
            df.at[idx, "country_code"] = f"WB_NAME_{slug}"
            df.at[idx, "country_code_type"] = "WB_SOURCE_NAME"
    codes = df["country_code"].fillna("").astype(str).str.strip().str.upper()
    df["country_code"] = codes
    types = df["country_code_type"].fillna("").astype(str).str.strip()
    missing_type = types.eq("")
    df.loc[missing_type & codes.str.startswith("WB_"), "country_code_type"] = "WB_SOURCE_ID"
    df.loc[missing_type & ~codes.str.startswith("WB_"), "country_code_type"] = "LEGACY_CODE_UNCLASSIFIED"
    missing_source_id = df["source_geo_id"].isna() | df["source_geo_id"].fillna("").astype(str).str.strip().eq("")
    wb_mask = codes.str.startswith("WB_")
    df.loc[missing_source_id & wb_mask, "source_geo_id"] = codes[missing_source_id & wb_mask].str.replace("WB_", "", regex=False)
    return df, repaired


def _wdi_signature_series(frame):
    def format_value(value):
        if pd.isna(value):
            return "<NA>"
        try:
            return format(float(value), ".15g")
        except (TypeError, ValueError):
            return str(value)
    signature = frame["value"].map(format_value).astype(str)
    for column in ["status", "indicator_name_api", "country_name_api"]:
        signature = signature + "|" + frame[column].fillna("").astype(str)
    return signature


def compact_wdi_history(history, fresh):
    """Keep the first WDI observation per natural key and only later real revisions."""
    history_norm, repaired_history = _normalise_wdi_history_geo_keys(history)
    fresh_norm, repaired_fresh = _normalise_wdi_history_geo_keys(fresh)
    keys = list(_WDI_HISTORY_KEYS)
    version_keys = ["run_id", *keys]
    fresh_duplicates = int(fresh_norm.duplicated(version_keys).sum()) if not fresh_norm.empty else 0
    if fresh_duplicates:
        raise ValueError(f"World Bank fresh panel has {fresh_duplicates} duplicate run/natural-key rows: {version_keys}")
    if not fresh_norm.empty and fresh_norm[keys].isna().any().any():
        raise ValueError("World Bank fresh panel contains missing natural-key fields")
    if not history_norm.empty and history_norm[keys].isna().any().any():
        raise ValueError("World Bank history contains missing natural-key fields")

    def latest_rows(frame):
        if frame.empty:
            return frame.copy()
        temp = frame.copy()
        temp["_sort_time"] = pd.to_datetime(temp["retrieved_utc"], errors="coerce", utc=True)
        temp = temp.sort_values(["_sort_time", "run_id"], kind="mergesort")
        return temp.drop_duplicates(keys, keep="last").drop(columns=["_sort_time"])

    old_latest = latest_rows(history_norm)
    old_index = pd.MultiIndex.from_frame(old_latest[keys]) if not old_latest.empty else pd.MultiIndex.from_arrays([[], [], []], names=keys)
    fresh_unique = fresh_norm.drop_duplicates(keys)
    fresh_index = pd.MultiIndex.from_frame(fresh_unique[keys]) if not fresh_unique.empty else pd.MultiIndex.from_arrays([[], [], []], names=keys)
    new_keys = int(len(fresh_index.difference(old_index)))
    common = fresh_index.intersection(old_index)
    value_revisions = 0
    if len(common):
        old_sig = pd.Series(_wdi_signature_series(old_latest).to_numpy(), index=old_index)
        fresh_sig = pd.Series(_wdi_signature_series(fresh_unique).to_numpy(), index=fresh_index)
        value_revisions = int((old_sig.loc[common] != fresh_sig.loc[common]).sum())
    fresh_run_count = int(fresh_norm["run_id"].nunique()) if not fresh_norm.empty else 0
    unchanged_rows_skipped = max(0, int(len(fresh_norm) - new_keys - value_revisions))
    if history_norm.empty and fresh_run_count > 1:
        unchanged_rows_skipped = 0

    combined = pd.concat([history_norm, fresh_norm], ignore_index=True, sort=False)
    if combined.empty:
        stats = {
            "new_keys": 0, "value_revisions": 0, "unchanged_rows_skipped": 0,
            "legacy_geo_rows_repaired": repaired_history + repaired_fresh,
            "duplicate_keys_in_fresh": fresh_duplicates, "duplicate_version_keys": 0,
            "history_rows_before": int(len(history_norm)), "history_rows_after": 0,
            "unique_observation_keys": 0,
        }
        return combined, stats
    combined["_sort_time"] = pd.to_datetime(combined["retrieved_utc"], errors="coerce", utc=True)
    combined = combined.sort_values(["_sort_time", "run_id"], kind="mergesort")
    combined["_signature"] = _wdi_signature_series(combined)
    duplicate_mask = combined.duplicated(version_keys, keep=False)
    duplicate_version_keys = 0
    if duplicate_mask.any():
        duplicate_groups = combined.loc[duplicate_mask].groupby(version_keys, dropna=False)["_signature"].nunique()
        conflicting = duplicate_groups[duplicate_groups > 1]
        if len(conflicting):
            raise ValueError(f"World Bank history has conflicting values for {len(conflicting)} duplicate run/natural-key groups")
        duplicate_version_keys = int(len(duplicate_groups))
        combined = combined.drop_duplicates(version_keys, keep="last")
    previous_signature = combined.groupby(keys, dropna=False)["_signature"].shift()
    keep = previous_signature.isna() | combined["_signature"].ne(previous_signature)
    compact = combined.loc[keep].drop(columns=["_sort_time", "_signature"]).copy()
    compact = compact.sort_values(keys + ["retrieved_utc", "run_id"], kind="mergesort").reset_index(drop=True)
    after_duplicates = int(compact.duplicated(version_keys).sum())
    if after_duplicates:
        raise ValueError(f"Compacted World Bank history has {after_duplicates} duplicate run/natural-key rows")
    stats = {
        "new_keys": new_keys,
        "value_revisions": value_revisions,
        "unchanged_rows_skipped": unchanged_rows_skipped,
        "legacy_geo_rows_repaired": repaired_history + repaired_fresh,
        "duplicate_keys_in_fresh": fresh_duplicates,
        "duplicate_version_keys": duplicate_version_keys,
        "history_rows_before": int(len(history_norm)),
        "history_rows_after": int(len(compact)),
        "unique_observation_keys": int(compact[keys].drop_duplicates().shape[0]),
    }
    return compact, stats


def fetch_one_indicator(code: str, label: str, run_id: str, start: int, end: int) -> tuple[list[dict], dict]:
    session = session_with_retries()
    rows, statuses = [], []
    request_urls, request_attempts = [], []
    per_page_used = None
    snapshot_dir = ROOT / "data" / "raw" / "snapshots" / "world_bank" / run_id
    api_code = WB_API_CODE_OVERRIDES.get(code, code)
    url = f"{WB_BASE}/country/all/indicator/{api_code}"
    page, pages, count, per_page = 1, 1, 0, 20000
    try:
        while page <= pages:
            last_error = None
            parsed = None
            for candidate_per_page in dict.fromkeys([per_page, 1000]):
                params = {"date": f"{start}:{end}", "format": "json", "per_page": candidate_per_page, "page": page}
                request_url = requests.Request("GET", url, params=params).prepare().url
                attempt = {"url": request_url, "per_page": candidate_per_page, "page": page, "status": "ATTEMPTED", "http_status": None, "error": ""}
                request_attempts.append(attempt)
                per_page_used = candidate_per_page
                try:
                    r = request_with_dns_retries(session, url, params=params, timeout=(8, 30))
                    attempt["url"] = r.url
                    attempt["http_status"] = r.status_code
                    r.raise_for_status()
                    payload = r.json()
                    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict) or not (payload[1] is None or isinstance(payload[1], list)):
                        preview = (r.text or "").replace("\n", " ")[:400]
                        raise ValueError(f"Unexpected World Bank API response for {code}: HTTP {r.status_code}, content-type={r.headers.get('Content-Type')}, payload_type={type(payload).__name__}, body_preview={preview!r}")
                    attempt["status"] = "SUCCESS"
                    request_urls.append(r.url)
                    parsed = (r, payload, payload[0], payload[1] or [], candidate_per_page)
                    break
                except Exception as exc:
                    attempt["status"] = "FAILED"
                    attempt["error"] = f"{type(exc).__name__}: {exc}"
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
                region = c.get("region") or {}
                income = c.get("incomeLevel") or {}
                lending = c.get("lendingType") or {}
                source_geo_id = str(c.get("id") or "").strip().upper()
                country_code, country_code_type = stable_wdi_country_key(item.get("countryiso3code"), source_geo_id, region.get("id"), c.get("value"))
                rows.append({
                    "country_code": country_code, "country_code_type": country_code_type,
                    "source_geo_id": source_geo_id, "country_name_api": c.get("value"),
                    "country_region_id": region.get("id"), "country_region_name": region.get("value"),
                    "income_level_id": income.get("id"), "income_level_name": income.get("value"),
                    "lending_type_id": lending.get("id"), "lending_type_name": lending.get("value"),
                    "indicator_code": code, "indicator_api_code": im.get("id", api_code),
                    "indicator_name_api": im.get("value") or label, "year": int(year),
                    "value": item.get("value"), "source": "World Bank Indicators API", "source_url": r.url,
                    "retrieved_utc": utc_now().isoformat(), "run_id": run_id,
                    "status": "observed" if item.get("value") is not None else "missing",
                    "api_lastupdated": str(meta.get("lastupdated", "")),
                })
            count += len(observations); pages = int(meta.get("pages", 1) or 1); page += 1
        status = {"source_id": f"WDI_{code}", "source": "World Bank Indicators API", "url": request_urls[0] if request_urls else (request_attempts[-1]["url"] if request_attempts else url),
            "url_base": url, "request_urls": json.dumps(request_urls), "request_attempts": json.dumps(request_attempts, ensure_ascii=False),
            "pages_fetched": len(request_urls), "per_page_used": per_page_used, "snapshot_dir": str(snapshot_dir.relative_to(ROOT)), "status": "SUCCESS",
            "rows_fetched": count, "indicator": code, "observation_start": start, "observation_end_requested": end, "error": ""}
    except Exception as e:
        status = {"source_id": f"WDI_{code}", "source": "World Bank Indicators API", "url": request_urls[0] if request_urls else (request_attempts[-1]["url"] if request_attempts else url),
            "url_base": url, "request_urls": json.dumps(request_urls), "request_attempts": json.dumps(request_attempts, ensure_ascii=False),
            "pages_fetched": len(request_urls), "per_page_used": per_page_used, "snapshot_dir": str(snapshot_dir.relative_to(ROOT)), "status": "FAILED",
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
        "changed_since_previous_check": "unknown",
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
        state_path = ROOT / "data" / "obmigra_page_state.json"
        try:
            previous_state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_state = {}
        previous_hash = (previous_state.get(OBMIGRA_URL) or {}).get("content_sha256", "")
        changed = "first_seen" if not previous_hash else str(previous_hash != digest).lower()
        previous_state[OBMIGRA_URL] = {
            "content_sha256": digest,
            "last_checked_utc": row["checked_at_utc"],
            "final_url": response.url,
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(previous_state, indent=2), encoding="utf-8")
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
            "changed_since_previous_check": changed,
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
        # An omitted sparse JSON-stat cell is different from an explicit suppressed
        # value. Leave the panel unchanged when Eurostat did not return the year.
        cell_present = item.get("source_cell_present", True)
        if cell_present is False or str(cell_present).strip().lower() == "false":
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
        eurostat_status = [{"source_id": f"EUROSTAT_{dataset}", "source": "Eurostat Statistics API", "dataset": dataset, "url": f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}", "status": "SKIPPED_OFFLINE", "rows_fetched": 0, "observed_rows": 0, "geographies_fetched": 0, "observation_start": args.start_year, "observation_end_requested": args.end_year, "error": "Offline audit requested; no network call made"} for _indicator, dataset in (("emigration_total", "migr_emi2"), ("immigration_total", "migr_imm8"))]
        obmigra = {"source_id": "BRAZIL_OBMIGRA_CATALOG", "source": "Brazil OBMigra consolidated migration statistics", "url": OBMIGRA_URL, "checked_at_utc": utc_now().isoformat(), "status": "SKIPPED_OFFLINE", "http_status": None, "content_sha256": "", "linked_data_assets": "", "linked_data_asset_count": 0, "error": "Offline audit requested; no network call made", "numeric_data_ingested": False}
        unhcr_data = pd.DataFrame()
        unhcr_status = {"source_id": "UNHCR_POPSTATS_OFFICIAL", "source": "UNHCR PopStatsOfficial", "url": "https://api-data.unhcr.org/api/v0/data/export/PopStatsOfficial", "checked_at_utc": utc_now().isoformat(), "status": "SKIPPED_OFFLINE", "source_rows": 0, "focus_rows": 0, "error": "Offline audit requested; no network call made", "output_path": "data/raw/unhcr_forced_displacement_focus.csv"}
        undesa_data = pd.DataFrame()
        undesa_status = [{"source_id": f"UN_DESA_IMS_2024_{direction.upper()}", "source": "UN DESA Population Division", "dataset": f"International Migrant Stock 2024 — {direction}", "url": "", "checked_at_utc": utc_now().isoformat(), "status": "SKIPPED_OFFLINE", "rows_fetched": 0, "countries_fetched": 0, "error": "Offline audit requested; no network call made", "output_path": "data/raw/undesa_migrant_stock_long.csv"} for direction in ("destination", "origin", "bilateral")]
        oecd_data = pd.DataFrame()
        oecd_status = {"source_id": "OECD_DF_MIG_B11", "source": "OECD International migration database (SDMX)", "url": "https://sdmx.oecd.org/public/rest/data/OECD.ELS.IMD,DSD_MIG@DF_MIG,1.0/.W.A.B11._T...", "checked_at_utc": utc_now().isoformat(), "status": "SKIPPED_OFFLINE", "rows_fetched": 0, "rows_focus": 0, "error": "Offline audit requested; no network call made", "output_path": "data/raw/oecd_migration_database_focus.csv"}
        ilostat_data = pd.DataFrame()
        ilostat_status = [{"source_id": f"ILOSTAT_{code}", "source": "International Labour Organization (ILOSTAT)", "indicator_code": code, "indicator_label_expected": label, "url": "https://rplumber.ilo.org/data/indicator/", "checked_at_utc": utc_now().isoformat(), "status": "SKIPPED_OFFLINE", "rows_fetched": 0, "rows_focus": 0, "geographies": 0, "error": "Offline audit requested; no network call made", "output_path": "data/raw/ilostat_migrant_labour_focus.csv"} for code, label in ILOSTAT_MIGRATION_INDICATORS.items()]
        policy = []
    else:
        fresh, statuses = fetch_world_bank(session, run_id, args.start_year, args.end_year)
        eurostat_rows, eurostat_status = fetch_eurostat_total_flows_all_geographies(
            session,
            run_id=run_id,
            start_year=args.start_year,
            end_year=args.end_year,
            snapshot_dir=ROOT / "data" / "raw" / "snapshots" / "eurostat" / run_id,
        )
        unhcr_data, unhcr_status = fetch_unhcr_focus(session, ROOT, run_id)
        undesa_data, undesa_status = fetch_undesa_migrant_stock(session, ROOT, run_id)
        oecd_data, oecd_status = fetch_oecd_migration_slice(
            session, ROOT, run_id, args.start_year, args.end_year
        )
        ilostat_data, ilostat_status = fetch_ilostat_migration_focus(
            session, ROOT, run_id, args.start_year, args.end_year
        )
        obmigra = check_obmigra_source(session, run_id)
        policy = [] if args.skip_policy_watch else check_policy_sources(session, run_id)
    raw_path = ROOT / "data" / "raw" / "world_bank_long.csv"
    history_path = ROOT / "data" / "observations_history" / "world_bank_observations.csv.gz"
    legacy_history_path = ROOT / "data" / "observations_history" / "world_bank_observations.csv"
    if history_path.exists():
        history = pd.read_csv(history_path, compression="gzip", low_memory=False)
    elif legacy_history_path.exists():
        history = pd.read_csv(legacy_history_path, low_memory=False)
    else:
        history = pd.DataFrame()
    history, history_stats = compact_wdi_history(history, fresh)
    atomic_csv(history, history_path)
    if legacy_history_path.exists():
        legacy_history_path.unlink()

    # Current normalized panel: latest known values for failed indicators and current
    # successful rows for refreshed indicators. Macro scoring uses a separate input file.
    if history.empty and fresh.empty:
        raise RuntimeError("No current or historical World Bank observations available; refusing to write an empty panel.")
    keys = ["country_code", "indicator_code", "year"]
    if history.empty:
        latest_history = pd.DataFrame(columns=fresh.columns)
    else:
        latest_history = history.copy()
        latest_history["_sort_time"] = pd.to_datetime(latest_history["retrieved_utc"], errors="coerce", utc=True)
        latest_history = latest_history.sort_values(["_sort_time", "run_id"], kind="mergesort")
        latest_history = latest_history.drop_duplicates(keys, keep="last").drop(columns=["_sort_time"])
    canonical = pd.concat([latest_history, fresh], ignore_index=True, sort=False)
    if not canonical.empty:
        canonical["_sort_time"] = pd.to_datetime(canonical["retrieved_utc"], errors="coerce", utc=True)
        canonical = canonical.sort_values(["_sort_time", "run_id"], kind="mergesort")
        canonical = canonical.drop_duplicates(keys, keep="last").drop(columns=["_sort_time"])
        duplicate_panel_keys = int(canonical.duplicated(keys).sum())
        if duplicate_panel_keys:
            raise ValueError(f"Canonical World Bank panel has {duplicate_panel_keys} duplicate natural keys.")
    raw_path = ROOT / "data" / "raw" / "world_bank_long.csv"
    atomic_csv(canonical, raw_path)
    brazil_macro_rows = update_brazil_macro_extract(fresh)
    status_df = pd.DataFrame(statuses)
    policy_df = pd.DataFrame(policy)
    eurostat_status_df = pd.DataFrame(eurostat_status)
    obmigra_df = pd.DataFrame([obmigra])
    unhcr_status_df = pd.DataFrame([unhcr_status])
    undesa_status_df = pd.DataFrame(undesa_status)
    oecd_status_df = pd.DataFrame([oecd_status])
    ilostat_status_df = pd.DataFrame(ilostat_status)
    atomic_csv(status_df, ROOT / "metadata" / "live_source_status.csv")
    atomic_csv(eurostat_status_df, ROOT / "metadata" / "eurostat_source_status.csv")
    atomic_csv(obmigra_df, ROOT / "metadata" / "obmigra_source_status.csv")
    atomic_csv(unhcr_status_df, ROOT / "metadata" / "unhcr_source_status.csv")
    atomic_csv(undesa_status_df, ROOT / "metadata" / "undesa_source_status.csv")
    atomic_csv(oecd_status_df, ROOT / "metadata" / "oecd_source_status.csv")
    atomic_csv(ilostat_status_df, ROOT / "metadata" / "ilostat_source_status.csv")
    if policy:
        atomic_csv(policy_df, ROOT / "metadata" / "policy_page_watch_status.csv")

    if eurostat_rows:
        eurostat_path = ROOT / "data" / "raw" / "eurostat_migration_flows.csv"
        existing_eurostat = pd.read_csv(eurostat_path) if eurostat_path.exists() else pd.DataFrame()
        combined_eurostat = merge_eurostat_history(existing_eurostat, eurostat_rows)
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
    rebuild_manifest_path = ROOT / "metadata" / "wdi_history_rebuild_manifest.json"
    try:
        rebuild_manifest = json.loads(rebuild_manifest_path.read_text(encoding="utf-8"))
    except Exception:
        rebuild_manifest = {}
    github_run_id = str(os.environ.get("GITHUB_RUN_ID", ""))
    rebuilt_this_run = bool(github_run_id) and str(rebuild_manifest.get("rebuild_workflow_run_id", "")) == github_run_id
    summary = {"run_id": run_id, "run_at_utc": run_dt.isoformat(), "requested_year_range": [args.start_year, args.end_year], "github_workflow_run_id": str(os.environ.get("GITHUB_RUN_ID", "")),
        "world_bank_indicators_successful": int((status_df["status"] == "SUCCESS").sum()) if not status_df.empty else 0,
        "world_bank_indicators_failed": int((status_df["status"] == "FAILED").sum()) if not status_df.empty else 0,
        "offline_audit": bool(args.offline_audit),
        "world_bank_rows_fetched": int(len(fresh)),
        "world_bank_rows_normalized": int(len(canonical)),
        "world_bank_rows_without_iso3": int(fresh["country_code_type"].eq("WB_SOURCE_ID").sum()) if "country_code_type" in fresh.columns else 0,
        "world_bank_history_rows": int(len(history)),
        "world_bank_history_new_keys": int(history_stats.get("new_keys", 0)),
        "world_bank_history_value_revisions": int(history_stats.get("value_revisions", 0)),
        "world_bank_history_unchanged_rows_skipped": int(history_stats.get("unchanged_rows_skipped", 0)),
        "world_bank_history_legacy_geo_rows_repaired": int(history_stats.get("legacy_geo_rows_repaired", 0)),
        "world_bank_history_duplicate_keys": int(history_stats.get("duplicate_keys_in_fresh", 0) + history_stats.get("duplicate_version_keys", 0)),
        "world_bank_history_storage": "gzip compact revision ledger; unchanged observations not appended; raw snapshots retained per workflow artifact",
        "world_bank_history_rebuilt_from_snapshots": rebuilt_this_run,
        "world_bank_history_rows_restored_from_snapshots": int(rebuild_manifest.get("rows_restored_vs_legacy_history", 0)) if rebuilt_this_run else 0,
        "world_bank_full_panel_path": "data/raw/world_bank_long.csv (current normalized panel; workflow artifact)",
        "world_bank_macro_focus_path": "data/raw/world_bank_macro_focus.csv (separate 11-indicator scoring input)", "brazil_macro_rows_fetched": int(brazil_macro_rows), "policy_pages_successful": int((policy_df["status"] == "SUCCESS").sum()) if not policy_df.empty else 0,
        "policy_pages_failed": int((policy_df["status"] == "FAILED").sum()) if not policy_df.empty else 0,
        "eurostat_series_successful": int((eurostat_status_df["status"] == "SUCCESS").sum()) if not eurostat_status_df.empty else 0,
        "eurostat_series_failed": int((eurostat_status_df["status"] == "FAILED").sum()) if not eurostat_status_df.empty else 0,
        "eurostat_observed_rows": int(eurostat_status_df["observed_rows"].sum()) if not eurostat_status_df.empty else 0,
        "eurostat_geographies_fetched": int(eurostat_status_df["geographies_fetched"].max()) if "geographies_fetched" in eurostat_status_df and not eurostat_status_df.empty else 0,
        "unhcr_source_status": unhcr_status.get("status", "Not reported"),
        "unhcr_source_rows": int(unhcr_status.get("source_rows", 0) or 0),
        "unhcr_focus_rows": int(unhcr_status.get("focus_rows", 0) or 0),
        "undesa_source_successful": int(sum(row.get("status") == "SUCCESS" for row in undesa_status)),
        "undesa_source_failed": int(sum(row.get("status") == "FAILED" for row in undesa_status)),
        "undesa_stock_rows": int(len(undesa_data)),
        "oecd_migration_status": oecd_status.get("status", "Not reported"),
        "oecd_migration_rows": int(oecd_status.get("rows_focus", 0) or 0),
        "ilostat_indicators_successful": int((ilostat_status_df["status"] == "SUCCESS").sum()) if not ilostat_status_df.empty else 0,
        "ilostat_indicators_failed": int((ilostat_status_df["status"] == "FAILED").sum()) if not ilostat_status_df.empty else 0,
        "ilostat_rows_fetched": int(len(ilostat_data)),
        "ilostat_rows_focus": int(ilostat_status_df["rows_focus"].sum()) if "rows_focus" in ilostat_status_df and not ilostat_status_df.empty else 0,
        "obmigra_source_status": obmigra.get("status", "Not reported"),
        "obmigra_numeric_data_ingested": False,
        "ranking_recomputed": False, "forecast_issued": False,
        "note": "This is a source refresh, not model calibration. Eurostat total flows are stored as a distinct all-geography series; UNHCR displacement data, UN DESA migrant stocks, and OECD migration database slices are stored separately from general immigration/emigration flows. OBMigra is source-page monitored only and is not numerically parsed. Failed sources preserve prior successful outputs; a new ranking requires a separate validated run."}
    out_dir = ROOT / "metadata" / "refresh_runs"; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    any_eurostat_success = not eurostat_status_df.empty and eurostat_status_df["status"].eq("SUCCESS").any()
    any_unhcr_success = unhcr_status.get("status") == "SUCCESS"
    any_undesa_success = not undesa_status_df.empty and undesa_status_df["status"].eq("SUCCESS").any()
    any_oecd_success = oecd_status.get("status") == "SUCCESS"
    any_ilostat_success = not ilostat_status_df.empty and ilostat_status_df["status"].eq("SUCCESS").any()
    obmigra_success = obmigra.get("status") == "SUCCESS"
    return 0 if (
        args.offline_audit
        or summary["world_bank_indicators_successful"] > 0
        or policy_df.get("status", pd.Series(dtype=str)).eq("SUCCESS").any()
        or any_eurostat_success
        or any_unhcr_success
        or any_undesa_success
        or any_oecd_success
        or any_ilostat_success
        or obmigra_success
    ) else 2

if __name__ == "__main__":
    raise SystemExit(main())
