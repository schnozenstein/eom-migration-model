# EOM empirical research programme

## Research objective

The primary question is whether the Entropy-Oriented Migration (EOM) formulation adds explanatory or out-of-sample predictive value to established models of international migration. Country rankings and daily source-refresh counts are secondary research infrastructure, not the main scientific outcome.

The main unit of analysis is an **origin–destination–year (OD-year)** observation. The general model is not restricted to students, MBAs, technology workers, or any single migration route. Population subgroups and visa scenarios are separate extensions when the data identify them.

## Why the programme is changing

The existing macro pipeline evaluates next-year national net migration per 1,000 residents. Its latest stored expanding-origin evaluation (7 November 2026) has 613 test observations across 44 destinations and 14 test origins (years 2012–2025): Ridge MAE 4.022, country-mean MAE 2.804, persistence MAE 2.363; equal-weight EOM rank Spearman 0.515 versus persistence 0.806. The outcome is a national country-year net figure, not bilateral migration. The current EOM macro proxy has not beaten the simple persistence benchmark.

That result is evidence against the current macro proxy, not a refutation of the complete EOM paper. A bilateral theory must be evaluated against bilateral outcomes. The existing 4,176-row outcome ledger must not be described as an OD flow panel.

## Phase 1 — build a defensible bilateral outcome panel

Primary source:
- Eurostat dataset migr_imm5prv: annual immigration by country of previous usual residence. The reporting geography is the destination; partner is the origin.
- Eurostat dataset migr_emi3nxt: annual emigration by country of next usual residence. The reporting geography is the origin; partner is the destination. This is a separate reverse-direction source for reconciliation, not a second flow to add to immigration.

Retain numeric zero only when the source explicitly publishes zero. Missing, confidential, suppressed, unreported or unconvertible country codes remain missing/absent with a documented status; they are never changed to zero. Keep the raw JSON-stat snapshots, source URLs, query parameters, retrieval time, flags, and observation periods. Convert the two Eurostat directions into a common origin/destination orientation while retaining the original measure.

History natural key: (dataset, measure, origin_iso3, destination_iso3, year). A same-valued retrieval is not a new observation. A changed source value creates a new revision row with its previous value and revision number. Geography conversion exceptions and unresolvable aggregate codes are audited.

The first panel is Europe-heavy. It does not support claims about global bilateral migration until non-European national statistical sources are harmonised. The UN DESA 2024 bilateral migrant-stock matrix can later provide a stock/network panel, but stock must never be relabelled as annual flow.

## Phase 2 — orthodox gravity benchmark

Start with a transparent Poisson pseudo-maximum-likelihood (PPML) gravity model. The initial specification includes:
- origin and destination population, measured at t-1;
- origin and destination GDP per capita at PPP, measured at t-1;
- bilateral distance, contiguity and common official language from CEPII GeoDist;
- origin and destination fixed effects;
- a time trend.

The dependent variable is the observed annual number of immigrants from origin to destination in year t. The current implementation uses Eurostat immigration by previous residence. The opposite emigration-by-next-residence series is retained as a consistency check rather than double-counted.

Only observed numeric source cells are included. The benchmark deliberately does not infer zero flows from missing pairs. This means the resulting estimator is conditional on the source's observed reporting universe; missingness and selection into the reported sample must be described in every result. PPML on a selected positive-only sample is not automatically a standard full-universe gravity estimate.

## Phase 3 — test whether EOM adds value

Compute the existing equal-weight EOM energy separately by country and feature year using the repo's documented paper-sign convention. For an OD pair, define the initial bilateral EOM attractor gap as origin energy minus destination energy. A positive gap means destination energy is lower and hence a stronger attractor under the paper's convention.

Compare on identical chronological train/test folds:
1. PPML gravity baseline;
2. same PPML specification plus the bilateral EOM attractor gap;
3. persistence for OD pairs with an actually observed flow in the prior year.

All macro features are lagged one year relative to the target flow. The primary test is whether adding EOM improves held-out error against gravity, not whether the coefficient has a desired sign in a single pooled regression. Report MAE, RMSE, Poisson deviance, rank association, fold-level convergence, sample counts and OD-pair-cluster bootstrap uncertainty for the MAE difference.

The composite currently overlaps conceptually with GDP, labour-market and institutional controls. Incremental improvement would be preliminary evidence for this operationalisation, not proof that the entire entropy framework is validated. No causal claim follows from predictive comparisons.

## Phase 4 — network and dynamic structure

Only after the gravity panel and baseline are stable:
- introduce lagged diaspora stocks / migrant-network measures, keeping stock and flow definitions distinct;
- test path dependence, cumulative feedback, memory kernels, and origin–destination transition dynamics;
- estimate rather than hand-pick memory decay or entropy parameters;
- compare with gravity plus lagged migrant stocks, Markov/transition baselines, and other justified alternatives;
- assess whether network/entropy terms improve later held-out years and unseen corridors.

Do not use contemporaneous migrant stock as a predictor for the same-year flow; it can be jointly determined with the outcome. Use the latest available prior-year stock vintage and record source revisions.

## Phase 5 — policy and causal evaluation

Maintain a policy event registry with publication date, effective date, affected origin/cohort/route, mechanism, implementation status and official source. Policy announcements alone do not identify effects.

Use difference-in-differences, event studies or natural experiments only where a defensible comparison group exists. Test pre-trends, placebo dates/outcomes, anticipation, spillovers and sensitivity to alternative control groups. Predictive correction is not a causal estimate.

## Research gates and reporting discipline

A daily run should report a research result only when it creates new evidence: new usable OD cells, source revision analysis, a newly matured forecast outcome, a validated model comparison, a failed hypothesis, or a meaningful methodological/data-quality finding. If none occurred, the report should be short and say so.

No daily re-ranking is required unless the eligible input panel or scoring rule changes. Do not retune equations or weights to improve a single test period. Preserve every prior model and report; adopt a revision only after credible later held-out improvement and sensitivity checks.

The current model is uncalibrated. No coefficients, EOM energy values or migration probabilities should be presented as validated without relevant parameter estimation and out-of-sample evidence.
