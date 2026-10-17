# EOM 2.0 — Live data pipeline implementation report

**Patch:** v9 live-data pipeline, 17 October 2026  
**Base:** EOM 2.0 v8 project bundle  
**Status:** Pipeline code implemented and offline-tested; daily scheduling is prepared but not deployed; this run did not retrieve new live numeric observations.

## Implemented

1. Added `scripts/refresh_eom_data.py`, an incremental World Bank Indicators API ETL for 16 selected macro, labour-market, demographic and migration indicators. The requested end year defaults to the current UTC year (2026 at implementation), not a fixed 2025.
2. Added HTTP retry/backoff, bounded request timeouts, source-level status rows, per-run JSON snapshots, retrieval-vintage history, and a canonical observation table that retains prior rows if a source fails.
3. Added `outputs/data_freshness_dashboard.csv` with latest observed year, country coverage, observed-row counts, retrieval timestamp where known, and freshness labels.
4. Added an official immigration/work-permit landing-page watcher. It stores HTML snapshots and content hashes. A changed page is only a review alert; this does not automatically extract a structured policy rule.
5. Added `.github/workflows/eom-daily-refresh.yml`, scheduled daily at 05:17 UTC with manual dispatch, and a run summary in `metadata/refresh_runs/`.
6. Added `--offline-audit` so cached evidence can be audited without pretending a live request succeeded. The legacy World Bank fetcher's default end year now also follows the current UTC year.
7. Added three focused ETL tests. The complete existing test suite plus the new tests passes: **11 passed**.

## What the existing cached data says

The pre-existing World Bank panel already contains newer data than the ranking table suggests. The offline freshness audit found:

- **11 of 16** tracked indicators have a latest observed year of 2025.
- Life expectancy has a latest observed year of 2024.
- Four indicators—government effectiveness, regulatory quality, political stability, and the PPP price-level ratio—have a latest observed year of 2023.
- The current cached panel has 175,361 rows. The dashboard is about indicator-level freshness, not a new migration-attractiveness ranking.

This explains an important distinction: the 2023 ranking is the latest *comparable ranking produced by the old scoring path*; it does not mean every source observation is from 2023. The current pipeline intentionally does not blend unmatched years into a new score without a defined recency and missingness policy.

## Execution and network limitation

I attempted a live refresh in this execution environment, but the run did not complete within 120 seconds. Earlier run metadata in the v8 bundle also records DNS-resolution failures for direct World Bank and Eurostat API calls. I therefore ran `python scripts/refresh_eom_data.py --offline-audit` to validate the freshness-report path against cached data. This produced **zero new numeric rows by design** and marked all World Bank connectors `SKIPPED_OFFLINE`; it must not be interpreted as a successful live data download.

## Tests

- `python -m py_compile scripts/refresh_eom_data.py src/eom_empirical/fetch_world_bank.py` — passed.
- `python -m unittest discover -s tests -p 'test_refresh_etl.py' -v` — 3 passed.
- `PYTHONPATH=src python -m pytest -q` — **11 passed**.
- Offline audit executed and generated the freshness dashboard and run manifest.

## What is not yet complete

- The daily GitHub Actions workflow is **not active** just because it is included in this ZIP. It must be pushed to a GitHub repository with Actions enabled and appropriate write permission. No connected EOM repository was found to deploy it into.
- Eurostat and OECD numeric ingestion is not yet wired into the new ETL; their dataset-specific dimensions and data schemas need separate validated connectors. Existing extracts retain their own vintage labels.
- The policy watcher detects page-content changes, not policy meaning or legal status. Human review or a validated text-extraction pipeline is required.
- The model ranking is not automatically recomputed. Before producing a current-conditions ranking, EOM needs an explicit recency/uncertainty rule and coverage gate. No new ranking, forecast, calibration, or causal estimate was produced in this patch.

## Deployment

1. Unzip this bundle into a repository.
2. Push the project, including `.github/workflows/eom-daily-refresh.yml`, to GitHub.
3. Enable Actions and permit the workflow to write to the target branch (branch protection may require a pull-request workflow instead).
4. Run the workflow manually once and inspect `metadata/live_source_status.csv`, `outputs/data_freshness_dashboard.csv`, and `metadata/refresh_runs/` before relying on the scheduled run.
5. If repository size grows too quickly, move raw snapshots to an artifact/object store and retain manifests/checksums in Git rather than committing every response body.
