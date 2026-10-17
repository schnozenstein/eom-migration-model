"""Summarize sourced Tech-MBA cohort transitions with confidence intervals.

This module does not fit a personal probability model. It summarizes the observed
stage rates only when counts and denominators are supplied with compatible definitions.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "templates" / "pathway_cohorts.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "pathway_transition_summary.csv"
STAGES = {
    "graduation": ("graduation_count", "graduation_denominator"),
    "relevant_employment_6m": ("relevant_employed_6m_count", "employment_denominator"),
    "sponsored_status_24m": ("sponsored_status_24m_count", "sponsorship_denominator"),
    "destination_employment_3y": ("employed_destination_3y_count", "retention_denominator"),
    "long_term_status_8y": ("long_term_status_8y_count", "settlement_denominator"),
}


def wilson_interval(successes: float, trials: float, z: float = 1.959963984540054):
    if pd.isna(successes) or pd.isna(trials) or trials <= 0 or successes < 0 or successes > trials:
        return (np.nan, np.nan, np.nan)
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    half = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return p, max(0.0, center - half), min(1.0, center + half)


def build_summary(cohorts: pd.DataFrame) -> pd.DataFrame:
    required = {"destination_id", "programme_id"}
    for count_col, denom_col in STAGES.values():
        required.add(count_col); required.add(denom_col)
    missing = required - set(cohorts.columns)
    if missing:
        raise ValueError(f"Missing required cohort columns: {sorted(missing)}")
    rows = []
    for (destination, programme), group in cohorts.groupby(["destination_id", "programme_id"], dropna=False):
        row = {"destination_id": destination, "programme_id": programme, "cohort_rows": int(len(group))}
        for stage, (count_col, denom_col) in STAGES.items():
            counts = pd.to_numeric(group[count_col], errors="coerce")
            denoms = pd.to_numeric(group[denom_col], errors="coerce")
            # Pool only explicit observed counts/denominators; do not treat missing as zero.
            valid = counts.notna() & denoms.notna() & (denoms > 0)
            s = float(counts[valid].sum()) if valid.any() else np.nan
            n = float(denoms[valid].sum()) if valid.any() else np.nan
            rate, lo, hi = wilson_interval(s, n)
            row[f"{stage}_successes"] = s
            row[f"{stage}_denominator"] = n
            row[f"{stage}_rate"] = rate
            row[f"{stage}_ci95_low"] = lo
            row[f"{stage}_ci95_high"] = hi
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    cohorts = pd.read_csv(args.input)
    if cohorts.empty:
        raise ValueError(f"{args.input} has no observations yet. Populate it only from cited cohort sources.")
    summary = build_summary(cohorts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)
    print(f"Saved sourced cohort transition summary to {args.output}")

if __name__ == "__main__":
    main()
