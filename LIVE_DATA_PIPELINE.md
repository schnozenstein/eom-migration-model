# EOM live data refresh (v9 pipeline patch)

## What this adds

- A daily, retrying World Bank Indicators API pull across 16 selected macro/labour/demographic indicators, with the requested end year defaulting to the current UTC year instead of being hard-coded to 2025.
- Immutable run-level JSON response snapshots and a retrieval-vintage history table.
- A canonical observation table that updates successful keys while retaining old rows when a source fails.
- Per-indicator freshness and country-coverage dashboard, per-source status logs, and per-run machine-readable summaries.
- Best-effort page-change monitoring of official immigration/work-permit landing pages. A content-hash change is a review signal, **not** an automatically interpreted policy change.
- GitHub Actions daily workflow (05:17 UTC) plus manual dispatch. Once committed to a GitHub repository with Actions enabled and write permission, it commits snapshots and reports to the repo.
- Offline unit tests for history deduplication, missingness and freshness labels.

## Run locally

```bash
python -m pip install pandas requests
python scripts/refresh_eom_data.py
```

Optional: `python scripts/refresh_eom_data.py --start-year 2015 --end-year 2026 --skip-policy-watch`.

## Important limitations

1. This run refreshes source evidence; it does **not** automatically recalibrate the EOM model, publish a ranking, issue a forecast or claim causal effects.
2. World Bank indicators have different publication lags. The dashboard reports the latest observed year per indicator and must not imply all data are current-year.
3. Eurostat/OECD migration flows are not yet wired into the numeric refresh here. Their API schemas and dimension selections require dataset-specific validation; existing harmonized extracts remain explicitly vintage-dated. The policy-page watcher does not parse policy text into structured rules.
4. The GitHub Actions schedule is a deployable workflow, not an active schedule in this ZIP. It only runs after the project is pushed to a repository and Actions are enabled. If the execution environment blocks DNS/network access, the workflow will log failures and preserve prior data.
5. The workflow is configured to commit refreshed data back to the repository. Review repository size/retention settings before running indefinitely because raw snapshots can accumulate.
6. A full current-conditions ranking should only be produced after the pipeline reports adequate feature coverage and the ranking code uses actual latest observations with missingness/uncertainty penalties; this patch deliberately does not substitute stale values or invent data.
