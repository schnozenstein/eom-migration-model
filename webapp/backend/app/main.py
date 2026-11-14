"""Read-only API over the existing EOM research outputs.

This first web milestone deliberately consumes generated CSV artifacts. It does not
re-run ETL, alter model scores, or present exploratory scores as personal probabilities.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUTS = REPO_ROOT / "outputs"

app = FastAPI(
    title="EOM Research API",
    version="0.1.0",
    description="Read-only API for published EOM research artifacts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

RANKING_FILES = {
    "baseline": ("latest_macro_eom_ranking.csv", "energy_rank", "year"),
    "oecd": ("latest_oecd_enhanced_macro_ranking.csv", "enhanced_rank_20pct", "comparison_year"),
}


def _read_csv(filename: str) -> list[dict[str, Any]]:
    path = OUTPUTS / filename
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"Research artifact is not available: {filename}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "eom-research-api", "version": "0.1.0"}


@app.get("/api/rankings")
def rankings(
    model: str = Query(default="baseline", pattern="^(baseline|oecd)$"),
    limit: int = Query(default=50, ge=1, le=250),
) -> dict[str, Any]:
    filename, rank_field, year_field = RANKING_FILES[model]
    rows = _read_csv(filename)
    rows.sort(key=lambda row: _number(row.get(rank_field)) or float("inf"))
    year_values = [row.get(year_field) for row in rows if row.get(year_field)]
    year = max(year_values, default=None)
    return {
        "model": model,
        "comparison_year": year,
        "count": len(rows),
        "returned": min(limit, len(rows)),
        "methodology_note": (
            "Exploratory macro proxy, not an individual migration probability. "
            "The OECD-enhanced series covers a smaller common sample and a different year."
            if model == "oecd"
            else "Exploratory equal-weight macro proxy; not calibrated or an individual migration probability."
        ),
        "results": rows[:limit],
    }


@app.get("/api/summary")
def summary() -> dict[str, Any]:
    baseline = _read_csv(RANKING_FILES["baseline"][0])
    oecd_path = OUTPUTS / RANKING_FILES["oecd"][0]
    oecd_count = 0
    if oecd_path.is_file():
        with oecd_path.open("r", encoding="utf-8-sig", newline="") as handle:
            oecd_count = sum(1 for _ in csv.DictReader(handle))
    years = sorted({row.get("year") for row in baseline if row.get("year")})
    return {
        "baseline_destinations": len(baseline),
        "baseline_year": years[-1] if years else None,
        "oecd_common_sample_destinations": oecd_count,
        "available_models": ["baseline"] + (["oecd"] if oecd_count else []),
        "status": "research-preview",
    }
