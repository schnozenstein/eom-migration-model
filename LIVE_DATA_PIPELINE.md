# EOM live data refresh (v9 pipeline patch)

## What this adds

- A daily, retrying World Bank Indicators API pull across 38 selected macro/labour/demographic/education/health/digital/institutional indicators, including complementary PPP measures, with the requested end year defaulting to the current UTC year instead of being hard-coded to 2025.
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


## Dense global indicator expansion (2026-10-20)

The World Bank indicator pull now covers 38 selected indicators across:
- income and purchasing power parity (PPP);
- macroeconomic growth, inflation, trade, FDI, remittances and natural-resource rents;
- employment, unemployment, youth unemployment and sex-disaggregated labour-force participation;
- education participation and public education spending;
- internet access, population structure, urbanization and demographic change;
- life expectancy, sex-specific life expectancy, fertility, infant mortality, crude birth/death rates and health spending;
- institutional quality, political stability and government debt.

The new indicators expand the raw evidence layer only. They are not automatically included in the existing EOM score; each feature needs a documented transformation, a consistent reference year, a coverage check and a sensitivity test before model use. Indicator requests that the World Bank retires or does not expose are recorded as failures rather than silently replaced by a similarly named measure.

The Hong Kong and Switzerland policy-page monitors now use their official current press/latest-news paths. Spain's monitor uses the canonical English migration landing page. HTTP success is still a page-monitor signal, not proof that policy text was parsed or interpreted; content changes require review.

## Supplemental migration datasets (2026-10-20; PR #7)

The live refresh now attempts four additional numeric datasets alongside World Bank and Eurostat:

- UNHCR PopStatsOfficial: downloads the official CSV export, hashes the complete source response, streams it in chunks, and retains a compact extract for registered destinations plus selected high-volume origin countries. The extract retains source dimensions, labels, units/footnotes where supplied, reference period, retrieval timestamp, and run ID. Population types remain distinct; do not treat displacement/statelessness counts as voluntary labour or study migration.
- UN DESA International Migrant Stock 2024: downloads official destination, origin, and bilateral destination-origin workbooks. The normalized long table preserves total-sex, male, and female stocks for 1990, 1995, 2000, 2005, 2010, 2015, 2020, and 2024. A bilateral record represents stock from origin residing in destination at the reference year, not an annual flow. Missing bilateral pairs are not interpolated.
- OECD International Migration Database (SDMX): attempts a bounded official annual query for focus geographies and preserves source dimension codes and labels. The selected B11 measure code is not given a model meaning until its data structure and definition are reviewed.
- Expanded Eurostat total flows: migr_emi2 and migr_imm8 now query all reporting geographies under selected total annual dimensions, rather than Spain alone. The extract includes reporting regions/aggregates as well as national geographies, so only comparable national rows should be used in country panels.

Compact outputs are data/raw/unhcr_forced_displacement_focus.csv, data/raw/undesa_migrant_stock_long.csv, and data/raw/oecd_migration_database_focus.csv. Per-source status and retrieval diagnostics are written beneath metadata/. The official UN DESA workbooks are retained as run artifacts, not checked into Git. metadata/supplemental_source_catalog.csv records endpoint, output, measure, period and caveats.

A successful source-status row means retrieval and basic schema checks succeeded, not that its data are suitable for EOM scoring. Each source stays separate until definitions, units, geography, revision vintage, coverage, and predictor availability are reviewed. Source failures must not overwrite prior successful extracts. These connectors do not update EOM scores or forecasts.
