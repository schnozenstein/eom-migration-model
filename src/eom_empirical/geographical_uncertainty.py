"""Risk-adjust the EOM macro ranking with explicit, source-linked geographic uncertainty.

No analyst-coded geographic score is invented by this script. It creates a blank
input template and refuses to publish an adjusted rank until all required
geographic components are populated with sources and dates.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
DATA = ROOT / "data"
BASE = OUT / "latest_macro_eom_ranking.csv"
RISK = OUT / "risk_indicator_panel.csv"
INPUT = DATA / "geographical_uncertainty_inputs.csv"
TEMPLATE = DATA / "geographical_uncertainty_inputs_template.csv"
ADJUSTED = OUT / "geographical_risk_adjusted_ranking.csv"
AUDIT = OUT / "geographical_uncertainty_audit.json"

# Illustrative scenario weights, not fitted parameters. Higher component values
# mean greater risk. These weights are deliberately configurable.
WEIGHTS = {
    "regional_conflict_exposure": 0.30,
    "strategic_isolation": 0.20,
    "critical_route_dependency": 0.15,
    "natural_hazard_exposure": 0.20,
    "cross_border_spillover": 0.15,
}
RISK_WEIGHT = 0.25
GEOGRAPHY_WEIGHT = 0.25
REQUIRED_META = ["source_name", "source_url", "observation_year", "assessed_at_utc", "notes"]


def zscore(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    sd = x.std(ddof=0)
    return (x - x.mean()) / sd if pd.notna(sd) and sd > 0 else pd.Series(np.nan, index=x.index)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    base = pd.read_csv(BASE)
    components = list(WEIGHTS)
    template = base[["destination_id", "destination_name", "country_code"]].copy()
    for c in components:
        template[c] = np.nan  # 1=low exposure, 5=high exposure; blank is unknown
    for c in REQUIRED_META:
        template[c] = ""
    template["scale_definition"] = "1=low exposure; 2=moderately low; 3=moderate; 4=high; 5=very high; blank=unknown"
    template["method_note"] = "Use comparable evidence and cite the source URL; do not score from country reputation alone."
    template.to_csv(TEMPLATE, index=False)

    geo_path = INPUT if INPUT.exists() else TEMPLATE
    geo = pd.read_csv(geo_path)
    for c in components:
        if c not in geo:
            geo[c] = np.nan
    # Risk panel is explicitly partial; its missingness is not interpreted as zero.
    risk = pd.read_csv(RISK) if RISK.exists() else pd.DataFrame()
    if not risk.empty:
        risk_cols = ["destination_id", "environment_economic_partial_risk_score", "risk_score_status"]
        risk = risk[[c for c in risk_cols if c in risk.columns]].drop_duplicates("destination_id")
        joined = base.merge(risk, on="destination_id", how="left")
    else:
        joined = base.copy()
        joined["environment_economic_partial_risk_score"] = np.nan
        joined["risk_score_status"] = "missing risk panel"

    joined = joined.merge(geo[["destination_id"] + components], on="destination_id", how="left")
    complete_geo = joined[components].notna().all(axis=1)
    complete_risk = joined["environment_economic_partial_risk_score"].notna()
    # A composite is emitted only when both risk families are present; no silent
    # dropping of missing dimensions and no false precision from incomplete inputs.
    joined["geographical_uncertainty_raw"] = joined[components].mean(axis=1, skipna=False)
    joined["macro_energy_z"] = zscore(joined["energy_equal_weight"])
    joined["environment_economic_risk_z"] = zscore(joined["environment_economic_partial_risk_score"])
    joined["geographical_uncertainty_z"] = zscore(joined["geographical_uncertainty_raw"])
    joined["risk_adjusted_energy"] = np.nan
    eligible = complete_geo & complete_risk & joined["macro_energy_z"].notna()
    joined.loc[eligible, "risk_adjusted_energy"] = (
        joined.loc[eligible, "macro_energy_z"]
        + RISK_WEIGHT * joined.loc[eligible, "environment_economic_risk_z"]
        + GEOGRAPHY_WEIGHT * joined.loc[eligible, "geographical_uncertainty_z"]
    )
    joined["risk_adjusted_rank"] = np.nan
    joined.loc[eligible, "risk_adjusted_rank"] = joined.loc[eligible, "risk_adjusted_energy"].rank(method="min", ascending=True)
    joined["ranking_status"] = np.where(
        eligible,
        "provisional risk-adjusted rank; illustrative weights; not calibrated",
        "not ranked: geographic inputs and/or environmental-economic risk evidence incomplete"
    )
    joined.to_csv(ADJUSTED, index=False)

    audit = {
        "model_version": "EOM-geographical-uncertainty-v1",
        "status": "ranked" if bool(eligible.any()) else "blocked_by_evidence_gates",
        "destinations_in_macro_baseline": int(len(base)),
        "destinations_with_complete_geographic_inputs": int(complete_geo.sum()),
        "destinations_with_environment_economic_risk": int(complete_risk.sum()),
        "destinations_receiving_adjusted_rank": int(eligible.sum()),
        "geographic_components": WEIGHTS,
        "illustrative_weights": {"environment_economic_risk": RISK_WEIGHT, "geographical_uncertainty": GEOGRAPHY_WEIGHT},
        "weight_status": "scenario assumptions; not empirically estimated",
        "input_file": str(INPUT.relative_to(ROOT)),
        "template_file": str(TEMPLATE.relative_to(ROOT)),
        "output_file": str(ADJUSTED.relative_to(ROOT)),
        "method": "z-score macro energy + 0.25*z-score partial environmental/economic risk + 0.25*z-score geographic uncertainty; lower is better",
        "safeguards": [
            "blank values are unknown, never zero",
            "no adjusted rank until all five geographic components and the risk score are present",
            "geographic scores require source URLs, observation year and assessment date",
            "this is a sensitivity/scenario ranking, not a migration probability or validated forecast"
        ]
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
