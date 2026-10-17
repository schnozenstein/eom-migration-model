# EOM General Migration Model — Daily Research Report

**Run date:** 16 October 2026  
**Model version:** EOM-general-equalweight-unfitted-2026-10-16-v2  
**Run status:** Processed-panel rerun, destination-set correction, source/policy audit complete; no fresh raw ZIP ingestion.

## 1. New policy evidence and policy shocks

1. **United Kingdom — implemented, 9 October 2026.** The Home Office states that recognised modern-slavery victims on Skilled Worker visas can leave abusive sponsors and take lawful work for any employer for the remainder of their existing permission. This reduces sponsor lock-in for a narrow cohort; it is not a general rule for all sponsored workers. Source: https://www.gov.uk/government/news/victims-freed-from-abusive-employers-under-new-visa-rules
2. **Singapore — announced, future effective date.** The Ministry of Manpower announced on 3 March 2026 that the ONE Pass (AI and Tech) track is planned for January 2027, and EP/S Pass qualifying salary increases apply to new applications from January 2027 and relevant renewals from January 2028. These changes target distinct cohorts; no broad energy adjustment is justified. Source: https://www.mom.gov.sg/-/media/mom/documents/press-releases/2026/factsheet-on-foreign-workforce-policies-03032026.pdf
3. **Ireland — implemented from 1 March 2026.** Minimum annual remuneration thresholds increased to EUR 36,605 for General Employment Permits and EUR 40,904 for Critical Skills Employment Permits, with further phased changes planned. This can raise eligibility friction for jobs below the thresholds; it is not a uniform effect across applicants. Source: https://enterprise.gov.ie/en/news-and-events/department-news/2025/december/20251202.html
4. **Canada — 2026 selection categories published 18 February 2026.** Express Entry categories include new and renewed groups, including STEM, healthcare/social services, education, trades and French-language proficiency. This changes relative opportunity for eligible profiles but does not guarantee invitation or PR. Source: https://www.canada.ca/en/immigration-refugees-citizenship/news/2026/02/attracting-the-worlds-best-talent-to-fill-canadas-labour-gaps-and-build-our-economy.html
5. **Australia — watchlist only.** Reuters reported an opposition proposal on 6 October 2026 to cut temporary migration and alter student/graduate routes. It is not treated as enacted policy and caused no baseline score change. Source: https://www.reuters.com/world/australian-opposition-party-vows-biggest-cut-immigration-countrys-history-2026-10-06/

All five records were appended to `data/policy_evidence_log.csv` and are also preserved separately in `data/policy_events_added_2026-10-16.csv`. Policy direction is cohort-specific and qualitative; no causal effect is estimated.

## 2. Actual data and pipeline changes

- Added **India** to `data/destinations.csv` as the 20th destination in the global country choice set; Edinburgh remains a nested subnational option, not an extra country in the flat global denominator.
- Re-executed `eom_empirical.fit_macro_model` on the existing merged panel. The ranking is recomputed across all 20 destinations.
- Re-ran tests: **6 passed**.
- Re-ran the general-panel coverage audit: **15 audit rows written**.
- Added `outputs/focus_indicator_coverage_2020_2025_20dest.csv`, `outputs/ranking_comparison_19_to_20_2026-10-16.csv`, `outputs/forecast_ledger_status_2026-10-16.json`, `data/model_feedback/prediction_ledger_2026-10-16.csv`, and `metadata/run_manifest_2026-10-16.json`.
- **No new raw WDI observations were ingested today.** The original uploaded ZIP was not present in the active runtime workspace, so this run used the already processed, source-labelled merged panel. This is a rerun and audit, not a fresh download/re-ingestion.

## 3. Current data coverage and missingness

