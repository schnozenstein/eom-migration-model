import pandas as pd

from eom_empirical.fetch_geopolitical_inputs import quintile_score


def test_higher_safety_value_maps_to_lower_exposure():
    scores = quintile_score(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]), higher_is_safer=True)
    assert scores.iloc[0] > scores.iloc[-1]
    assert scores.min() >= 1
    assert scores.max() <= 5


def test_higher_risk_value_maps_to_higher_exposure():
    scores = quintile_score(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]), higher_is_safer=False)
    assert scores.iloc[0] < scores.iloc[-1]


def test_missing_values_remain_unknown():
    scores = quintile_score(pd.Series([1.0, None, 3.0, 4.0, 5.0]), higher_is_safer=True)
    assert pd.isna(scores.iloc[1])
    assert scores.notna().sum() == 4
