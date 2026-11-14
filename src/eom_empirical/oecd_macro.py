"""Build an explicitly exploratory OECD-augmented macro ranking.

The World Bank equal-weight EOM score remains the baseline. OECD A-series
migration indicators form a separate ecosystem signal and are blended only
for destinations with complete same-year overlap.
"""
from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OECD_HISTORY = ROOT / "data" / "observations_history" / "oecd_imo_2026_a_series_history.csv"
WDI_RAW = ROOT / "data" / "raw" / "world_bank_macro_focus.csv"
DESTINATIONS = ROOT / "data" / "destinations.csv"
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"

NAME_TO_ISO3 = {
    "Australia":"AUS", "Austria":"AUT", "Belgium":"BEL", "Canada":"CAN",
    "Chile":"CHL", "Colombia":"COL", "Costa Rica":"CRI", "Czechia":"CZE",
    "Denmark":"DNK", "Estonia":"EST", "Finland":"FIN", "France":"FRA",
    "Germany":"DEU", "Greece":"GRC", "Hungary":"HUN", "Iceland":"ISL",
    "Ireland":"IRL", "Israel":"ISR", "Italy":"ITA", "Japan":"JPN",
    "Korea":"KOR", "Latvia":"LVA", "Lithuania":"LTU", "Luxembourg":"LUX",
    "Mexico":"MEX", "Netherlands":"NLD", "New Zealand":"NZL", "Norway":"NOR",
    "Poland":"POL", "Portugal":"PRT", "Slovak Republic":"SVK",
    "Slovenia":"SVN", "Spain":"ESP", "Sweden":"SWE", "Switzerland":"CHE",
    "Türkiye":"TUR", "United Kingdom":"GBR", "United States":"USA",
}

FEATURE_MEASURES = {
    "immigration_foreign_population": "inflow_per_1000_residents",
    "foreign_born_population_share": "foreign_born_share_pct",
    "acquisitions_share_of_foreign_population": "nationality_acquisition_share_pct",
}


def _z(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    sd = x.std(ddof=0)
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.nan, index=x.index)
    return (x - x.mean()) / sd


