# Migrant Hostility & Social Climate Index (MHSCI) — v0.1

**Status:** pilot / evidence-led, manually coded release. Reviewed 23 October 2026.

## Purpose

MHSCI adds a social-climate and migrant-hostility lens to the EOM destination framework for Indian students, researchers and skilled migrants. It is deliberately separate from the macroeconomic ranking and should not be read as a rating of a country's population or culture.

## Four components

Each component is coded on an ordinal scale from 0 (lowest adverse signal) to 4 (highest adverse signal); higher values indicate greater estimated risk.

1. **Public sentiment** — survey evidence on immigration attitudes, favorability toward immigrants and the context around immigration concerns.
2. **Group hostility** — direct evidence of anti-Indian/South Asian discrimination or incidents; broader AAPI/Asian evidence can be used only as a labelled proxy.
3. **Policy friction** — visa, student, graduate-work, dependent, skilled-work and settlement rules that increase the risk of a migrant's planned pathway failing or becoming harder.
4. **Political rhetoric** — credible evidence that anti-immigrant rhetoric or politicization may worsen the climate. This should not be inferred solely from a policy tightening.

The v0.1 scores are expert-coded evidence levels, not raw percentages, causal estimates or statistically validated scales. They should not be mistaken for measurements with interval-scale precision.

## Composite and coverage rules

The pilot composite is the simple average of the available component scores multiplied by 25 to create a 0–100 risk score. It is calculated only if at least three of the four components have a coded value. A high score indicates higher evidence-coded risk, not a prediction that an individual migrant will experience hostility. Score bands: 0–24 lower signal, 25–49 moderate signal, 50–74 elevated signal, 75–100 high signal.

- Missing values remain missing; they are never replaced by zero.
- A country's rank is not published when fewer than three dimensions have data.
- The evidence confidence field describes the quality and comparability of the current evidence, separately from risk score.
- Every row should retain source URLs, survey/report year, population/sample, definition and limits. Changes in reporting or identification can change hate-crime counts as well as underlying prevalence.

## Initial rank, v0.1

The initial ranking is restricted to five destinations for which at least three dimensions have been coded. The values are a **provisional directional comparison**, not a defensible cross-national statistical league table: inputs use different survey questions, populations and incident-counting systems. The score should not yet be blended into the EOM macro rank.

| Rank | Destination | Pilot score | Band | Confidence | Read this as |
|---:|---|---:|---|---|---|
| 1 | Canada | 93.8 | High | Medium | Public concern, rising South Asian hate-crime counts and immigration-policy tightening all register strongly. |
| 2 | United Kingdom | 87.5 | High | Medium | High public concern and politicization; available hate-crime data have substantial ethnicity missingness. |
| 3 | United States | 81.2 | High | Medium | The composite is high because targeted AAPI hate and policy/rhetoric signals are serious even though broad public opinion on immigration remains mostly positive. AAPI evidence is not Indian-specific. |
| 4 | Australia | 62.5 | Elevated | Medium | Direct survey evidence shows widespread perception that discrimination against Indian Australians is frequent, alongside continued broad support for multiculturalism. |
| 5 | New Zealand | 43.8 | Moderate | Low–medium | Mixed public opinion, some reported discrimination among Asian respondents, and recent India-specific visa commitments. |

Scores are for investigation and sensitivity analysis only. Small score differences should not be overinterpreted. Given the evidence gaps and heterogeneity of source measures, the ranking could change as country-specific and comparable data are added.

## Why this is not a pure anti-Indian ranking

The evidence base is not equally available across countries. Canada's current input includes police-recorded incidents targeting South Asians; U.S. reporting uses a survey of Asian American and Pacific Islander adults; UK's published ethnicity breakdown is broader and incomplete; Australia's source asks about perceived discrimination against Indian Australians. These are valuable but different constructs. The policy-friction component also measures pathway risk, not public prejudice. v0.1 therefore labels itself an overall migrant-hostility/social-climate pilot and preserves the component-level inputs for inspection.

