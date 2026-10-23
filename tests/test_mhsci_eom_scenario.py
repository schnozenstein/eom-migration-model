import pandas as pd
import pytest

from scripts.build_mhsci_eom_scenario import build_scenario


def baseline():
    return pd.DataFrame({
        "destination_name": ["Canada", "Ireland", "Japan", "Singapore"],
        "energy_equal_weight": [-2.0, -1.0, -1.5, -3.0],
        "energy_rank": [2, 4, 3, 1],
    })


def mhsci():
    return pd.DataFrame({
        "country": ["Canada", "Ireland", "Japan"],
        "score_0_100": [90.0, 20.0, ""],
        "component_count": [4, 3, 2],
    })


def test_higher_hostility_increases_energy_and_lower_hostility_decreases_it():
    result = build_scenario(baseline(), mhsci(), weight=0.5).set_index("destination_name")
    assert result.loc["Canada", "energy_mhsci_adjusted"] > result.loc["Canada", "energy_equal_weight"]
    assert result.loc["Ireland", "energy_mhsci_adjusted"] < result.loc["Ireland", "energy_equal_weight"]


def test_missing_or_incomplete_mhsci_is_not_scored_or_ranked():
    result = build_scenario(baseline(), mhsci()).set_index("destination_name")
    for country in ["Japan", "Singapore"]:
        assert pd.isna(result.loc[country, "energy_mhsci_adjusted"])
        assert pd.isna(result.loc[country, "mhsci_adjusted_rank"])


def test_baseline_energy_is_preserved():
    base = baseline()
    result = build_scenario(base, mhsci()).set_index("destination_name")
    for _, row in base.iterrows():
        assert result.loc[row["destination_name"], "energy_equal_weight"] == row["energy_equal_weight"]


def test_negative_weight_is_rejected():
    with pytest.raises(ValueError):
        build_scenario(baseline(), mhsci(), weight=-0.1)
