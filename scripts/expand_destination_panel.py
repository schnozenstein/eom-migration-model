#!/usr/bin/env python3
"""Append missing destination-year scaffold rows without imputing observations.

Reads the destination registry and existing panel, adds missing national/region
destinations for 1990-2025, preserves all existing observations, and marks all
source fields as missing until a verified ingestion populates them.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS = ROOT / "data" / "destinations.csv"
PANEL = ROOT / "data" / "historical_destination_year_panel.csv"
START_YEAR, END_YEAR = 1990, 2025
SPECIAL_NAMES = {"EDI": "Scotland / Edinburgh (subnational)"}

registry = pd.read_csv(DESTINATIONS, dtype=str).fillna("")
panel = pd.read_csv(PANEL)
existing = set(panel["destination"].astype(str))
rows = []
for _, d in registry.iterrows():
    code = d["id"]
    name = SPECIAL_NAMES.get(code, d["name"])
    if name in existing:
        continue
    for year in range(START_YEAR, END_YEAR + 1):
        row = {c: pd.NA for c in panel.columns}
        row["destination"] = name
        row["year"] = year
        for c in panel.columns:
            if c.startswith("missing_"):
                row[c] = True
        if "data_level_note" in panel.columns:
            row["data_level_note"] = (
                "Scaffold only; Taiwan source coverage requires separate official-source "
                "mapping; no value inferred"
                if code == "TWN"
                else "Scaffold only; comparable source observations not yet integrated; "
                     "no value inferred"
            )
        rows.append(row)
        existing.add(name)

if rows:
    panel = pd.concat([panel, pd.DataFrame(rows, columns=panel.columns)], ignore_index=True)
panel["year"] = panel["year"].astype(int)
panel = panel.sort_values(["destination", "year"], kind="stable")
if panel.duplicated(["destination", "year"]).any():
    raise ValueError("Duplicate destination-year keys detected")
panel.to_csv(PANEL, index=False)
print(f"Rows: {len(panel)}; destinations: {panel['destination'].nunique()}; "
      f"years: {panel['year'].min()}-{panel['year'].max()}; added: {len(rows)}")
print("Scaffolding is not data ingestion and does not support ranking by itself.")
