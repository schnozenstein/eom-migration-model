"""Fetch a comparable public macro panel from the World Bank Indicators API."""
from __future__ import annotations
import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DESTINATIONS = ROOT / "data" / "destinations.csv"
OUT = ROOT / "data" / "raw" / "world_bank_long.csv"
INDICATORS = {
    "NY.GDP.PCAP.PP.KD": "GDP per capita, PPP (constant 2021 international $)",
    "NY.GDP.MKTP.PP.CD": "GDP, PPP (current international $)",
    "PA.NUS.PPP": "PPP conversion factor, GDP (LCU per international $)",
    "PA.NUS.PPPC.RF": "Price level ratio of PPP conversion factor (GDP) to market exchange rate",
    "PA.NUS.PRVT.PP": "PPP conversion factor, household/private consumption (LCU per international $)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force, ILO modeled estimate)",
    "RQ.EST": "Regulatory quality estimate",
    "GE.EST": "Government effectiveness estimate",
    "PV.EST": "Political stability and absence of violence/terrorism estimate",
    "SP.POP.TOTL": "Population, total",
    "SM.POP.NETM": "Net migration",
}
BASE_URL = "https://api.worldbank.org/v2"


def fetch_indicator(codes: str, indicator: str, start: int, end: int, timeout: int = 40) -> list[dict]:
    url = f"{BASE_URL}/country/{codes}/indicator/{indicator}"
    params = {"date": f"{start}:{end}", "format": "json", "per_page": 20000}
    all_rows: list[dict] = []
    page = 1
    while True:
        params["page"] = page
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError(f"Unexpected API response for {indicator}: {payload!r}")
        metadata, observations = payload[0], payload[1]
        observations = observations or []
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
    for indicator in INDICATORS:
        print(f"Fetching {indicator} ({INDICATORS[indicator]})...")
        all_rows.extend(fetch_indicator(codes_path, indicator, args.start, args.end))
    df = pd.DataFrame(all_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df):,} observations to {args.out}")
    print("Note: empty values are preserved as missing; no cross-country imputation was applied.")


if __name__ == "__main__":
    main()
