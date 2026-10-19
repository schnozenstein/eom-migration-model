# EOM General Migration Model — Daily Research Pipeline

**Current status: conceptual and uncalibrated; an expanding-origin historical backtest exists, but the model is not validated and the equal-weight EOM score underperforms persistence on pooled rank association.** This is a research pipeline for general migration dynamics based on the user's Entropy-Oriented Migration (EOM) paper. Tech MBA is an optional scenario configuration, not the core target or dataset.

## Research scope

The model is intended to study general destination attractiveness, migration flows and stocks, origin–destination transitions, heterogeneity where harmonized data support it, and policy/economic counterfactuals. Scenario inputs may specify origins, destinations, migrant attributes, objectives, constraints and horizons for labour, education, family, humanitarian or other migration.

The paper's sign convention is:

`E_i = -S_i + C_i - P_i - O_i - U_i - R_i`

Read in English: energy equals minus salary plus cost minus policy friendliness minus job opportunity minus institutional quality minus stability. Lower energy means a stronger attractor. The empirical model is **uncalibrated until parameters are estimated from relevant data**. Code execution, broad correlations, or a qualitative policy assessment do not constitute validation.

## Data currently present

- `data/historical_destination_year_panel.csv`: 792 destination-year rows, 22 destinations (21 country comparators plus nested Scotland/Edinburgh), 1990–2025. It is a rectangular scaffold; indicators are intermittent and definitions differ.
- `data/eurostat_selected_total_indicators_long.csv`: 960 selected-total rows across five flow indicators, 32 reporting geographies, 2019–2024. Per-indicator observed values range from 166 to 186 of 192.
- `data/eurostat_new_migration_indicators_long.csv`: 396 rows for two indicators across 33 geographies, 2019–2024; 188/198 and 190/198 observed values.
- `data/data_quality_audit_general_2026-10-13.csv`: expanded audit across panel columns and native Eurostat extracts.
- `metadata/source_lineage_2026-10-13.csv`: source, vintage, definition, units, geography, cohort, retrieval date and missingness notes.
- `data/model_feedback/feature_readiness_audit_2026-10-13.csv`: mapping of EOM terms to candidate measurements and known gaps.

UN DESA migrant stock is a stock measure, not an annual flow. Eurostat immigration/emigration are annual flow measures with distinct birth, citizenship and previous-residence definitions. ILOSTAT 5WAP and DWAP are retained separately because standards differ. Missing or suppressed values are not imputed.

## Daily-run result — 13 October 2026, second run

The current Irish employment-permit page was checked live and seven receipt-date frontiers were appended as of 13 October. Critical Skills and General Employment Permit frontiers moved since 12 October; this is a short administrative snapshot, not a processing-duration estimate or a migration-attractiveness score. See `data/operational_indicators_snapshot.csv` and the daily report.

No new bulk macro data were downloaded: a local World Bank API request failed at DNS/network resolution. The package does not claim live World Bank retrieval. No numerical EOM ranking, fit, forecast, backtest or causal estimate was produced.

## Why fitting is gated

The existing panel does not yet contain a comparable, aligned set of salary/income, cost, policy, job opportunity, institutional quality and stability features. Migration-flow coverage in the merged 21-destination panel is limited to 11–12 destinations during 2019–2024, and the current package does not contain a consistently aligned population denominator for a defensible flow-rate target. Fitting coefficients or presenting EOM-vs-baseline metrics from this matrix would be misleading.

## Feedback and scientific safeguards

- Prediction ledger remains empty until a specific target can be forecast by an eligible model version before the outcome is known.
- Keep observed facts, proxies, assumptions, derived features, predictions and causal estimates separate.
- Use chronological rolling/expanding-origin backtests, never random splits for time series.
- Compare equal-weight EOM separately from transparent baselines.
- Preserve source vintage, revisions, units, cohort definitions and missingness.
- Evaluate policy causality separately from prediction using defensible comparison groups, pre-trend/placebo checks and sensitivity analyses where suitable.
- Preserve older package/report versions in `archive/`; model versions are recorded in `data/model_feedback/model_version_registry.csv`.

## Configuration

