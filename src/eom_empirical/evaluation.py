"""Chronological expanding-origin evaluation helpers for macro EOM benchmarks."""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def expanding_origin_backtest(
    panel: pd.DataFrame,
    feature_columns: list[str],
    *,
    min_train_rows: int = 25,
    min_test_rows: int = 8,
    ridge_alpha: float = 2.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit on all prior target years and score the next year, one origin at a time.

    The input panel must already contain only rows with a valid target and the
    requested features. This function never random-splits time-indexed data.
    The persistence baseline uses the observed outcome in the feature year.
    """
    required = {"country_code", "year", "target_year", "target_net_migration_per_1000", "net_migration_per_1000_feature_year", *feature_columns}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    data = panel.copy().replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=feature_columns + ["target_net_migration_per_1000", "target_year"])
    predictions: list[pd.DataFrame] = []
    folds: list[dict] = []
    for target_year in sorted(data["target_year"].dropna().astype(int).unique()):
        train = data[data["target_year"] < target_year]
        test = data[data["target_year"] == target_year]
        if len(train) < min_train_rows or len(test) < min_test_rows:
            continue
        model = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=ridge_alpha))
        model.fit(train[feature_columns], train["target_net_migration_per_1000"])
        out = test[["country_code", "year", "target_year", "target_net_migration_per_1000", "net_migration_per_1000_feature_year"]].copy()
        out = out.rename(columns={"net_migration_per_1000_feature_year": "persistence_baseline"})
        out["ridge_prediction"] = model.predict(test[feature_columns])
        country_mean = train.groupby("country_code")["target_net_migration_per_1000"].mean()
        out["country_mean_baseline"] = out["country_code"].map(country_mean).fillna(float(train["target_net_migration_per_1000"].mean()))
        out["train_rows"] = int(len(train))
        out["test_rows"] = int(len(test))
        out["training_target_year_min"] = int(train["target_year"].min())
        out["training_target_year_max"] = int(train["target_year"].max())
        predictions.append(out)
        folds.append({
            "target_year": int(target_year),
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "training_target_year_min": int(train["target_year"].min()),
            "training_target_year_max": int(train["target_year"].max()),
            "status": "scored"
        })
    pred = pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()
    return pred, pd.DataFrame(folds)
