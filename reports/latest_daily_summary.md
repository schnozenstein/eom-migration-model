# EOM Daily Research Report

> Generated: 2026-10-28 07:24 UTC

## 1. Executive summary

- **Workflow trigger:** push; configured UTC schedule 17 5 * * *.
- **Latest refresh run:** `2026-10-28T072323Z`
- **ETL manifest matches this workflow run:** Yes
- **Full ETL step outcome:** success
- **Macro ranking step outcome:** success
- **Freshness warning:** None
- **Refresh timestamp:** 2026-10-28T07:23:23.365041+00:00
- **World Bank observations fetched:** 165984
- **World Bank indicator requests:** 39 succeeded; 0 failed
- **Normalized WDI panel:** 165984 current rows; 3120 aggregate rows use stable non-ISO3 source keys
- **Persistent WDI revision ledger:** 165984 rows; 0 new keys; 0 value revisions; 165984 unchanged observations skipped
- **WDI history migration this run:** No; 0 rows restored from archived raw snapshots
- **Macro scoring input:** `data/raw/world_bank_macro_focus.csv` (7744 rows; fetched during this run; separate 11-indicator destination input)
- **Brazil World Bank extract:** 624 fresh Brazil indicator-year rows
- **Eurostat total migration flows:** 2 series succeeded; 0 failed; 1034 observed annual cells across up to 44 reporting geographies
- **UNHCR forced-displacement extract:** SUCCESS; 242461 retained focus/origin rows
- **UN DESA migrant-stock tables:** 3 of 3 files succeeded; 0 failed; 235632 normalized rows
- **OECD migration database slice:** SUCCESS; 290 focus-country rows retained
- **ILOSTAT migrant-labour indicators:** 3 succeeded; 0 failed; 6469 focus rows
- **Brazil OBMigra official source page:** SUCCESS (catalogue monitor only; report tables are not numerically parsed)
- **Policy pages:** 11 succeeded; 0 failed
- **Freshness dashboard:** 38 recent; 1 requiring attention out of 39 indicators
- **Macro ranking recomputed in this run:** Yes
- **Ranking delta audit:** RECOMPUTED; data cutoff 2025; 0 score changes and 0 rank changes across 45 destinations; 42 scored and 3 unscored.
- **Consolidated source-retrieval audit:** 62 source records; 0 failed/unknown statuses; validation PASS.
- **Numeric source rows fetched:** 1095164 across endpoints; 652213 normalized rows retained. These are source-record counts, not unique people.
- **Panel validation:** 0 duplicate WDI natural keys; 27778 missing values (16.7353% of panel cells).
- **Cross-source natural-key audit:** 0 duplicate-key rows across audited tables; audit validation PASS.
- **Source lineage registry:** 62 current source records in metadata/source_lineage_current.csv; legacy registry status preserved_legacy_registry (not overwritten).
- **Policy-event delta:** 0 confirmed events; 6 page-content changes requiring review; 0 failed/unknown pages. Hash changes are not policy-event confirmation.
- **Prediction/outcome ledger:** 0 production forecasts; 4176 versioned country-year outcomes; 0 forecast-outcome matches; 0 new outcomes and 0 revisions.
- **Prior WDI history recovery:** 7296 rows recovered from archived raw snapshots during the one-time migration; current run rebuild: No.
- **Macro ranking comparison year:** 2025
- **Destinations scored / total:** 42 / 45
- **Forecast issued during refresh:** No

Source refresh and model reranking are separate steps. Check the ranking status and comparison year above before treating this as a new ranking.

### Supplemental dataset notes

- UN DESA International Migrant Stock 2024 is a stock measure at selected reference years (1990–2024), split by sex and direction (destination/origin); it is not an annual flow.
- UNHCR forced-displacement counts include distinct population categories such as refugees, asylum-seekers and other groups; population types must not be summed or treated as voluntary economic migration.
- OECD records preserve the original SDMX dimensions and labels from a bounded official query. The B11 measure code is not interpreted or added to the EOM score until its structure and definition are reviewed.
- ILOSTAT migrant-labour series include migrant working-age stock, employment and inflow by sex and country of birth. Retain national source flags and notes; these surveys cover only a subset of countries/years and are not a fully harmonized bilateral flow panel.
- Eurostat total immigration and emigration are stored across all reporting geographies; some rows may represent aggregate regions rather than independent countries.

