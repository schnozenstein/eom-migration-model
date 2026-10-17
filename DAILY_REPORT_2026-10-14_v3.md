# EOM General Migration Model — Daily Research Run v3

**Run date:** 14 October 2026 (Asia/Kolkata)  
**Status:** Audit completed; macro-ingestion blocker remains.  
**Model:** Conceptual and empirically uncalibrated; no ranking, fit, backtest or causal estimate was produced.

## 1. Executive result

The pipeline's offline data audit was regenerated, the current source state was checked for Ireland, the UK and Australia, and the implementation was reviewed. The World Bank ingestion was retried and failed because the local runtime could not resolve `api.worldbank.org`. No new macroeconomic observations were downloaded. Six unit tests passed when run with `PYTHONPATH=src`.

No new policy event was appended because the checked official items were already represented in the prior policy log or showed no newer dated observation. No numerical energy change or destination reranking is warranted.

## 2. Evidence and source checks

- **Ireland:** the official Department of Enterprise, Tourism and Employment page still states a processing-date snapshot as of 13 October 2026. It is a receipt-date frontier, not a processing duration or approval rate. The existing snapshot is retained; no duplicate row was added. Source: https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/current-application-processing-dates/current-processing-dates-for-employment-permits.html
- **United Kingdom:** the Home Office September 2026 monthly entry-clearance release was published on 8 October and is already recorded in the evidence log. It reports provisional rolling-year application counts, including 352,500 sponsored-study main-applicant applications (-19% year-on-year) and 26,400 Skilled Worker main-applicant applications (-43%). These are application volumes, not approvals or a causal measure of attractiveness. No newer release was identified. Source: https://www.gov.uk/government/statistics/monthly-entry-clearance-visa-applications-september-2026/monthly-entry-clearance-visa-applications-september-2026
- **Australia:** the official explainer confirms student-visa application rule changes effective 2 October 2026, with pre-effective-date applications treated under previous rules. This is already logged; no new rule change was identified. Effects are cohort-specific, so no national energy score was changed. Source: https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/changes-to-student-visa-application-rules-500-590/what-you-need-to-do

These are source checks, not new observations added to the historical panel. Full check metadata is in `metadata/source_checks_2026-10-14.csv`.

## 3. Data coverage and missingness

The historical scaffold remains **756 destination-year rows**, **21 destinations**, **1990–2025**. The regenerated audit contains 15 indicator records across the historical panel and two native Eurostat extracts.

| Indicator | Observed / expected | Coverage | Interpretation caveat |
|---|---:|---:|---|
| UN DESA migrant stock in panel | 160 / 756 | 21.16% | Stock, not annual flow |
| ILO 5WAP labour-force participation | 228 / 756 | 30.16% | Labour-supply proxy, not job vacancies |
| ILO DWAP labour-force participation | 696 / 756 | 92.06% | Alternate standard; kept separate from 5WAP |
| Eurostat immigration by birth in merged panel | 58 / 756 | 7.67% | Limited Europe-heavy coverage |
| Eurostat emigration in merged panel | 58 / 756 | 7.67% | Annual flow; definitions differ by series |
| Eurostat immigration by citizenship in merged panel | 58 / 756 | 7.67% | Not interchangeable with birth/residence definitions |
| Eurostat emigration by birth in merged panel | 65 / 756 | 8.60% | Sparse in the global scaffold |
| Eurostat immigration by previous residence in merged panel | 67 / 756 | 8.86% | Sparse in the global scaffold |

Native Eurostat selected-total extract: 960 rows, five indicators, 32 geographies, 2019–2024; observed values per indicator range from 166/192 to 186/192. The two-indicator extract contains 396 rows across 33 geographies, 2019–2024; 188/198 and 190/198 values are observed. The destination-year panel merge covers far fewer geographies than the native extracts.

The raw World Bank macro panel is still absent (`data/raw/world_bank_long.csv`). The fetcher was actually run for 2010–2025 and failed before retrieving the first indicator due to DNS/network resolution. This run added **zero** macro observations.

## 4. Model/code audit

The following issues are documented in `metadata/code_review_2026-10-14.csv`; no model formula was changed this run:

1. `robust_z` currently uses arithmetic mean and standard deviation, not a median/MAD robust scaler. Rename or implement a genuinely robust scaler in a versioned change, then sensitivity-test.
2. `make_lagged_panel` labels same-year feature values `lag_*` while using year *t* features to predict year *t+1*. This is not itself future-target leakage, but the naming is misleading; add an explicit origin-alignment test before future edits.
3. GDP price-level ratio is only a broad cost proxy, not housing or migrant-specific affordability.
4. Six energy components are required for a complete equal-weight score; they are not currently aligned in the available historical panel.
5. The prediction ledger remains correctly empty: zero forecasts registered. No forecast was manufactured merely to populate it.

## 5. EOM energy direction and ranking

**No numerical energy scores or rankings were produced.** The paper's convention remains: lower energy indicates a stronger attractor. The current evidence suggests profile-specific qualitative considerations—for example, Australia's recent onshore-switching/family rules may raise energy for affected cohorts—but the evidence does not support comparable numeric adjustments across countries. Ireland queue movement is an administrative processing indicator, not a destination attractiveness score. UK rolling application declines do not directly identify policy effects or a general attractor shift.

## 6. Model and evaluation status

| Component | Status |
|---|---|
| Calibration / parameter estimation | Not performed |
| Equal-weight EOM ranking | Not produced |
| Prediction ledger | 0 rows |
| Chronological expanding-origin backtest | Not performed |
| Benchmark metrics | Not available |
| Causal policy estimates | Not performed |
| Unit tests | 6 passed with `PYTHONPATH=src` |

There are no training or test periods and no empirical metrics to report. Unit tests validate selected software behaviour only; they do not validate the migration theory. Predictive validation and causal inference remain distinct.

## 7. Change log and next empirical limitation

- Added `data/data_quality_audit_general_2026-10-14.csv` (15 indicator records).
- Added `metadata/code_review_2026-10-14.csv` and `metadata/source_checks_2026-10-14.csv`.
- Refreshed `data/model_feedback/evaluation_gate_2026-10-14.json` and `metadata/run_manifest_2026-10-14.json`.
- No changes to the conceptual energy equation, model coefficients, source observations or prediction ledger.
- Preserved prior run report and the previous package.

**Next action:** ingest a sourceable, aligned macro panel in a network-enabled environment; then audit coverage for each energy term and the migration outcome denominator before registering forecasts or ranking destinations. Maintain the global architecture; Tech MBA remains an optional scenario only.
