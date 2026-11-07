# CBS YTD release panel validation; corrected origin-year mapping checked against the official release.
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "research" / "cbs_nl_migration_release_ytd_2026-11-07.csv"
AUDIT = ROOT / "metadata" / "cbs_nl_source_audit_2026-11-07.csv"


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_cbs_nl_release_is_separate_ytd_panel_with_no_annual_mixing():
    rows = read_csv(PANEL)
    assert len(rows) == 64
    assert {row["period_type"] for row in rows} == {"YTD_JAN_SEP"}
    assert {row["period_start"][-5:] for row in rows} == {"01-01"}
    assert {row["period_end"][-5:] for row in rows} == {"09-30"}
    assert {row["unit"] for row in rows} == {"thousand persons"}
    keys = [(r["source_id"], r["destination_code"], r["origin_code"], r["observation_year"], r["measure"]) for r in rows]
    assert len(keys) == len(set(keys))
    assert all(r["source_release_date"] == "2026-10-30" for r in rows)
    assert all(r["provisional_flag"] == "True" for r in rows if r["observation_year"] == "2026")
    assert all(r["provisional_flag"] == "False" for r in rows if r["observation_year"] != "2026")


def test_cbs_nl_total_ytd_values_and_signed_emigration_are_preserved():
    rows = read_csv(PANEL)
    y2026 = {r["measure"]: float(r["value"]) for r in rows if r["source_id"] == "CBS_NL_YTD_TOTALS" and r["observation_year"] == "2026"}
    assert y2026 == {"immigration": 226.1, "emigration_signed": -159.8, "net_migration": 66.3}
    assert abs((y2026["immigration"] + y2026["emigration_signed"]) - y2026["net_migration"]) <= 0.2


def test_cbs_nl_origin_panel_is_top_ten_selection_not_full_matrix():
    rows = [r for r in read_csv(PANEL) if r["source_id"] == "CBS_NL_YTD_ORIGIN_NET"]
    assert len(rows) == 40
    assert len({r["origin_code"] for r in rows}) == 10
    india = {int(r["observation_year"]): float(r["value"]) for r in rows if r["origin_code"] == "IND"}
    assert india == {2023: 6.6, 2024: 3.3, 2025: 2.7, 2026: 3.3}
    assert all("top" in r["selection_note"].lower() or "ten countries" in r["selection_note"].lower() for r in rows)


def test_cbs_manual_source_audit_is_complete_and_not_counted_as_core_macro_input():
    rows = read_csv(AUDIT)
    assert len(rows) == 2
    assert sum(int(r["normalized_rows"]) for r in rows) == 64
    assert sum(int(r["rows_rejected"]) for r in rows) == 0
    assert sum(int(r["duplicate_rows"]) for r in rows) == 0
    assert all(r["counted_in_core_numeric_totals"] == "False" for r in rows)
