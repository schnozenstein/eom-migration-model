"""Fetch a comparable public macro panel from the World Bank Indicators API."""
from __future__ import annotations
import argparse
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
OUT = ROOT / "data" / "raw" / "world_bank_long.csv"
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
        total=3,
        connect=0,
        read=2,
        status=3,
        backoff_factor=0.5,
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
    timeout: int = 40,
    session: requests.Session | None = None,
) -> list[dict]:
    url = f"{BASE_URL}/country/{codes}/indicator/{indicator}"
    params = {"date": f"{start}:{end}", "format": "json", "per_page": 20000}
    all_rows: list[dict] = []
    owns_session = session is None
    http = session if session is not None else build_http_session()
    page = 1
    try:
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
                raise ValueError(f"Unexpected observations payload for {indicator}: {type(observations).__name__}")
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
                    "retrieved_utc": pd.Timestamp.utcnow().isoformat(),
                })
            total_pages = int(metadata.get("pages", 1) or 1)
            if page >= total_pages:
                break
            page += 1
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
    with build_http_session() as session:
        for indicator in INDICATORS:
            print(f"Fetching {indicator} ({INDICATORS[indicator]})...")
            all_rows.extend(
                fetch_indicator(codes_path, indicator, args.start, args.end, session=session)
            )
    df = pd.DataFrame(all_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df):,} observations to {args.out}")
    print("Note: empty values are preserved as missing; no cross-country imputation was applied.")


if __name__ == "__main__":
    main()
