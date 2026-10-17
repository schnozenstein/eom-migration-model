# Empirical design decisions

## Primary question
For this user's intended path, which destinations maximise the probability of a financially sustainable transition from a strong technology-management degree to relevant employment, lawful sponsorship, career progression, and secure long-term residence?

## Primary personal outcome
Prefer a cohort-based binary outcome: a graduate from a relevant programme obtains role-relevant employment within 12 months, transitions to a work status allowing continued employment, and remains in the destination at year 3. The long-horizon endpoint is secure long-term residence by year 8–10. If public cohorts do not report each stage, retain separate stage-specific outcomes and show the missing transition probabilities explicitly.

## Two models, not one
- **Macro EOM benchmark:** uses public country-year indicators and the World Bank net-migration rate as a broad target. This checks whether the EOM sign structure adds predictive value over a naïve baseline.
- **Personal pathway model:** uses programme/cohort-level outcomes. It should not be fitted until sufficient comparable samples exist. Use pooled / hierarchical estimates and broad uncertainty intervals where data is sparse.

## Candidate energy specification
Keep the paper's structure but estimate feature weights rather than fixing them to one. For a predictive macro benchmark, estimate a supervised model with a temporal split; convert predicted attraction to relative energy only as a monotonic transformation and state that the target is net migration. For the personal model, define utility/energy from a calibrated probability of completing each stage, cost/ROI, and stability; do not assume that coefficients from aggregate national data transfer to an individual.

## Possible candidate dependent variable
- Macro: next-year net migration per 1,000 residents, smoothed or averaged over multi-year windows to reduce estimate noise.
- Personal: programme-cohort transition rates for international graduates, with Indian-origin / prior-experience subgroups when observable; long-term residence is the preferred endpoint but data availability may be the limiting factor.

## Missingness and uncertainty
Create separate flags for missing-not-published, not-applicable, and genuinely observed zero. Do not equate unpublished outcomes with zero. Use data availability in confidence labels rather than silently filling values. Where sources use different response windows or denominators, either harmonize or exclude comparisons.

## Validation
1. Temporal backtest: train on earlier years, test on later years.
2. Benchmark comparison: country mean / last observed value, then a conventional model without EOM interpretation.
3. Calibration: if producing probabilities, compare predicted and observed probabilities (Brier score/reliability curve) and only calibrate on a holdout set.
4. Rank stability: bootstrap years/sources/cohorts and show how often each destination appears in the top tier.
5. Policy shocks: define announcement/effective dates, treated groups, exposure, and suitable controls before interpreting causal effects.

## Important construct limitation
National net migration includes many populations and migration reasons. It is a useful broad macro benchmark for attractor dynamics, but it cannot establish that a destination is strong for Indian technology professionals pursuing an MBA. That claim requires the second dataset.
