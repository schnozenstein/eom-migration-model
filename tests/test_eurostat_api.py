from eom_empirical.eurostat_api import parse_jsonstat_observations


def _payload(values):
    return {
        "id": ["freq", "unit", "geo", "age", "agedef", "sex", "time"],
        "size": [1, 1, 2, 1, 1, 1, 2],
        "dimension": {
            "freq": {"category": {"index": {"A": 0}}},
            "unit": {"category": {"index": {"NR": 0}}},
            "geo": {"category": {"index": {"ES": 0, "PT": 1}}},
            "age": {"category": {"index": {"TOTAL": 0}}},
            "agedef": {"category": {"index": {"REACH": 0}}},
            "sex": {"category": {"index": {"T": 0}}},
            "time": {"category": {"index": {"2020": 0, "2021": 1}}},
        },
        "value": values,
    }


def test_parser_returns_spain_values_and_excludes_other_geographies():
    # Flat order is geo-major then time: ES 2020/2021, followed by PT 2020/2021.
    values, _flags = parse_jsonstat_observations(
        _payload({"0": 1234, "1": 1500, "2": 9999, "3": 10000}),
        requested_geo="ES",
        start_year=2020,
        end_year=2021,
    )
    assert values == {2020: 1234.0, 2021: 1500.0}


def test_parser_preserves_missing_values_instead_of_substituting_zero():
    values, _flags = parse_jsonstat_observations(
        _payload({"0": 1234, "2": 9999}),
        requested_geo="ES",
        start_year=2020,
        end_year=2021,
    )
    assert values == {2020: 1234.0}


def test_parser_handles_observation_flags_and_invalid_values():
    payload = _payload({"0": ":", "1": 1500})
    payload["status"] = {"0": "e"}
    values, flags = parse_jsonstat_observations(
        payload,
        requested_geo="ES",
        start_year=2020,
        end_year=2021,
    )
    assert values == {2020: None, 2021: 1500.0}
    assert flags[2020] == "e"


def test_parser_rejects_invalid_dimension_metadata():
    try:
        parse_jsonstat_observations({"id": ["time"], "size": []})
    except ValueError as exc:
        assert "invalid JSON-stat dimensions" in str(exc)
    else:
        raise AssertionError("Expected malformed JSON-stat response to be rejected")



def test_sparse_eurostat_merge_preserves_unreturned_prior_and_accepts_explicit_missing():
    import pandas as pd
    from eom_empirical.eurostat_api import merge_eurostat_history

    existing = pd.DataFrame([
        {
            "geo_code": "ES", "indicator": "immigration_total", "year": 2021,
            "value": 1500.0, "source_cell_present": True, "observation_status": "observed",
            "retrieved_utc": "2026-10-19T10:00:00+00:00",
        },
        {
            "geo_code": "ES", "indicator": "immigration_total", "year": 2020,
            "value": 1300.0, "source_cell_present": True, "observation_status": "observed",
            "retrieved_utc": "2026-10-19T10:00:00+00:00",
        },
    ])
    incoming = [
        {
            "geo_code": "ES", "indicator": "immigration_total", "year": 2021,
            "value": None, "source_cell_present": False, "observation_status": "not_returned_by_source",
            "retrieved_utc": "2026-10-20T10:00:00+00:00",
        },
        {
            "geo_code": "ES", "indicator": "immigration_total", "year": 2020,
            "value": None, "source_cell_present": True, "observation_status": "missing_or_suppressed",
            "source_flag": "s", "retrieved_utc": "2026-10-20T10:00:00+00:00",
        },
    ]

    merged = merge_eurostat_history(existing, incoming)
    by_year = merged.set_index("year")

    assert by_year.loc[2021, "value"] == 1500.0
    assert by_year.loc[2021, "observation_status"] == "observed"
    assert pd.isna(by_year.loc[2020, "value"])
    assert by_year.loc[2020, "observation_status"] == "missing_or_suppressed"
    assert by_year.loc[2020, "source_flag"] == "s"