## 2. Stored macro ranking

This is the latest stored macro-proxy ranking, not a personalised migration recommendation. It does not include complete quality-of-life or individual visa-feasibility scoring.

| Rank | Destination | Year | Macro score |
|---:|---|---:|---:|
| 1.0 | Singapore | 2025 | -7.011 |
| 2.0 | Japan | 2025 | -4.344 |
| 3.0 | Norway | 2025 | -3.828 |
| 4.0 | Hong Kong | 2025 | -3.752 |
| 5.0 | New Zealand | 2025 | -3.513 |
| 6.0 | Ireland | 2025 | -3.347 |
| 7.0 | South Korea | 2025 | -3.218 |
| 8.0 | Australia | 2025 | -2.830 |
| 9.0 | Denmark | 2025 | -2.784 |
| 10.0 | Netherlands | 2025 | -2.748 |
| 11.0 | Switzerland | 2025 | -2.725 |
| 12.0 | Czechia | 2025 | -2.678 |
| 13.0 | Finland | 2025 | -2.229 |
| 14.0 | Sweden | 2025 | -2.175 |
| 15.0 | Canada | 2025 | -2.091 |
| 16.0 | Germany | 2025 | -1.642 |
| 17.0 | Poland | 2025 | -1.526 |
| 18.0 | Austria | 2025 | -1.484 |
| 19.0 | Malaysia | 2025 | -1.326 |
| 20.0 | Saudi Arabia | 2025 | -0.908 |
| 21.0 | United Kingdom | 2025 | -0.852 |
| 22.0 | Belgium | 2025 | -0.655 |
| 23.0 | Portugal | 2025 | -0.312 |
| 24.0 | Italy | 2025 | 0.144 |
| 25.0 | United States | 2025 | 0.378 |
| 26.0 | France | 2025 | 0.596 |
| 27.0 | Chile | 2025 | 0.893 |
| 28.0 | Spain | 2025 | 1.325 |
| 29.0 | Thailand | 2025 | 1.846 |
| 30.0 | Vietnam | 2025 | 1.933 |
| 31.0 | Israel | 2025 | 1.938 |
| 32.0 | China | 2025 | 2.059 |
| 33.0 | Greece | 2025 | 2.216 |
| 34.0 | Indonesia | 2025 | 3.225 |
| 35.0 | India | 2025 | 3.594 |
| 36.0 | Philippines | 2025 | 3.878 |
| 37.0 | Türkiye | 2025 | 4.418 |
| 38.0 | Mexico | 2025 | 4.547 |
| 39.0 | Peru | 2025 | 4.631 |
| 40.0 | Brazil | 2025 | 4.635 |
| 41.0 | Colombia | 2025 | 5.604 |
| 42.0 | South Africa | 2025 | 10.115 |

### Destination coverage

- **Registered destinations:** 46
- **Destinations scored in stored macro ranking:** 42
- **Registered destinations not in stored ranking:** 4

| Destination | ID | Coverage note |
|---|---|---|
| Edinburgh | EDI | Nested city option; compare conditionally within the UK or in a hierarchical model |
| Taiwan | TWN | not ranked: one or more required macro components are missing for comparison year; Added 2026-10-20; major advanced economy; World Bank WDI coverage is limited or absent for many indicators, so use official Taiwan national statistics and preserve source-specific coverage. |
| United Arab Emirates | ARE | not ranked: one or more required macro components are missing for comparison year; Added 2026-10-20; major Gulf economy and migrant-labour destination; World Bank country code is ARE. |
| Argentina | ARG | not ranked: one or more required macro components are missing for comparison year; Added 2026-10-20; major Latin American economy. |

These destinations are registered but were not scored in the stored ranking. Registration or newly ingested source data does not automatically create a comparable score. Do not infer a rank for an unscored destination.

## 3. Historical model evaluation

- **Evaluation status:** completed_expanding_origin_backtest
- **Target:** next-year national net migration per 1,000 residents
- **Evaluation method:** expanding-origin; each test year is predicted using only earlier target years; no random split
- **Test observations:** 613
- **Destinations:** 44
- **Rolling test origins:** 14

| Metric | EOM / Ridge | Persistence baseline | Country-mean baseline |
|---|---:|---:|---:|
| Mean absolute error (MAE; lower is better) | Ridge: 4.022 | 2.363 | 2.804 |
| Rank correlation (higher is better) | EOM: 0.515; Ridge: 0.438 | 0.806 | Not reported |

