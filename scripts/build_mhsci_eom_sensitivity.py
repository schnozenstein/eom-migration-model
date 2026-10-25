"""Build evidence-gated EOM social-climate sensitivity scenarios.

This adds the provisional MHSCI hostility penalty to the existing macro energy
for lambda values 0.25, 0.50, and 1.00. It never imputes missing hostility as
zero. Ranks are meaningful only within the destinations with a scored MHSCI
composite, not across the full destination registry.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "outputs" / "latest_macro_eom_ranking.csv"
MHSCI = ROOT / "outputs" / "mhsci_initial_ranking.csv"
OUT_CSV = ROOT / "outputs" / "mhsci_adjusted_eom_sensitivity.csv"
OUT_MD = ROOT / "reports" / "mhsci_eom_sensitivity.md"
WEIGHTS = (0.25, 0.50, 1.00)


def build_sensitivity(baseline: pd.DataFrame, mhsci: pd.DataFrame,
                      weights: tuple[float, ...] = WEIGHTS) -> pd.DataFrame:
    required_base = {"destination_id", "destination_name", "energy_equal_weight", "energy_rank"}
    required_mhsci = {"country", "score_0_100", "component_count"}
    if not required_base.issubset(baseline.columns):
        raise ValueError(f"baseline missing columns: {sorted(required_base - set(baseline.columns))}")
    if not required_mhsci.issubset(mhsci.columns):
        raise ValueError(f"MHSCI data missing columns: {sorted(required_mhsci - set(mhsci.columns))}")
    if any(w < 0 for w in weights):
        raise ValueError("all hostility weights must be >= 0")

    out = baseline.copy()
    m = mhsci[["country", "score_0_100", "component_count"]].copy()
    m["score_0_100"] = pd.to_numeric(m["score_0_100"], errors="coerce")
    m["component_count"] = pd.to_numeric(m["component_count"], errors="coerce")
    m = m[(m["component_count"] >= 3) & m["score_0_100"].notna()]
    m = m.drop_duplicates("country", keep="last").rename(
        columns={"country": "destination_name", "score_0_100": "mhsci_score_0_100"}
    )
    out = out.merge(m, on="destination_name", how="left", validate="many_to_one")
    out["mhsci_component_count"] = out["component_count"]
    out["mhsci_z"] = pd.NA
    out["mhsci_adjustment_status"] = "not scored: insufficient comparable MHSCI evidence"

    observed = out["mhsci_score_0_100"].notna()
    if int(observed.sum()) >= 2:
        scores = out.loc[observed, "mhsci_score_0_100"].astype(float)
        sd = scores.std(ddof=0)
        out.loc[observed, "mhsci_z"] = (scores - scores.mean()) / sd if sd > 0 else 0.0
        out.loc[observed, "mhsci_adjustment_status"] = (
            "provisional scenario only; ordinal/manual MHSCI; compare scored destinations only"
        )

    for weight in weights:
        suffix = str(weight).replace(".", "_")
        energy_col = f"energy_mhsci_adjusted_lambda_{suffix}"
        rank_col = f"rank_lambda_{suffix}"
        out[energy_col] = pd.NA
        out[rank_col] = pd.NA
        eligible = observed & pd.to_numeric(out["energy_equal_weight"], errors="coerce").notna()
        out.loc[eligible, energy_col] = (
            pd.to_numeric(out.loc[eligible, "energy_equal_weight"], errors="coerce")
            + weight * pd.to_numeric(out.loc[eligible, "mhsci_z"], errors="coerce")
        )
        out.loc[eligible, rank_col] = (
            pd.to_numeric(out.loc[eligible, energy_col], errors="coerce")
            .rank(method="min", ascending=True).astype("Int64")
        )
        out[f"lambda_{suffix}"] = weight
    return out


def write_report(result: pd.DataFrame, path: Path) -> None:
    scored = result[result["mhsci_score_0_100"].notna()].copy()
    lines = [
        "# EOM Social-Climate Sensitivity Analysis",
        "",
        "- Baseline: latest macro EOM energy, preserved unchanged.",
        "- Adjustment: `E_adj = E_macro + lambda × z(MHSCI)`; higher MHSCI means greater adverse social-climate signal, so it raises energy.",
        "- Tested lambda values: 0.25, 0.50, and 1.00 energy units per one standard deviation of MHSCI.",
        "- Lambda is illustrative, not estimated from observed migration choices.",
        f"- Macro destinations: {len(result)}; destinations with a scored MHSCI composite: {len(scored)}; destinations left unscored for this adjustment: {len(result) - len(scored)}.",
        "- Scores use heterogeneous, manually coded evidence. This is a pilot scenario, not a validated anti-Indian-hostility measure.",
        "- Ranks below compare only the scored subset. Unscored destinations are not assigned zero hostility and are not treated as safer.",
        "",
        "## Sensitivity ranks",
        "",
        "| Destination | Macro energy | MHSCI / 100 | Rank λ=0.25 | Rank λ=0.50 | Rank λ=1.00 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in scored.sort_values("energy_mhsci_adjusted_lambda_0_5").iterrows():
        ranks = []
        for w in WEIGHTS:
            col = f"rank_lambda_{str(w).replace('.', '_')}"
            value = row[col]
            ranks.append(str(int(value)) if pd.notna(value) else "—")
        lines.append(
            f"| {row['destination_name']} | {float(row['energy_equal_weight']):.3f} | "
            f"{float(row['mhsci_score_0_100']):.1f} | " + " | ".join(ranks) + " |"
        )
    lines += [
        "",
        "## Interpretation and remaining gates",
        "",
        "This sensitivity run adds only the social-climate layer. It does not claim to be the complete EOM total-energy ranking: the comparable geopolitical inputs, quality-of-life panel, and verified profile-specific visa/PR feasibility inputs are incomplete. The separate geography risk pipeline remains evidence-gated.",
        "",
        "Historical backtests currently show the persistence baseline outperforming the macro EOM score. Do not interpret these scenario ranks as calibrated migration probabilities or as proof of predictive validity.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    baseline = pd.read_csv(BASELINE)
    mhsci = pd.read_csv(MHSCI)
    result = build_sensitivity(baseline, mhsci)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_CSV, index=False)
    write_report(result, OUT_MD)
    print(f"Wrote {OUT_CSV}; scored {result['mhsci_score_0_100'].notna().sum()} destinations")


if __name__ == "__main__":
    main()
