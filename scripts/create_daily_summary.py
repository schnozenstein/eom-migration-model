import csv
import json
import os
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
    current_workflow_run_id = str(os.environ.get("GITHUB_RUN_ID", ""))
    manifest_workflow_run_id = str(manifest.get("github_workflow_run_id", ""))
    manifest_is_current = (not current_workflow_run_id) or (manifest_workflow_run_id == current_workflow_run_id)
    etl_outcome = str(os.environ.get("EOM_ETL_OUTCOME", "unknown")).lower()
    ranking_outcome = str(os.environ.get("EOM_RANKING_RECOMPUTE_OUTCOME", "unknown")).lower()
    freshness_warning = "None" if manifest_is_current and etl_outcome == "success" else "The full ETL did not write a current manifest; source/panel counts below are last stored values. Ranking status is reported from the actual ranking step outcome."

    dashboard = read_csv(OUT / "data_freshness_dashboard.csv")
    source_audit_manifest = read_json(META / "source_audit_manifest.json")
    policy_delta_manifest = read_json(META / "policy_event_delta_manifest.json")
    prediction_manifest = read_json(META / "prediction_ledger_manifest.json")
    history_rebuild_manifest = read_json(META / "wdi_history_rebuild_manifest.json")
    macro_focus = read_csv(ROOT / "data" / "raw" / "world_bank_macro_focus.csv")
    macro_focus_rows = len(macro_focus)
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

    ranked_rows = [r for r in ranking if (r.get("energy_rank") or "").strip() and (r.get("energy_equal_weight") or "").strip()]
    unscored_rows_by_id = {str(r.get("destination_id", "")).strip().upper(): r for r in ranking if str(r.get("destination_id", "")).strip() and not (r.get("energy_rank") or "").strip()}
    ranked_rows.sort(key=lambda r: float(r.get("energy_rank") or 999999))
    lines = [
        "# EOM Daily Research Report",
        "",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## 1. Executive summary",
        "",
        f"- **Latest refresh run:** `{manifest.get('run_id', 'Not reported')}`",
        f"- **ETL manifest matches this workflow run:** {yes_no(manifest_is_current)}",
        f"- **Full ETL step outcome:** {etl_outcome}",
        f"- **Macro ranking step outcome:** {ranking_outcome}",
        f"- **Freshness warning:** {freshness_warning}",
        f"- **Refresh timestamp:** {manifest.get('run_at_utc', 'Not reported')}",
        f"- **World Bank observations fetched:** {manifest.get('world_bank_rows_fetched', 'Not reported')}",
        f"- **World Bank indicator requests:** {manifest.get('world_bank_indicators_successful', 'Not reported')} succeeded; {manifest.get('world_bank_indicators_failed', 'Not reported')} failed",
        f"- **Normalized WDI panel:** {manifest.get('world_bank_rows_normalized', 'Not reported')} current rows; {manifest.get('world_bank_rows_without_iso3', 'Not reported')} aggregate rows use stable non-ISO3 source keys",
        f"- **Persistent WDI revision ledger:** {manifest.get('world_bank_history_rows', 'Not reported')} rows; {manifest.get('world_bank_history_new_keys', 'Not reported')} new keys; {manifest.get('world_bank_history_value_revisions', 'Not reported')} value revisions; {manifest.get('world_bank_history_unchanged_rows_skipped', 'Not reported')} unchanged observations skipped",
        f"- **WDI history migration this run:** {yes_no(manifest.get('world_bank_history_rebuilt_from_snapshots'))}; {manifest.get('world_bank_history_rows_restored_from_snapshots', 0)} rows restored from archived raw snapshots",
        f"- **Macro scoring input:** `data/raw/world_bank_macro_focus.csv` ({macro_focus_rows} rows; {'fetched during this run' if ranking_outcome == 'success' else 'last stored input'}; separate 11-indicator destination input)",
        f"- **Brazil World Bank extract:** {manifest.get('brazil_macro_rows_fetched', 'Not reported')} fresh Brazil indicator-year rows",
        f"- **Eurostat total migration flows:** {eurostat_succeeded} series succeeded; {eurostat_failed} failed; {eurostat_observed} observed annual cells across up to {eurostat_geos} reporting geographies",
        f"- **UNHCR forced-displacement extract:** {unhcr_state}; {unhcr_rows} retained focus/origin rows",
        f"- **UN DESA migrant-stock tables:** {undesa_succeeded} of 3 files succeeded; {undesa_failed} failed; {undesa_rows} normalized rows",
        f"- **OECD migration database slice:** {oecd_state}; {oecd_rows} focus-country rows retained",
        f"- **ILOSTAT migrant-labour indicators:** {ilostat_succeeded} succeeded; {ilostat_failed} failed; {ilostat_rows} focus rows",
        f"- **Brazil OBMigra official source page:** {obmigra_state} (catalogue monitor only; report tables are not numerically parsed)",
        f"- **Policy pages:** {manifest.get('policy_pages_successful', 'Not reported')} succeeded; {manifest.get('policy_pages_failed', 'Not reported')} failed",
        f"- **Freshness dashboard:** {len(recent)} recent; {len(attention)} requiring attention out of {len(dashboard)} indicators",
        f"- **Macro ranking recomputed in this run:** {yes_no(ranking_outcome == 'success')}",
        f"- **Consolidated source-retrieval audit:** {source_audit_manifest.get('source_records', 'not generated')} source records; {source_audit_manifest.get('source_failures_or_unknown_status', 'unknown')} failed/unknown statuses; validation {source_audit_manifest.get('validation_status', 'not reported')}.",
        f"- **Numeric source rows fetched:** {source_audit_manifest.get('numeric_source_rows_fetched_sum_across_endpoints', 'not reported')} across endpoints; {source_audit_manifest.get('numeric_normalized_rows_sum_across_primary_datasets', 'not reported')} normalized rows retained. These are source-record counts, not unique people.",
        f"- **Panel validation:** {source_audit_manifest.get('panel_duplicate_natural_keys', 'unknown')} duplicate natural keys; {source_audit_manifest.get('panel_missing_values', 'unknown')} missing values ({source_audit_manifest.get('panel_missingness_pct', 'unknown')}% of panel cells).",
        f"- **Policy-event delta:** {policy_delta_manifest.get('confirmed_policy_events', 'not reported')} confirmed events; {policy_delta_manifest.get('content_changed_pages', 'not reported')} page-content changes requiring review; {policy_delta_manifest.get('failed_or_unknown_pages', 'not reported')} failed/unknown pages. Hash changes are not policy-event confirmation.",
        f"- **Prediction/outcome ledger:** {prediction_manifest.get('prediction_rows', 'not reported')} production forecasts; {prediction_manifest.get('outcome_rows', 'not reported')} versioned country-year outcomes; {prediction_manifest.get('matched_outcomes', 'not reported')} forecast-outcome matches; {prediction_manifest.get('outcome_rows_inserted', 'not reported')} new outcomes and {prediction_manifest.get('outcome_rows_revised', 'not reported')} revisions.",
        f"- **Prior WDI history recovery:** {history_rebuild_manifest.get('rows_restored_vs_legacy_history', 0)} rows recovered from archived raw snapshots during the one-time migration; current run rebuild: {yes_no(manifest.get('world_bank_history_rebuilt_from_snapshots'))}.",
        f"- **Macro ranking comparison year:** {manifest.get('ranking_year', 'Not reported')}",
        f"- **Destinations scored / total:** {manifest.get('ranking_destinations_scored', 'Not reported')} / {manifest.get('ranking_destinations_total', len(ranking))}",
        f"- **Forecast issued during refresh:** {yes_no(manifest.get('forecast_issued'))}",
        "",
        "Source refresh and model reranking are separate steps. Check the ranking status and comparison year above before treating this as a new ranking.",
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
        "It does not include complete quality-of-life or individual visa-feasibility scoring.",
        "",
    ]

    if ranked_rows:
        lines += [
            "| Rank | Destination | Year | Macro score |",
            "|---:|---|---:|---:|",
        ]
        # Report the full stored ranking; do not silently truncate at the top ten.
        for r in ranked_rows:
            lines.append(
                f"| {r.get('energy_rank', '—')} | {r.get('destination_name', 'Unknown')} "
                f"| {r.get('year', '—')} | {fmt(r.get('energy_equal_weight'))} |"
            )
    else:
        lines.append("No stored macro ranking file or rows were available.")

    ranked_ids = {str(r.get("destination_id", "")).strip().upper() for r in ranked_rows}
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
        f"- **Destinations scored in stored macro ranking:** {len(ranked_rows)}",
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
            unscored_row = unscored_rows_by_id.get(str(d.get("destination_id", "")).strip().upper(), {})
            score_note = (unscored_row.get("score_status") or "").strip()
            if score_note:
                note = (score_note + ("; " + note if note else "")).replace("|", "\\|")
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
        "- Obtain comparable, sourced wellbeing and work-life indicators before calculating quality-of-life scores.",
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
        "- `data/observations_history/world_bank_observations.csv.gz`",
        "- `data/raw/world_bank_long.csv` (full current WDI panel in workflow artifact)",
        "- `data/raw/world_bank_macro_focus.csv` (separate macro scoring input)",
        "- `metadata/wdi_history_rebuild_manifest.json`",
        "- `data/raw/eurostat_migration_flows.csv`",
        "- `data/raw/undesa_migrant_stock_long.csv`",
        "- `data/raw/unhcr_forced_displacement_focus.csv.gz`",
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
