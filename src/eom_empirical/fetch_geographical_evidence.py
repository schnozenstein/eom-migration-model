"""Fetch a traceable natural-hazard exposure proxy for EOM geographic uncertainty.

Source: IFHV/Ruhr University Bochum WorldRiskIndex 2025, distributed as a
country-level CSV by Nations Inquiry. The source's exposure measure covers
population exposure to earthquakes, storms, floods, droughts and sea-level rise.
Scores are converted to within-dataset quintiles (1=lowest exposure, 5=highest).
This is a relative proxy, not an absolute probability or a forecast.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
import pandas as pd
import requests
from eom_empirical.http_utils import get_with_retries

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs" / "latest_macro_eom_ranking.csv"
INPUT = ROOT / "data" / "geographical_uncertainty_inputs.csv"
SOURCE_URL = "https://www.nationsinquiry.com/datasets/world-risk-index/2025/data.csv"
SOURCE_NAME = "IFHV WorldRiskIndex 2025 (country CSV via Nations Inquiry)"
SOURCE_YEAR = 2025


def load_source() -> pd.DataFrame:
    response = get_with_retries(SOURCE_URL, timeout=(10, 45))
    response.raise_for_status()
    payload = response.content
    # The distributor adds 11 lines of source notes before the CSV header.
    for skip in (11, 12, 0):
        frame = pd.read_csv(BytesIO(payload), skiprows=skip)
        frame.columns = [str(c).strip().lower().replace(" ", "_") for c in frame.columns]
        if {"country_code", "exposure"}.issubset(frame.columns):
            return frame
    raise ValueError("WorldRiskIndex source schema changed: expected country_code and exposure columns")


def main() -> None:
    base = pd.read_csv(BASE)
    try:
        source = load_source()
    except Exception as exc:
        # A transient source/network outage must not destroy last-known evidence or
        # fail the entire daily pipeline. Keep the existing snapshot unchanged.
        if INPUT.exists():
            print(
                f"WARNING: WorldRiskIndex fetch failed ({type(exc).__name__}: {exc}); "
                f"preserving existing {INPUT.relative_to(ROOT)} unchanged. "
                "Mark this source stale and inspect the workflow artifact."
            )
            return
        # First-run outage: create an all-unknown hazard file, never zero exposure.
        out = base[["destination_id", "destination_name", "country_code"]].copy()
        out["natural_hazard_exposure"] = pd.NA
        for component in [
            "regional_conflict_exposure", "strategic_isolation",
            "critical_route_dependency", "cross_border_spillover"
        ]:
            out[component] = pd.NA
        out["source_name"] = SOURCE_NAME
        out["source_url"] = SOURCE_URL
        out["observation_year"] = SOURCE_YEAR
        out["assessed_at_utc"] = datetime.now(timezone.utc).isoformat()
        out["notes"] = f"Source unavailable; exposure unknown, not zero. Error: {type(exc).__name__}: {exc}"
        out["scale_definition"] = "1=lowest exposure quintile; 2=second; 3=middle; 4=fourth; 5=highest; blank=unknown"
        out["method_note"] = "WorldRiskIndex source unavailable during this run; no hazard scores imputed."
        INPUT.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(INPUT, index=False)
        print(f"WARNING: WorldRiskIndex fetch failed; wrote {len(out)} rows with unknown hazard scores.")
        return
    source["country_code"] = source["country_code"].astype(str).str.upper().str.strip()
    source["exposure"] = pd.to_numeric(source["exposure"], errors="coerce")
    source = source.dropna(subset=["country_code", "exposure"]).drop_duplicates("country_code")

    # Rank percentile into five comparable groups, preserving ties as much as possible.
    percentile = source["exposure"].rank(method="average", pct=True)
    source["natural_hazard_exposure"] = (percentile.mul(5).apply(__import__("math").ceil)).clip(1, 5).astype(int)

    out = base[["destination_id", "destination_name", "country_code"]].copy()
    out = out.merge(source[["country_code", "exposure", "natural_hazard_exposure"]], on="country_code", how="left")
    # Preserve other dimensions as unknown until a defensible source/operational definition is implemented.
    for component in [
        "regional_conflict_exposure", "strategic_isolation",
        "critical_route_dependency", "cross_border_spillover"
    ]:
        out[component] = pd.NA
    out["source_name"] = SOURCE_NAME
    out["source_url"] = SOURCE_URL
    out["observation_year"] = SOURCE_YEAR
    out["assessed_at_utc"] = datetime.now(timezone.utc).isoformat()
    out["notes"] = out["exposure"].apply(
        lambda x: "Natural-hazard exposure quintile derived from WorldRiskIndex exposure measure; 1=lowest relative exposure, 5=highest."
        if pd.notna(x) else "No matching source row; unknown, not zero."
    )
    out["scale_definition"] = "1=lowest exposure quintile; 2=second; 3=middle; 4=fourth; 5=highest; blank=unknown"
    out["method_note"] = "Natural-hazard component is a relative quintile of WorldRiskIndex exposure; other geographic components remain unscored pending source-backed measures."
    out = out.drop(columns=["exposure"])
    INPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(INPUT, index=False)
    print(f"Wrote {INPUT.relative_to(ROOT)}: {out['natural_hazard_exposure'].notna().sum()} of {len(out)} destinations matched; other geographic dimensions remain unknown.")


if __name__ == "__main__":
    main()
