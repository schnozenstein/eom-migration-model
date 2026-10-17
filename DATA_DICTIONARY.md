# Data dictionary and collection rules

## Core identifiers
- `destination_id`: stable identifier in `data/destinations.csv`.
- `programme_id`: stable identifier for a specific programme and format; do not merge MBA, MSc Management of Technology and executive MBA outcomes without a model that explicitly accounts for the difference.
- `cohort_year`: year of entry or graduation, to be defined consistently in each dataset.

## Evidence categories
- `observed`: a published value from a traceable data source.
- `inferred`: a proxy, transformation, or model output; it must not be presented as a directly observed fact.
- `missing-not-published`: searched but not published at the needed level.
- `not-applicable`: measure does not apply to this destination/programme.
- `unknown`: collection not yet completed.

## Comparability rules
1. Record the year and exact definition (e.g. employed 3 months after graduation versus 6 months after graduation).
2. Record denominators and response rate for every graduate outcome.
3. Distinguish local-currency salary from PPP-adjusted salary, and record the price-year used.
4. Separate graduates who have work authorization from graduates who actually obtain sponsored employment.
5. Separate a job-search permit, a work permit, a renewable residence permit and permanent residence/citizenship.
6. Do not infer policy friendliness directly from regulatory quality; policy events need their own official source and direction coding.
7. Record programme-level and destination-level factors in separate tables; the school can dominate the destination average for MBA outcomes.
8. Store publication date, effective date and access date separately for policy changes.

## Primary target fields
- Macro benchmark target: `net_migration_per_1000`, derived from World Bank net migration divided by population. Its broad, national character is a deliberate limitation.
- Personal pathway targets: stage-specific outcomes with explicit numerators and denominators. The preferred long-horizon outcome is secure long-term status in the destination after 8-10 years, but public data may not expose it by nationality, programme and prior work experience.

## Data-quality grading
- `A`: official, directly measured, well-defined denominator and recent cohort.
- `B`: official but broad/indirect or subgroup not exactly matched.
- `C`: reputable secondary/industry source with defined method.
- `D`: inferred/proxy or weak comparability; use only in sensitivity analysis.
- `X`: exclude from quantitative fit; keep as narrative context only.
