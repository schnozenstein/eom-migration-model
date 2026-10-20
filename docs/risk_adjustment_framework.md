# EOM Risk-Adjusted Attractiveness: framework and 2026 evidence

## Status

This is a research extension, not a validated ranking. The existing `latest_macro_eom_ranking.csv` remains the six-indicator macro proxy. Risk evidence is recorded separately in `data/risk_event_evidence_2026.csv`; it is **not yet numerically added to the macro score**.

## Why we are not applying arbitrary penalties

Current evidence mixes fundamentally different quantities: an air-quality forecast in PSI, qualitative reports of military tensions, active conflict events, and a regional GDP forecast. Adding these directly or assigning hand-picked score penalties would create a misleadingly precise ranking. The evidence register is intended to preserve provenance and make missing comparability explicit.

## Proposed dimensions

1. **Environmental exposure:** annual mean PM2.5, population-weighted exposure, unhealthy-air days, heat stress and natural-hazard exposure.
2. **Geopolitical exposure:** conflict deaths/events per capita, distance to active conflict, strategic chokepoint exposure, military escalation indicators and trade/energy disruption.
3. **Social and political instability:** comparable protest/event data, political violence, policy volatility and rule-of-law changes.
4. **Economic resilience:** real GDP growth and volatility, energy-import dependence, export/trade concentration, inflation shocks and fiscal capacity.
5. **Resilience and mitigation:** emergency response capacity, health-system capacity, energy diversification and institutional ability to absorb shocks.

## Proposed calculation

- Keep the current six-indicator macro score as a baseline.
- Build a separate risk score using comparable, documented series. Orient every risk variable so higher means more risk.
- Standardize indicators over a declared comparison set and year; document missingness and avoid substituting zeros.
- Compute a risk-adjusted scenario score as `macro_score + lambda * standardized_risk_score`, where lower remains better and `lambda` is published and varied in sensitivity analysis.
- Publish baseline, risk score, adjusted rank, rank change, evidence year, and coverage/completeness separately.
- Add a current-event alert layer for sudden conflicts or air-quality emergencies. Do not confuse a short-lived alert with a long-run country risk estimate.
- Do not issue a global adjusted ranking until all included destinations have sufficiently comparable risk inputs. Countries with incomplete risk coverage must be marked unscored, not silently treated as low risk.

## Current evidence captured

- **Singapore:** Singapore's NEA forecast PSI of 101–190 for 19 October 2026, classified as unhealthy. This is an event-specific haze signal; it is not an annual pollution metric. Source: https://www.nea.gov.sg/media/news/advisories/index/haze-situation-update-18-october-2026
- **Japan:** reporting documents heightened Japan–China tensions around defence policy and Taiwan. This is evidence of regional strategic exposure, not a prediction of imminent war. Source: https://www.reuters.com/world/china/japan-pushes-back-against-accusations-new-militarism-2026-05-31
- **Saudi Arabia:** reporting on 14 October 2026 describes attacks affecting Saudi targets and regional shipping/energy risks. This merits a current-risk alert, but a single event is not a standardized country score. Source: https://www.reuters.com/world/middle-east/houthis-bring-war-riyadh-2026-10-14
- **Iran:** regional shipping and conflict risk is documented in current reporting, but Iran is not currently a destination in the registry. It should not be inserted into a country ranking without explicitly adding it to scope and establishing comparable inputs. Source: https://www.reuters.com/business/energy/oil-prices-climb-traders-weigh-saudi-supply-risk-russian-diesel-flow-2026-10-14
- **European Union:** the European Commission's Spring 2026 forecast projected EU growth at 1.1% in 2026 and euro-area growth at 0.9%. This is a regional forecast and must not be copied into individual country records. Source: https://commission.europa.eu/news-and-media/news/eu-economy-forecast-slow-down-amid-rising-inflation-following-energy-shock-2026-05-21_en

## Next data work before a defensible reranking

- Add harmonized annual PM2.5 exposure and climate hazard measures for every destination.
- Add a comparable conflict-risk dataset with explicit definitions and reference periods.
- Add country-level GDP growth/volatility and energy-import dependence; keep regional aggregates separate.
- Add comparable political violence/protest indicators, with clear coverage limits.
- Add automated freshness/coverage checks and scenario-weight sensitivity outputs.
- Only then generate a new risk-adjusted ranking. The existing macro ranking is not overwritten by this framework.
