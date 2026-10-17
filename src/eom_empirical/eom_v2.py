"""EOM 2.0: separate attraction, joie-de-vivre, feasibility and uncertainty.

This module deliberately refuses to fabricate missing QoL or visa inputs. It
preserves the legacy macro ranking and creates explicit input/coverage outputs.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"

# Illustrative starting weights, intentionally not fitted/calibrated.
QOL_WEIGHTS = {
    "life_evaluation": 0.25,
    "work_life_balance": 0.20,
    "social_connection": 0.15,
    "autonomy": 0.15,
    "leisure_cultural_access": 0.15,
    "everyday_environment": 0.10,
}
QOL_INPUT_COLUMNS = list(QOL_WEIGHTS)


def zscore(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if pd.notna(sd) and sd > 0 else pd.Series(np.nan, index=s.index)


def make_templates(ranking: pd.DataFrame) -> None:
    """Create explicit source-data templates; blank means unknown, never zero."""
    destinations = ranking[["destination_id", "destination_name", "country_code"]].drop_duplicates()
    qol = destinations.copy()
    qol["data_year"] = 2025
    for c in QOL_INPUT_COLUMNS:
        qol[c] = np.nan
    qol["source_name"] = ""
    qol["source_url"] = ""
    qol["retrieved_at_utc"] = ""
    qol["notes"] = "Blank = not yet ingested; do not treat as zero. Prefer comparable official/survey data."
    qol.to_csv(DATA / "wellbeing_inputs_template.csv", index=False)

    feasibility = destinations.copy()
    feasibility["origin_country"] = "India"
    for c in ["visa_route", "eligible", "minimum_salary_or_funds", "tuition_and_fees", "language_requirement", "time_to_permanent_residence_years", "dependent_rights", "work_rights", "source_url", "effective_date", "verified_at"]:
        feasibility[c] = ""
    feasibility["feasibility_status"] = "unscored: profile/route evidence missing"
    feasibility.to_csv(DATA / "migration_feasibility_inputs_template.csv", index=False)


def main() -> None:
    OUTPUTS.mkdir(exist_ok=True)
    ranking_path = OUTPUTS / "latest_macro_eom_ranking.csv"
    ranking = pd.read_csv(ranking_path)
    make_templates(ranking)

    # Joie de vivre remains a distinct subsystem; only compute a score when
    # every weighted dimension is present for that destination.
    qol_path = DATA / "wellbeing_inputs.csv"
    if qol_path.exists():
        qol = pd.read_csv(qol_path)
    else:
        qol = pd.read_csv(DATA / "wellbeing_inputs_template.csv")
    for c in QOL_INPUT_COLUMNS:
        if c not in qol.columns:
            qol[c] = np.nan
    zcols = []
    for c in QOL_INPUT_COLUMNS:
        zc = f"z_{c}"
        qol[zc] = zscore(qol[c])
        zcols.append(zc)
    complete = qol[QOL_INPUT_COLUMNS].notna().all(axis=1)
    qol["joie_de_vivre_score"] = np.nan
    if complete.any():
        qol.loc[complete, "joie_de_vivre_score"] = sum(
            QOL_WEIGHTS[c] * qol.loc[complete, f"z_{c}"] for c in QOL_INPUT_COLUMNS
        )
    qol["qol_score_status"] = np.where(complete, "computed_from_observed_inputs; exploratory weights", "not scored: incomplete QoL evidence")
    qol.to_csv(OUTPUTS / "eom_joie_de_vivre_scores.csv", index=False)

    # Scenario sensitivity for the six existing macro components. No new score
    # is presented as a fitted estimate. We perturb positive weights +/-20%.
    features = ["salary_proxy", "cost_proxy", "opportunity_proxy", "policy_proxy", "institution_proxy", "stability_proxy"]
    valid = ranking.dropna(subset=features).copy()
    rng = np.random.default_rng(20261017)
    sens_rows = []
    if len(valid):
        z = {c: zscore(valid[c]).to_numpy() for c in features}
        base_energy = -z["salary_proxy"] + z["cost_proxy"] - z["opportunity_proxy"] - z["policy_proxy"] - z["institution_proxy"] - z["stability_proxy"]
        valid["baseline_rank_recomputed"] = pd.Series(base_energy).rank(method="min").to_numpy()
        draws = 2000
        rank_matrix = []
        signs = np.array([-1, 1, -1, -1, -1, -1])
        for _ in range(draws):
            weights = rng.uniform(0.8, 1.2, size=len(features))
            energy = sum(signs[j] * weights[j] * z[features[j]] for j in range(len(features)))
            rank_matrix.append(pd.Series(energy).rank(method="min", ascending=True).to_numpy())
        ranks = np.vstack(rank_matrix)
        for i, row in valid.reset_index(drop=True).iterrows():
            sens_rows.append({
                "destination_name": row.get("destination_name", ""),
                "country_code": row.get("country_code", ""),
                "baseline_rank": int(pd.Series(base_energy).rank(method="min").iloc[i]),
                "median_rank_under_weights_0_8_1_2": float(np.median(ranks[:, i])),
                "p10_rank": float(np.quantile(ranks[:, i], .10)),
                "p90_rank": float(np.quantile(ranks[:, i], .90)),
                "top5_share": float(np.mean(ranks[:, i] <= min(5, len(valid)))),
                "bottom5_share": float(np.mean(ranks[:, i] > max(0, len(valid)-5))),
                "draws": draws,
            })
    pd.DataFrame(sens_rows).to_csv(OUTPUTS / "eom_v2_weight_sensitivity.csv", index=False)

    # Year-balanced diagnostics reduce domination by years with more countries.
    pred_path = OUTPUTS / "macro_backtest_predictions.csv"
    year_rows = []
    if pred_path.exists():
        pred = pd.read_csv(pred_path)
        needed = {"target_year", "target_net_migration_per_1000", "ridge_prediction", "country_mean_baseline", "persistence_baseline", "energy_equal_weight"}
        if needed.issubset(pred.columns):
            from scipy.stats import spearmanr
            for year, g in pred.groupby("target_year"):
                y = pd.to_numeric(g["target_net_migration_per_1000"], errors="coerce")
                row = {"target_year": int(year), "n_destinations": int(y.notna().sum())}
                for label, col in [("eom_attraction", "energy_equal_weight"), ("ridge", "ridge_prediction"), ("persistence", "persistence_baseline")]:
                    pair = pd.concat([(-pd.to_numeric(g[col], errors="coerce") if label == "eom_attraction" else pd.to_numeric(g[col], errors="coerce")), y], axis=1).dropna()
                    row[f"{label}_spearman"] = float(spearmanr(pair.iloc[:, 0], pair.iloc[:, 1]).statistic) if len(pair) >= 5 and pair.iloc[:, 0].nunique() > 1 and pair.iloc[:, 1].nunique() > 1 else np.nan
                for label, col in [("ridge", "ridge_prediction"), ("country_mean", "country_mean_baseline"), ("persistence", "persistence_baseline")]:
                    pair = pd.concat([pd.to_numeric(g[col], errors="coerce"), y], axis=1).dropna()
                    row[f"{label}_mae"] = float(np.abs(pair.iloc[:, 0] - pair.iloc[:, 1]).mean()) if len(pair) else np.nan
                year_rows.append(row)
    year_diag = pd.DataFrame(year_rows)
    year_diag.to_csv(OUTPUTS / "eom_v2_year_balanced_backtest.csv", index=False)
    year_summary = {}
    if not year_diag.empty:
        for col in [c for c in year_diag.columns if c.endswith("_spearman") or c.endswith("_mae")]:
            year_summary[f"mean_of_yearly_{col}"] = float(year_diag[col].mean()) if year_diag[col].notna().any() else None
        year_summary["years_scored"] = int(year_diag["target_year"].nunique())

    # Do not invent a combined attraction/feasibility rank until migration
    # route, origin profile, costs and current rules are present and verified.
    status = {
        "model_version": "EOM-general-v2-architecture-2026-10-17",
        "run_status": "completed_with_data_gates",
        "legacy_macro_ranking_preserved": True,
        "legacy_ranking_file": "outputs/latest_macro_eom_ranking.csv",
        "joie_de_vivre": {
            "weights": QOL_WEIGHTS,
            "weight_status": "illustrative, not estimated",
            "destinations_with_complete_inputs": int(complete.sum()),
            "destinations_in_input_template": int(len(qol)),
            "score_output": "outputs/eom_joie_de_vivre_scores.csv",
            "interpretation": "separate subsystem; no score if any required component is missing"
        },
        "feasibility": {
            "origin_country_default": "India",
            "scored_destinations": 0,
            "reason": "No verified person-specific visa-route/eligibility/funds/language inputs supplied; template created rather than fabricate scores.",
            "input_template": "data/migration_feasibility_inputs_template.csv"
        },
        "uncertainty": {
            "weight_sensitivity_draws": 2000,
            "range": "each existing macro component weight independently perturbed uniformly from 0.8 to 1.2; signs held fixed",
            "output": "outputs/eom_v2_weight_sensitivity.csv",
            "not_a_confidence_interval": True
        },
        "year_balanced_backtest": {"output": "outputs/eom_v2_year_balanced_backtest.csv", **year_summary},
        "fresh_numeric_ingestion": "blocked in prior v7 run by DNS/network resolution; no new observations claimed",
        "combined_v2_ranking": "not produced: wellbeing and feasibility evidence incomplete",
        "next_required_inputs": ["official comparable wellbeing/life-evaluation series", "annual hours/work-life balance", "verified visa route and eligibility by profile", "housing/rent and after-tax occupation-specific salary"]
    }
    (OUTPUTS / "eom_v2_run_status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()
