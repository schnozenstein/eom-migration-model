import pandas as pd

from eom_empirical import fetch_geopolitical_inputs as geo_inputs
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


def test_wgi_source_uses_current_official_indicator_and_vintage():
    assert "/indicator/GOV_WGI_PV_EST?" in geo_inputs.WB_URL
    assert "date=2025" in geo_inputs.WB_URL
    assert "source=3" not in geo_inputs.WB_URL
    assert geo_inputs.COMPONENTS["regional_conflict_exposure"]["observation_year"] == 2025
    assert "2026 update" in geo_inputs.WB_NAME


def test_world_bank_loader_accepts_standard_indicator_api_payload(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {"page": 1},
                [
                    {"countryiso3code": "NZL", "value": 1.2},
                    {"countryiso3code": "SGP", "value": 1.3},
                ],
            ]

    monkeypatch.setattr(geo_inputs, "get_with_retries", lambda *args, **kwargs: FakeResponse())
    frame = geo_inputs.load_world_bank()
    assert set(frame["country_code"]) == {"NZL", "SGP"}
    assert frame["raw_value"].notna().all()
