import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "data"
MANIFEST_DIR = ROOT / "metadata" / "refresh_runs"
REPORT = ROOT / "reports" / "latest_daily_summary.md"


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_csv(path):
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def fmt(value, digits=3):
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "Not available"


def yes_no(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Not reported"


def main():
    manifests = sorted(MANIFEST_DIR.glob("*.json")) if MANIFEST_DIR.exists() else []
    manifest = read_json(manifests[-1]) if manifests else {}

    dashboard = read_csv(OUT / "data_freshness_dashboard.csv")
    ranking = read_csv(OUT / "latest_macro_eom_ranking.csv")
    sensitivity = read_csv(OUT / "eom_v2_weight_sensitivity.csv")
    qol = read_csv(OUT / "eom_joie_de_vivre_scores.csv")
    status = read_json(OUT / "eom_v2_run_status.json")
    backtest = read_json(OUT / "macro_backtest.json")

    recent = [r for r in dashboard if r.get("freshness_status") == "RECENT"]
    attention = [r for r in dashboard if r.get("freshness_status") != "RECENT"]
    scored_qol = [
        r for r in qol
        if r.get("joie_de_vivre_score", "").strip()
        and r.get("qol_score_status", "").startswith("scored")
    ]

    ranking.sort(key=lambda r: float(r.get("energy_rank") or 999999))
    lines = [
        "# EOM Daily Research Report",
        "",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## 1. Executive summary",
        "",
        f"- **Latest refresh run:** `{manifest.get('run_id', 'Not reported')}`",
        f"- **Refresh timestamp:** {manifest.get('run_at_utc', 'Not reported')}",
        f"- **World Bank observations fetched:** {manifest.get('world_bank_rows_fetched', 'Not reported')}",
        f"- **World Bank indicator requests:** {manifest.get('world_bank_indicators_successful', 'Not reported')} succeeded; {manifest.get('world_bank_indicators_failed', 'Not reported')} failed",
        f"- **Policy pages:** {manifest.get('policy_pages_successful', 'Not reported')} succeeded; {manifest.get('policy_pages_failed', 'Not reported')} failed",
        f"- **Freshness dashboard:** {len(recent)} recent; {len(attention)} requiring attention out of {len(dashboard)} indicators",
        f"- **Ranking recomputed during refresh:** {yes_no(manifest.get('ranking_recomputed'))}",
        f"- **Forecast issued during refresh:** {yes_no(manifest.get('forecast_issued'))}",
        "",
        "A successful data refresh is not evidence that a ranking or forecast was recalculated.",
        "",
        "## 2. Stored macro ranking",
        "",
        "This is the latest stored macro-proxy ranking, not a personalised migration recommendation. "
        "It does not include complete joie de vivre or individual visa-feasibility scoring.",
        "",
    ]

    if ranking:
        lines += [
            "| Rank | Destination | Year | Macro score |",
            "|---:|---|---:|---:|",
        ]
        for r in ranking[:10]:
            lines.append(
                f"| {r.get('energy_rank', '—')} | {r.get('destination_name', 'Unknown')} "
                f"| {r.get('year', '—')} | {fmt(r.get('energy_equal_weight'))} |"
            )
    else:
        lines.append("No stored macro ranking file or rows were available.")

    lines += [
        "",
        "## 3. Historical model evaluation",
        "",
        f"- **Evaluation status:** {backtest.get('status', 'Not available')}",
        f"- **Target:** {backtest.get('target', 'Not reported')}",
        f"- **Evaluation method:** {backtest.get('evaluation_method', 'Not reported')}",
        f"- **Test observations:** {backtest.get('n_scored', 'Not reported')}",
        f"- **Destinations:** {backtest.get('n_destinations', 'Not reported')}",
        f"- **Rolling test origins:** {backtest.get('rolling_origins_scored', 'Not reported')}",
        "",
        "| Metric | EOM / Ridge | Persistence baseline | Country-mean baseline |",
        "|---|---:|---:|---:|",
        f"| Mean absolute error (MAE; lower is better) | Ridge: {fmt(backtest.get('ridge_mae'))} | {fmt(backtest.get('persistence_baseline_mae'))} | {fmt(backtest.get('country_mean_baseline_mae'))} |",
        f"| Rank correlation (higher is better) | EOM: {fmt(backtest.get('eom_equal_weight_energy_rank_spearman'))}; Ridge: {fmt(backtest.get('ridge_rank_spearman'))} | {fmt(backtest.get('persistence_rank_spearman'))} | Not reported |",
        "",
        "**Interpretation:** These are historical, macro-level evaluation results, not a new forecast. "
        "The stored evaluation reports that persistence performs better than Ridge on MAE and rank correlation. "
        "Investigate baseline construction, sample comparability and forecast-time information availability before drawing strong conclusions.",
        "",
        backtest.get("interpretation", "No additional interpretation was recorded."),
        "",
        "The results evaluate national net migration, not an individual's chance of successful migration. "
        "Correlation is not causation, and an ordinal score is not a calibrated probability.",
        "",
        "## 4. Ranking sensitivity",
        "",
        "The following sensitivity analysis perturbs existing macro-component weights. "
        "Top-five share is the fraction of weight draws in which a destination appeared in the top five; "
        "it is not a probability of migration success or of being the best destination.",
        "",
    ]

    if sensitivity:
        lines += [
            "| Destination | Baseline rank | Median rank | 10th–90th percentile rank | Top-five share |",
            "|---|---:|---:|---:|---:|",
        ]
        for r in sensitivity[:10]:
            try:
                share = f"{100 * float(r['top5_share']):.1f}%"
            except (KeyError, TypeError, ValueError):
                share = "Not available"
            lines.append(
                f"| {r.get('destination_name', 'Unknown')} | {r.get('baseline_rank', '—')} "
                f"| {r.get('median_rank_under_weights_0_8_1_2', '—')} "
                f"| {r.get('p10_rank', '—')}–{r.get('p90_rank', '—')} | {share} |"
            )
    else:
        lines.append("No ranking sensitivity output was available.")

    lines += [
        "",
        "These draws are a weight-sensitivity exercise, not a statistical confidence interval.",
        "",
        "## 5. Joie de vivre and visa feasibility",
        "",
        f"- **Destinations in QoL input file:** {len(qol)}",
        f"- **Destinations with a recorded scored QoL value:** {len(scored_qol)}",
        f"- **Destinations with complete inputs according to model status:** {status.get('joie_de_vivre', {}).get('destinations_with_complete_inputs', 'Not reported')}",
        f"- **QoL weights:** {status.get('joie_de_vivre', {}).get('weight_status', 'Not reported')}",
        f"- **Visa-feasibility destinations scored:** {status.get('feasibility', {}).get('scored_destinations', 'Not reported')}",
        f"- **Feasibility limitation:** {status.get('feasibility', {}).get('reason', 'Not reported')}",
        f"- **Combined EOM ranking status:** {status.get('combined_v2_ranking', 'Not reported')}",
        "",
        "Missing QoL or visa data must remain missing, not be silently converted to zero. "
        "A combined personal migration ranking should wait until comparable wellbeing data and verified, profile-specific feasibility inputs are available.",
        "",
        "## 6. Indicators requiring attention",
        "",
    ]

    if attention:
        lines += [
            "| Indicator | Latest observation year | Status |",
            "|---|---:|---|",
        ]
        for r in attention:
            lines.append(
                f"| {r.get('indicator_code', 'Unknown')} | "
                f"{r.get('latest_observation_year', 'Unknown')} | "
                f"{r.get('freshness_status', 'Unknown')} |"
            )
    else:
        lines.append("No indicators are currently flagged by the dashboard.")

    lines += [
        "",
        "A recent retrieval timestamp does not guarantee a recent statistical observation. "
        "Some indicators are released with a delay, so check release schedules before labelling them defective.",
        "",
        "## 7. Next research actions",
        "",
        "- Investigate failed data requests and retry policy pages that were not retrieved.",
        "- Check observation years and source release schedules for indicators needing attention.",
        "- Investigate why the persistence baseline outperforms Ridge and EOM in the stored backtest.",
        "- Verify that every predictor would have been available at the forecast date; inspect missing-data handling and baseline definitions.",
        "- Obtain comparable, sourced wellbeing and work-life indicators before calculating joie de vivre scores.",
        "- Add verified visa routes, eligibility, funds, language and study-to-work pathways for a defined applicant profile.",
        "- Recompute and validate the model separately before describing any ranking as new.",
        "",
        "## 8. Source files",
        "",
        "- `outputs/data_freshness_dashboard.csv`",
        "- `metadata/refresh_runs/`",
        "- `outputs/latest_macro_eom_ranking.csv`",
        "- `outputs/macro_backtest.json`",
        "- `outputs/eom_v2_run_status.json`",
        "- `outputs/eom_v2_weight_sensitivity.csv`",
        "- `outputs/eom_joie_de_vivre_scores.csv`",
        "- `data/observations_history/world_bank_observations.csv`",
        "",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Human-readable report written to: {REPORT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