**Interpretation:** These are historical, macro-level evaluation results, not a new forecast. The stored evaluation reports that persistence performs better than Ridge on MAE and rank correlation. Investigate baseline construction, sample comparability and forecast-time information availability before drawing strong conclusions.

Macro-level predictive evaluation only. National net migration is not an individual or programme-specific outcome. Equal-weight EOM energy is an ordinal score, not a calibrated probability; its Spearman correlation is not a causal estimate. Weak performance is evidence against this operationalization, not proof that every EOM formulation fails.

The results evaluate national net migration, not an individual's chance of successful migration. Correlation is not causation, and an ordinal score is not a calibrated probability.

## 4. Ranking sensitivity

The following sensitivity analysis perturbs existing macro-component weights. Top-five share is the fraction of weight draws in which a destination appeared in the top five; it is not a probability of migration success or of being the best destination.

| Destination | Baseline rank | Median rank | 10th–90th percentile rank | Top-five share |
|---|---:|---:|---:|---:|
| Singapore | 1 | 1.0 | 1.0–1.0 | 100.0% |
| Ireland | 2 | 3.0 | 2.0–4.0 | 99.5% |
| Norway | 3 | 3.0 | 2.0–4.0 | 100.0% |
| Japan | 4 | 4.0 | 2.0–5.0 | 93.2% |
| Switzerland | 5 | 5.0 | 4.0–7.0 | 51.6% |
| New Zealand | 6 | 6.0 | 5.0–7.0 | 26.6% |
| Hong Kong | 7 | 6.0 | 5.0–7.0 | 29.0% |
| Netherlands | 8 | 8.0 | 8.0–9.0 | 0.0% |
| Australia | 9 | 9.0 | 8.0–10.0 | 0.0% |
| Denmark | 10 | 10.0 | 8.0–11.0 | 0.1% |

These draws are a weight-sensitivity exercise, not a statistical confidence interval.

## 5. Quality of life and visa feasibility

- **Destinations in QoL input file:** 21
- **Destinations with a recorded scored QoL value:** 0
- **Destinations with complete inputs according to model status:** 0
- **QoL weights:** illustrative, not estimated
- **Visa-feasibility destinations scored:** 0
- **Feasibility limitation:** No verified person-specific visa-route/eligibility/funds/language inputs supplied; template created rather than fabricate scores.
- **Combined EOM ranking status:** not produced: wellbeing and feasibility evidence incomplete

Missing QoL or visa data must remain missing, not be silently converted to zero. A combined personal migration ranking should wait until comparable wellbeing data and verified, profile-specific feasibility inputs are available.

## 6. Indicators requiring attention

| Indicator | Latest observation year | Status |
|---|---:|---|
| NY.GDP.TOTL.RT.ZS | 2021 | STALE_OR_SLOW_RELEASE |

A recent retrieval timestamp does not guarantee a recent statistical observation. Some indicators are released with a delay, so check release schedules before labelling them defective.

## 7. Next research actions

- Investigate failed data requests and retry policy pages that were not retrieved.
- Check observation years and source release schedules for indicators needing attention.
- Investigate why the persistence baseline outperforms Ridge and EOM in the stored backtest.
- Verify that every predictor would have been available at the forecast date; inspect missing-data handling and baseline definitions.
- Obtain comparable, sourced wellbeing and work-life indicators before calculating quality-of-life scores.
- Add verified visa routes, eligibility, funds, language and study-to-work pathways for a defined applicant profile.
- Recompute and validate the model separately before describing any ranking as new.

## 8. Source files

