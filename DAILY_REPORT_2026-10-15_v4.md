# EOM General Migration Model — Daily Research Run (2026-10-15)

## Executive result

The user-supplied World Bank WDI workbook was successfully ingested. A first **exploratory equal-weight EOM ranking** was produced for the 19 focus destinations using the latest common year with complete values for all six current energy proxies: **2023**. A chronological expanding-origin macro backtest also ran. **EOM remains uncalibrated**: no energy weights were estimated, and the equal-weight score is not a probability or a causal effect.

## 1. New observations and policy evidence

- **Macro data:** imported the user-supplied `WDI_excel.zip` containing `WDIEXCEL.xlsx`. The workbook member timestamp is 2025-06-05 17:55; this timestamp is recorded as file metadata, **not asserted to be the official publication date**. The dataset catalog is [World Development Indicators](https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators), publisher: World Bank. Selected 16 indicators; observations span 1960–2024.
- **UK policy update:** the Home Office Immigration Rules updates page lists amendments published 8 October 2026 reflecting Statement of Changes HC 584. Some provisions have different commencement dates (8 October, 29 October, 30 November and 9 December 2026). The update affects specified appendices/cohorts, including Government Authorised Exchange and Hong Kong BN(O), alongside other provisions; it is **not treated as a general Skilled Worker rule change**. Source: [Home Office updates](https://www.gov.uk/guidance/immigration-rules/updates) and [Parliamentary statement on commencement dates](https://questions-statements.parliament.uk/written-statements/detail/2026-09-03/hlws317).
- No numerical EOM energy adjustment was assigned to the UK policy update because cohort-specific eligibility and mechanism need to be mapped before scoring.

## 2. Data and pipeline changes

- Converted WDI wide Data sheet into `data/raw/world_bank_long.csv`: **171,299 nonmissing country-indicator-year observations**, 16 selected indicators, 265 country/aggregate codes, 1960–2024. Missing values were not converted to zero.
- Added `data/world_bank_indicator_metadata_selected.csv` with definitions, units, periodicity and source information.
- Added `data/world_bank_focus_coverage_2023.csv` with per-destination indicator availability and missingness flags.
- Added `data/data_quality_audit_world_bank_2026-10-15.csv`, `metadata/world_bank_ingestion_manifest_2026-10-15.json`, source registry entry, and evaluation gate.
- Updated `data/policy_evidence_log.csv` with the UK HC 584 update, keeping publication date and provision-specific effective dates separate.
- Corrected the misleading `robust_z` helper name to `standard_z`; it uses mean/std standardization, **not** median/MAD robust scaling.
- Excluded WDI rows without a country-region classification from country-level backtesting to avoid treating aggregate geographies as countries.
- Tests: **6 passed**.

## 3. Coverage and missingness

- WDI input: 171,299 observed rows, 16 indicators, 265 country/aggregate codes, 1960–2024.
- The six EOM macro proxies all have values for **19 of 19 focus destinations in 2023**: GDP per capita PPP, PPP price-level ratio, unemployment, regulatory quality, government effectiveness and political stability.
- The global backtest scored 177 countries and 4,005 country-year predictions across 23 test target years. Test years: 1999, 2001, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023.
- Coverage is indicator-specific; absence of a value is not interpreted as a zero. The WDI source includes national aggregates, which are retained in the source file but excluded from country-level model fitting.

## 4. Equal-weight EOM ranking — 2023

Lower energy means a stronger attractor under the paper's sign convention. These are dimensionless scores from within-choice-set mean/std standardized proxies, **not calibrated energy units, probabilities, or personal migration success estimates**.

| Rank | Destination | Equal-weight energy (lower = stronger attractor) |
|---:|---|---:|
| 1 | Singapore | -11.707 |
| 2 | Ireland | -2.853 |
| 3 | Norway | -2.120 |
| 4 | Switzerland | -1.593 |
| 5 | New Zealand | -1.355 |
| 6 | Denmark | -1.243 |
| 7 | Hong Kong | -1.206 |
| 8 | Netherlands | -1.083 |
| 9 | Japan | -1.022 |
| 10 | Australia | -0.958 |
| 11 | Czechia | 0.310 |
| 12 | Canada | 1.470 |
| 13 | Germany | 1.555 |
| 14 | Finland | 1.974 |
| 15 | Sweden | 2.098 |
| 16 | Austria | 2.503 |
| 17 | United Kingdom | 3.355 |
| 18 | United States | 5.000 |
| 19 | France | 6.876 |

### Proxy interpretation and limits

- Salary/income proxy: log GDP per capita, PPP (not wages or graduate salaries).
- Cost proxy: GDP price-level ratio of PPP to market exchange rate (not housing affordability or a complete cost-of-living measure).
- Opportunity proxy: negative total unemployment rate (not occupation-specific labour demand).
- Policy: Worldwide Governance Indicators Regulatory Quality estimate.
- Institution: Government Effectiveness estimate.
- Stability: Political Stability and Absence of Violence/Terrorism estimate.

All six inputs are from 2023 for this ranking. No ranking comparison against a prior EOM baseline is available because no prior numerical ranking had been produced. This is the first baseline ranking, not evidence that the ordering is stable. In a separate 1,000-draw sensitivity check with each positive component weight varied uniformly between 0.8 and 1.2 (signs held fixed), Singapore, Ireland and Norway remained ranks 1–3 in every draw. This is only weight-perturbation sensitivity—not a confidence interval, data-uncertainty analysis or parameter estimation.

## 5. Model status and chronological backtest

- **EOM status:** uncalibrated equal-weight baseline; ranking generated; not approved for forward prediction.
- **Backtest:** expanding-origin chronological evaluation; features observed in year t predict national net migration per 1,000 residents in t+1. No random split. Training target years ranged from 1997 through 2022; test target years were 1999–2023, with years omitted when coverage was insufficient.
- **Scored sample:** 4,005 country-year predictions, 177 countries, 23 test years. Minimum training rows per fold: 165; maximum: 3994.
- Ridge benchmark: MAE 6.081, RMSE 11.175, R² 0.131.
- Country-mean baseline MAE: 3.963. Persistence baseline MAE: 2.438.
- Mean within-test-year Spearman association between **EOM attraction (−energy)** and next-year net migration rate: 0.402; Ridge prediction rank association: 0.446; persistence baseline: 0.871.
- The persistence baseline is substantially stronger on rank association, and Ridge MAE is worse than both simple baselines. This is evidence that this current proxy operationalization is not competitive; it does **not** falsify every possible EOM formulation.
- No uncertainty intervals accounting for country/year dependence were computed. Metrics are descriptive and pooled/within-year as noted; stronger claims need cluster/block-aware uncertainty and robust outcome checks.
- Prediction ledger: **0 forward forecasts**. Backtest predictions are stored separately in `outputs/macro_backtest_predictions.csv`.

## 6. Predictive findings vs causal conclusions

- **Predictive:** the equal-weight energy ordering has a positive within-year rank association with next-year national net migration in this historical backtest, but it is weaker than persistence and slightly weaker than Ridge rank association on average. The fitted Ridge model's MAE does not beat simple baselines.
- **Causal:** no causal estimates were made. The UK rule update is logged with publication and effective dates; no difference-in-differences, event study or counterfactual effect is claimed.
- National net migration combines different migrant profiles and reasons. These results cannot be transferred to Indian technology workers, international students, MBA cohorts, family migration or humanitarian flows without separate data and assumptions.

## 7. Model version, change log and next limitation

- Version: `EOM-general-equalweight-unfitted-2026-10-15-v1`.
- Change: WDI source ingestion; 2023 focus-country equal-weight ranking; chronological expanding-origin backtest; global country-level sample excludes unclassified aggregates; UK HC 584 update logged; weight-sensitivity analysis under ±20% positive weight perturbations.
- Sensitivity output: `outputs/weight_sensitivity_2023.csv`. This is a sensitivity diagnostic, not parameter estimation.
- Next limitation: add comparable bilateral origin–destination flows and cohort-specific measures; improve direct wages, labour demand, housing/cost, migration-network, visa-to-work and settlement-transition features; test robustness to outcome revisions and structural breaks; add cluster/block-aware uncertainty; estimate weights only after justified outcome/identification and held-out evaluation.
- No causal estimate, personal migration recommendation, or calibrated probability is produced by this run.
