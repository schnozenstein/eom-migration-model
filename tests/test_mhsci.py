import csv
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_mhsci.py"
spec = importlib.util.spec_from_file_location("build_mhsci", SCRIPT)
mhsci = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mhsci)


def test_missing_dimensions_are_not_zero_and_not_scored():
    row = {
        "country": "Example",
        "public_sentiment_score": "4",
        "group_hostility_score": "",
        "policy_friction_score": "2",
        "political_rhetoric_score": "",
    }
    result = mhsci.score_row(row)
    assert result["component_count"] == 2
    assert result["score_0_100"] == ""
    assert result["risk_band"] == "Not scored"


def test_three_dimensions_allow_score():
    row = {
        "country": "Example",
        "public_sentiment_score": "4",
        "group_hostility_score": "2",
        "policy_friction_score": "3",
        "political_rhetoric_score": "",
    }
    result = mhsci.score_row(row)
    assert result["component_count"] == 3
    assert result["score_0_100"] == 75.0
    assert result["risk_band"] == "High"


def test_invalid_score_rejected():
    with pytest.raises(ValueError):
        mhsci.score_row({
            "country": "Example",
            "public_sentiment_score": "5",
            "group_hostility_score": "",
            "policy_friction_score": "",
            "political_rhetoric_score": "",
        })


def test_initial_dataset_ranks_only_countries_with_three_dimensions(tmp_path):
    mhsci.build(
        input_path=mhsci.INPUT,
        out_csv=tmp_path / "rank.csv",
        out_md=tmp_path / "rank.md",
    )
    with (tmp_path / "rank.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    scored = [r for r in rows if r["score_0_100"]]
    assert len(scored) == 5
    assert scored[0]["country"] == "Canada"
    assert scored[-1]["country"] == "New Zealand"
    assert all(int(r["component_count"]) >= 3 for r in scored)
    assert len(rows) >= 12
