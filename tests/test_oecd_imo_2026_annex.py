from io import BytesIO
import pandas as pd
from openpyxl import Workbook
from scripts.oecd_imo_2026_annex import parse_numeric, parse_statlink_workbook

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


def _history_row(**overrides):
    row = {column: "" for column in __import__("scripts.oecd_imo_2026_annex", fromlist=["OUTPUT_COLUMNS"]).OUTPUT_COLUMNS}
    row.update({
        "table_code": "A.4",
        "table_heading": "Table A.4. Stocks of foreign-born population in OECD countries",
        "destination": "Canada",
        "origin": "",
        "measure": "foreign_born_population_stock",
        "year": 2025,
        "value": None,
        "raw_value": "",
        "unit": "thousands",
        "observation_status": "missing",
        "missing_marker": "",
        "publisher": "Organisation for Economic Co-operation and Development (OECD)",
        "source_url": "https://stat.link/files/a9eab36b-en/2d1v8s.xlsx",
        "source_permalink": "https://stat.link/2d1v8s",
        "source_page": "https://www.oecd.org/en/publications/international-migration-outlook-2026_a9eab36b-en/full-report/statistical-annex_f79de055.html",
        "release_date": "2026-11-12",
        "source_vintage": "IMO2026-2026-11-12",
        "source_version": "1",
        "source_sheet": "A4_EN_2026",
        "retrieved_at_utc": "2026-11-16T17:26:36+00:00",
        "run_id": "first-run",
        "raw_snapshot_sha256": "hash-1",
    })
    row.update(overrides)
    return row


def test_identical_missing_cell_is_not_appended_as_a_revision(tmp_path):
    from scripts.oecd_imo_2026_annex import OUTPUT_COLUMNS, append_revision_history

    path = tmp_path / "history.csv"
    original = _history_row()
    pd.DataFrame([original], columns=OUTPUT_COLUMNS).to_csv(path, index=False)

    current = pd.DataFrame([_history_row(
        retrieved_at_utc="2026-11-17T00:00:00+00:00",
        run_id="second-run",
        raw_snapshot_sha256="hash-2",
    )], columns=OUTPUT_COLUMNS)
    stats = append_revision_history(current, path)

    assert stats["inserted_new_natural_keys"] == 0
    assert stats["appended_revisions"] == 0
    assert stats["appended_value_revisions"] == 0
    assert stats["appended_metadata_revisions"] == 0
    assert stats["unchanged_keys_skipped"] == 1
    assert len(pd.read_csv(path)) == 1


def test_source_vintage_change_is_recorded_without_a_value_change(tmp_path):
    from scripts.oecd_imo_2026_annex import OUTPUT_COLUMNS, append_revision_history

    path = tmp_path / "history.csv"
    original = _history_row(
        value=123.0, raw_value="123", observation_status="observed",
        source_vintage="v1", source_version="1",
    )
    pd.DataFrame([original], columns=OUTPUT_COLUMNS).to_csv(path, index=False)

    current = pd.DataFrame([_history_row(
        value=123.0, raw_value="123", observation_status="observed",
        source_vintage="v2", source_version="2",
        retrieved_at_utc="2026-11-17T00:00:00+00:00",
        run_id="second-run",
    )], columns=OUTPUT_COLUMNS)
    stats = append_revision_history(current, path)

    assert stats["appended_revisions"] == 1
    assert stats["appended_value_revisions"] == 0
    assert stats["appended_metadata_revisions"] == 1
    assert stats["unchanged_keys_skipped"] == 0
    assert len(pd.read_csv(path)) == 2


def test_actual_numeric_change_is_recorded_as_value_revision(tmp_path):
    from scripts.oecd_imo_2026_annex import OUTPUT_COLUMNS, append_revision_history

    path = tmp_path / "history.csv"
    original = _history_row(
        value=123.0, raw_value="123", observation_status="observed",
    )
    pd.DataFrame([original], columns=OUTPUT_COLUMNS).to_csv(path, index=False)

    current = pd.DataFrame([_history_row(
        value=124.0, raw_value="124", observation_status="observed",
        retrieved_at_utc="2026-11-17T00:00:00+00:00",
        run_id="second-run",
    )], columns=OUTPUT_COLUMNS)
    stats = append_revision_history(current, path)

    assert stats["appended_revisions"] == 1
    assert stats["appended_value_revisions"] == 1
    assert stats["appended_metadata_revisions"] == 0
    assert stats["unchanged_keys_skipped"] == 0
    assert len(pd.read_csv(path)) == 2
