# EOM General Migration Model — Daily Research Report
**Run date:** 13 October 2026 (second run)  
**Model version:** `EOM-general-unfitted-2026-10-13-r1`  
**Status:** conceptual / uncalibrated / not backtested

## 1. Executive result

This run made real, auditable progress on data lineage and coverage, corrected the package's default scenario interface to be general-purpose, and appended the latest Irish employment-permit processing-date frontiers. It did **not** estimate model parameters, issue forecasts, run a backtest, produce a numerical energy ranking, or estimate causal effects.

The paper's sign convention remains: `E_i = -S_i + C_i - P_i - O_i - U_i - R_i`. Read in English: energy equals minus salary plus cost minus policy friendliness minus job opportunity minus institutional quality minus stability. Lower energy means a stronger attractor. The empirical model remains uncalibrated until relevant parameters are estimated and evaluated against suitable outcomes.

## 2. New observation / policy evidence

### Ireland — processing-date frontier, as of 13 October 2026

The Department of Enterprise, Tourism and Employment page states that applications are processed in date order of receipt of a fully completed application and fee. As of 13 October, it reports receipt frontiers of 6 October for Critical Skills permits, 8 September for new General Employment Permits, 19 August for other new permits, 12 October for new intra-company transfers, 23 July for ICT renewals, 23 July for other renewals, and 28 April for reviews/appeals. The Critical Skills frontier remained at 6 October between 12 and 13 October. The General Employment frontier moved from 4 September on 12 October to 8 September on 13 October; that is a four-calendar-day receipt-frontier shift over one calendar day, not a four-day processing time. Compared with the 8 October snapshot, the ICT-new frontier moved from 5 October to 12 October, the ICT-renewal frontier from 20 July to 23 July, the other-renewal frontier from 17 July to 23 July, and the other-new and reviews/appeals frontiers were unchanged.

These are operational queue-frontier observations, not average processing times, approval rates, labour-demand measures, or settlement probabilities. The movement is too short to justify an energy-score or ranking change. The current page is the only newly retrieved external observation in this run; no new policy shock was verified.

Source: Ireland Department of Enterprise, Tourism and Employment, current processing dates, page status as of 13 October 2026: https://www.enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/current-application-processing-dates/current-processing-dates-for-employment-permits.html

### Previously recorded signals retained, not treated as new today

- UK Home Office's 8 October release reports 352,500 sponsored-study main-applicant applications (19% lower year-on-year), 26,400 Skilled Worker main-applicant applications (43% lower), and 15,700 student-dependant applications (31% lower) for the 12 months ending 30 September 2026. These are provisional rolling 12-month application counts, not approvals, hires, or settlement outcomes. Source: https://www.gov.uk/government/statistics/monthly-entry-clearance-visa-applications-september-2026/monthly-entry-clearance-visa-applications-september-2026
- Australia's Student visa onshore/family rules took effect 2 October 2026; the official explainer was published 7 October. Offshore first-time applications remain possible; exemptions apply; existing Student visas are unaffected. This was already logged in the prior run. Source: https://www.studyaustralia.gov.au/en/tools-and-resources/news/student-visa-changes-october-2026
- New Zealand's qualification-specific post-study changes are scheduled from 16 November 2026; not a general MBA entitlement and not a new announcement today. Source: https://www.immigration.govt.nz/about-us/news-centre/new-and-updated-post-study-work-visa-options/

No verified new policy item for the other tracked destinations was incorporated in this run. This does not imply no changes occurred; only that no new sufficiently verified event was added.

## 3. Actual pipeline changes

- Appended **7** Ireland processing-date frontier observations dated 13 October to `data/operational_indicators_snapshot.csv`. For Critical Skills and GEP, the previous-day comparison is recorded; the other five categories are compared with the 8 October official snapshot. No prior values were inferred.
- Added `metadata/source_lineage_2026-10-13.csv` with **8** source-lineage records covering publisher, dates/vintage, observation period, definition, unit, geography, cohort, missingness and limitations.
- Added `data/data_quality_audit_general_2026-10-13.csv` with **15** audit rows across destination-year panel variables and native Eurostat long indicators.
- Added `data/model_feedback/feature_readiness_audit_2026-10-13.csv` with **12** EOM component/domain rows mapping the paper's terms to candidate measurements, available evidence and next actions.
- Updated `data/model_feedback/baseline_coverage_and_status_2026-10-13.json` with exact current coverage and explicit no-fit/no-backtest status.
- Added `data/model_feedback/evaluation_gate_2026-10-13.json` explaining why fitting/backtesting is currently gated.
- Added model registry version `EOM-general-unfitted-2026-10-13-r1`, preserving the previous version row.
- Replaced the default configuration with a generic scenario interface and moved the previous Tech-MBA profile to `config/scenarios/tech_mba_example.json` as optional only.
- Added reusable code under `src/eom_empirical/`, including an expanding-origin evaluation helper and a macro backtest that compares Ridge with persistence/country-mean baselines; added tests under `tests/` and an offline coverage-audit script at `scripts/audit_general_eom_panel.py`. The evaluator was tested on synthetic fixtures only; no empirical model was fit in this run.
- Preserved the prior same-day report in `archive/DAILY_REPORT_2026-10-13_previous_run.md`.

