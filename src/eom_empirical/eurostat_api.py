"""Validated, small-scope Eurostat migration-flow adapter.

This connector retrieves Spain's annual total immigration and emigration series.
It intentionally keeps the two flow measures distinct from migrant stocks and
from immigration classified by citizenship, birth, or previous residence.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

EUROSTAT_API_BASE = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
)
DATASETS = (
    ("emigration_total", "migr_emi2"),
    ("immigration_total", "migr_imm8"),
)
SELECTED_DIMENSIONS = {
    "freq": "A",
    "unit": "NR",
    "age": "TOTAL",
    "agedef": "REACH",
    "sex": "T",
}


def _category_codes_by_position(payload: dict, dimension_id: str) -> dict[int, str]:
    dimension = payload.get("dimension", {}).get(dimension_id, {})
    index = dimension.get("category", {}).get("index", {})
    if isinstance(index, dict):
        return {int(position): str(code) for code, position in index.items()}
    if isinstance(index, list):
        return {position: str(code) for position, code in enumerate(index)}
    return {}


def _value_items(payload: dict):
    values = payload.get("value", {})
    if isinstance(values, dict):
        for position, value in values.items():
            yield int(position), value
    elif isinstance(values, list):
        yield from enumerate(values)
    elif values is None:
        return
    else:
        raise ValueError("Eurostat JSON-stat 'value' must be an object or list")


def parse_jsonstat_observations(
    payload: dict,
    *,
    requested_geo: str = "ES",
    start_year: int = 2010,
    end_year: int = 2026,
) -> tuple[dict[int, float | None], dict[int, str]]:
    """Decode JSON-stat's flattened cells into year-keyed observations.

    Missing/suppressed years remain None; absent values are never converted to zero.
    """
    dimension_ids = [str(item) for item in payload.get("id", [])]
    sizes = [int(item) for item in payload.get("size", [])]
    if not dimension_ids or len(dimension_ids) != len(sizes):
        raise ValueError("Eurostat response has invalid JSON-stat dimensions")
    dimensions = {name.lower(): name for name in dimension_ids}
    if "geo" not in dimensions or "time" not in dimensions:
        raise ValueError("Eurostat response must include geo and time dimensions")

    codes_by_position = {
        name.lower(): _category_codes_by_position(payload, name)
        for name in dimension_ids
    }
    if not codes_by_position["geo"] or not codes_by_position["time"]:
        raise ValueError("Eurostat response is missing geo or time category indexes")

    values_by_year: dict[int, float | None] = {}
    flags_by_year: dict[int, str] = {}
    status_map = payload.get("status") or payload.get("extension", {}).get("status", {})
    if not isinstance(status_map, dict):
        status_map = {}

    for flat_position, raw_value in _value_items(payload):
        if flat_position < 0 or flat_position >= math.prod(sizes):
            raise ValueError("Eurostat JSON-stat cell index is outside the dimensions")
        coordinates = {}
        for offset, (dimension_id, size) in enumerate(zip(dimension_ids, sizes)):
            stride = math.prod(sizes[offset + 1:]) if offset + 1 < len(sizes) else 1
            position = (flat_position // stride) % size
            coordinates[dimension_id.lower()] = codes_by_position[
                dimension_id.lower()
            ].get(position)

        if coordinates.get("geo") != requested_geo:
            continue
        if any(
            name in coordinates and coordinates[name] != expected
            for name, expected in SELECTED_DIMENSIONS.items()
        ):
            continue
        year_code = coordinates.get("time", "")
        try:
            year = int(year_code)
        except (TypeError, ValueError):
            continue
        if year < start_year or year > end_year:
            continue

        try:
            value = None if raw_value is None else float(raw_value)
        except (TypeError, ValueError):
            value = None
        values_by_year[year] = value
        source_flag = status_map.get(str(flat_position), status_map.get(flat_position, ""))
        if isinstance(source_flag, dict):
            source_flag = source_flag.get("label", source_flag.get("status", ""))
        flags_by_year[year] = str(source_flag or "")

    return values_by_year, flags_by_year


def fetch_spain_migration_flows(
    session,
    *,
    run_id: str,
    start_year: int,
    end_year: int,
    snapshot_dir: Path,
) -> tuple[list[dict], list[dict]]:
    """Fetch Spain's annual total immigration/emigration series from Eurostat.

    Per-dataset failures are reported separately. Existing canonical data can be
    retained by the caller when a source fails.
    """
    rows: list[dict] = []
    statuses: list[dict] = []
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    for indicator, dataset in DATASETS:
        url = f"{EUROSTAT_API_BASE}/{dataset}"
        params = {
            "lang": "EN",
            "geo": "ES",
            "freq": "A",
            "unit": "NR",
            "age": "TOTAL",
            "agedef": "REACH",
            "sex": "T",
            "sinceTimePeriod": start_year,
            "untilTimePeriod": end_year,
        }
        try:
            response = session.get(url, params=params, timeout=(8, 30))
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or "id" not in payload or "size" not in payload:
                raise ValueError(f"Unexpected Eurostat JSON-stat response for {dataset}")
            (snapshot_dir / f"{dataset}.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            observed, flags = parse_jsonstat_observations(
                payload, requested_geo="ES", start_year=start_year, end_year=end_year
            )
            observed_count = sum(value is not None for value in observed.values())
            retrieved = datetime.now(timezone.utc).isoformat()
            for year in range(start_year, end_year + 1):
                value = observed.get(year)
                flag = flags.get(year, "")
                rows.append({
                    "geo_code": "ES",
                    "destination": "Spain",
                    "year": year,
                    "indicator": indicator,
                    "value": value,
                    "observation_status": (
                        "observed" if value is not None else "missing_or_suppressed"
                    ),
                    "source_flag": flag,
                    "source": "Eurostat Statistics API",
                    "source_dataset": dataset,
                    "source_url": response.url,
                    "retrieved_utc": retrieved,
                    "run_id": run_id,
                })
            statuses.append({
                "source_id": f"EUROSTAT_{dataset}",
                "source": "Eurostat Statistics API",
                "dataset": dataset,
                "url": response.url,
                "status": "SUCCESS",
                "rows_fetched": end_year - start_year + 1,
                "observed_rows": int(observed_count),
                "observation_start": start_year,
                "observation_end_requested": end_year,
                "error": "",
            })
        except Exception as exc:
            statuses.append({
                "source_id": f"EUROSTAT_{dataset}",
                "source": "Eurostat Statistics API",
                "dataset": dataset,
                "url": url,
                "status": "FAILED",
                "rows_fetched": 0,
                "observed_rows": 0,
                "observation_start": start_year,
                "observation_end_requested": end_year,
                "error": f"{type(exc).__name__}: {exc}",
            })

    return rows, statuses
