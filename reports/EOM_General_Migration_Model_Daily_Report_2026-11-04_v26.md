# EOM General Migration Model — Daily Data ETL & Research Report

**Run date:** 2026-11-04  
**Workflow:** [EOM Daily Refresh #169](https://github.com/schnozenstein/eom-migration-model/actions/runs/41781127844)  
**Status:** completed successfully; required tests, ETL, policy delta, source audit, prediction/outcome ledger, macro ranking recomputation, ranking delta, risk/geographic stages, report, artifact upload, and repository commit all succeeded  
**Trigger:** push/manual workaround because no distinct Nov 4 scheduled run was visible  
**ETL run ID:** `2026-11-04T054549Z`  
**Code version at run start:** `f2f86f28cd3eff806a7acac860854fa564d6a6aa`  
**Output commit:** `3ca3fb4470747190de6eac4bbe16d4c360644ae2`

## Numeric ETL
- World Bank WDI: 39/39 indicator requests succeeded; 165,984 fetched and normalized; 0 new natural keys; 0 value revisions; 165,984 unchanged rows skipped; 0 duplicate keys. Vintage 2026-10-08; observed years 2010–2025.
- Primary numeric endpoints: 1,095,164 source records fetched; 652,213 normalized primary rows retained. These are source records, not unique migrants.
- Eurostat: 2 total-flow series succeeded; 1,034 annual cells across up to 44 reporting geographies.
- UNHCR: 670,526 fetched; 242,461 focus/origin rows retained.
- UN DESA: 3/3 2024 migrant-stock files succeeded; 235,632 normalized rows.
- OECD: 290 focus-country records retained.
- ILOSTAT: 3 indicators succeeded; 6,469 focus rows retained.
- Brazil: 624 WDI rows fetched as a derived subset; OBMigra official page monitored but not numerically parsed.
- WDI panel: 165,984 rows, 39 indicators, 266 geographies (261 ISO3); 27,778 missing cells (16.7353%); 0 duplicate WDI natural keys.
- Source audit: 64 records; 62 successful, 1 failed/unknown, 1 derived. Validation: PASS_WITH_WARNINGS.

## Ranking and model status
- Macro ranking recomputed for 2025: 45 destinations compared; 42 scored; 3 unscored (Taiwan, UAE, Argentina); 0 score changes and 0 rank changes. Pakistan and Bangladesh remain excluded.
- Top 10: Singapore, Japan, Norway, Hong Kong, New Zealand, Ireland, South Korea, Australia, Denmark, Netherlands.
- Expanding-origin backtest: 14 origins, 2012–2025, 613 observations, 44 destinations. Ridge MAE 4.022; country-mean MAE 2.804; persistence MAE 2.363. EOM rank Spearman 0.515 vs persistence 0.806.
- Model remains uncalibrated; no production forecast, parameter fitting, or causal estimate issued. Persistence still outperforms the current operationalization.

## Manual policy and operational review
1. **UK Earned Settlement announcement (2 Nov):** announced/set out before Parliament; implementation date not confirmed. Proposed default 10-year settlement, 3-year high-earner route, 5-year route for earnings >£50,271 and some public-service workers, care-worker exception, and non-negotiable conditions. Logged as settlement-access/policy uncertainty, not implemented law.
2. **Canada asylum regulations (effective 3 Nov):** single online application process, review timelines, reinstatement rules, vulnerable-claimant support, and work-permit access for eligible claims. This is asylum-system administration, not a skilled-worker pathway. IRCC's reported 52%/68% claim declines are descriptive, not causal estimates.
3. **Ireland employment-permit processing frontiers (as of 3 Nov):** Critical Skills 23 Oct; new General Employment 25 Sep; other new 21 Sep; ICT new 1 Nov; ICT renewal 25 Aug; other renewals 25 Aug; reviews/appeals 29 Apr. These are receipt-date frontiers, not processing durations.

## Schedule and limitations
- Configured cron: `17 5 * * *` UTC. No distinct Nov 4 schedule-triggered run was visible. The dated audit-note commit triggered a full push run; this is not a schedule repair.
- Polish MOS work-permit endpoint failed TLS certificate verification; TLS verification was not disabled. Official gov.pl MOS guidance succeeded.
- Supplemental per-row revision tracking remains incomplete. Bilateral flows remain incomplete; country-year outcomes are a documented fallback.
- No causal effect was estimated; no score change was forced.
