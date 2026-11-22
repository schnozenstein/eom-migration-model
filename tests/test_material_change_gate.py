import pandas as pd

from scripts.detect_material_changes import canonical_hash


def test_canonical_hash_is_invariant_to_row_order_and_retrieval_metadata():
    frame = pd.DataFrame(
        {
            "country_code": ["SGP", "CHE"],
            "year": [2025, 2025],
            "value": [123.0, 456.0],
            "retrieved_at_utc": ["2026-11-21T00:00:00Z", "2026-11-21T00:00:00Z"],
        }
    )
    first = canonical_hash(frame, ["country_code", "year", "value"], ["country_code", "year"], ["year", "value"])
    second = canonical_hash(frame.iloc[::-1], ["country_code", "year", "value"], ["country_code", "year"], ["year", "value"])
    assert first == second


def test_canonical_hash_changes_when_a_scoring_value_is_revised():
    frame = pd.DataFrame(
        {
            "country_code": ["SGP", "CHE"],
            "year": [2025, 2025],
            "value": [123.0, 456.0],
        }
    )
    before = canonical_hash(frame, ["country_code", "year", "value"], ["country_code", "year"], ["year", "value"])
    revised = frame.copy()
    revised.loc[revised["country_code"] == "CHE", "value"] = 457.0
    after = canonical_hash(revised, ["country_code", "year", "value"], ["country_code", "year"], ["year", "value"])
    assert before != after


def test_canonical_hash_treats_missing_to_observed_as_material():
    frame = pd.DataFrame({"country_code": ["SGP"], "year": [2025], "value": [None]})
    before = canonical_hash(frame, ["country_code", "year", "value"], ["country_code", "year"], ["year", "value"])
    revised = frame.copy()
    revised.loc[0, "value"] = 1.0
    after = canonical_hash(revised, ["country_code", "year", "value"], ["country_code", "year"], ["year", "value"])
    assert before != after
