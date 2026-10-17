# EOM General Migration Model — daily rerun report

**Run date:** 15 October 2026  
**Run ID:** EOM-GENERAL-2026-10-15-v5-rerun  
**Status:** Completed with empirical limitations

## 1. What failed, and what was fixed

The previous attempt failed before processing because the file-processing runtime returned a `ClientError`. The uploaded ZIP itself is not corrupt: the archive passed its CRC/integrity test and contains `WDICSV.csv`, `WDICountry.csv`, `WDISeries.csv`, `WDIcountry-series.csv`, `WDIfootnote.csv`, and `WDIseries-time.csv`. The latest CSV has a `2025` column. The current run successfully streamed the relevant indicator rows, created a long-format dataset, reran the score and chronological evaluation, and passed all six tests. The exact cause of the earlier runtime error could not be established; the new run succeeded in the current session.

## 2. Data ingestion and source lineage

- Source: user-uploaded `WDI_CSV.zip`, publisher World Bank; official catalog: https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators
- ZIP integrity: passed. The archive includes a 2025 year column; the exact official publication date for this particular ZIP was not independently verified.
- Current CSV: **153,770 observed rows** across **12 of the 16 requested indicators**, 265 country/aggregate codes, with observed values through 2025 for several indicators. Blank cells were not converted to zero.
- Combined historical panel: **175,361 rows**, **16 indicators**, **265 country/aggregate codes**, 1960–2025.
- Four requested indicators were absent entirely from the uploaded CSV: `GE.EST` (government effectiveness), `PA.NUS.PPPC.RF` (GDP price-level ratio), `PV.EST` (political stability), and `RQ.EST` (regulatory quality). They were retained from the prior user-supplied WDI Excel vintage and explicitly marked as legacy-source rows. No values were fabricated or carried forward.

## 3. Why the ranking is still 2023, not 2025

The six-component energy baseline requires income, cost, job-opportunity, policy, institutional-quality and stability proxies. The latest CSV provides 2025 data for some components, but the four missing series listed above have no 2024/2025 observations in this input. The latest year with complete six-component coverage for at least 10 focus destinations is therefore **2023**. A 2025 partial-observation dashboard is provided separately and is not presented as an EOM ranking.

### Focus-country indicator coverage in 2025

| Indicator | Destinations with observations | Coverage |
|---|---:|---:|
| GDP per capita, PPP (income proxy) | 19/19 | 100.0% |
| Price-level ratio (cost proxy) | 0/19 | 0.0% |
| Unemployment (job-opportunity proxy) | 19/19 | 100.0% |
| Regulatory quality (policy proxy) | 0/19 | 0.0% |
| Government effectiveness (institution proxy) | 0/19 | 0.0% |
| Political stability (stability proxy) | 0/19 | 0.0% |
| Net migration count | 19/19 | 100.0% |
| Population | 19/19 | 100.0% |

## 4. Updated equal-weight EOM ranking — 2023

Lower energy indicates a stronger attractor under the paper’s convention. These are standardized macro proxies with equal weights—not migration probabilities, personal recommendations, or calibrated parameters.

| Rank | Destination | Energy score | Change vs prior run |
|---:|---|---:|---:|
| 1 | Singapore | -11.716 | 0 |
| 2 | Ireland | -2.887 | 0 |
| 3 | Norway | -2.231 | 0 |
| 4 | Switzerland | -1.706 | 0 |
| 5 | New Zealand | -1.413 | 0 |
| 6 | Hong Kong | -1.172 | +1 |
| 7 | Japan | -1.125 | +2 |
| 8 | Denmark | -1.079 | -2 |
| 9 | Netherlands | -1.024 | -1 |
| 10 | Australia | -0.945 | 0 |
| 11 | Czechia | 0.318 | 0 |
| 12 | Canada | 1.407 | 0 |
| 13 | Germany | 1.587 | 0 |
| 14 | Finland | 2.026 | 0 |
| 15 | Sweden | 2.163 | 0 |
| 16 | Austria | 2.525 | 0 |
| 17 | United Kingdom | 3.344 | 0 |
| 18 | United States | 5.049 | 0 |
| 19 | France | 6.879 | 0 |

The ranking correlation with the prior 2023 run is **0.991** (Spearman); **15 of 19** destinations kept the same rank. The top five remain Singapore, Ireland, Norway, Switzerland and New Zealand. Hong Kong moved 7th to 6th, Japan 9th to 7th, Denmark 6th to 8th, and the Netherlands 8th to 9th. This comparison reflects refreshed values and standardization, not a change to EOM theory or a policy-driven reranking.

## 5. Chronological backtest

- Outcome: next-year national net migration per 1,000 residents.
- Method: expanding-origin evaluation; no random split. Features in year t predict the outcome in t+1.
- Scored rows: **4,174** across **177** countries/territories and **24** eligible target years (1999, 2001, 2003–2024; gaps reflect data availability).
- Ridge comparator: MAE **6.013**, RMSE **11.000**, R² **0.131**.
- Country-mean baseline MAE: **3.939**. Persistence baseline MAE: **2.408**.
- Mean pooled rank association: equal-weight EOM **0.402**, Ridge **0.445**, persistence **0.876**.

Persistence substantially outperforms the EOM score and the Ridge comparator on pooled MAE and rank association. This is evidence that the current macro operationalization is not yet a strong forecasting model; it does not refute every possible EOM specification. Pooled metrics do not fully account for serial dependence or country clustering; uncertainty intervals have not been estimated.

## 6. Tests, model status and causal claims

- Unit tests: **6 passed**. This verifies selected code behaviour only.
- Equal-weight baseline: computed for 2023; not calibrated.
- Fitted model: Ridge comparator fitted within expanding-origin folds; this does not calibrate EOM energy weights.
- Prediction ledger: no forward forecasts entered. Historical backtest predictions remain in the separate backtest output.
- Causal estimates: none. Predictive association is not causal evidence.
- 2024/2025 full EOM ranking: not produced because key energy components are unavailable for those years.

## 7. Artifacts and next limitation

- `data/raw/world_bank_long.csv` — merged long-format panel with per-row source/vintage labels.
- `data/raw/wdi_csv_long_latest.csv` — selected observations extracted from the uploaded CSV release.
- `metadata/world_bank_ingestion_manifest_2026-10-16.json` — ingestion details; filename reflects the internal execution path, not the report date.
- `outputs/latest_macro_eom_ranking.csv` — current ranking.
- `outputs/ranking_comparison_2023_previous_vs_rerun.csv` — rank changes vs previous baseline.
- `outputs/focus_indicator_coverage_2020_2025.csv` — coverage matrix.
- `outputs/focus_observed_indicators_2025_no_ranking.csv` — 2025 observed-data dashboard, no energy ranking.
- `outputs/macro_backtest.json`, `outputs/macro_backtest_predictions.csv`, `outputs/macro_backtest_folds.csv`, and `outputs/macro_backtest_rank_metrics.csv` — evaluation records.
- `data/data_quality_audit_world_bank_2026-10-16.csv` — row/coverage audit.

Next priority: obtain defensible, source-documented replacement series for cost/price level, regulatory quality, government effectiveness and political stability, with comparable observations for 2024–2025 if available. Do not fill gaps by forward-carrying old values or silently change the energy formula. The EOM model remains uncalibrated and not causally validated.