## Next validation work

1. Build a common, multi-country public-opinion panel using identical survey questions where possible (for example, attitudes toward immigration and toward South Asian/Indian neighbours or colleagues).
2. Normalize targeted incidents with population denominators where defensible, retaining reported-count and survey-prevalence measures separately.
3. Add source vintage, population denominator, confidence intervals/sample size and reporting coverage as first-class fields.
4. Add change-over-time flags for policy changes instead of treating every longstanding immigration filter as a new hostile trend.
5. Run weight sensitivity (equal weights and alternatives), report rank ranges, and only then consider a bounded EOM adjustment.

## Sources used in v0.1

- Canada: [Environics Institute, 2025 immigration attitudes](https://environicsinstitute.org/canadian-public-opinion-about-immigration-and-refugees-2025/); [Statistics Canada, 2021–2025 South Asian police-reported hate crime series](https://www150.statcan.gc.ca/n1/en/daily-quotidien/260722/t006a-eng.htm); [IRCC study permit eligibility](https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/eligibility.html).
- United Kingdom: [Migration Observatory, public attitudes briefing (8 Sep 2026)](https://migrationobservatory.ox.ac.uk/resources/briefings/uk-public-opinion-toward-immigration/); [June 2025 polling detail](https://migrationobservatory.ox.ac.uk/wp-content/uploads/2026/08/F1-Overall-attitudes.html); [Graduate visa rules](https://www.gov.uk/graduate-visa); [Home Office hate-crime statistics](https://www.gov.uk/government/statistics/hate-crime-england-and-wales-year-ending-march-2025/hate-crime-england-and-wales-year-ending-march-2025).
- United States: [Gallup, immigration opinion (9 Jul 2026)](https://news.gallup.com/poll/712289/americans-support-immigration-down-strong.aspx); [Stop AAPI Hate, 2025 survey reported 1 May 2026](https://stopaapihate.org/2026/05/01/new-report-half-of-aapis-experienced-a-hate-act-in-2025/).
- Australia: [Social Research Centre / ANU, Australia–India Relations Sentiment Survey (May 2025)](https://srcentre.com.au/wp-content/uploads/2025/08/Sentiment-Survey-Report-FINAL_20250805.pdf); [Scanlon Mapping Social Cohesion 2025](https://scanloninstitute.org.au/mapping-social-cohesion-2025/); [Australian Government migration-policy changes](https://immi.homeaffairs.gov.au/support-subsite/Pages/australian-government-migration-policy-changes.aspx).
- New Zealand: [Social Cohesion in New Zealand 2026 report](https://socialink.org.nz/wp-content/uploads/2026/04/Social-Cohesion-in-New-Zealand-2026.pdf); [India–New Zealand FTA visa commitments (20 Oct 2026)](https://www.immigration.govt.nz/about-us/news-centre/india-new-zealand-free-trade-agreement-brings-new-visa-commitments/).
- Ireland: [European Commission, Autumn 2025 Eurobarometer Ireland](https://ireland.representation.ec.europa.eu/news-and-events/news/irish-trust-eu-remains-strong-amid-growing-concerns-over-housing-and-immigration-2025-12-17_en).
- Japan: [Immigration Services Agency of Japan, FY2024 foreign-resident survey](https://www.moj.go.jp/isa/content/001450859.pdf); [FY2022 human-rights/discrimination survey](https://www.moj.go.jp/isa/content/001415876.pdf).
- Switzerland: [State Secretariat for Migration, working in Switzerland](https://www.sem.admin.ch/sem/en/home/overview-arbeit.html).
- Hong Kong: [Immigration Department review 2025](https://www.immd.gov.hk/eng/press/press-releases/20260213.html); [employment-entry guidelines](https://www.immd.gov.hk/en/services/hk-visas/immigration-entry-guideline.html).
