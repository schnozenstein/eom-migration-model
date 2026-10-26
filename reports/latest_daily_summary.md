# EOM Daily Research Report

> Generated: 2026-10-26 11:07 UTC

## 1. Executive summary

- **Latest refresh run:** `2026-10-26T110344Z`
- **Refresh timestamp:** 2026-10-26T11:03:44.807665+00:00
- **World Bank observations fetched:** 165984
- **World Bank indicator requests:** 39 succeeded; 0 failed
- **Brazil World Bank extract:** 624 fresh Brazil indicator-year rows
- **Eurostat total migration flows:** 2 series succeeded; 0 failed; 1034 observed annual cells across up to 44 reporting geographies
- **UNHCR forced-displacement extract:** SUCCESS; 242461 retained focus/origin rows
- **UN DESA migrant-stock tables:** 3 of 3 files succeeded; 0 failed; 235632 normalized rows
- **OECD migration database slice:** SUCCESS; 290 focus-country rows retained
- **ILOSTAT migrant-labour indicators:** 3 succeeded; 0 failed; 6469 focus rows
- **Brazil OBMigra official source page:** SUCCESS (catalogue monitor only; report tables are not numerically parsed)
- **Policy pages:** 11 succeeded; 0 failed
- **Freshness dashboard:** 38 recent; 2 requiring attention out of 40 indicators
- **Macro ranking recomputed in this run:** Yes
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

This is the latest stored macro-proxy ranking, not a personalised migration recommendation. It does not include complete joie de vivre or individual visa-feasibility scoring.

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

## 5. Joie de vivre and visa feasibility

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
| PA.NUS.PPPC.RF | 2023 | STALE_OR_SLOW_RELEASE |

A recent retrieval timestamp does not guarantee a recent statistical observation. Some indicators are released with a delay, so check release schedules before labelling them defective.

## 7. Next research actions

- Investigate failed data requests and retry policy pages that were not retrieved.
- Check observation years and source release schedules for indicators needing attention.
- Investigate why the persistence baseline outperforms Ridge and EOM in the stored backtest.
- Verify that every predictor would have been available at the forecast date; inspect missing-data handling and baseline definitions.
- Obtain comparable, sourced wellbeing and work-life indicators before calculating joie de vivre scores.
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
- `data/observations_history/world_bank_observations.csv`
- `data/raw/eurostat_migration_flows.csv`
- `data/raw/undesa_migrant_stock_long.csv`
- `data/raw/unhcr_forced_displacement_focus.csv.gz`
- `data/raw/oecd_migration_database_focus.csv`
- `data/raw/ilostat_migrant_labour_focus.csv`
- `metadata/eurostat_source_status.csv`, `metadata/undesa_source_status.csv`, `metadata/unhcr_source_status.csv`, `metadata/oecd_source_status.csv`, `metadata/ilostat_source_status.csv`
