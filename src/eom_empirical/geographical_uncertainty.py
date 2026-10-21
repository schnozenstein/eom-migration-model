"""Risk-adjust the EOM macro ranking using separately sourced geography inputs.

Natural-hazard exposure is maintained by fetch_geographical_evidence.py.
Geopolitical components are sourced independently; each component therefore has
its own provenance fields. Blank values are unknown, never zero.
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
HAZARD_INPUT = DATA / "geographical_uncertainty_inputs.csv"
GEO_INPUT = DATA / "geopolitical_uncertainty_inputs.csv"
TEMPLATE = DATA / "geopolitical_uncertainty_inputs_template.csv"
ADJUSTED = OUT / "geographical_risk_adjusted_ranking.csv"
AUDIT = OUT / "geographical_uncertainty_audit.json"

# Scenario weights, not fitted parameters. Higher values mean higher exposure.
WEIGHTS = {
    "regional_conflict_exposure": 0.30,
    "strategic_isolation": 0.20,
    "critical_route_dependency": 0.15,
    "natural_hazard_exposure": 0.20,
    "cross_border_spillover": 0.15,
}
RISK_WEIGHT = 0.25
GEOGRAPHY_WEIGHT = 0.25
GEO_COMPONENTS = [
    "regional_conflict_exposure", "strategic_isolation",
    "critical_route_dependency", "cross_border_spillover"
]
META_SUFFIXES = [
    "source_name", "source_url", "observation_year",
    "assessed_at_utc", "notes", "raw_value_definition"
]
GEO_META_BY_COMPONENT = {
    component: [f"{component}_{suffix}" for suffix in META_SUFFIXES]
    for component in GEO_COMPONENTS
}
ALL_GEO_META = [col for cols in GEO_META_BY_COMPONENT.values() for col in cols]


def zscore(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    sd = x.std(ddof=0)
    return (x - x.mean()) / sd if pd.notna(sd) and sd > 0 else pd.Series(np.nan, index=x.index)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    base = pd.read_csv(BASE)
    template = base[["destination_id", "destination_name", "country_code"]].copy()
    for c in GEO_COMPONENTS:
        template[c] = np.nan
        template[f"{c}_raw_value"] = np.nan
        for suffix in META_SUFFIXES:
            template[f"{c}_{suffix}"] = ""
    # Keep legacy aggregate fields for compatibility, but never use them as
    # provenance for multiple components sourced from different datasets.
    template["source_name"] = ""
    template["source_url"] = ""
    template["observation_year"] = ""
    template["assessed_at_utc"] = ""
    template["notes"] = ""
    template["scale_definition"] = "1=lowest relative exposure proxy; 2=second; 3=middle; 4=fourth; 5=highest relative exposure proxy; blank=unknown"
    template["method_note"] = (
        "Each score requires its own source name, URL, observation year, assessment date, "
        "notes and raw-value definition. This file is separate from the natural-hazard feed."
    )
    template.to_csv(TEMPLATE, index=False)

    # Natural-hazard scores are fetched separately and refreshed automatically.
    hazard = pd.read_csv(HAZARD_INPUT) if HAZARD_INPUT.exists() else base[["destination_id"]].copy()
    if "natural_hazard_exposure" not in hazard:
        hazard["natural_hazard_exposure"] = np.nan
    hazard = hazard[["destination_id", "natural_hazard_exposure"]].drop_duplicates("destination_id")

    geo = pd.read_csv(GEO_INPUT) if GEO_INPUT.exists() else template.copy()
    for c in GEO_COMPONENTS:
        if c not in geo:
            geo[c] = np.nan
        for suffix in META_SUFFIXES:
            col = f"{c}_{suffix}"
            if col not in geo:
                geo[col] = np.nan if suffix == "observation_year" else ""
    selected = ["destination_id"] + GEO_COMPONENTS + [
        f"{c}_raw_value" for c in GEO_COMPONENTS if f"{c}_raw_value" in geo.columns
    ] + ALL_GEO_META
    geo = geo[[c for c in selected if c in geo.columns]].drop_duplicates("destination_id")

    risk = pd.read_csv(RISK) if RISK.exists() else pd.DataFrame()
    if not risk.empty and {"destination_id", "environment_economic_partial_risk_score"}.issubset(risk.columns):
        risk = risk[[c for c in ["destination_id", "environment_economic_partial_risk_score", "risk_score_status"] if c in risk.columns]].drop_duplicates("destination_id")
        joined = base.merge(risk, on="destination_id", how="left")
    else:
        joined = base.copy()
        joined["environment_economic_partial_risk_score"] = np.nan
        joined["risk_score_status"] = "missing risk panel"

    joined = joined.merge(hazard, on="destination_id", how="left")
    joined = joined.merge(geo, on="destination_id", how="left", suffixes=("", "_geo"))
    geo_complete = joined[GEO_COMPONENTS].notna().all(axis=1)
    metadata_checks = []
    for component, columns in GEO_META_BY_COMPONENT.items():
        cols = [c for c in columns if c in joined.columns]
        if len(cols) != len(columns):
            metadata_checks.append(pd.Series(False, index=joined.index))
        else:
            ok = joined[cols].notna().all(axis=1)
            ok &= joined[cols].astype(str).apply(lambda col: col.str.strip().ne("")).all(axis=1)
            metadata_checks.append(ok)
    geo_metadata_complete = pd.concat(metadata_checks, axis=1).all(axis=1)
    hazard_complete = pd.to_numeric(joined["natural_hazard_exposure"], errors="coerce").notna()
    complete_geo = geo_complete & geo_metadata_complete & hazard_complete
    complete_risk = pd.to_numeric(joined["environment_economic_partial_risk_score"], errors="coerce").notna()

    joined["geographical_uncertainty_raw"] = joined[list(WEIGHTS)].mean(axis=1, skipna=False)
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
        "not ranked: one or more source-backed geographic components/provenance fields or environmental-economic risk inputs are incomplete"
    )
    joined.to_csv(ADJUSTED, index=False)

    audit = {
        "model_version": "EOM-geographical-uncertainty-v3",
        "status": "ranked" if bool(eligible.any()) else "blocked_by_evidence_gates",
        "destinations_in_macro_baseline": int(len(base)),
        "destinations_with_all_four_geopolitical_components_and_component_level_provenance": int((geo_complete & geo_metadata_complete).sum()),
        "destinations_with_natural_hazard_exposure": int(hazard_complete.sum()),
        "destinations_with_complete_geographic_inputs": int(complete_geo.sum()),
        "destinations_with_environment_economic_risk": int(complete_risk.sum()),
        "destinations_receiving_adjusted_rank": int(eligible.sum()),
        "geopolitical_component_coverage": {
            component: int(pd.to_numeric(joined[component], errors="coerce").notna().sum())
            for component in GEO_COMPONENTS
        },
        "geopolitical_component_provenance_fields": GEO_META_BY_COMPONENT,
        "geographic_component_weights": WEIGHTS,
        "illustrative_weights": {"environment_economic_risk": RISK_WEIGHT, "geographical_uncertainty": GEOGRAPHY_WEIGHT},
        "weight_status": "scenario assumptions; not empirically estimated",
        "geopolitical_input_file": str(GEO_INPUT.relative_to(ROOT)),
        "geopolitical_template_file": str(TEMPLATE.relative_to(ROOT)),
        "natural_hazard_input_file": str(HAZARD_INPUT.relative_to(ROOT)),
        "output_file": str(ADJUSTED.relative_to(ROOT)),
        "method": "z-score macro energy + 0.25*z-score partial environmental/economic risk + 0.25*z-score geographic uncertainty; lower is better",
        "safeguards": [
            "blank values are unknown, never zero",
            "natural-hazard refresh is separated from geopolitical evidence to prevent overwrites",
            "each geopolitical score must have its own source URL, observation year and assessment date",
            "no adjusted rank until all five geographic components, component-level provenance, and risk score are present",
            "regional conflict and strategic isolation currently use explicitly labelled proxies, not direct measurements",
            "this is a sensitivity/scenario ranking, not a migration probability or validated forecast"
        ]
    }
    AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
