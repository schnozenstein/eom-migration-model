"""Refresh reproducible geopolitical proxies while preserving unknowns.

Sources:
- World Bank Worldwide Governance Indicators 2026 update, Political Stability
  governance estimate (GOV_WGI_PV_EST), 2025 observation. This is a *proxy* for
  conflict exposure, not a direct measure of regional conflict.
- UNCTAD Liner Shipping Connectivity Index (LSCI), 2026. The inverse percentile
  is used as a proxy for strategic isolation; it is not route-dependency data.

Other components remain blank until defensible comparable measures are sourced.
All source provenance is stored per component because sources differ.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import numpy as np
from pathlib import Path
import json
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs" / "latest_macro_eom_ranking.csv"
INPUT = ROOT / "data" / "geopolitical_uncertainty_inputs.csv"
WB_URL = "https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_PV_EST?date=2025&format=json&per_page=1000"
LSCI_URL = "https://www.nationsinquiry.com/datasets/liner-shipping-connectivity/2026/data.csv"
WB_NAME = "World Bank Worldwide Governance Indicators 2026 update, GOV_WGI_PV_EST (2025 observation)"
LSCI_NAME = "UNCTAD Liner Shipping Connectivity Index 2026 (CSV via Nations Inquiry)"
COMPONENTS = {
    "regional_conflict_exposure": {
        "source_name": WB_NAME,
        "source_url": WB_URL,
        "observation_year": 2025,
        "raw_value_definition": "Political Stability - Governance estimate (approximately -2.5 to +2.5); higher is more stable. Used only as a conflict-risk proxy, not direct regional-conflict exposure.",
    },
    "strategic_isolation": {
        "source_name": LSCI_NAME,
        "source_url": LSCI_URL,
        "observation_year": 2026,
        "raw_value_definition": "UNCTAD LSCI score; higher means better liner-shipping connectivity. Inverted percentile is used as an isolation proxy, not a measure of import dependence or military vulnerability.",
    },
}


def quintile_score(values: pd.Series, higher_is_safer: bool) -> pd.Series:
    """Map comparable source values to 1 (lower exposure) ... 5 (higher exposure)."""
    numeric = pd.to_numeric(values, errors="coerce")
    pct = numeric.rank(method="average", pct=True)
    risk_pct = 1 - pct if higher_is_safer else pct
    return risk_pct.mul(5).apply(lambda x: np.floor(x) + 1 if pd.notna(x) else np.nan).clip(1, 5)


def load_world_bank() -> pd.DataFrame:
    response = requests.get(WB_URL, timeout=45)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        raise ValueError(f"Unexpected World Bank JSON object: {str(payload)[:500]}")
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ValueError(f"Unexpected World Bank API response shape: {str(payload)[:500]}")
    if not payload[1]:
        raise ValueError(f"World Bank GOV_WGI_PV_EST returned no rows; metadata={str(payload[0])[:500]}")
    rows = []
    for item in payload[1]:
        code = str(item.get("countryiso3code", "")).upper()
        value = item.get("value")
        if len(code) == 3 and value is not None:
            rows.append({"country_code": code, "raw_value": float(value)})
    frame = pd.DataFrame(rows).drop_duplicates("country_code")
    if frame.empty:
        raise ValueError(f"World Bank GOV_WGI_PV_EST returned no usable ISO3 rows; sample={str(payload[1][:2])}")
    return frame


def load_lsci() -> pd.DataFrame:
    response = requests.get(LSCI_URL, timeout=45)
    response.raise_for_status()
    payload = response.content
    frame = None
    for skip in (12, 11, 0):
        candidate = pd.read_csv(BytesIO(payload), skiprows=skip)
        candidate.columns = [str(c).strip().lower().replace(" ", "_") for c in candidate.columns]
        if {"country_code", "lsci_score"}.issubset(candidate.columns):
            frame = candidate
            break
    if frame is None:
        raise ValueError("LSCI CSV schema changed: expected country_code and lsci_score")
    frame["country_code"] = frame["country_code"].astype(str).str.upper().str.strip()
    frame["raw_value"] = pd.to_numeric(frame["lsci_score"], errors="coerce")
    frame = frame.loc[frame["country_code"].str.len().eq(3)].dropna(subset=["raw_value"])
    frame = frame[["country_code", "raw_value"]].drop_duplicates("country_code")
    if frame.empty:
        raise ValueError("LSCI CSV returned no usable ISO3 rows")
    return frame


def apply_component(
    out: pd.DataFrame,
    component: str,
    source: pd.DataFrame,
    *,
    higher_is_safer: bool,
) -> pd.DataFrame:
    meta = COMPONENTS[component]
    raw_col = f"{component}_raw_value"
    out = out.drop(columns=[raw_col], errors="ignore").merge(
        source.rename(columns={"raw_value": raw_col}), on="country_code", how="left"
    )
    score = quintile_score(out[raw_col], higher_is_safer=higher_is_safer)
    out[component] = score
    assessed = datetime.now(timezone.utc).isoformat()
    out[f"{component}_source_name"] = meta["source_name"]
    out[f"{component}_source_url"] = meta["source_url"]
    out[f"{component}_observation_year"] = meta["observation_year"]
    out[f"{component}_assessed_at_utc"] = assessed
    out[f"{component}_notes"] = (
        "Relative quintile across available source observations; 1=lower exposure proxy, "
        "5=higher exposure proxy. Not an absolute probability or forecast. "
        + meta["raw_value_definition"]
    )
    out[f"{component}_raw_value_definition"] = meta["raw_value_definition"]
    return out


def main() -> None:
    base = pd.read_csv(BASE)
    keys = base[["destination_id", "destination_name", "country_code"]].copy()
    if INPUT.exists():
        old = pd.read_csv(INPUT)
        out = keys.merge(old.drop(columns=["destination_name", "country_code"], errors="ignore"), on="destination_id", how="left")
        # Fill stable identifiers from the current baseline.
        for col in ("destination_name", "country_code"):
            old_col = f"{col}_old"
            if old_col in out:
                out[col] = out[col].fillna(out[old_col])
                out = out.drop(columns=[old_col])
    else:
        out = keys.copy()

    # Ensure every expected field exists; blank means unknown, never zero.
    for component in COMPONENTS:
        for col in [
            component, f"{component}_raw_value", f"{component}_source_name",
            f"{component}_source_url", f"{component}_observation_year",
            f"{component}_assessed_at_utc", f"{component}_notes",
            f"{component}_raw_value_definition",
        ]:
            if col not in out:
                out[col] = pd.NA

    failures = []
    try:
        out = apply_component(out, "regional_conflict_exposure", load_world_bank(), higher_is_safer=True)
        print("Updated regional-conflict proxy from World Bank GOV_WGI_PV_EST.")
    except Exception as exc:
        failures.append(f"World Bank PV.EST: {type(exc).__name__}: {exc}")
        print(f"WARNING: preserving previous regional-conflict proxy; {failures[-1]}")

    try:
        out = apply_component(out, "strategic_isolation", load_lsci(), higher_is_safer=True)
        print("Updated strategic-isolation proxy from UNCTAD LSCI.")
    except Exception as exc:
        failures.append(f"UNCTAD LSCI: {type(exc).__name__}: {exc}")
        print(f"WARNING: preserving previous strategic-isolation proxy; {failures[-1]}")

    # Keep compatibility columns for older consumers, but component-level provenance
    # above is authoritative because the scores come from different sources.
    if "source_name" not in out:
        out["source_name"] = ""
    if "source_url" not in out:
        out["source_url"] = ""
    if "observation_year" not in out:
        out["observation_year"] = pd.NA
    if "assessed_at_utc" not in out:
        out["assessed_at_utc"] = ""
    if "notes" not in out:
        out["notes"] = ""
    out["scale_definition"] = "1=lowest relative exposure proxy; 2=second; 3=middle; 4=fourth; 5=highest relative exposure proxy; blank=unknown"
    out["method_note"] = "Source-specific proxy scores are quintiles. Regional conflict uses World Bank GOV_WGI_PV_EST (WGI 2026 update; political stability proxy); strategic isolation uses inverse UNCTAD LSCI. Critical-route dependency and cross-border spillover remain unknown pending defensible comparable measures."
    INPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(INPUT, index=False)
    print(json.dumps({"rows": len(out), "source_failures": failures, "scored": {
        component: int(pd.to_numeric(out[component], errors="coerce").notna().sum())
        for component in COMPONENTS
    }}, indent=2))


if __name__ == "__main__":
    main()
