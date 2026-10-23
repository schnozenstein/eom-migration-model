"""Build the v0.1 Migrant Hostility & Social Climate Index outputs.

This script does not scrape or infer values. It scores only the explicitly
coded evidence in data/mhsci_initial_evidence.csv and leaves unavailable data
unknown. See docs/mhsci_methodology.md before interpreting any rank.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "mhsci_initial_evidence.csv"
OUT_CSV = ROOT / "outputs" / "mhsci_initial_ranking.csv"
OUT_MD = ROOT / "reports" / "mhsci_latest.md"
SCORE_FIELDS = (
    "public_sentiment_score",
    "group_hostility_score",
    "policy_friction_score",
    "political_rhetoric_score",
)
MIN_COMPONENTS = 3


def parse_score(value: str, *, field: str, country: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{country}: {field} must be blank or an integer 0-4") from exc
    if number < 0 or number > 4:
        raise ValueError(f"{country}: {field} must be in the range 0-4")
    return number


def score_row(row: dict[str, str]) -> dict[str, object]:
    values = [parse_score(row.get(field, ""), field=field, country=row["country"]) for field in SCORE_FIELDS]
    observed = [value for value in values if value is not None]
    score = round(mean(observed) * 25, 1) if len(observed) >= MIN_COMPONENTS else None
    if score is None:
        band = "Not scored"
    elif score < 25:
        band = "Lower signal"
    elif score < 50:
        band = "Moderate"
    elif score < 75:
        band = "Elevated"
    else:
        band = "High"
    return {
        **row,
        "component_count": len(observed),
        "score_0_100": score if score is not None else "",
        "risk_band": band,
    }


def build(input_path: Path = INPUT, out_csv: Path = OUT_CSV, out_md: Path = OUT_MD) -> list[dict[str, object]]:
    with input_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"country", *SCORE_FIELDS, "evidence_confidence", "evidence_summary", "source_urls", "reviewed_on"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"Input CSV missing required fields: {sorted(required - set(reader.fieldnames or []))}")
        ranked = [score_row(row) for row in reader]

    scored = sorted(
        (row for row in ranked if row["score_0_100"] != ""),
        key=lambda row: float(row["score_0_100"]),
        reverse=True,
    )
    for rank, row in enumerate(scored, start=1):
        row["rank"] = rank
    scored_ids = {row["country"] for row in scored}
    for row in ranked:
        row["rank"] = "" if row["country"] not in scored_ids else next(r["rank"] for r in scored if r["country"] == row["country"])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    fields = ["rank", "country", "score_0_100", "risk_band", "component_count", "evidence_confidence", *SCORE_FIELDS, "evidence_summary", "source_urls", "reviewed_on"]
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(ranked, key=lambda r: (r["rank"] == "", r["rank"] if r["rank"] != "" else 999)))

    lines = [
        "# MHSCI v0.1 — Initial Country Risk Comparison",
        "",
        "> Pilot index generated from manually coded evidence. This is not a validated cross-national statistical ranking. See [methodology](../docs/mhsci_methodology.md).",
        "",
        "Reviewed: 2026-10-23. Higher score indicates greater evidence-coded social-climate / migrant-hostility risk.",
        "",
        "| Rank | Destination | Score / 100 | Band | Components | Confidence |",
        "|---:|---|---:|---|---:|---|",
    ]
    for row in scored:
        lines.append(f"| {row['rank']} | {row['country']} | {row['score_0_100']:.1f} | {row['risk_band']} | {row['component_count']}/4 | {row['evidence_confidence']} |")
    lines += [
        "",
        "## Key caveat",
        "",
        "The measures differ by country: public opinion surveys ask different questions, target-group evidence ranges from South-Asian police reports to broad AAPI surveys, and immigration rules measure pathway friction rather than prejudice. Do not use small score differences as meaningful, and do not feed this pilot into EOM's main ranking until validation and weight sensitivity work is complete.",
        "",
        "Countries with fewer than three scored components remain unranked; missing evidence is not treated as zero risk.",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return ranked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--out-csv", type=Path, default=OUT_CSV)
    parser.add_argument("--out-md", type=Path, default=OUT_MD)
    args = parser.parse_args()
    build(args.input, args.out_csv, args.out_md)
    print(f"Wrote {args.out_csv} and {args.out_md}")


if __name__ == "__main__":
    main()
