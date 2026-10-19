# EOM live data refresh (v9 pipeline patch)

## What this adds

- A daily, retrying World Bank Indicators API pull across 18 selected macro/labour/demographic indicators, including complementary PPP measures, with the requested end year defaulting to the current UTC year instead of being hard-coded to 2025.
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
3. Spain total immigration and emigration are now fetched from Eurostat's official Statistics API (`migr_imm8` and `migr_emi2`) into a normalized, vintage-stamped CSV and the compatible fields in the historical panel. These totals remain distinct from flows classified by citizenship, birth or previous residence. OECD numeric ingestion is still future work. The official Brazil OBMigra catalogue page is monitored for source changes and data-asset links; its PDF/spreadsheet tables are not yet numerically parsed.
4. The GitHub Actions schedule is a deployable workflow, not an active schedule in this ZIP. It only runs after the project is pushed to a repository and Actions are enabled. If the execution environment blocks DNS/network access, the workflow will log failures and preserve prior data.
5. The workflow is configured to commit refreshed data back to the repository. Review repository size/retention settings before running indefinitely because raw snapshots can accumulate.
6. A full current-conditions ranking should only be produced after the pipeline reports adequate feature coverage and the ranking code uses actual latest observations with missingness/uncertainty penalties; this patch deliberately does not substitute stale values or invent data.


## Spain Eurostat and Brazil expansion (2026-10-20)

- Added a small Eurostat Statistics API adapter for Spain's annual total immigration (`migr_imm8`) and emigration (`migr_emi2`) flows. API response snapshots are retained by run; the normalized table carries data values, flags, missingness, source URL, and retrieval timestamp.
- Refreshed Spanish emigration is merged into the existing matching panel field. Immigration is stored in its own generic total-flow field to avoid conflating it with the existing birth/citizenship/previous-residence-specific measures.
- Added Brazil to the destination registry and panel scaffold. The global World Bank pull is filtered into a compact, versioned `data/raw/brazil_world_bank_macro.csv` extract that the workflow can commit separately from the oversized all-country history. OBMigra's official statistics page is monitored, but numeric parsing from its reports remains an explicit follow-up task.
- The refresh still never recalibrates or ranks automatically.

## Country and PPP expansion (2026-10-19)

- Spain (ESP) is now in `data/destinations.csv` and the maintained historical panel scaffold. Its numeric migration/QoL evidence remains explicitly missing until ingested; blanks are not zeros. Austria (AUT) was already in the destination set and is now monitored through the official Austrian Federal Government migration portal.
- The PPP block includes GDP per capita at constant 2021 PPP, current PPP GDP, GDP PPP conversion factor and household/private-consumption PPP conversion factor. The legacy `PA.NUS.PPPC.RF` series is not polled because the live API returned an indicator-not-found/archived response; prior historical observations are not deleted. These measures remain separately named.
