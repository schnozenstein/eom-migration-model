"""Create an optional EOM social-climate energy scenario from MHSCI v0.1.

Lower EOM energy is better. Higher MHSCI (0-100) means more hostility/risk,
so its standardized value is added as a positive energy penalty. Destinations
without a full MHSCI composite remain unscored in this scenario; they are never
assigned zero hostility or ranked as if evidence were complete. The baseline
macro ranking is not overwritten.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "outputs" / "latest_macro_eom_ranking.csv"
MHSCI = ROOT / "outputs" / "mhsci_initial_ranking.csv"
OUT_CSV = ROOT / "outputs" / "mhsci_adjusted_eom_scenario.csv"
OUT_MD = ROOT / "reports" / "mhsci_eom_scenario.md"


def build_scenario(
    baseline: pd.DataFrame,
    mhsci: pd.DataFrame,
    weight: float = 0.5,
) -> pd.DataFrame:
    """Return baseline rows plus a sensitivity-style social-climate energy scenario.

    weight is the energy penalty for a one-standard-deviation increase in MHSCI.
    Only destinations with a scored, full MHSCI composite are assigned scenario
    energy/rank. Missing evidence stays missing rather than being imputed.
    """
    if weight < 0:
        raise ValueError("weight must be >= 0; hostility should not improve energy")
    required_base = {"destination_name", "energy_equal_weight", "energy_rank"}
    required_mhsci = {"country", "score_0_100", "component_count"}
    if not required_base.issubset(baseline.columns):
        raise ValueError(f"baseline missing columns: {sorted(required_base - set(baseline.columns))}")
    if not required_mhsci.issubset(mhsci.columns):
        raise ValueError(f"MHSCI data missing columns: {sorted(required_mhsci - set(mhsci.columns))}")

    out = baseline.copy()
    m = mhsci[["country", "score_0_100", "component_count"]].copy()
    m["score_0_100"] = pd.to_numeric(m["score_0_100"], errors="coerce")
    m["component_count"] = pd.to_numeric(m["component_count"], errors="coerce")
    m = m.dropna(subset=["score_0_100"])
    m = m[m["component_count"] >= 3]
    m = m.drop_duplicates(subset=["country"], keep="last")
    m = m.rename(columns={"country": "destination_name", "score_0_100": "mhsci_score_0_100"})
    out = out.merge(m, on="destination_name", how="left", validate="many_to_one")

    out["mhsci_z"] = pd.NA
    out["mhsci_energy_penalty"] = pd.NA
    out["energy_mhsci_adjusted"] = pd.NA
    out["mhsci_adjusted_rank"] = pd.NA
    out["mhsci_adjustment_weight"] = float(weight)
    out["mhsci_adjustment_status"] = "not scored: insufficient comparable MHSCI evidence"

    observed = out["mhsci_score_0_100"].notna()
    if observed.sum() >= 2:
        scores = out.loc[observed, "mhsci_score_0_100"].astype(float)
        sd = scores.std(ddof=0)
        z = (scores - scores.mean()) / sd if sd > 0 else scores * 0.0
        out.loc[observed, "mhsci_z"] = z
        out.loc[observed, "mhsci_energy_penalty"] = weight * z
        out.loc[observed, "energy_mhsci_adjusted"] = (
            pd.to_numeric(out.loc[observed, "energy_equal_weight"], errors="coerce")
            + weight * z
        )
        out.loc[observed, "mhsci_adjustment_status"] = (
            "provisional scenario only; composite score is ordinal/manual"
        )
        out.loc[observed, "mhsci_adjusted_rank"] = (
            out.loc[observed, "energy_mhsci_adjusted"]
            .rank(method="min", ascending=True)
            .astype("Int64")
        )
    elif observed.sum() == 1:
        out.loc[observed, "mhsci_adjustment_status"] = (
            "one scored destination only; cannot standardize or rank comparatively"
        )
    return out


def write_report(result: pd.DataFrame, weight: float, path: Path) -> None:
    scored = result[result["energy_mhsci_adjusted"].notna()].sort_values("energy_mhsci_adjusted")
    unscored = int(result["energy_mhsci_adjusted"].isna().sum())
    lines = [
        "# EOM Social-Climate Energy Scenario (MHSCI)",
        "",
        f"- Standardized MHSCI penalty weight: **{weight:.2f} EOM energy units per MHSCI standard deviation**.",
        "- Direction: higher hostility adds energy; lower hostility reduces energy. Lower total energy remains better.",
        "- This is a separate exploratory scenario. The baseline macro ranking is not overwritten.",
        "- Only destinations with a full provisional MHSCI composite (at least 3 of 4 coded dimensions) receive adjusted energy.",
        "- General immigration attitudes and manually coded evidence are not a validated measure of anti-Indian hostility; treat results as provisional.",
        f"- Destinations in baseline: {len(result)}; destinations with comparable scored MHSCI: {len(scored)}; unscored in this scenario: {unscored}.",
        "",
        "## Scored destinations",
        "",
        "| Scenario rank | Destination | Baseline energy | MHSCI (0–100) | Energy penalty | Adjusted energy |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for _, row in scored.iterrows():
        lines.append(
            f"| {int(row['mhsci_adjusted_rank'])} | {row['destination_name']} | "
            f"{float(row['energy_equal_weight']):.3f} | {float(row['mhsci_score_0_100']):.1f} | "
            f"{float(row['mhsci_energy_penalty']):+.3f} | {float(row['energy_mhsci_adjusted']):.3f} |"
        )
    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- Adjusted ranks compare only the destinations with scored MHSCI composites. Do not compare these ranks directly against unscored destinations.",
        "- The adjustment weight is a sensitivity parameter, not an empirically estimated causal effect. Re-run at several weights before drawing conclusions.",
        "- The original EOM macro rank and energy columns are preserved unchanged.",
        "- Missing evidence is not zero hostility and is not a favorable score.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weight", type=float, default=0.5,
                        help="energy penalty per one SD of MHSCI (default: 0.5)")
    args = parser.parse_args()
    baseline = pd.read_csv(BASELINE)
    mhsci = pd.read_csv(MHSCI)
    result = build_scenario(baseline, mhsci, weight=args.weight)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_CSV, index=False)
    write_report(result, args.weight, OUT_MD)
    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")
    print(f"Scored destinations: {result['energy_mhsci_adjusted'].notna().sum()} / {len(result)}")


if __name__ == "__main__":
    main()