- Merged long panel: **175,361 observed rows**, **16 indicators**, **265 country/aggregate codes**, years **1960–2025**. Long-format rows contain observed values; absent country-indicator-year combinations must be assessed via coverage, not interpreted as zeros.
- For the 20-destination set, all six ranking components have **20/20 coverage in 2023**.
- The current WDI CSV vintage lacks `PA.NUS.PPPC.RF` (price-level ratio), `RQ.EST` (regulatory quality), `GE.EST` (government effectiveness) and `PV.EST` (political stability). The project retains these four series from an earlier user-uploaded Excel vintage, whose archive timestamp is not a verified publication date. Their latest year is **2023**, so no full six-component 2024/2025 ranking is produced.
- In 2024 and 2025, income PPP, unemployment, net migration and population are present for **20/20** destinations, while each of the four legacy cost/governance series has **0/20** coverage. The coverage matrix explicitly marks these gaps.
- National net migration counts are not origin-destination flows. Comparable origin-destination-year coverage, wages, housing costs and occupation-specific labour access remain major gaps.

## 4. Current 20-destination equal-weight EOM ranking — 2023

Lower energy means a stronger attractor under the paper's convention. Scores are standardized macro proxies within this 20-destination set; they are not calibrated probabilities or individual recommendations.

| Rank | Destination | Energy |
|---:|---|---:|
| 1 | Singapore | -8.481 |
| 2 | Ireland | -2.183 |
| 3 | Norway | -2.158 |
| 4 | Japan | -2.023 |
| 5 | Switzerland | -1.801 |
| 6 | New Zealand | -1.685 |
| 7 | Hong Kong | -1.681 |
| 8 | Netherlands | -1.319 |
| 9 | Australia | -1.235 |
| 10 | Denmark | -1.156 |
| 11 | Czechia | -0.916 |
| 12 | Germany | 0.331 |
| 13 | Canada | 0.630 |
| 14 | Austria | 1.363 |
| 15 | Finland | 1.403 |
| 16 | Sweden | 1.682 |
| 17 | United Kingdom | 1.726 |
| 18 | United States | 2.966 |
| 19 | France | 4.726 |
| 20 | India | 9.809 |

**Ranking change:** adding India changes the standardisation set and therefore the absolute energy values; the old 19-destination scores must not be compared numerically with the new 20-destination scores. Relative order changes are recorded in `outputs/ranking_comparison_19_to_20_2026-10-16.csv`. No country was reranked because of today's policy headlines; the only ranking change is the deliberate destination-set expansion and consistent rescoring.

## 5. Model status and chronological backtest

- **EOM status:** uncalibrated equal-weight baseline. The weights are not estimated from migration outcomes.
- **Backtest:** expanding-origin chronological evaluation, features from year *t* predicting national net migration per 1,000 residents in year *t+1*. No random split.
- **Evaluation sample:** **4,174** country-year predictions across **177** geographies and **24** eligible target years (1999, 2001, 2003–2024, with gaps where data are unavailable). Training rows per fold: 165–4,170.
- **Ridge comparator:** MAE **6.013**, RMSE **11.000**, R² **0.131**.
- **Country-mean baseline MAE:** **3.939**. **Persistence baseline MAE:** **2.408**.
- **Mean pooled rank association:** EOM attraction **0.402**, Ridge **0.445**, persistence **0.876**.
- Persistence strongly outperforms EOM on pooled rank association, and simple baselines outperform Ridge on MAE. Metrics are pooled and not cluster/block-adjusted; uncertainty intervals have not been estimated.
- **Forward prediction ledger:** zero new forecasts issued. Because EOM is uncalibrated and the current operationalization underperforms simple comparators, no point forecast or migration probability is published.
- **Causal estimates:** none. These predictive results do not establish a causal effect of policy or validate EOM theory.

## 6. Version/change log and next limitation

- **v2 change:** added India as the 20th global comparator; recalculated all 20 scores with the same six-feature equation; added policy records and 20-country coverage audit; re-ran tests and expanding-origin evaluation.
- **No theory or equation change** was made. The policy log is qualitative and did not trigger a numerical score adjustment.
- Next priorities: obtain a verified current vintage for price-level and governance series; add comparable household/housing cost and wages data; construct origin-destination-year migration panels; separate permanent, temporary, education, family and humanitarian flows; estimate parameters only when the outcome sample and identification support it; then test with rolling-origin and origin/destination-cluster-aware uncertainty.

**Research conclusion:** the pipeline ran on the existing processed panel and the 20-country ranking is reproducible from that panel. The empirical EOM model remains uncalibrated, is not causally validated, and should not be described as a validated migration forecast model.
