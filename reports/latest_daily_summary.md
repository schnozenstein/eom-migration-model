# EOM Daily Research Report

> Generated: 2026-10-17 20:02 UTC

## 1. Executive summary

- **Latest refresh run:** `2026-10-17T200205Z`
- **Refresh timestamp:** 2026-10-17T20:02:05.758060+00:00
- **World Bank observations fetched:** 51072
- **World Bank indicator requests:** 12 succeeded; 4 failed
- **Policy pages:** 7 succeeded; 2 failed
- **Freshness dashboard:** 12 recent; 4 requiring attention out of 16 indicators
- **Ranking recomputed during refresh:** No
- **Forecast issued during refresh:** No

A successful data refresh is not evidence that a ranking or forecast was recalculated.

## 2. Stored macro ranking

This is the latest stored macro-proxy ranking, not a personalised migration recommendation. It does not include complete joie de vivre or individual visa-feasibility scoring.

| Rank | Destination | Year | Macro score |
|---:|---|---:|---:|
| 1.0 | Singapore | 2023 | -8.481 |
| 2.0 | Ireland | 2023 | -2.183 |
| 3.0 | Norway | 2023 | -2.158 |
| 4.0 | Japan | 2023 | -2.023 |
| 5.0 | Switzerland | 2023 | -1.801 |
| 6.0 | New Zealand | 2023 | -1.685 |
| 7.0 | Hong Kong | 2023 | -1.681 |
| 8.0 | Netherlands | 2023 | -1.319 |
| 9.0 | Australia | 2023 | -1.235 |
| 10.0 | Denmark | 2023 | -1.156 |

## 3. Historical model evaluation

- **Evaluation status:** completed_expanding_origin_backtest
- **Target:** next-year national net migration per 1,000 residents
- **Evaluation method:** expanding-origin; each test year is predicted using only earlier target years; no random split
- **Test observations:** 4174
- **Destinations:** 177
- **Rolling test origins:** 24

| Metric | EOM / Ridge | Persistence baseline | Country-mean baseline |
|---|---:|---:|---:|
| Mean absolute error (MAE; lower is better) | Ridge: 6.013 | 2.408 | 3.939 |
| Rank correlation (higher is better) | EOM: 0.402; Ridge: 0.445 | 0.876 | Not reported |

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

- **Destinations in QoL input file:** 20
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
| GE.EST | 2023 | STALE_OR_SLOW_RELEASE |
| PA.NUS.PPPC.RF | 2023 | STALE_OR_SLOW_RELEASE |
| PV.EST | 2023 | STALE_OR_SLOW_RELEASE |
| RQ.EST | 2023 | STALE_OR_SLOW_RELEASE |

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
