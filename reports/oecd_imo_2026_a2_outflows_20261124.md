# EOM General Migration Model — 24 November 2026 (partial research capture)

**Status:** `PARTIAL_RESEARCH_CAPTURE_ONLY_FULL_DAILY_WORKFLOW_UNVERIFIED`

## Executive result

The full daily GitHub Actions ETL for 24 November is **not verified**. The latest verified complete daily run remains #244 (`45077878869`), which completed successfully with the no-material-change gate. A manual trigger commit was created at `2a72d83ad42973e0753cc502fec05b6681a2029a`, and a rerun request was accepted by the GitHub action surface, but no new workflow job, artifact, or automated output commit was visible at the audit cutoff. Therefore this report does not claim a full daily ETL run or a full-pipeline no-op.

A useful manual numeric capture was completed from the official OECD International Migration Outlook 2026 statistical annex: **Table A.2, foreign-population outflows**. It was not present in the prior A-series ingestion manifest.

## 1. New numeric data capture

- Publisher: OECD
- Release date: 12 November 2026
- Source: https://www.oecd.org/en/publications/international-migration-outlook-2026_a9eab36b-en/full-report/statistical-annex_f79de055.html
- Table: A.2 — Outflows of foreign population from selected OECD countries
- Observation period: 2014–2024
- Coverage: 29 destinations
- Unit: thousands of persons
- Rows: 319 destination-year keys; 312 numeric; 7 missing
- Duplicate natural keys: 0
- Invalid numeric values: 0
- Numeric range: 0.0–1,083.8 thousand
- Natural key: table code + destination ISO3 + year
- Origin dimension: not reported; this is **not** a bilateral OD flow.

The wide source-table capture, normalized long panel and country-definition notes are stored separately. The OECD HTML page was inspected through its official rendered text, but raw HTML bytes could not be downloaded in this run; the manifest explicitly records that limitation.

### Comparability cautions

Definitions vary materially by country. Examples:
- Ireland's A.2 reference year is May–April.
- Latvia has a methodological break in the 2023–2024 population-estimation series; 2022 was not recalculated.
- The Netherlands includes net administrative corrections for unreported emigration of foreigners.
- Switzerland includes administrative corrections, including some expired permits.
- The UK series ends in 2019 in this table.
- New Zealand uses a 12/16-month migration rule and the figures can be revised after 16 months.

These data are therefore kept as a separate exploratory destination-year outflow panel. They are not merged with bilateral flows or treated as a harmonized voluntary-migration predictor without further definition work.

## 2. Data-to-ranking gate

**Disposition:** exploratory outflow evidence only.

A.2 does not map to the six existing primary macro score components (GDP per capita PPP, private-consumption price level, unemployment, Regulatory Quality, Government Effectiveness and Political Stability). It therefore does not alter the primary scoring input and does not, by itself, justify macro reranking or OECD-enhanced ranking recalculation.

The full current-day WDI scoring-input retrieval was not verified, so the overall 24 November recomputation gate remains `NOT_EVALUATED_FULL_WORKFLOW_UNVERIFIED`, not `SKIPPED_NO_MATERIAL_CHANGE`.

Last validated primary ranking: run `44955413214`; original timestamp `2026-11-21T22:14:28.784546Z`; data cutoff 2025; 42 of 45 destinations scored. No new score/rank delta is claimed.

## 3. Policy research delta

The Australian Department of Home Affairs' official SkillSelect decision-tree PDF states that the existing portal is unavailable from 24–27 November 2026, with the new portal launching on 28 November. Submitted EOIs can be imported; unsubmitted drafts cannot be imported and must be restarted. The source does not state a change to visa eligibility, points or occupation rules.

This is recorded as a temporary administrative-system transition for people preparing or managing a SkillSelect EOI, not as a change to migration eligibility and not as a realized migration outcome.

Official source: https://immi.homeaffairs.gov.au/work-in-australia/Documents1/skillselect-decision-tree.pdf

## 4. Other source freshness

- World Bank WDI: latest release note located in this review is 11 November 2026. It describes updates to 2025 external-debt data, FDI, remittances and other indicators. The last verified full WDI refresh was 22 November; this partial run did not re-pull the WDI numeric API.
- OECD International Migration Outlook 2026: 12 November release; A-series A.1/A.3/A.4/A.5/A.6 were captured in the 23 November OECD annex ingestion, while A.2 was absent and is now separately captured.
- World Bank and Eurostat live numeric API endpoints could not be retrieved through the current web retrieval surface; no new WDI or Eurostat numeric rows are claimed for 24 November.

## 5. Model, ranking and causality

- No model fitting or backtesting performed.
- No production forecasts issued.
- No causal estimates produced.
- No primary or OECD-enhanced ranking recalculated.
- EOM remains uncalibrated.
- The A.2 dataset is not a bilateral flow panel and is not yet suitable for PPML fitting.

## 6. Workflow and persistence

- Latest verified daily workflow: [run #244](https://github.com/schnozenstein/eom-migration-model/actions/runs/45077878869).
- Manual trigger/audit commit: [2a72d83](https://github.com/schnozenstein/eom-migration-model/commit/2a72d83ad42973e0753cc502fec05b6681a2029a).
- Latest complete Library archive observed: `/EOM_Daily_Runs/2026-11-15_v37`.
- The 23 November v42 Library folder was verified empty after six storage-limit failures. No prior Library artifacts were deleted or overwritten.
- This v43 partial package is available in the current conversation; the full daily workflow remains unverified.

## 7. Files in this package

- OECD A.2 wide source-table capture
- OECD A.2 normalized destination-year panel
- Country-specific definition/comparability notes
- Source retrieval audit addendum
- Policy-event delta addendum
- Dataset-to-ranking eligibility matrix
- Run manifest and recomputation-gate record


## Current automation and Library status

The scheduled ChatGPT automation `EOM Daily Data ETL & Ranking` is marked `in_progress` for run `28cbc715-0580-8328-996c-c5afd1663b2f`, scheduled for `2026-11-24T02:30:00Z` and started at `2026-11-24T02:45:13.834560Z`. No completion timestamp is available yet; the latest completed result still refers to the previous day. No duplicate immediate run was started.

The Library folder `/EOM_Daily_Runs/2026-11-24_v43_partial` was created, but the compact ZIP and standalone report uploads both failed with `library_storage_limit_exceeded`. No earlier artifacts were deleted or overwritten. The current partial package remains available in the conversation; the dataset and audit files are committed in this repository.