def build_oecd_enhanced_ranking(oecd_path: Path = OECD_HISTORY,
                                wdi_path: Path = WDI_RAW,
                                destinations_path: Path = DESTINATIONS,
                                output_dir: Path = OUTPUTS,
                                report_dir: Path = REPORTS) -> dict:
    for path in (oecd_path, wdi_path, destinations_path):
        if not path.exists():
            raise FileNotFoundError(f"Required input missing: {path}")

    oecd = pd.read_csv(oecd_path, low_memory=False)
    required = {"table_code", "destination", "measure", "year", "value",
                "unit", "observation_status", "retrieved_at_utc"}
    missing = required - set(oecd.columns)
    if missing:
        raise ValueError(f"OECD history missing columns: {sorted(missing)}")
    oecd["value"] = pd.to_numeric(oecd["value"], errors="coerce")
    oecd["year"] = pd.to_numeric(oecd["year"], errors="coerce")
    oecd = oecd[oecd["observation_status"].eq("observed") & oecd["value"].notna()].copy()
    # Keep the most recent published/retrieved revision for each natural key.
    keys = [c for c in ["table_code", "destination", "origin", "measure", "year"] if c in oecd]
    oecd = oecd.sort_values("retrieved_at_utc").drop_duplicates(keys, keep="last")
    oecd = oecd[oecd["measure"].isin(FEATURE_MEASURES)].copy()
    oecd["country_code"] = oecd["destination"].map(NAME_TO_ISO3)
    oecd = oecd[oecd["country_code"].notna()].copy()

    # A.1 is reported in thousands; WDI population is persons. Convert to
    # immigration inflows per 1,000 residents. A.4/A.6 percentages stay in %.
    pop = pd.read_csv(wdi_path, low_memory=False)
    pop = pop[(pop["indicator_code"] == "SP.POP.TOTL")].copy()
    pop["year"] = pd.to_numeric(pop["year"], errors="coerce")
    pop["value"] = pd.to_numeric(pop["value"], errors="coerce")
    pop = pop.rename(columns={"value": "population"})[["country_code", "year", "population"]]
    oecd = oecd.merge(pop, on=["country_code", "year"], how="left")
    oecd["feature_value"] = oecd["value"]
    is_inflow = oecd["measure"].eq("immigration_foreign_population")
    oecd.loc[is_inflow, "feature_value"] = (
        oecd.loc[is_inflow, "value"] * 1000 /
        oecd.loc[is_inflow, "population"] * 1000
    )
    oecd.loc[is_inflow & oecd["population"].isna(), "feature_value"] = np.nan
    oecd["feature"] = oecd["measure"].map(FEATURE_MEASURES)

    panel = oecd.pivot_table(index=["country_code", "year"], columns="feature",
                             values="feature_value", aggfunc="first").reset_index()
    feature_cols = list(FEATURE_MEASURES.values())
    for col in feature_cols:
        if col not in panel:
            panel[col] = np.nan
    panel = panel.dropna(subset=feature_cols).copy()
    if panel.empty:
        raise ValueError("No destination-year has complete OECD A.1/A.4/A.6 plus population coverage.")

    # Compare in the latest year with full three-indicator OECD coverage and
    # complete six-component World Bank baseline coverage.
    from .model import to_wide, add_derived_features, equal_weight_energy
    wdi_long = pd.read_csv(wdi_path, low_memory=False)
    if "country_region" in wdi_long:
        wdi_long = wdi_long[wdi_long["country_region"].notna()].copy()
    wdi_wide = add_derived_features(to_wide(wdi_long))
    energy_features = ["salary_proxy", "cost_proxy", "opportunity_proxy",
                       "policy_proxy", "institution_proxy", "stability_proxy"]
    dest = pd.read_csv(destinations_path, dtype=str).fillna("")
    focus = dest[dest["primary_choice_set"].eq("global_country")][
        ["destination_id", "destination_name", "wb_country_code"]
    ]
    candidates = []
    for year in sorted(panel["year"].dropna().unique(), reverse=True):
        op = panel[panel["year"].eq(year)].copy()
        wp = wdi_wide[wdi_wide["year"].eq(year)].copy()
        wp = wp[wp[energy_features].notna().all(axis=1)]
        joined = op.merge(wp[["country_code", *energy_features]], on="country_code", how="inner")
        joined = joined.merge(focus, left_on="country_code", right_on="wb_country_code", how="inner")
        if len(joined) >= 10:
            candidates.append((int(year), joined))
            break
    if not candidates:
        raise ValueError("Fewer than 10 destinations have complete OECD and World Bank features in a common year.")
    year, joined = candidates[0]

    baseline = equal_weight_energy(joined.rename(columns={
        "salary_proxy":"salary_proxy", "cost_proxy":"cost_proxy",
        "opportunity_proxy":"opportunity_proxy", "policy_proxy":"policy_proxy",
        "institution_proxy":"institution_proxy", "stability_proxy":"stability_proxy"
    }))
    joined["baseline_energy"] = baseline["energy_equal_weight"].to_numpy()
    joined["baseline_attractiveness_z"] = _z(-joined["baseline_energy"])
    component_z = []
    for col in feature_cols:
        zcol = col + "_z"
        joined[zcol] = _z(joined[col])
        component_z.append(zcol)
    joined["oecd_migration_ecosystem_signal"] = joined[component_z].mean(axis=1)
    joined["oecd_signal_z"] = _z(joined["oecd_migration_ecosystem_signal"])

    # 20% is a transparent exploratory weight, not an estimated causal parameter.
    joined["enhanced_attractiveness_20pct"] = (
        0.80 * joined["baseline_attractiveness_z"] + 0.20 * joined["oecd_signal_z"]
    )
    joined["enhanced_energy_20pct"] = -joined["enhanced_attractiveness_20pct"]
    joined["baseline_rank_common_sample"] = joined["baseline_energy"].rank(method="min")
    joined["enhanced_rank_20pct"] = joined["enhanced_energy_20pct"].rank(method="min")
    for weight in (0.10, 0.30):
        col = f"enhanced_energy_{int(weight*100)}pct"
        joined[col] = -( (1-weight) * joined["baseline_attractiveness_z"] +
                         weight * joined["oecd_signal_z"] )
        joined[f"enhanced_rank_{int(weight*100)}pct"] = joined[col].rank(method="min")

    joined["comparison_year"] = year
    joined["oecd_weight"] = 0.20
    joined["interpretation"] = "Exploratory macro ecosystem signal; not an individual migration probability"
    out_cols = ["destination_id", "destination_name", "country_code", "comparison_year",
                *feature_cols, "baseline_energy", "baseline_rank_common_sample",
                "oecd_migration_ecosystem_signal", "enhanced_energy_20pct",
                "enhanced_rank_20pct", "enhanced_rank_10pct", "enhanced_rank_30pct",
                "oecd_weight", "interpretation"]
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    ranking = joined[out_cols].sort_values("enhanced_rank_20pct")
    ranking.to_csv(output_dir / "latest_oecd_enhanced_macro_ranking.csv", index=False)
    joined.to_csv(output_dir / "oecd_macro_component_panel.csv", index=False)
    result = {
        "status": "completed",
        "comparison_year": year,
        "destinations_scored": int(len(ranking)),
        "oecd_inputs": {
            "A.1": "foreign-population immigration inflows per 1,000 residents",
            "A.4": "foreign-born population share (%)",
            "A.6": "nationality acquisitions as share of foreign population (%)",
        },
        "excluded_from_score": {
            "A.3": "asylum requests; retained as contextual pressure/risk, not attractiveness",
            "A.5": "foreign-population stock by nationality; excluded to avoid overlapping stock signal",
        },
        "weight": {"world_bank_baseline": 0.80, "oecd_ecosystem_signal": 0.20},
        "sensitivity_outputs": ["10%", "20%", "30% OECD weight"],
        "caveat": "OECD measures are a destination ecosystem/context signal, not causal attraction estimates. Cross-country definitions and coverage differ. Do not interpret scores as personal probabilities.",
        "ranking_path": "outputs/latest_oecd_enhanced_macro_ranking.csv",
        "component_path": "outputs/oecd_macro_component_panel.csv",
    }
    (report_dir / "oecd_enhanced_macro_methodology.md").write_text(
        "# OECD-enhanced EOM macro comparison\n\n"
        f"- Comparison year: {year}\n- Destinations: {len(ranking)}\n"
        "- Baseline: World Bank six-component equal-weight EOM macro proxy.\n"
        "- OECD signal: A.1 inflow rate, A.4 foreign-born share, A.6 nationality-acquisition share.\n"
        "- Blend: 80% standardized baseline attractiveness + 20% standardized OECD ecosystem signal.\n"
        "- Sensitivity rankings: 10%, 20%, 30% OECD weights.\n"
        "- A.3 asylum requests are excluded from attractiveness scoring and retained as contextual pressure; A.5 is excluded to avoid overlapping stock measures.\n"
        "- This is exploratory and not a calibrated migration probability or an individual recommendation.\n",
        encoding="utf-8"
    )
    return result


def main() -> None:
    print(json.dumps(build_oecd_enhanced_ranking(), indent=2))


if __name__ == "__main__":
    main()