`config/profile.json` is a generic interface with no personal weights. The former Tech-MBA-oriented profile is preserved at `config/scenarios/tech_mba_example.json` as an optional parameterization only.

## Reproduce the offline audit

From the package root, run:

`python scripts/audit_general_eom_panel.py`

This writes an audit CSV only. It does not fetch new data, fit a model, forecast, calibrate, rank destinations or estimate causal effects. The macro World Bank API starter code is under `src/eom_empirical/`. The backtest implementation uses expanding-origin folds and compares the fitted Ridge model with persistence and country-mean baselines; it also reports the equal-weight EOM energy rank association separately. Live data retrieval requires network access and must be recorded with source URLs and retrieval timestamps. Synthetic unit tests check logic only and are not empirical validation.

## Geographic coverage and known gaps

The maintained focus set is UK (with Scotland/Edinburgh as nested regional analysis where data allow), Ireland, Netherlands, Germany, Switzerland, Hong Kong, Japan, Singapore, Australia, Canada, USA, New Zealand, France, Sweden, Denmark, Finland, Norway, Austria, Czechia and Spain. The general architecture is global, not restricted to this set. Current harmonized flow coverage is Europe-heavy; most focus countries outside Eurostat's reporting universe remain gaps. Scotland/Edinburgh is not separately observed in the current national migration panel.


## 2026-10-15 WDI ingestion run

See `DAILY_REPORT_2026-10-15_v4.md`. The WDI input is now available as `data/raw/world_bank_long.csv`; a 2023 exploratory equal-weight ranking and chronological backtest are stored under `outputs/`. The EOM model remains uncalibrated.


## Latest daily run — 2026-10-16 (v6)

See `DAILY_REPORT_2026-10-16_v6.md`. India has been added as the 20th global comparator. The model remains uncalibrated; no forward forecast or causal estimate was issued.


## Daily ETL attempt — 2026-10-17 (v7)

- Audit timestamp: 2026-10-17T09:48:30+05:30 (IST).
- Direct World Bank and Eurostat API calls failed at DNS resolution in the execution environment; zero new numeric observations were ingested.
- Official IRCC policy release dated 2026-10-16 and UK Home Office bill factsheet dated 2026-10-08 were verified and added as cohort-specific policy records.
- OECD and Eurostat landing-page metadata were checked; metadata access is not counted as a numeric data download.
- Six unit tests passed with `PYTHONPATH=src python -m pytest -q`.
- No ranking update, new forward forecast, calibration or causal estimate was made. See `metadata/source_retrieval_audit_2026-10-17.csv`, `metadata/run_manifest_2026-10-17.json`, and `DAILY_REPORT_2026-10-17_v7.md`.

## EOM live refresh pipeline patch (v9, 17 October 2026)

See `LIVE_DATA_PIPELINE.md`. `scripts/refresh_eom_data.py` now requests the current UTC year by default, uses retries, preserves per-run source snapshots and retrieval vintages, writes source-level status/freshness dashboards, and watches official immigration landing pages for content changes. `.github/workflows/eom-daily-refresh.yml` defines a daily GitHub Actions run at 05:17 UTC plus manual dispatch. The workflow is deployable but not active until this project is pushed to a GitHub repository with Actions enabled. Eurostat/OECD numeric connectors and automatic policy interpretation remain future work. Source refresh does not automatically create a new ranking or forecast.


## PPP parameter coverage (2026-10-19)

The live World Bank refresh now collects complementary PPP measures: GDP per capita at constant 2021 international dollars (`NY.GDP.PCAP.PP.KD`), GDP at current PPP international dollars (`NY.GDP.MKTP.PP.CD`), the GDP PPP conversion factor (`PA.NUS.PPP`), and the household/private-consumption PPP conversion factor (`PA.NUS.PRVT.PP`). These are distinct concepts, not interchangeable “PPP scores.” The legacy GDP price-level-ratio code (`PA.NUS.PPPC.RF`) returned an API “not found or archived” error in the 19 October run and is no longer actively polled pending re-verification; previously stored observations remain. Spain is added as a focus destination; Austria was already in the focus set and now also has official policy-page monitoring.