- `outputs/data_freshness_dashboard.csv`
- `metadata/refresh_runs/`
- `outputs/latest_macro_eom_ranking.csv`
- `outputs/macro_backtest.json`
- `outputs/eom_v2_run_status.json`
- `outputs/eom_v2_weight_sensitivity.csv`
- `outputs/eom_joie_de_vivre_scores.csv`
- `data/observations_history/world_bank_observations.csv.gz`
- `data/raw/world_bank_long.csv` (full current WDI panel in workflow artifact)
- `data/raw/world_bank_macro_focus.csv` (separate macro scoring input)
- `metadata/wdi_history_rebuild_manifest.json`
- `data/raw/eurostat_migration_flows.csv`
- `data/raw/undesa_migrant_stock_long.csv`
- `data/raw/unhcr_forced_displacement_focus.csv.gz`
- `data/raw/oecd_migration_database_focus.csv`
- `data/raw/ilostat_migrant_labour_focus.csv`
- `metadata/eurostat_source_status.csv`, `metadata/undesa_source_status.csv`, `metadata/unhcr_source_status.csv`, `metadata/oecd_source_status.csv`, `metadata/ilostat_source_status.csv`
- `outputs/source_retrieval_audit.csv`, `metadata/source_audit_manifest.json`, and `metadata/source_lineage_current.csv`
- `outputs/policy_event_delta.csv` and `metadata/policy_event_delta_manifest.json`
- `outputs/macro_ranking_delta.csv` and `metadata/macro_ranking_delta_manifest.json`
- `data/prediction_ledger.csv`, `data/outcome_ledger.csv`, `data/prediction_outcome_join.csv`, and `metadata/prediction_ledger_manifest.json`

## 9. Source endpoint, release and validation audit

Exact current-run URLs and per-source counts follow. Source-record totals are not unique people. A release/vintage of 'not exposed' means the source endpoint did not provide a publication date in the captured status metadata. The CSV is the authoritative machine-readable record.

