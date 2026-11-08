from scripts.create_daily_summary import freshness_warning_text


def test_freshness_warning_lists_slow_release_indicators():
    attention = [{
        "indicator_code": "NY.GDP.TOTL.RT.ZS",
        "indicator_name": "Total natural resources rents (% of GDP)",
        "latest_observation_year": 2021,
        "freshness_status": "STALE_OR_SLOW_RELEASE",
    }]
    warning = freshness_warning_text(True, "success", attention)
    assert "1 indicator(s) require attention" in warning
    assert "NY.GDP.TOTL.RT.ZS" in warning
    assert "2021" in warning


def test_freshness_warning_is_clear_when_all_indicators_are_recent():
    assert freshness_warning_text(True, "success", []) == "None; all monitored indicators are recent."


def test_freshness_warning_reports_stale_manifest_separately():
    warning = freshness_warning_text(False, "success", [])
    assert "did not write a current manifest" in warning
