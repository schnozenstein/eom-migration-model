# EOM General Migration Model — Daily ETL & Research Report

**Run date:** 2026-10-17
**Run timestamp:** 2026-10-17T09:48:30+05:30 (IST) / 2026-10-17T04:18:30+00:00 (UTC)
**Package:** v7; model equation/version unchanged (`EOM-general-equalweight-unfitted-2026-10-16-v2`)
**Run status:** source audit and policy-log update completed; fresh numeric ETL blocked by network DNS failures.

## 1. Audit of prior state

The prior v6 package was present and inspected. It contains a 756-row destination-year scaffold (21 destinations, 1990–2025), a processed World Bank long panel of 175,361 observed rows (16 indicators, 265 country/aggregate codes, years 1960–2025), a 24-row policy evidence log, and 4,174 historical expanding-origin backtest predictions. The forward prediction ledger had 0 rows and causal estimates were 0. The package is a versioned artifact, not proof of a durable database or a continuously running service.

## 2. New evidence and source checks

### Policy records added

1. **Canada — IRCC announcement, 16 October 2026; scheduled effective date 3 November 2026.** Express Entry CRS changes will award points for eligible Canadian work experience or a qualifying job offer in a high-wage occupation; the two routes are not combined. LMIA requirements change for qualifying job-offer points and specified program eligibility uses. A high-wage occupation is defined as at least 1.3 times the overall workforce median wage. Affected cohort is limited to eligible Express Entry candidates. This is announced future policy on the run date, not yet effective. No causal effect or numeric energy adjustment assigned. Source: https://www.canada.ca/en/immigration-refugees-citizenship/news/2026/10/canada-refocusing-express-entry-on-top-talent-that-drives-economic-growth.html

2. **United Kingdom — Home Office Immigration and Asylum Bill factsheet, published 8 October 2026.** The factsheet describes proposed reforms affecting humanitarian protection, appeals, Article 8, modern slavery and asylum support. It is recorded as bill/proposal status, not treated as fully enacted or commenced policy. No numeric energy adjustment assigned. Source: https://www.gov.uk/government/publications/immigration-and-asylum-bill-2026-factsheets/immigration-and-asylum-bill-overarching-factsheet

### Numeric data-source retrieval

| Source | Attempt/result | Rows fetched | ETL result |
|---|---|---:|---|
| World Bank API, `SM.POP.NETM` | Direct urllib request failed with DNS `Temporary failure in name resolution`; browser open of endpoint inaccessible | 0 | No append/update |
| Eurostat API, `migr_imm1ctz` | Direct urllib request failed with DNS resolution error; browser open of endpoint inaccessible | 0 | No append/update |
| Eurostat dataset metadata | Official data-browser metadata checked; immigration-by-citizenship dataset coverage 1998–2024, last data update shown as 29 May 2026 | 0 numeric rows | Metadata only |
| OECD migration databases | Official landing page checked; identifies flows/stocks, naturalisation, labour-market and integration datasets | 0 numeric rows | Metadata only |

Exact endpoints, retrieval timestamps, definitions, units, geography, cohorts, release/vintage status and failure notes are recorded in `metadata/source_retrieval_audit_2026-10-17.csv`. Metadata access is not counted as numeric ingestion.

## 3. Actual files and row changes

- `data/policy_evidence_log.csv`: **24 → 26 records**; 2 new policy records added after natural-key deduplication.
- `data/policy_events_added_2026-10-17.csv`: 2 records.
- `metadata/source_retrieval_audit_2026-10-17.csv`: 5 source-attempt records.
- `metadata/run_manifest_2026-10-17.json`: new dated run manifest with row counts, network failures, checksums and test result. The 2026-10-16 manifest and original v6 ZIP remain unchanged.
- Numeric panel: **0 inserted, 0 updated, 0 rejected, 0 duplicates detected from new numeric pulls**, because no numeric pull succeeded. The existing panel was not mutated.
- Unit tests: `PYTHONPATH=src python -m pytest -q` → **6 passed**. Running pytest without `PYTHONPATH=src` fails collection due the project's src-layout import path; this is a test invocation issue, not a test assertion failure.

## 4. Coverage and missingness

The inherited World Bank panel remains 175,361 observed long-format rows, 16 indicators, 265 country/aggregate codes, 1960–2025. The inherited 756-row destination-year panel remains a sparse scaffold; migration-flow coverage is Europe-heavy and not a globally complete origin–destination–year panel. Four price/governance series in the prior manifest are retained from an older vintage with latest year 2023; their publication vintage was not independently verified. No missing values were imputed, and no new numeric coverage was added today.

## 5. EOM energy and ranking

**No ranking change is warranted.** No comparable numeric observations were retrieved, and qualitative policy records do not justify arbitrary numeric energy shifts. The previous 2023 20-destination ranking remains unchanged and is not rerun today. Lower energy continues to mean a stronger attractor under the paper's convention.

## 6. Model status and evaluation

- Status: **uncalibrated; historical backtest retained, not rerun in this daily run**.
- Existing expanding-origin backtest: 4,174 country-year predictions, 177 geographies, target years 1999 and 2001–2024 where eligible. Prior metrics remain in `outputs/macro_backtest.json`: Ridge MAE 6.013, country-mean MAE 3.939, persistence MAE 2.408; pooled rank association EOM 0.402, Ridge 0.445, persistence 0.876. These are prior-run metrics, not new evaluation today.
- No new forward forecast issued; forward ledger remains empty.
- No parameter fitting, model revision, causal estimate or policy counterfactual was run.

### Predictive versus causal conclusions

The previous backtest suggests this operationalization underperforms persistence on pooled rank association and simple baselines on MAE. This is predictive evidence about the current operationalization, not causal evidence and not a rejection of every possible EOM formulation. Today's policy observations are descriptive only; no causal impact is claimed.

## 7. Version log and next limitation

- v7 adds a source-retrieval audit and two policy records, corrects the README's inconsistent description of historical backtesting, and records SHA-256 hashes of the inherited panel files.
- EOM equation and weights are unchanged. No ranking was updated.
- Six unit tests passed using the correct source-layout import path.
- Main blocker: the execution environment could not resolve the World Bank or Eurostat hosts, and no durable external database/repository was available to append to. The v7 package is a new versioned artifact; it does not prove cross-run persistent storage outside the available file workspace.
- Next: restore a permitted network path or scheduled runner with DNS/API access and durable storage; then ingest a raw official snapshot, compare natural keys against prior data, record revisions, and append only verified new/revised observations. Prioritise origin–destination–year flows and comparable housing, wages and work-access data.
