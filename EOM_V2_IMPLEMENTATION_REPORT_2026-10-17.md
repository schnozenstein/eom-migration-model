# EOM 2.0 implementation and run report

**Run date:** 2026-10-17  
**Model version:** `EOM-general-v2-architecture-2026-10-17`  
**Status:** Code changes implemented; empirical run completed with explicit data gates.  
**Fresh numeric ingestion:** Not completed. The prior v7 retrieval attempts to the World Bank and Eurostat APIs failed due to DNS/network resolution; this run does not claim fresh external observations.

## Changes implemented

1. **Separated the model's outputs.** Legacy macro attraction score is retained. Joie de vivre and migration feasibility are separate subsystems and are not silently folded into the old ranking.
2. **Added a joie-de-vivre feature model.** The score accepts six separately measured dimensions: life evaluation (25%), work-life balance (20%), social connection (15%), autonomy (15%), leisure/cultural access (15%) and everyday environment (10%). These are initial design weights only, not fitted parameters. The module refuses to score a destination unless every required dimension is observed.
3. **Added feasibility data structure.** The India-origin template records visa route, eligibility, minimum salary/funds, fees, language requirements, permanent-residence timeline, dependent rights, work rights, source, effective date and verification date. It does not fabricate a feasibility score without a specified profile and verified route evidence.
4. **Added weight sensitivity.** 2,000 deterministic-seed draws independently perturb the six legacy macro-component weights between 0.8 and 1.2, keeping signs fixed. This measures rank sensitivity to weight perturbation only; it is not a confidence interval.
5. **Added year-balanced chronological evaluation.** Per-year Spearman rank correlations and error metrics are saved separately, so years with more countries do not dominate the summary as they do in pooled metrics.
6. **Added reproducible tests and run status.** The new module writes its input templates, component scores, sensitivity results and machine-readable status.

## Run results

- Unit tests: **8 passed** (`PYTHONPATH=src python -m pytest -q`).
- Legacy macro ranking: recomputed from the existing observed panel; latest year with complete six-component focus coverage remains **2023**. It remains an exploratory macro-proxy ranking, not a personal migration recommendation or calibrated probability.
- Existing panel: 175,361 observed long-format rows, 16 indicators, 265 country/aggregate codes, spanning 1960–2025. No missing values were converted to zero and no new external numeric observations were added in this run.
- Historical expanding-origin evaluation: **4,174 predictions**, **177 geographies**, **24 eligible target years** (1999, 2001, 2003–2024 with data gaps).

### Evaluation results

| Metric | EOM attraction | Ridge | Country-mean baseline | Persistence baseline |
|---|---:|---:|---:|---:|
| Pooled MAE | Not applicable to ordinal score | 6.013 | 3.939 | 2.408 |
| Pooled rank association with next-year net migration | 0.402 | 0.445 | — | 0.876 |
| Mean yearly Spearman correlation | 0.403 | 0.448 | — | 0.870 |
| Mean yearly MAE | Not applicable to ordinal score | 6.004 | 3.932 | 2.399 |

The current macro operationalization underperforms persistence. This is a predictive evaluation of national net migration, not a causal estimate and not an individual-level migration outcome.

## Data gates and what remains unscored

- **Joie de vivre:** 0 of 20 destinations had all six required inputs. A blank template was created at `data/wellbeing_inputs_template.csv`; `outputs/eom_joie_de_vivre_scores.csv` correctly reports unscored rows.
- **Migration feasibility:** 0 destinations scored because no verified profile-specific eligibility, funds, language and route data were present. Template: `data/migration_feasibility_inputs_template.csv`.
- **Combined EOM 2.0 ranking:** intentionally not produced. Combining the new dimensions before comparable data exist would create false precision.
- **Fresh ETL:** blocked by network/DNS failure from the previous v7 run. The run preserves the source audit and does not label old values as new.

## New outputs

- `src/eom_empirical/eom_v2.py` — new scoring and gate logic.
- `tests/test_eom_v2.py` — tests for the new dimensions and weight schema.
- `data/wellbeing_inputs_template.csv` — required QoL data schema.
- `data/migration_feasibility_inputs_template.csv` — India-origin feasibility schema.
- `outputs/eom_joie_de_vivre_scores.csv` — currently unscored because inputs are missing.
- `outputs/eom_v2_weight_sensitivity.csv` — 2,000-draw rank sensitivity.
- `outputs/eom_v2_year_balanced_backtest.csv` — year-by-year and equally weighted evaluation.
- `outputs/eom_v2_run_status.json` — machine-readable run status and limitations.

## Source definitions to ingest next

- World Happiness Report, data sharing and Figure 2.1 data: https://www.worldhappiness.report/data-sharing/ — life evaluation, confidence intervals and explanatory factors. The data download was not successfully ingested into this run.
- OECD, hours worked: https://www.oecd.org/en/data/indicators/hours-worked.html — annual hours worked. OECD cautions that level comparisons are affected by source/method differences, so use for trend/context and document comparability.

## Conclusion

The code architecture has been upgraded and the existing model has been rerun. The implementation deliberately preserves the old ranking and exposes missing evidence rather than inventing scores. The next meaningful step is to ingest comparable wellbeing and work-time data, then verify visa feasibility for a clearly defined migrant profile before calculating a combined personal ranking.
