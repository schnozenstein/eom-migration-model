from io import BytesIO
import pandas as pd
from openpyxl import Workbook
from scripts.oecd_imo_2026_annex import (OUTPUT_COLUMNS, append_revision_history, parse_numeric, parse_statlink_workbook)

def test_missing_markers_are_not_zero():
    assert parse_numeric("..") == (None, "missing", "..")
    assert parse_numeric(".") == (None, "missing", ".")
    assert parse_numeric("1 234.5") == (1234.5, "observed", "")
    assert parse_numeric("729 105 (S1)") == (729105.0, "observed", "")
    assert parse_numeric("911 952 (partial)") == (911952.0, "observed", "")

def test_parse_a4_statlink_preserves_stock_and_share_separately():
    wb = Workbook()
    ws = wb.active
    ws.title = "A4_EN_2026"
    ws.append(["Table A.4. Stocks of foreign-born population in OECD countries"])
    ws.append(["Thousands and percentages"])
    ws.append(["", 2020, 2021, 2022, 2023, 2024])
    ws.append(["Germany", 14000, 14200, 14500, 15000, 15500])
    ws.append(["% of total population", 17.0, 17.2, 17.5, 18.0, 18.5])
    about = wb.create_sheet("About this file")
    about.append(["", "Version 1 - Last updated: 12-Nov-2026"])
    buffer = BytesIO()
    wb.save(buffer)
    raw = buffer.getvalue()
    frame, audit = parse_statlink_workbook(
        raw, "https://stat.link/test", "https://stat.link/files/test.xlsx",
        "2026-11-14T00:00:00+00:00", "test-run", "abc123"
    )
    assert set(frame["table_code"]) == {"A.4"}
    assert len(frame) == 10
    assert ((frame.measure == "foreign_born_population_stock") & (frame.unit == "thousands")).sum() == 5
    assert ((frame.measure == "foreign_born_population_share") & (frame.unit == "percent")).sum() == 5
    assert set(frame.destination) == {"Germany"}
    assert audit["release_date"] == "2026-11-12"


def test_a5_share_row_without_percent_symbol_is_not_a_country():
    wb = Workbook()
    ws = wb.active
    ws.title = "A5_EN_2026"
    ws.append(["Table A.5. Stocks of foreign population by nationality in OECD countries"])
    ws.append(["Thousands and percentages"])
    ws.append(["", 2020, 2021, 2022, 2023, 2024])
    ws.append(["Poland", 80.0, 85.0, 90.0, 100.0, 110.0])
    ws.append(["of total population", 0.25, 0.26, 0.27, 0.28, 0.29])
    about = wb.create_sheet("About this file")
    about.append(["", "Version 1 - Last updated: 12-Nov-2026"])
    buffer = BytesIO()
    wb.save(buffer)
    frame, _ = parse_statlink_workbook(
        buffer.getvalue(), "https://stat.link/test", "https://stat.link/files/test.xlsx",
        "2026-11-14T00:00:00+00:00", "test-run", "abc123"
    )
    share = frame[frame.measure == "foreign_population_share"]
    assert len(share) == 5
    assert set(share.destination) == {"Poland"}
    assert set(share.unit) == {"percent"}



def test_append_revision_history_skips_metadata_only_missing_cell_and_keeps_real_revision(tmp_path):
    row = {column: "" for column in OUTPUT_COLUMNS}
    row.update({
        "table_code": "A.4",
        "destination": "Canada",
        "origin": "",
        "measure": "foreign_born_population_stock",
        "year": 2025,
        "value": None,
        "raw_value": "",
        "unit": "thousands",
        "observation_status": "missing",
        "missing_marker": "..",
        "source_version": 1,
        "source_vintage": "IMO2026-2026-11-12",
        "retrieved_at_utc": "2026-11-15T14:58:14+00:00",
        "run_id": "run2",
        "raw_snapshot_sha256": "abc123",
    })
    current = pd.DataFrame([row], columns=OUTPUT_COLUMNS)
    history_path = tmp_path / "history.csv"
    prior = current.copy()
    prior.loc[0, "retrieved_at_utc"] = "2026-11-15T05:45:29+00:00"
    prior.loc[0, "run_id"] = "run1"
    prior.to_csv(history_path, index=False)

    unchanged = append_revision_history(current, history_path)
    assert unchanged["inserted_new_natural_keys"] == 0
    assert unchanged["appended_value_revisions"] == 0
    assert unchanged["unchanged_keys_skipped"] == 1
    assert unchanged["history_rows_after"] == 1

    revised = current.copy()
    revised.loc[0, "value"] = 1300070.0
    revised.loc[0, "raw_value"] = "1 300 070"
    revised.loc[0, "observation_status"] = "observed"
    revision_stats = append_revision_history(revised, history_path)
    assert revision_stats["appended_value_revisions"] == 1
    assert revision_stats["history_rows_after"] == 2
