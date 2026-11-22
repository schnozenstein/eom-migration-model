"""Fetch a comparable public macro panel from the World Bank Indicators API."""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
DESTINATIONS = ROOT / "data" / "destinations.csv"
OUT = ROOT / "data" / "raw" / "world_bank_macro_focus.csv"
INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "GDP per capita, PPP (constant 2021 international $)",
    "NY.GDP.MKTP.PP.CD": "GDP, PPP (current international $)",
    "PA.NUS.PPP": "PPP conversion factor, GDP (LCU per international $)",
    "PA.NUS.PRVT.PP": "PPP conversion factor, household/private consumption (LCU per international $)",
    "PA.NUS.PRVT.PLI": "Price level index (households and NPISHs final consumption expenditure; US=100)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force, ILO modeled estimate)",
    "GOV_WGI_RQ_EST": "Regulatory quality governance estimate (Worldwide Governance Indicators 2026 revision)",
    "GOV_WGI_GE_EST": "Government effectiveness governance estimate (Worldwide Governance Indicators 2026 revision)",
    "GOV_WGI_PV_EST": "Political stability governance estimate (Worldwide Governance Indicators 2026 revision)",
    "SP.POP.TOTL": "Population, total",
    "SM.POP.NETM": "Net migration",
}
BASE_URL = "https://api.worldbank.org/v2"
COUNTRY_CHUNK_SIZE = 12


DNS_ERROR_MARKERS = (
    "temporary failure in name resolution",
    "name or service not known",
    "getaddrinfo failed",
    "failed to resolve",
    "nodename nor servname",
    "name resolution",
)


def build_http_session() -> requests.Session:
    """Retry transient HTTP status/read failures; DNS is retried explicitly below."""
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=0,
        read=4,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "EOM-Research-ETL/2.2 (+reproducible academic research)"})
    return session


