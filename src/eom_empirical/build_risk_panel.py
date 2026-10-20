"""Build a source-linked environmental/economic risk panel; never silently publish a partial global rank."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import requests
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DESTINATIONS = ROOT / "data" / "destinations.csv"
OUT = ROOT / "outputs" / "risk_indicator_panel.csv"
AUDIT = ROOT / "outputs" / "risk_coverage_audit.json"
API = "https://api.worldbank.org/v2"
INDICATORS = {
    "EN.ATM.PM25.MC.M3": "annual_pm25_exposure",
    "NY.GDP.MKTP.KD.ZG": "real_gdp_growth_pct",
    "EG.IMP.CONS.ZS": "net_energy_imports_pct_energy_use",
}

def fetch(code_string: str, indicator: str, start: int = 2010, end: int | None = None) -> pd.DataFrame:
    end = end or datetime.now(timezone.utc).year
    url = f"{API}/country/{code_string}/indicator/{indicator}"
    response = requests.get(url, params={"date": f"{start}:{end}", "format": "json", "per_page": 20000}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(f"Unexpected World Bank API response for {indicator}")
    rows = []
    for item in payload[1] or []:
        if item.get("countryiso3code") and item.get("date"):
            rows.append({"country_code": item["countryiso3code"].upper(), "year": int(item["date"]),
                         "indicator": INDICATORS[indicator], "value": item.get("value"),
                         "source": "World Bank Indicators API", "source_url": response.url})
    return pd.DataFrame(rows)

def zscore(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    sd = s.std(ddof=0)
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.nan, index=s.index)
    return (s - s.mean()) / sd

def main() -> None:
    destinations = pd.read_csv(DESTINATIONS, dtype=str).fillna("")
    focus = destinations[destinations["primary_choice_set"] == "global_country"].copy()
    codes = sorted(set(focus["wb_country_code"]) - {""})
    if not codes:
        raise ValueError("No World Bank country codes found in destination registry")
    code_string = ";".join(codes)
    pieces = [fetch(code_string, indicator) for indicator in INDICATORS]
    long = pd.concat(pieces, ignore_index=True)
    wide = long.pivot_table(index=["country_code", "year"], columns="indicator", values="value", aggfunc="first").reset_index()
    wide.columns.name = None
    # Compute GDP growth volatility from a trailing 5-year window, requiring at least 3 observations.
    wide = wide.sort_values(["country_code", "year"])
    if "real_gdp_growth_pct" in wide:
        wide["gdp_growth_volatility_5y"] = wide.groupby("country_code")["real_gdp_growth_pct"].transform(
            lambda s: s.rolling(5, min_periods=3).std(ddof=0))
    else:
        wide["gdp_growth_volatility_5y"] = np.nan
    latest_year = int(wide["year"].max()) if not wide.empty else None
    latest = wide[wide["year"] == latest_year].copy() if latest_year else wide.iloc[0:0].copy()
    # Higher risk means worse: higher PM2.5, greater energy import dependence, and higher growth volatility.
    # Do not treat low/negative net energy imports as risk-free; retain raw value and flag interpretive limits.
    risk_cols = ["annual_pm25_exposure", "net_energy_imports_pct_energy_use", "gdp_growth_volatility_5y"]
    for col in risk_cols:
        if col in latest:
            latest[f"{col}_risk_z"] = zscore(latest[col])
        else:
            latest[f"{col}_risk_z"] = np.nan
    zcols = [f"{c}_risk_z" for c in risk_cols]
    latest["environment_economic_partial_risk_score"] = latest[zcols].mean(axis=1, skipna=False)
    latest["partial_risk_components_present"] = latest[zcols].notna().sum(axis=1)
    latest["risk_score_status"] = np.where(
        latest["partial_risk_components_present"].eq(len(zcols)),
        "partial only: environmental/economic indicators present; geopolitical/social indicators not yet integrated",
        "unscored: incomplete environmental/economic indicators; no imputation"
    )
    out = focus[["destination_id", "destination_name", "wb_country_code"]].merge(
        latest, left_on="wb_country_code", right_on="country_code", how="left")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_source_year": latest_year,
        "destinations_registered": int(len(focus)),
        "destinations_with_latest_year_record": int(out["year"].notna().sum()),
        "destinations_with_all_three_partial_risk_indicators": int(out["risk_score_status"].eq("partial only: environmental/economic indicators present; geopolitical/social indicators not yet integrated").sum()),
        "full_risk_adjusted_ranking_published": False,
        "reason": "This panel covers only environmental/economic proxies. Comparable geopolitical/conflict and social-instability measures are not yet integrated; no adjusted ranking is emitted.",
        "indicators": INDICATORS,
        "source": "World Bank Indicators API",
        "source_data_url": "https://data.worldbank.org/indicator/EN.ATM.PM25.MC.M3",
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))

if __name__ == "__main__":
    main()
