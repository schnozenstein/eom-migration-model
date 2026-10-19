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
