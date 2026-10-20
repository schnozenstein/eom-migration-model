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
    destinations = read_csv(DATA / "destinations.csv")
    sensitivity = read_csv(OUT / "eom_v2_weight_sensitivity.csv")
    qol = read_csv(OUT / "eom_joie_de_vivre_scores.csv")
    status = read_json(OUT / "eom_v2_run_status.json")
    backtest = read_json(OUT / "macro_backtest.json")
    eurostat_status = read_csv(ROOT / "metadata" / "eurostat_source_status.csv")
    obmigra_status = read_csv(DATA.parent / "metadata" / "obmigra_source_status.csv")
    unhcr_status = read_csv(ROOT / "metadata" / "unhcr_source_status.csv")
    undesa_status = read_csv(ROOT / "metadata" / "undesa_source_status.csv")
    oecd_status = read_csv(ROOT / "metadata" / "oecd_source_status.csv")
    ilostat_status = read_csv(ROOT / "metadata" / "ilostat_source_status.csv")

    eurostat_succeeded = sum(r.get("status") == "SUCCESS" for r in eurostat_status)
    eurostat_failed = sum(r.get("status") == "FAILED" for r in eurostat_status)
    eurostat_observed = sum(int(r.get("observed_rows") or 0) for r in eurostat_status)
    eurostat_geos = max((int(r.get("geographies_fetched") or 0) for r in eurostat_status), default=0)
    unhcr_state = unhcr_status[0].get("status", "Not reported") if unhcr_status else "Not reported"
    unhcr_rows = int(unhcr_status[0].get("focus_rows") or 0) if unhcr_status else 0
    undesa_succeeded = sum(r.get("status") == "SUCCESS" for r in undesa_status)
    undesa_failed = sum(r.get("status") == "FAILED" for r in undesa_status)
    undesa_rows = sum(int(r.get("rows_fetched") or 0) for r in undesa_status)
    oecd_state = oecd_status[0].get("status", "Not reported") if oecd_status else "Not reported"
    oecd_rows = int(oecd_status[0].get("rows_focus") or 0) if oecd_status else 0
    ilostat_succeeded = sum(r.get("status") == "SUCCESS" for r in ilostat_status)
    ilostat_failed = sum(r.get("status") == "FAILED" for r in ilostat_status)
    ilostat_rows = sum(int(r.get("rows_focus") or 0) for r in ilostat_status)
    obmigra_state = obmigra_status[0].get("status", "Not reported") if obmigra_status else "Not reported"

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
        f"- **Brazil World Bank extract:** {manifest.get('brazil_macro_rows_fetched', 'Not reported')} fresh Brazil indicator-year rows",
        f"- **Eurostat total migration flows:** {eurostat_succeeded} series succeeded; {eurostat_failed} failed; {eurostat_observed} observed annual cells across up to {eurostat_geos} reporting geographies",
        f"- **UNHCR forced-displacement extract:** {unhcr_state}; {unhcr_rows} retained focus/origin rows",
        f"- **UN DESA migrant-stock tables:** {undesa_succeeded} of 3 files succeeded; {undesa_failed} failed; {undesa_rows} normalized rows",
        f"- **OECD migration database slice:** {oecd_state}; {oecd_rows} focus-country rows retained",
        f"- **ILOSTAT migrant-labour indicators:** {ilostat_succeeded} succeeded; {ilostat_failed} failed; {ilostat_rows} focus rows",
        f"- **Brazil OBMigra official source page:** {obmigra_state} (catalogue monitor only; report tables are not numerically parsed)",
        f"- **Policy pages:** {manifest.get('policy_pages_successful', 'Not reported')} succeeded; {manifest.get('policy_pages_failed', 'Not reported')} failed",
        f"- **Freshness dashboard:** {len(recent)} recent; {len(attention)} requiring attention out of {len(dashboard)} indicators",
        f"- **Ranking recomputed during refresh:** {yes_no(manifest.get('ranking_recomputed'))}",
        f"- **Forecast issued during refresh:** {yes_no(manifest.get('forecast_issued'))}",
        "",
        "A successful data refresh is not evidence that a ranking or forecast was recalculated.",
        "",
        "### Supplemental dataset notes",
        "",
        "- UN DESA International Migrant Stock 2024 is a stock measure at selected reference years (1990–2024), split by sex and direction (destination/origin); it is not an annual flow.",
        "- UNHCR forced-displacement counts include distinct population categories such as refugees, asylum-seekers and other groups; population types must not be summed or treated as voluntary economic migration.",
        "- OECD records preserve the original SDMX dimensions and labels from a bounded official query. The B11 measure code is not interpreted or added to the EOM score until its structure and definition are reviewed.",
        "- ILOSTAT migrant-labour series include migrant working-age stock, employment and inflow by sex and country of birth. Retain national source flags and notes; these surveys cover only a subset of countries/years and are not a fully harmonized bilateral flow panel.",
        "- Eurostat total immigration and emigration are stored across all reporting geographies; some rows may represent aggregate regions rather than independent countries.",
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
        # Report the full stored ranking; do not silently truncate at the top ten.
        for r in ranking:
            lines.append(
                f"| {r.get('energy_rank', '—')} | {r.get('destination_name', 'Unknown')} "
                f"| {r.get('year', '—')} | {fmt(r.get('energy_equal_weight'))} |"
            )
    else:
        lines.append("No stored macro ranking file or rows were available.")

    ranked_ids = {str(r.get("destination_id", "")).strip().upper() for r in ranking}
    unranked_destinations = [
        d for d in destinations
        if str(d.get("destination_id", "")).strip().upper()
        and str(d.get("destination_id", "")).strip().upper() not in ranked_ids
    ]
    lines += [
        "",
        "### Destination coverage",
        "",
        f"- **Registered destinations:** {len(destinations)}",
        f"- **Destinations in stored macro ranking:** {len(ranking)}",
        f"- **Registered destinations not in stored ranking:** {len(unranked_destinations)}",
        "",
    ]
    if unranked_destinations:
        lines += [
            "| Destination | ID | Coverage note |",
            "|---|---|---|",
        ]
        for d in unranked_destinations:
            note = (d.get("notes") or "").replace("|", "\\|").strip()
            lines.append(
                f"| {d.get('destination_name', 'Unknown')} | {d.get('destination_id', '—')} | "
                f"{note or 'No comparable macro score in the stored ranking; not scored'} |"
            )
        lines += [
            "",
            "These destinations are registered but were not scored in the stored ranking. "
            "Registration or newly ingested source data does not automatically create a comparable score. "
            "Do not infer a rank for an unscored destination.",
        ]
    else:
        lines.append("Every registered destination appears in the stored ranking.")
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
        "- `data/raw/eurostat_migration_flows.csv`",
        "- `data/raw/undesa_migrant_stock_long.csv`",
        "- `data/raw/unhcr_forced_displacement_focus.csv`",
        "- `data/raw/oecd_migration_database_focus.csv`",
        "- `data/raw/ilostat_migrant_labour_focus.csv`",
        "- `metadata/eurostat_source_status.csv`, `metadata/undesa_source_status.csv`, `metadata/unhcr_source_status.csv`, `metadata/oecd_source_status.csv`, `metadata/ilostat_source_status.csv`",
        "",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Human-readable report written to: {REPORT}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
