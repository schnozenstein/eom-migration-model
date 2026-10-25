import pandas as pd
import pytest

from scripts.build_mhsci_eom_sensitivity import build_sensitivity


def test_adjustment_penalizes_higher_hostility_and_preserves_macro_energy():
    baseline = pd.DataFrame({
        "destination_id": ["A", "B", "C"],
        "destination_name": ["Low", "Mid", "High"],
        "energy_equal_weight": [-2.0, -1.0, 0.0],
        "energy_rank": [1, 2, 3],
    })
    mhsci = pd.DataFrame({
        "country": ["Low", "Mid", "High"],
        "score_0_100": [10, 50, 90],
        "component_count": [4, 4, 4],
    })
    result = build_sensitivity(baseline, mhsci).set_index("destination_name")
    assert result.loc["High", "energy_mhsci_adjusted_lambda_0_5"] > result.loc["High", "energy_equal_weight"]
    assert result.loc["Low", "energy_mhsci_adjusted_lambda_0_5"] < result.loc["Low", "energy_equal_weight"]
    assert result.loc["Low", "energy_equal_weight"] == -2.0


def test_missing_or_incomplete_mhsci_is_not_ranked():
    baseline = pd.DataFrame({
        "destination_id": ["A", "B"],
        "destination_name": ["Scored", "Missing"],
        "energy_equal_weight": [-1.0, -2.0],
        "energy_rank": [2, 1],
    })
    mhsci = pd.DataFrame({
        "country": ["Scored", "Missing"],
        "score_0_100": [50, None],
        "component_count": [3, 0],
    })
    result = build_sensitivity(baseline, mhsci).set_index("destination_name")
    assert pd.isna(result.loc["Missing", "energy_mhsci_adjusted_lambda_0_5"])
    assert pd.isna(result.loc["Missing", "rank_lambda_0_5"])


def test_negative_weight_rejected():
    base = pd.DataFrame({
        "destination_id": ["A"], "destination_name": ["A"],
        "energy_equal_weight": [-1.0], "energy_rank": [1],
    })
    mh = pd.DataFrame({"country": ["A"], "score_0_100": [50], "component_count": [3]})
    with pytest.raises(ValueError):
        build_sensitivity(base, mh, weights=(-0.1,))
