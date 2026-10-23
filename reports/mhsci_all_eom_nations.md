# MHSCI — Full EOM Destination Coverage (v0.2)

**Reviewed:** 23 October 2026  
**Coverage:** all 46 destinations registered in EOM's latest daily report: 42 macro-ranked destinations plus Edinburgh, Taiwan, United Arab Emirates and Argentina.

## What this release provides

This release adds a common public-attitude baseline for every EOM destination where the Ipsos Populism Report 2025 has a comparable observation. Its item asks whether the country "would be stronger if we stopped immigration". The survey covered 23,228 adults aged 16–74 in 31 markets between 21 February and 7 March 2025. Higher percentages indicate more agreement with stopping immigration, not necessarily hostility toward Indian people.

The full country-specific MHSCI composite is **not** available for every destination yet. Composite scores require at least three separately evidenced dimensions: public sentiment, anti-Indian/South Asian hostility, policy friction, and political rhetoric. Missing data remain missing; no country receives a zero-risk score because data are absent.

## Comparable public-sentiment observations

Among EOM destinations with an Ipsos 2025 observation, highest percentages agreeing immigration stoppage would make the country stronger include Türkiye (78%), Thailand (71%), Chile (65%), India (60%), Malaysia (57%), South Africa (55%), Colombia (52%), Indonesia (51%), and several countries in the 45–49% range. Lowest include New Zealand (20%), Brazil (24%), Singapore (27%), Japan (28%), the United States (33%), Canada (34%) and Spain (34%). These are general immigration attitudes, not direct measures of anti-Indian sentiment.

Source: [Ipsos Populism Report 2025](https://www.ipsos.com/sites/default/files/ct/news/documents/2025-06/ipsos-populism-report-2025.pdf).

## Full destination coverage register

See [mhsci_eom_nation_coverage.csv](../data/mhsci_eom_nation_coverage.csv) for all 46 rows, EOM's latest macro rank where available, Ipsos percentage, other available hostility/policy evidence, missing-data status, and source links.

| Coverage group | Count | Meaning |
|---|---:|---|
| Registered EOM destinations | 46 | Full destination universe represented |
| Ipsos comparable national survey observation | 31-market survey, overlapping EOM destinations | Broad public sentiment is available for most but not all EOM countries |
| Full composite score retained from pilot v0.1 | 5 | Canada, UK, US, Australia, New Zealand; directional only |
| Other destinations with at least one evidence point | Several | Partial evidence only; no full composite |
| Composite-ready destinations in this release | 5 provisional | The rest remain unscored pending comparable evidence |

## Existing provisional composite (not statistically validated)

| Rank | Destination | Pilot score / 100 |
|---:|---|---:|
| 1 | Canada | 93.8 |
| 2 | United Kingdom | 87.5 |
| 3 | United States | 81.2 |
| 4 | Australia | 62.5 |
| 5 | New Zealand | 43.8 |

These five pilot scores use manually coded ordinal evidence and are not directly interchangeable with the Ipsos percentages above. They are retained to preserve the initial pilot; the public-opinion data is shown separately rather than silently retrofitted into the old composite. The scores are not yet validated cross-national estimates.

## Interpretation and safeguards

- Public concern about immigration levels is not the same as anti-Indian sentiment.
- Hate-crime counts, survey-reported hate experiences and public opinion use different definitions and denominators.
- A policy that restricts a visa pathway is not itself evidence that the population is hostile.
- Edinburgh uses a UK-level survey proxy and must not be interpreted as city-specific.
- India appears in the macro universe, but its own public sentiment is not a host-country risk score for Indian migrants abroad.
- No composite ranking should be published for a country with fewer than three measured dimensions.
- Do not blend MHSCI into EOM's primary macro score until cross-country comparability, weight sensitivity and out-of-sample validity are assessed.

## Next data-collection priorities

1. Collect comparable India/South Asian discrimination and hate-incident evidence for all 46 destinations.
2. Add policy-pathway evidence by migrant type (student, researcher, skilled worker, family), separately from public attitudes.
3. Include survey year, population, sample size, uncertainty intervals and source coverage in machine-readable fields.
4. Add time series so changes in attitudes and policy can be distinguished from stable institutional rules.
5. Recompute composite scores only after evidence coverage and sensitivity checks support it.