def get_with_dns_retries(
    session: requests.Session,
    url: str,
    *,
    attempts: int = 4,
    base_delay: float = 1.0,
    **kwargs,
):
    """Retry only transient DNS resolution failures with bounded exponential backoff."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last_error = None
    for attempt in range(attempts):
        try:
            return session.get(url, **kwargs)
        except (socket.gaierror, requests.exceptions.ConnectionError) as exc:
            message = str(exc).lower()
            is_dns_error = isinstance(exc, socket.gaierror) or any(
                marker in message for marker in DNS_ERROR_MARKERS
            )
            if not is_dns_error:
                raise
            last_error = exc
            if attempt + 1 < attempts:
                delay = min(base_delay * (2**attempt), 8.0) + random.uniform(0.0, 0.25)
                print(
                    f"Transient DNS failure for {url} "
                    f"(attempt {attempt + 1}/{attempts}); retrying in {delay:.2f}s"
                )
                time.sleep(delay)
    raise requests.exceptions.ConnectionError(
        f"DNS resolution failed for {url} after {attempts} attempts: {last_error}"
    ) from last_error


def fetch_indicator(
    codes: str,
    indicator: str,
    start: int,
    end: int,
    timeout: int = 90,
    session: requests.Session | None = None,
    country_chunk_size: int = COUNTRY_CHUNK_SIZE,
) -> list[dict]:
    """Fetch an indicator in smaller country batches to avoid slow oversized API responses."""
    code_list = sorted({code.strip() for code in codes.split(";") if code.strip()})
    if not code_list:
        raise ValueError("At least one World Bank country code is required")
    if country_chunk_size < 1:
        raise ValueError("country_chunk_size must be >= 1")

    chunks = [
        code_list[index:index + country_chunk_size]
        for index in range(0, len(code_list), country_chunk_size)
    ]
    all_rows: list[dict] = []
    owns_session = session is None
    http = session if session is not None else build_http_session()
    try:
        for chunk_number, country_chunk in enumerate(chunks, start=1):
            codes_path = ";".join(country_chunk)
            url = f"{BASE_URL}/country/{codes_path}/indicator/{indicator}"
            params = {"date": f"{start}:{end}", "format": "json", "per_page": 20000}
            page = 1
            while True:
                params["page"] = page
                response = get_with_dns_retries(http, url, params=params, timeout=timeout)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
                    raise ValueError(f"Unexpected API response for {indicator}: {payload!r}")
                metadata, observations = payload[0], payload[1]
                observations = observations or []
                if not isinstance(observations, list):
                    raise ValueError(
                        f"Unexpected observations payload for {indicator}: {type(observations).__name__}"
                    )
                for item in observations:
                    country = item.get("country") or {}
                    indicator_meta = item.get("indicator") or {}
                    all_rows.append({
                        "country_code": (item.get("countryiso3code") or "").upper(),
                        "country_name_api": country.get("value"),
                        "indicator_code": indicator_meta.get("id", indicator),
                        "indicator_name_api": indicator_meta.get("value") or INDICATORS[indicator],
                        "year": int(item["date"]) if item.get("date") else None,
                        "value": item.get("value"),
                        "source": "World Bank Indicators API",
                        "source_url": response.url,
                        "retrieved_utc": pd.Timestamp.now(tz="UTC").isoformat(),
                    })
                total_pages = int(metadata.get("pages", 1) or 1)
                if page >= total_pages:
                    break
                page += 1
                time.sleep(0.15)
            if chunk_number < len(chunks):
                time.sleep(0.15)
        return all_rows
    finally:
        if owns_session:
            http.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2010)
    parser.add_argument("--end", type=int, default=datetime.now(timezone.utc).year)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must be <= --end")

    destinations = pd.read_csv(DESTINATIONS, dtype=str).fillna("")
    codes = sorted({c for c in destinations.loc[destinations["primary_choice_set"] == "global_country", "wb_country_code"].tolist() if c})
    codes_path = ";".join(codes)
    all_rows: list[dict] = []
    retrieved_at = pd.Timestamp.now(tz="UTC").isoformat()
    audit_path = ROOT / "metadata" / "scoring_input_audit.json"
    try:
        with build_http_session() as session:
            for indicator in INDICATORS:
                print(f"Fetching {indicator} ({INDICATORS[indicator]})...")
                all_rows.extend(
                    fetch_indicator(codes_path, indicator, args.start, args.end, session=session)
                )
    except Exception as exc:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps({
            "source_id": "WDI_MACRO_FOCUS_SCORING_INPUT",
            "publisher": "World Bank",
            "source_type": "numeric_api",
            "status": "FAILED",
            "retrieved_at_utc": retrieved_at,
            "publication_release_date": "not exposed by the Indicators API response",
            "observation_period_start": args.start,
            "observation_period_end_requested": args.end,
            "definition": "Destination-only 11-indicator macro scoring input; indicator definitions remain source-specific.",
            "unit": "indicator-specific; see official World Bank indicator metadata",
            "geography_scope": f"{len(codes)} registered global-country destinations",
            "rows_fetched": len(all_rows),
            "numeric_rows": sum(row.get("value") is not None for row in all_rows),
            "missing_values": sum(row.get("value") is None for row in all_rows),
            "exact_urls": sorted({row.get("source_url", "") for row in all_rows if row.get("source_url")}),
            "error": f"{type(exc).__name__}: {exc}",
            "counted_in_numeric_totals": False,
            "note": "Separate scoring-panel fetch failed; previous normalized scoring input was not overwritten."
        }, indent=2), encoding="utf-8")
        raise
    df = pd.DataFrame(all_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    numeric = pd.to_numeric(df.get("value", pd.Series(dtype=float)), errors="coerce")
    years = pd.to_numeric(df.get("year", pd.Series(dtype=float)), errors="coerce")
    audit = {
        "source_id": "WDI_MACRO_FOCUS_SCORING_INPUT",
        "publisher": "World Bank",
        "source_type": "numeric_api",
        "status": "SUCCESS",
        "retrieved_at_utc": retrieved_at,
        "publication_release_date": "not exposed by the Indicators API response",
        "observation_period_start": args.start,
        "observation_period_end_requested": args.end,
        "observation_period_end_observed": int(years.max()) if years.notna().any() else None,
        "definition": "Destination-only 11-indicator macro scoring input; indicator definitions remain source-specific.",
        "unit": "indicator-specific; see official World Bank indicator metadata",
        "geography_scope": f"{df['country_code'].nunique() if not df.empty else 0} registered global-country destinations",
        "destination_codes": sorted(df["country_code"].dropna().astype(str).unique().tolist()) if not df.empty else [],
        "indicators": sorted(df["indicator_code"].dropna().astype(str).unique().tolist()) if not df.empty else [],
        "rows_fetched": int(len(df)),
        "numeric_rows": int(numeric.notna().sum()),
        "missing_values": int(numeric.isna().sum()),
        "missingness_pct": round(float(numeric.isna().mean() * 100), 4) if len(df) else None,
        "duplicate_natural_keys": int(df.duplicated(["country_code", "indicator_code", "year"]).sum()) if not df.empty else 0,
        "exact_urls": sorted(df["source_url"].dropna().astype(str).unique().tolist()) if not df.empty else [],
        "normalized_output_path": str(args.out.relative_to(ROOT)),
        "normalized_output_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
        "counted_in_numeric_totals": False,
        "note": "This focus extract is a duplicate scoring view of WDI; it is audited separately and excluded from source-row totals to prevent double counting."
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Saved {len(df):,} observations to {args.out}")
    print("Note: empty values are preserved as missing; no cross-country imputation was applied.")


if __name__ == "__main__":
    main()