| Source | Exact URL | Release/vintage | Observation period | Fetch status | Fetched / normalized | Inserted / updated / rejected | Duplicate keys / missing values |
|---|---|---|---|---|---:|---:|---:|
| WDI:BX.KLT.DINV.WD.GD.ZS | [https://api.worldbank.org/v2/country/all/indicator/BX.KLT.DINV.WD.GD.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/BX.KLT.DINV.WD.GD.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 372 |
| WDI:BX.TRF.PWKR.CD.DT | [https://api.worldbank.org/v2/country/all/indicator/BX.TRF.PWKR.CD.DT?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/BX.TRF.PWKR.CD.DT?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 693 |
| WDI:FP.CPI.TOTL.ZG | [https://api.worldbank.org/v2/country/all/indicator/FP.CPI.TOTL.ZG?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/FP.CPI.TOTL.ZG?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 548 |
| WDI:GC.DOD.TOTL.GD.ZS | [https://api.worldbank.org/v2/country/all/indicator/GC.DOD.TOTL.GD.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/GC.DOD.TOTL.GD.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 3444 |
| WDI:GE.EST | [https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_GE_EST?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_GE_EST?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 987 |
| WDI:IT.NET.USER.ZS | [https://api.worldbank.org/v2/country/all/indicator/IT.NET.USER.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/IT.NET.USER.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 840 |
| WDI:NE.TRD.GNFS.ZS | [https://api.worldbank.org/v2/country/all/indicator/NE.TRD.GNFS.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/NE.TRD.GNFS.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 728 |
| WDI:NY.GDP.MKTP.KD.ZG | [https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.KD.ZG?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.KD.ZG?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 169 |
| WDI:NY.GDP.MKTP.PP.CD | [https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.PP.CD?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.PP.CD?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 320 |
| WDI:NY.GDP.PCAP.CD | [https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 149 |
| WDI:NY.GDP.PCAP.PP.KD | [https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.KD?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 327 |
| WDI:NY.GDP.TOTL.RT.ZS | [https://api.worldbank.org/v2/country/all/indicator/NY.GDP.TOTL.RT.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.TOTL.RT.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2021 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 1189 |
| WDI:PA.NUS.PPP | [https://api.worldbank.org/v2/country/all/indicator/PA.NUS.PPP?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/PA.NUS.PPP?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 1065 |
| WDI:PA.NUS.PRVT.PP | [https://api.worldbank.org/v2/country/all/indicator/PA.NUS.PRVT.PP?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/PA.NUS.PRVT.PP?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 1150 |
| WDI:PV.EST | [https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_PV_EST?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_PV_EST?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 962 |
| WDI:RQ.EST | [https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_RQ_EST?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/GOV_WGI_RQ_EST?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 987 |
| WDI:SE.SEC.ENRR | [https://api.worldbank.org/v2/country/all/indicator/SE.SEC.ENRR?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SE.SEC.ENRR?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 1417 |
| WDI:SE.TER.ENRR | [https://api.worldbank.org/v2/country/all/indicator/SE.TER.ENRR?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SE.TER.ENRR?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 1625 |
| WDI:SE.XPD.TOTL.GD.ZS | [https://api.worldbank.org/v2/country/all/indicator/SE.XPD.TOTL.GD.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SE.XPD.TOTL.GD.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 1394 |
| WDI:SH.XPD.CHEX.GD.ZS | [https://api.worldbank.org/v2/country/all/indicator/SH.XPD.CHEX.GD.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SH.XPD.CHEX.GD.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 882 |
| WDI:SI.POV.GINI | [https://api.worldbank.org/v2/country/all/indicator/SI.POV.GINI?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SI.POV.GINI?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 3107 |
| WDI:SL.EMP.TOTL.SP.ZS | [https://api.worldbank.org/v2/country/all/indicator/SL.EMP.TOTL.SP.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SL.EMP.TOTL.SP.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 510 |
| WDI:SL.TLF.CACT.FE.ZS | [https://api.worldbank.org/v2/country/all/indicator/SL.TLF.CACT.FE.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SL.TLF.CACT.FE.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 510 |
| WDI:SL.TLF.CACT.MA.ZS | [https://api.worldbank.org/v2/country/all/indicator/SL.TLF.CACT.MA.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SL.TLF.CACT.MA.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 510 |
| WDI:SL.TLF.CACT.ZS | [https://api.worldbank.org/v2/country/all/indicator/SL.TLF.CACT.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SL.TLF.CACT.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 510 |
| WDI:SL.UEM.1524.ZS | [https://api.worldbank.org/v2/country/all/indicator/SL.UEM.1524.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SL.UEM.1524.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 510 |
| WDI:SL.UEM.TOTL.ZS | [https://api.worldbank.org/v2/country/all/indicator/SL.UEM.TOTL.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SL.UEM.TOTL.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 510 |
| WDI:SM.POP.NETM | [https://api.worldbank.org/v2/country/all/indicator/SM.POP.NETM?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SM.POP.NETM?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 16 |
| WDI:SP.DYN.CBRT.IN | [https://api.worldbank.org/v2/country/all/indicator/SP.DYN.CBRT.IN?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.CBRT.IN?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 281 |
| WDI:SP.DYN.CDRT.IN | [https://api.worldbank.org/v2/country/all/indicator/SP.DYN.CDRT.IN?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.CDRT.IN?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 281 |
| WDI:SP.DYN.IMRT.IN | [https://api.worldbank.org/v2/country/all/indicator/SP.DYN.IMRT.IN?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.IMRT.IN?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 596 |
| WDI:SP.DYN.LE00.FE.IN | [https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.FE.IN?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.FE.IN?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 281 |
| WDI:SP.DYN.LE00.IN | [https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.IN?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 281 |
| WDI:SP.DYN.LE00.MA.IN | [https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.MA.IN?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.LE00.MA.IN?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 281 |
| WDI:SP.DYN.TFRT.IN | [https://api.worldbank.org/v2/country/all/indicator/SP.DYN.TFRT.IN?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.DYN.TFRT.IN?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2024 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 281 |
| WDI:SP.POP.1564.TO.ZS | [https://api.worldbank.org/v2/country/all/indicator/SP.POP.1564.TO.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.POP.1564.TO.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 16 |
| WDI:SP.POP.GROW | [https://api.worldbank.org/v2/country/all/indicator/SP.POP.GROW?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.POP.GROW?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 17 |
| WDI:SP.POP.TOTL | [https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 16 |
| WDI:SP.URB.TOTL.IN.ZS | [https://api.worldbank.org/v2/country/all/indicator/SP.URB.TOTL.IN.ZS?date=2010%3A2026&format=json&per_page=20000&page=1](https://api.worldbank.org/v2/country/all/indicator/SP.URB.TOTL.IN.ZS?date=2010%3A2026&format=json&per_page=20000&page=1) | 2026-10-08 | 2010–2025 | SUCCESS (HTTP 200) | 4256 / 4256 | 0 / 0 / 0 | 0 / 16 |
| Eurostat:migr_emi2 | [https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/migr_emi2?lang=EN&freq=A&unit=NR&age=TOTAL&agedef=REACH&sex=T&sinceTimePeriod=2010&untilTimePeriod=2026](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/migr_emi2?lang=EN&freq=A&unit=NR&age=TOTAL&agedef=REACH&sex=T&sinceTimePeriod=2010&untilTimePeriod=2026) | not exposed by dataset API | 2010–2026 | SUCCESS (HTTP 200) | 748 / 748 | not tracked / not tracked / not tracked | 0 / 237 |
| Eurostat:migr_imm8 | [https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/migr_imm8?lang=EN&freq=A&unit=NR&age=TOTAL&agedef=REACH&sex=T&sinceTimePeriod=2010&untilTimePeriod=2026](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/migr_imm8?lang=EN&freq=A&unit=NR&age=TOTAL&agedef=REACH&sex=T&sinceTimePeriod=2010&untilTimePeriod=2026) | not exposed by dataset API | 2010–2026 | SUCCESS (HTTP 200) | 629 / 629 | not tracked / not tracked / not tracked | 0 / 106 |
| OECD:DSD_MIG@DF_MIG; official Explorer query selector .W.A.B11._T... | [https://sdmx.oecd.org/public/rest/data/OECD.ELS.IMD,DSD_MIG@DF_MIG,1.0/.W.A.B11._T...?startPeriod=2010&endPeriod=2026&dimensionAtObservation=AllDimensions&format=csvfilewithlabels](https://sdmx.oecd.org/public/rest/data/OECD.ELS.IMD,DSD_MIG@DF_MIG,1.0/.W.A.B11._T...?startPeriod=2010&endPeriod=2026&dimensionAtObservation=AllDimensions&format=csvfilewithlabels) | not exposed by endpoint | 2010–2023 | SUCCESS (HTTP 200) | 505 / 290 | not tracked / not tracked / not tracked | 0 / 0 |
| ILOSTAT:ILOSTAT | [https://rplumber.ilo.org/data/indicator?id=POP_MFRB_SEX_CBR_NB_A&lang=en&type=both&format=.csv&timefrom=2010&timeto=2025](https://rplumber.ilo.org/data/indicator?id=POP_MFRB_SEX_CBR_NB_A&lang=en&type=both&format=.csv&timefrom=2010&timeto=2025) | not exposed by endpoint | 2010–2024 | SUCCESS (HTTP 200) | 8448 / 2522 | not tracked / not tracked / not tracked | 0 / 0 |
| ILOSTAT:ILOSTAT | [https://rplumber.ilo.org/data/indicator?id=EMP_MFRB_SEX_CBR_NB_A&lang=en&type=both&format=.csv&timefrom=2010&timeto=2025](https://rplumber.ilo.org/data/indicator?id=EMP_MFRB_SEX_CBR_NB_A&lang=en&type=both&format=.csv&timefrom=2010&timeto=2025) | not exposed by endpoint | 2010–2024 | SUCCESS (HTTP 200) | 6940 / 2171 | not tracked / not tracked / not tracked | 0 / 0 |
| ILOSTAT:ILOSTAT | [https://rplumber.ilo.org/data/indicator?id=POP_MFLB_SEX_CBR_NB_A&lang=en&type=both&format=.csv&timefrom=2010&timeto=2025](https://rplumber.ilo.org/data/indicator?id=POP_MFLB_SEX_CBR_NB_A&lang=en&type=both&format=.csv&timefrom=2010&timeto=2025) | not exposed by endpoint | 2011–2024 | SUCCESS (HTTP 200) | 5752 / 1776 | not tracked / not tracked / not tracked | 0 / 0 |
| UNHCR:UNHCR | [https://api-data.unhcr.org/api/v0/data/export/PopStatsOfficial](https://api-data.unhcr.org/api/v0/data/export/PopStatsOfficial) | not exposed by endpoint | 2009-12–2025-12 | SUCCESS (HTTP 200) | 670526 / 242461 | not tracked / not tracked / not tracked | 0 / 0 |
| UN DESA:destination | [https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_and_destination.xlsx](https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_and_destination.xlsx) | 2024 dataset release; exact publication date not exposed by status file | 1990–2024 | SUCCESS (HTTP 200) | 5640 / 5640 | not tracked / not tracked / not tracked | 0 / 48 |
| UN DESA:origin | [https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_and_origin.xlsx](https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_and_origin.xlsx) | 2024 dataset release; exact publication date not exposed by status file | 1990–2024 | SUCCESS (HTTP 200) | 5640 / 5640 | not tracked / not tracked / not tracked | 0 / 48 |
| UN DESA:bilateral | [https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx](https://www.un.org/development/desa/pd/sites/www.un.org.development.desa.pd/files/undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx) | 2024 dataset release; exact publication date not exposed by status file | 1990–2024 | SUCCESS (HTTP 200) | 224352 / 224352 | not tracked / not tracked / not tracked | 0 / 1 |
| OBMigra:official_page_monitor | [https://www.gov.br/mj/pt-br/assuntos/seus-direitos/migracoes/portal-de-imigracao-laboral/obmigra-1/relatorios-obmigra/dados-consolidados/2025](https://www.gov.br/mj/pt-br/assuntos/seus-direitos/migracoes/portal-de-imigracao-laboral/obmigra-1/relatorios-obmigra/dados-consolidados/2025) | not applicable | — | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Canada:IRCC Express Entry news | [https://www.canada.ca/en/immigration-refugees-citizenship/news.html](https://www.canada.ca/en/immigration-refugees-citizenship/news.html) | not extracted; manual event review required | 2026-10-28T07:24:28.792570+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:United Kingdom:UK immigration policy news | [https://www.gov.uk/government/organisations/uk-visas-and-immigration](https://www.gov.uk/government/organisations/uk-visas-and-immigration) | not extracted; manual event review required | 2026-10-28T07:24:28.865108+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Australia:Department of Home Affairs immigration news | [https://immi.homeaffairs.gov.au/news-media/archive](https://immi.homeaffairs.gov.au/news-media/archive) | not extracted; manual event review required | 2026-10-28T07:24:29.006496+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:New Zealand:Immigration New Zealand news | [https://www.immigration.govt.nz/about-us/news-centre/](https://www.immigration.govt.nz/about-us/news-centre/) | not extracted; manual event review required | 2026-10-28T07:24:29.938852+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Ireland:Employment permits current processing dates | [https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/current-application-processing-dates/](https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/current-application-processing-dates/) | not extracted; manual event review required | 2026-10-28T07:24:31.757291+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Singapore:Ministry of Manpower work passes | [https://www.mom.gov.sg/passes-and-permits](https://www.mom.gov.sg/passes-and-permits) | not extracted; manual event review required | 2026-10-28T07:24:32.708798+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Hong Kong:Immigration Department press releases | [https://www.immd.gov.hk/eng/press/press_releases.html](https://www.immd.gov.hk/eng/press/press_releases.html) | not extracted; manual event review required | 2026-10-28T07:24:33.359634+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Japan:Immigration Services Agency | [https://www.moj.go.jp/isa/](https://www.moj.go.jp/isa/) | not extracted; manual event review required | 2026-10-28T07:24:33.725442+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Switzerland:State Secretariat for Migration latest news | [https://www.sem.admin.ch/sem/en/home/sem/aktuell.html](https://www.sem.admin.ch/sem/en/home/sem/aktuell.html) | not extracted; manual event review required | 2026-10-28T07:24:34.058890+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Austria:Austrian Federal Government migration portal | [https://www.migration.gv.at/en/welcome/](https://www.migration.gv.at/en/welcome/) | not extracted; manual event review required | 2026-10-28T07:24:35.560244+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| PolicyPage:Spain:La Moncloa press releases — Inclusion, Social Security and Migration | [https://www.lamoncloa.gob.es/serviciosdeprensa/notasprensa/inclusion/Paginas/index.aspx](https://www.lamoncloa.gob.es/serviciosdeprensa/notasprensa/inclusion/Paginas/index.aspx) | not extracted; manual event review required | 2026-10-28T07:24:36.545322+00:00 | SUCCESS (HTTP 200) | 0 / 0 | not tracked / not tracked / not tracked | — / — |
| Derived:Brazil_WDI_subset | [multiple WDI indicator endpoints; see WDI indicator rows](multiple WDI indicator endpoints; see WDI indicator rows) | inherits WDI vintages; see indicator rows | 2010–2025 | DERIVED | 0 / 624 | not tracked / not tracked / not tracked | 0 / — |

Hash changes on policy pages are review flags, not confirmed policy events. Supplemental tables retain raw snapshots, but not all yet have per-row revision ledgers. Country-year outcomes remain a fallback because a globally harmonized bilateral flow panel is not yet complete.
