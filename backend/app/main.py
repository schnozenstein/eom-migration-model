from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# backend/app/main.py -> repository root
REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = REPO_ROOT / "outputs"

BASELINE_FILE = OUTPUTS_DIR / "latest_macro_eom_ranking.csv"
OECD_FILE = OUTPUTS_DIR / "latest_oecd_enhanced_macro_ranking.csv"

app = FastAPI(
    title="EOM Research API",
    description=(
        "Read-only API over the existing EOM research outputs. "
        "Scores are exploratory research measures, not individual migration probabilities."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def parse_cell(value: str | None) -> Any:
    """Convert CSV cells to JSON-friendly values without inventing missing data."""
    if value is None or value.strip() == "":
        return None

    cleaned = value.strip()
    try:
        number = float(cleaned)
    except ValueError:
        return cleaned

    if number.is_integer():
        return int(number)
    return number


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Required EOM output is not available: {path.name}",
        )

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {key: parse_cell(value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def get_rankings(
    ranking_type: Literal["baseline", "oecd"],
    oecd_weight: Literal[10, 20, 30] = 20,
) -> dict[str, Any]:
    if ranking_type == "baseline":
        records = read_csv(BASELINE_FILE)
        rank_field = "energy_rank"
        score_field = "energy_equal_weight"
        year_field = "year"
        score_label = "Baseline EOM macro proxy"
        caveat = (
            "Equal-weight macro proxy. It is not calibrated and is not an "
            "individual migration probability."
        )
    else:
        records = read_csv(OECD_FILE)
        rank_field = f"enhanced_rank_{oecd_weight}pct"
        score_field = f"enhanced_energy_{oecd_weight}pct"
        year_field = "comparison_year"
        score_label = f"OECD-enhanced EOM exploratory score ({oecd_weight}% OECD blend)"
        caveat = (
            "OECD-enhanced common-sample comparison. Coverage is narrower than "
            "the baseline ranking; missing OECD coverage is not treated as zero. "
            "This is not an individual migration probability."
        )

    records.sort(
        key=lambda row: (
            row.get(rank_field) is None,
            row.get(rank_field) if row.get(rank_field) is not None else float("inf"),
            str(row.get("destination_name") or ""),
        )
    )
    years = sorted(
        {row.get(year_field) for row in records if row.get(year_field) is not None}
    )
    ranked_count = sum(row.get(rank_field) is not None for row in records)

    return {
        "ranking_type": ranking_type,
        "comparison_year": years[-1] if years else None,
        "rank_field": rank_field,
        "score_field": score_field,
        "score_label": score_label,
        "count": len(records),
        "ranked_count": ranked_count,
        "unranked_count": len(records) - ranked_count,
        "methodology_note": caveat,
        "results": records,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "eom-research-api",
        "outputs": {
            "baseline_ranking_available": BASELINE_FILE.is_file(),
            "oecd_ranking_available": OECD_FILE.is_file(),
        },
    }


@app.get("/api/v1/rankings")
def rankings(
    ranking_type: Literal["baseline", "oecd"] = Query(
        default="baseline",
        alias="type",
        description="Choose the broad baseline ranking or OECD-enhanced common-sample ranking.",
    ),
    oecd_weight: Literal[10, 20, 30] = Query(
        default=20,
        description="OECD blend weight; applies only when type=oecd.",
    ),
) -> dict[str, Any]:
    return get_rankings(ranking_type, oecd_weight)


@app.get("/api/v1/countries/{country_code}")
def country_detail(country_code: str) -> dict[str, Any]:
    code = country_code.strip().upper()
    if not code or len(code) > 3:
        raise HTTPException(status_code=400, detail="Use a valid three-letter destination code.")

    baseline = read_csv(BASELINE_FILE)
    oecd = read_csv(OECD_FILE)

    baseline_row = next(
        (row for row in baseline if str(row.get("country_code", "")).upper() == code),
        None,
    )
    oecd_row = next(
        (row for row in oecd if str(row.get("country_code", "")).upper() == code),
        None,
    )

    if baseline_row is None and oecd_row is None:
        raise HTTPException(status_code=404, detail=f"No EOM data found for {code}.")

    return {
        "country_code": code,
        "destination_name": (
            (baseline_row or oecd_row or {}).get("destination_name")
        ),
        "baseline": baseline_row,
        "oecd_enhanced": oecd_row,
        "coverage": {
            "baseline_available": baseline_row is not None,
            "oecd_common_sample_available": oecd_row is not None,
        },
        "interpretation": (
            "These are exploratory country-level research indicators. "
            "They do not estimate an individual's probability of migrating."
        ),
    }
