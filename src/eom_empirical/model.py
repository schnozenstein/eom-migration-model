"""Transparent EOM feature construction and macro validation helpers."""
from __future__ import annotations
import numpy as np
import pandas as pd

FEATURE_MAP = {
    "salary": "NY.GDP.PCAP.PP.KD",
    "cost": "PA.NUS.PRVT.PLI",
    "unemployment": "SL.UEM.TOTL.ZS",
    "policy_proxy": "GOV_WGI_RQ_EST",
    "institution_proxy": "GOV_WGI_GE_EST",
    "stability": "GOV_WGI_PV_EST",
    "population": "SP.POP.TOTL",
    "net_migration": "SM.POP.NETM",
}


def to_wide(panel: pd.DataFrame) -> pd.DataFrame:
    required = {"country_code", "year", "indicator_code", "value"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    wide = panel.pivot_table(
        index=["country_code", "year"], columns="indicator_code", values="value", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    for col in wide.columns:
        if col not in {"country_code", "year"}:
            wide[col] = pd.to_numeric(wide[col], errors="coerce")
    return wide


def add_derived_features(wide: pd.DataFrame) -> pd.DataFrame:
    out = wide.copy()
    if "SM.POP.NETM" in out and "SP.POP.TOTL" in out:
        out["net_migration_per_1000"] = out["SM.POP.NETM"] / out["SP.POP.TOTL"] * 1000
    else:
        out["net_migration_per_1000"] = np.nan
    # All model features are oriented so that larger = more attractive, except cost.
    out["salary_proxy"] = np.log(out["NY.GDP.PCAP.PP.KD"].where(out["NY.GDP.PCAP.PP.KD"] > 0))
    # Prefer current household-consumption price levels and the 2026 WGI series.
    # Fall back to legacy columns for reproducibility with previously downloaded panels.
    out["cost_proxy"] = out["PA.NUS.PRVT.PLI"] if "PA.NUS.PRVT.PLI" in out else out.get("PA.NUS.PPPC.RF", np.nan)
    out["opportunity_proxy"] = -out.get("SL.UEM.TOTL.ZS", np.nan)
    out["policy_proxy"] = out["GOV_WGI_RQ_EST"] if "GOV_WGI_RQ_EST" in out else out.get("RQ.EST", np.nan)
    out["institution_proxy"] = out["GOV_WGI_GE_EST"] if "GOV_WGI_GE_EST" in out else out.get("GE.EST", np.nan)
    out["stability_proxy"] = out["GOV_WGI_PV_EST"] if "GOV_WGI_PV_EST" in out else out.get("PV.EST", np.nan)
    return out


def standard_z(series: pd.Series) -> pd.Series:
    """Mean/std standardization (not median/MAD robust scaling)."""
    values = pd.to_numeric(series, errors="coerce")
    mean = values.mean(skipna=True)
    std = values.std(skipna=True, ddof=0)
    if pd.isna(std) or std == 0:
        return values * np.nan
    return (values - mean) / std


def equal_weight_energy(latest: pd.DataFrame) -> pd.DataFrame:
    """Compute the paper-sign EOM benchmark; scores are not calibrated probabilities."""
    out = latest.copy()
    mapping = {
        "salary_proxy": "salary_z",
        "cost_proxy": "cost_z",
        "policy_proxy": "policy_z",
        "opportunity_proxy": "opportunity_z",
        "institution_proxy": "institution_z",
        "stability_proxy": "stability_z",
    }
    for source, target in mapping.items():
        out[target] = standard_z(out[source]) if source in out.columns else np.nan
    # Paper sign convention, translated to standardized features.
    out["energy_equal_weight"] = (
        -out["salary_z"] + out["cost_z"] - out["policy_z"] - out["opportunity_z"]
        - out["institution_z"] - out["stability_z"]
    )
    out["energy_rank"] = out["energy_equal_weight"].rank(method="min", ascending=True)
    out["score_status"] = "macro proxy; equal weights; not personal probability"
    return out.sort_values("energy_equal_weight", na_position="last")


def make_lagged_panel(wide: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    features = ["salary_proxy", "cost_proxy", "opportunity_proxy", "policy_proxy", "institution_proxy", "stability_proxy"]
    data = add_derived_features(wide).sort_values(["country_code", "year"]).copy()
    for feature in features:
        data[f"lag_{feature}"] = data.groupby("country_code")[feature].shift(0)
    data["target_year"] = data["year"] + 1
    target = data[["country_code", "year", "net_migration_per_1000"]].copy()
    target["target_year"] = target["year"]
    target = target[["country_code", "target_year", "net_migration_per_1000"]]
    result = data.merge(target, on=["country_code", "target_year"], suffixes=("_feature_year", ""), how="left")
    lag_cols = [f"lag_{f}" for f in features]
    result = result.rename(columns={"net_migration_per_1000": "target_net_migration_per_1000"})
    return result, lag_cols