## 4. Current data coverage and missingness

### Historical destination-year panel

- **756 rows**, **21 destinations**, **1990–2025**; rectangular coverage does not imply complete annual observations.
- UN DESA migrant stock: **160/756 nonmissing (21.16%)**, covering 20 destinations. This is a stock estimate available at selected benchmark years, not an annual flow.
- ILOSTAT 5WAP labour-force participation: **228/756 (30.16%)**, 19 destinations; nonmissing observations span 2014–2025.
- ILOSTAT DWAP legacy/alternate labour-force participation: **696/756 (92.06%)**, 20 destinations; kept separate from 5WAP because standards differ.
- Merged Eurostat flow fields have only **58–67 nonmissing values per 756-row global panel field**, generally 11–12 destinations in 2019–2024. Only **67 of 756 destination-year rows** contain at least one observed Eurostat flow value. The apparent low percentage reflects a global panel scaffold containing many non-Eurostat geographies and pre-2019 years.

### Native Eurostat extracts

- Selected-total long table: **960 rows**, five indicators, 32 geographies, 2019–2024. Observed values: emigration 168/192; emigration by birth 184/192; immigration by birth 166/192; immigration by citizenship 166/192; immigration by previous residence 186/192.
- Two newly processed indicators: **396 rows**, 33 geographies, 2019–2024. Emigration by birth has 188/198 observed values; immigration by previous residence has 190/198.
- Total dimensions were selected rather than summed over categories; missing/suppressed values remain missing. Definitions by birth, citizenship and previous residence are not interchangeable.
- The current bilateral origin-destination-year template remains empty; no harmonized global bilateral flow panel has been populated.

## 5. EOM energy direction and ranking

**No numeric energy change or destination reranking is warranted.** The Ireland receipt-date frontier is an operational queue measure and cannot be translated into a calibrated energy term without an explicit measurement model. The UK and Australia signals already logged are still relevant qualitative policy/route evidence, but they do not justify numerical score changes. No energy feature set is sufficiently complete and comparable to calculate a defensible general ranking in this run.

## 6. Model status, fitting and backtesting

- Status: **conceptual, uncalibrated, not backtested**.
- Training/test periods: **none**; no model was fitted.
- Prediction ledger: **0 forecasts**; outcome ledger: **0 matched outcomes**; evaluation runs: **0 completed**; causal studies: **0 completed**.
- No metrics are reported because no EOM forecast or baseline comparison was run.
- Reason for gate: current panel lacks aligned salary/income, cost, policy, institutional-quality and stability features. Existing flows cover a limited set of destinations and years and lack a consistently aligned population denominator in the current package. A purported EOM-versus-baseline backtest from these inputs would be misleading.
- A World Bank API download was attempted from the local runtime but failed at DNS/network resolution. No new World Bank observations were downloaded or claimed.

## 7. Predictive findings vs causal conclusions

**Predictive:** no forecasts or accuracy findings were produced.  
**Causal:** no policy effect was estimated. The Ireland queue frontier is descriptive only. The UK rolling application changes are not causally attributed to any single policy, and Australia's route restrictions have not been evaluated with a counterfactual design. Correlation, qualitative energy direction, and feedback alone do not prove causation.

## 8. Model version, change log and next limitation

- New version: `EOM-general-unfitted-2026-10-13-r1`; prior version preserved in the registry.
- Change: broadened audit/lineage, updated Ireland operational snapshot, mapped EOM terms to measurement gaps, and made the default configuration general-purpose.
- Next empirical limitation: construct a harmonized destination-year feature matrix for the paper's energy terms and a consistently defined flow or stock outcome, then pre-register a chronological evaluation design. Prioritize origin-destination stocks/networks and official annual flows; add salary, costs/housing, labour demand, governance/stability and policy regime data with source vintage and missingness. Do not fit or rerank until that matrix is adequate.

## 9. Reproducibility and source caveats

The expanded audit is reproducible with `python scripts/audit_general_eom_panel.py`. It only audits existing local data; it does not fetch, impute, fit, forecast, calibrate, rank, or estimate causal effects. The macro evaluation code now uses expanding-origin folds, but was not run on empirical data because the World Bank raw panel is absent and the current processed panel is not feature-aligned. Full source details are in `metadata/source_lineage_2026-10-13.csv`.
