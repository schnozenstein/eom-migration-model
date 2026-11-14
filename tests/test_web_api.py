from __future__ import annotations

import csv

from fastapi import HTTPException

from webapp.backend.app import main


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_health_endpoint():
    assert main.health()["status"] == "ok"


def test_baseline_rankings_are_sorted_and_limited(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "OUTPUTS", tmp_path)
    _write_csv(tmp_path / "latest_macro_eom_ranking.csv", [
        {"destination_id": "B", "destination_name": "Beta", "country_code": "BET", "year": "2025", "energy_rank": "2"},
        {"destination_id": "A", "destination_name": "Alpha", "country_code": "ALP", "year": "2025", "energy_rank": "1"},
    ])

    response = main.rankings(model="baseline", limit=1)

    assert response["comparison_year"] == "2025"
    assert response["count"] == 2
    assert response["results"][0]["destination_name"] == "Alpha"
    assert response["returned"] == 1


def test_oecd_rankings_use_oecd_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "OUTPUTS", tmp_path)
    _write_csv(tmp_path / "latest_oecd_enhanced_macro_ranking.csv", [
        {"destination_id": "NOR", "destination_name": "Norway", "country_code": "NOR",
         "comparison_year": "2024", "enhanced_rank_20pct": "1"},
    ])

    response = main.rankings(model="oecd", limit=50)

    assert response["comparison_year"] == "2024"
    assert response["results"][0]["destination_name"] == "Norway"


def test_missing_artifact_returns_service_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "OUTPUTS", tmp_path)

    try:
        main.rankings(model="baseline", limit=50)
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("Expected HTTP 503 when the ranking artifact is missing")
