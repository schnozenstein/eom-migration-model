from io import BytesIO
import pandas as pd
from openpyxl import Workbook
from scripts.oecd_imo_2026_annex import parse_numeric, parse_statlink_workbook

def test_missing_markers_are_not_zero():
    assert parse_numeric("..") == (None, "missing", "..")
    assert parse_numeric(".") == (None, "missing", ".")
    assert parse_numeric("1 234.5") == (1234.5, "observed", "")

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
    assert len(frame) == 4
    assert ((frame.measure == "foreign_born_population_stock") & (frame.unit == "thousands")).sum() == 2
    assert ((frame.measure == "foreign_born_population_share") & (frame.unit == "percent")).sum() == 2
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
    assert len(share) == 2
    assert set(share.destination) == {"Poland"}
    assert set(share.unit) == {"percent"}
