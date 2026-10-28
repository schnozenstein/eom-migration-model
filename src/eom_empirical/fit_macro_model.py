"""Create an equal-weight EOM macro score and expanding-origin backtest."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from .model import to_wide, add_derived_features, equal_weight_energy, make_lagged_panel
from .evaluation import expanding_origin_backtest

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "world_bank_macro_focus.csv"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
FEATURE_COLS = ["lag_salary_proxy", "lag_cost_proxy", "lag_opportunity_proxy", "lag_policy_proxy", "lag_institution_proxy", "lag_stability_proxy"]


def safe_rho(a: pd.Series, b: pd.Series) -> float | None:
    pair = pd.concat([a, b], axis=1).dropna()
    if len(pair) < 5 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return None
    value = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1]).statistic
    return float(value) if pd.notna(value) else None


def main() -> None:
    if not RAW.exists():
        raise FileNotFoundError(f"Missing {RAW}. Run: python -m eom_empirical.fetch_world_bank (requires network access).")
    long = pd.read_csv(RAW)
    # WDI includes regional/income aggregates with no country-region classification.
    # Exclude those from country-level training and ranking to avoid duplicate geographies.
    if "country_region" in long.columns:
        long = long[long["country_region"].notna()].copy()
    wide = add_derived_features(to_wide(long))
    PROCESSED.mkdir(parents=True, exist_ok=True); OUTPUTS.mkdir(parents=True, exist_ok=True)
    wide.to_csv(PROCESSED / "macro_panel_wide.csv", index=False)

    # Score the full registered country choice set, preserving destinations with missing inputs as unranked.
    energy_features = ["salary_proxy", "cost_proxy", "opportunity_proxy", "policy_proxy", "institution_proxy", "stability_proxy"]
    dest = pd.read_csv(ROOT / "data" / "destinations.csv", dtype=str).fillna("")
    focus = dest[dest["primary_choice_set"] == "global_country"].copy()
    focus_codes = set(focus["wb_country_code"].dropna()) - {""}
    focus_wide = wide[wide["country_code"].isin(focus_codes)].copy()
    coverage = focus_wide.groupby("year")[energy_features].apply(lambda g: g.notna().all(axis=1).sum())
    candidates = coverage[coverage >= 10]
    if candidates.empty:
        (OUTPUTS / "macro_backtest.json").write_text(json.dumps({"status":"insufficient_data","message":"No year has complete comparable features for at least 10 focus destinations; no numerical ranking produced."}, indent=2))
        raise ValueError("No year has complete macro-feature coverage for at least 10 focus destinations.")
    latest_year = int(candidates.index.max())
    focus_latest = focus_wide[focus_wide["year"] == latest_year].copy()
    complete = focus_latest[energy_features].notna().all(axis=1)
    scored = equal_weight_energy(focus_latest.loc[complete].copy())
    # Start from the full registry so destinations without WDI records remain explicitly visible.
    base = focus[["wb_country_code", "destination_id", "destination_name"]].merge(
        focus_latest, left_on="wb_country_code", right_on="country_code", how="left"
    )
    base["year"] = latest_year
    base["country_code"] = base["country_code"].fillna(base["wb_country_code"])
    scored_cols = ["country_code", "energy_equal_weight", "energy_rank", "score_status"]
    result = base.merge(scored[scored_cols], on="country_code", how="left")
    result["score_status"] = result["score_status"].fillna(
        "not ranked: one or more required macro components are missing for comparison year"
    )
    out_cols = ["destination_id", "destination_name", "country_code", "year", *energy_features, "energy_equal_weight", "energy_rank", "score_status"]
    ranking_path = OUTPUTS / "latest_macro_eom_ranking.csv"
    ranking_output = result[[c for c in out_cols if c in result.columns]].sort_values("energy_rank", na_position="last")
    ranking_output.to_csv(ranking_path, index=False)

    # Distinguish a successful source refresh from a genuine model reranking in the manifest.
    manifests = sorted((ROOT / "metadata" / "refresh_runs").glob("*.json"))
    if manifests:
        manifest_path = manifests[-1]
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        manifest.update({
            "ranking_recomputed": True,
            "ranking_year": latest_year,
            "ranking_destinations_scored": int(complete.sum()),
            "ranking_destinations_total": int(len(focus)),
            "ranking_destinations_unscored": int(len(focus) - complete.sum()),
            "ranking_run_at_utc": datetime.now(timezone.utc).isoformat(),
            "ranking_method": "equal-weight standardized macro proxy; latest common year with at least 10 complete destinations"
        })
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    lagged, lag_cols = make_lagged_panel(wide)
    lagged = lagged.replace([np.inf, -np.inf], np.nan)
    usable = lagged[lag_cols + ["target_net_migration_per_1000", "target_year", "net_migration_per_1000_feature_year"]].notna().all(axis=1)
    lagged = lagged.loc[usable].copy()
    predictions, folds = expanding_origin_backtest(lagged, lag_cols, min_train_rows=25, min_test_rows=8)
    if predictions.empty or predictions["target_year"].nunique() < 3:
        report = {"status":"insufficient_data","rows_with_complete_features_and_target":int(len(lagged)),"rolling_origins_scored":int(predictions["target_year"].nunique()) if not predictions.empty else 0,"message":"Fewer than three eligible expanding-origin test years; no performance claim or ranking inference."}
        (OUTPUTS / "macro_backtest.json").write_text(json.dumps(report, indent=2))
        folds.to_csv(OUTPUTS / "macro_backtest_folds.csv", index=False)
        print(json.dumps(report, indent=2)); return

    # Compute EOM energy on each feature year, separately from fitted Ridge and naive baselines.
    energy_parts=[]
    for feature_year, group in wide.groupby("year"):
        e=equal_weight_energy(group)
        energy_parts.append(e[["country_code","year","energy_equal_weight"]])
    energy_panel=pd.concat(energy_parts,ignore_index=True)
    predictions=predictions.merge(energy_panel,on=["country_code","year"],how="left")
    y=predictions["target_net_migration_per_1000"]
    ridge=predictions["ridge_prediction"]
    country_mean=predictions["country_mean_baseline"]
    persistence=predictions["persistence_baseline"]
    valid_persistence=persistence.notna()
    report={
      "status":"completed_expanding_origin_backtest",
      "target":"next-year national net migration per 1,000 residents",
      "feature_year_rule":"features observed in year t; target observed in year t+1",
      "evaluation_method":"expanding-origin; each test year is predicted using only earlier target years; no random split",
      "rolling_origins_scored":int(predictions["target_year"].nunique()),
      "test_target_years":[int(v) for v in sorted(predictions["target_year"].unique())],
      "n_scored":int(len(predictions)),
      "n_destinations":int(predictions["country_code"].nunique()),
      "train_rows_min":int(predictions["train_rows"].min()),
      "train_rows_max":int(predictions["train_rows"].max()),
      "ridge_mae":float(mean_absolute_error(y,ridge)),
      "ridge_rmse":float(np.sqrt(mean_squared_error(y,ridge))),
      "ridge_r2":float(r2_score(y,ridge)) if y.nunique()>1 else None,
      "country_mean_baseline_mae":float(mean_absolute_error(y,country_mean)),
      "persistence_baseline_mae":float(mean_absolute_error(y[valid_persistence],persistence[valid_persistence])) if valid_persistence.any() else None,
      "eom_equal_weight_energy_rank_spearman":safe_rho(-predictions["energy_equal_weight"],y),
      "ridge_rank_spearman":safe_rho(ridge,y),
      "persistence_rank_spearman":safe_rho(persistence,y),
      "uncertainty_note":"Metrics are pooled across chronological test origins; serial dependence and cross-country heterogeneity remain. Use block/cluster-aware intervals before strong claims.",
      "interpretation":"Macro-level predictive evaluation only. National net migration is not an individual or programme-specific outcome. Equal-weight EOM energy is an ordinal score, not a calibrated probability; its Spearman correlation is not a causal estimate. Weak performance is evidence against this operationalization, not proof that every EOM formulation fails."
    }
    predictions.to_csv(OUTPUTS/"macro_backtest_predictions.csv",index=False)
    folds.to_csv(OUTPUTS/"macro_backtest_folds.csv",index=False)
    (OUTPUTS/"macro_backtest.json").write_text(json.dumps(report,indent=2))
    # Coefficients from the last expanding-origin fold only, explicitly not treated as final calibrated weights.
    last_year=int(predictions["target_year"].max())
    last_train=lagged[lagged["target_year"]<last_year]
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    model=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=2.0))
    model.fit(last_train[lag_cols],last_train["target_net_migration_per_1000"])
    coefs=pd.DataFrame({"feature":lag_cols,"ridge_coefficient_standardized_features":model.named_steps["ridge"].coef_,"fit_cutoff_target_year":last_year})
    coefs["absolute_coefficient"]=coefs["ridge_coefficient_standardized_features"].abs()
    coefs.sort_values("absolute_coefficient",ascending=False).to_csv(OUTPUTS/"macro_model_coefficients_last_fold.csv",index=False)
    rank_rows=[]
    for year,group in predictions.groupby("target_year"):
        rank_rows.append({"target_year":int(year),"n_destinations":int(len(group)),"eom_energy_rank_spearman":safe_rho(-group["energy_equal_weight"],group["target_net_migration_per_1000"]),"ridge_rank_spearman":safe_rho(group["ridge_prediction"],group["target_net_migration_per_1000"]),"persistence_rank_spearman":safe_rho(group["persistence_baseline"],group["target_net_migration_per_1000"])})
    pd.DataFrame(rank_rows).to_csv(OUTPUTS/"macro_backtest_rank_metrics.csv",index=False)
    print(json.dumps(report,indent=2))
    print(f"Latest equal-weight EOM macro score: {OUTPUTS/'latest_macro_eom_ranking.csv'} (year {latest_year}); scores are not calibrated probabilities.")

if __name__ == "__main__": main()
