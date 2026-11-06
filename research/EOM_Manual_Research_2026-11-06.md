# EOM manual policy and release watch — 6 November 2026

Retrieval date: 2026-11-06 (UTC)
Purpose: preserve source-backed policy/release observations separately from numeric outcome data and macro scoring.

## Confirmed / pending policy observations

### New Zealand — graduate-to-work transition changes (announced 29 May 2026; effective 16 November 2026)
Official source: https://www.immigration.govt.nz/about-us/news-centre/new-and-updated-post-study-work-visa-options/
Publisher: Immigration New Zealand.
Affected cohorts:
- Eligible NZ graduates with NZQCF Level 5–7 qualifications who studied full-time in New Zealand for at least 24 weeks and are not otherwise eligible for a Post-Study Work Visa.
- Eligible Level 7 graduate-diploma holders who also hold a bachelor's degree and studied the graduate diploma full-time in New Zealand.
Mechanism:
- A new Short-Term Graduate Work Visa opens for applications on 2026-11-16, granting six months of open work rights to seek employment and potentially transition to an Accredited Employer Work Visa.
- Applicants need at least NZD 5,000; application must be made within three months of student-visa expiry; one grant only; no extension; cannot support a partner's work visa or dependent child's student visa; business ownership is not allowed.
- Post-Study Work Visa eligibility expands to specified Level 7 graduate-diploma holders with a bachelor's degree; maximum duration up to one year, tied to study duration.
Model treatment: record as a dated study-to-work access feature, segmented by qualification/cohort. Do not treat as a permanent-residence route or universal graduate entitlement. No macro score adjustment; no causal estimate.

### United Kingdom — earned settlement consultation outcome (updated 2026-11-02; implementation pending)
Official sources:
- https://www.gov.uk/government/consultations/earned-settlement
- https://www.gov.uk/government/news/home-secretary-unveils-new-rules-for-migrants-settling-in-the-uk
Publisher: Home Office.
Announcement/publication date: 2026-11-02.
Affected cohorts: migrants applying for indefinite leave to remain, with route-specific exemptions and transitional provisions.
Mechanism: announced framework proposes a 10-year default, faster 3-year route for the highest earners, 5-year route for some higher earners and public-service workers, and distinct arrangements for refugees and other cohorts. The government response says the next step is detailed rules and operational arrangements, with further technical guidance and an impact assessment before implementation.
Model treatment: announced/pending settlement-access uncertainty only. Do not code as in-force law. No macro score adjustment; no causal estimate.

### Canada — Express Entry labour-market integration changes (effective 2026-11-03; rechecked)
Official source: https://www.canada.ca/en/immigration-refugees-citizenship/news/2026/10/canada-refocusing-express-entry-on-top-talent-that-drives-economic-growth.html
Publisher: IRCC.
Affected cohorts: Express Entry candidates with eligible Canadian work experience or qualifying high-wage job offers.
Mechanism: labour-market integration factor adds CRS points for eligible Canadian work experience or qualifying high-wage job offers; LMIA no longer required for qualifying job offers used for specified Express Entry eligibility/points purposes. Job genuineness and program requirements remain.
Model treatment: access/selection-rule change by cohort; not a general increase in all applicants' eligibility. No causal estimate.

## Official data-release watch

### UNHCR Refugee Data Finder
Official source: https://refugeedata.unhcr.org/en/data-finder/
Publisher: UNHCR.
Page last updated: 2026-11-05.
Coverage displayed: official population statistics from December 1952 to December 2025, 192 countries.
Treatment: freshness metadata confirms a new/updated release surface; this page view itself is not a numeric ingestion. Numeric extraction remains dependent on the PopStatsOfficial API export and its captured raw snapshot.

### OECD International Migration Outlook 2026
Official source: https://www.oecd.org/en/about/news/media-advisories/2026/11/oecd-international-migration-outlook-2026-to-be-published-thursday-12-november.html
Publisher: OECD.
Advisory published: 2026-11-05.
Scheduled release: 2026-11-12 at 13:30 CET.
Expected coverage: recent migration trends, immigrant labour-market outcomes, migration/integration policy, labour migration and long-term-care workforce shortages, and migration/productivity links; country notes and statistical annex.
Treatment: future release watch only. Do not count as data ingested before publication. On release, separately capture report, annex, definitions, reference periods, and any revised historical series.

### Eurostat Demography 2026
Official source: https://ec.europa.eu/eurostat/fr/web/interactive-publications/demography-2026
Publisher: Eurostat.
Current published reference periods include 2024 migration flows and 1 January 2025 population stocks. The publication reports nearly 6 million EU immigrants and 3.1 million emigrants in 2024; these are annual flows and must remain distinct from population stocks and from bilateral-only records.
Treatment: release/context audit only; do not infer that the interactive publication itself adds new rows to the daily numeric ETL without parsing its underlying dataset/API.

## Causal and scoring safeguards
- No causal effects estimated.
- No ranking or energy changes justified by these policy/release observations alone.
- Policy announcements, effective rules, operational backlog indicators, and source-release metadata remain separate data classes.
