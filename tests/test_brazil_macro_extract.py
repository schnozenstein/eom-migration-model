import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "refresh_eom_data_for_test", ROOT / "scripts" / "refresh_eom_data.py"
)
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)


def test_brazil_extract_filters_other_countries_and_updates_latest_vintage(tmp_path):
    output = tmp_path / "brazil_world_bank_macro.csv"
    first = pd.DataFrame([
        {"country_code": "BRA", "indicator_code": "NY.GDP.PCAP.CD", "year": 2020, "value": 7000, "retrieved_utc": "2026-10-20T00:00:00+00:00", "run_id": "first"},
        {"country_code": "ESP", "indicator_code": "NY.GDP.PCAP.CD", "year": 2020, "value": 28000, "retrieved_utc": "2026-10-20T00:00:00+00:00", "run_id": "first"},
    ])
    assert refresh.update_brazil_macro_extract(first, output) == 1
    saved = pd.read_csv(output)
    assert set(saved["country_code"]) == {"BRA"}
    assert saved.iloc[0]["value"] == 7000

    second = pd.DataFrame([
        {"country_code": "BRA", "indicator_code": "NY.GDP.PCAP.CD", "year": 2020, "value": 7200, "retrieved_utc": "2026-10-21T00:00:00+00:00", "run_id": "second"},
    ])
    assert refresh.update_brazil_macro_extract(second, output) == 1
    saved = pd.read_csv(output)
    assert len(saved) == 1
    assert saved.iloc[0]["value"] == 7200
    assert saved.iloc[0]["run_id"] == "second"


def test_failed_or_empty_brazil_pull_does_not_delete_existing_extract(tmp_path):
    output = tmp_path / "brazil_world_bank_macro.csv"
    first = pd.DataFrame([
        {"country_code": "BRA", "indicator_code": "SP.POP.TOTL", "year": 2020, "value": 212000000, "retrieved_utc": "2026-10-20T00:00:00+00:00", "run_id": "first"},
    ])
    refresh.update_brazil_macro_extract(first, output)
    assert refresh.update_brazil_macro_extract(pd.DataFrame(columns=["country_code"]), output) == 0
    saved = pd.read_csv(output)
    assert len(saved) == 1
    assert saved.iloc[0]["value"] == 212000000
