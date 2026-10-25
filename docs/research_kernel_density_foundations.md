# EOM research note: memory kernels and density states

## Status and scope

This is an experimental mathematical foundation only. It does **not** alter production rankings, fit parameters, issue forecasts, or claim that the EOM framework is empirically validated. The current EOM benchmark and its persistence baseline remain unchanged.

## 1. Memory kernel

For an observed time-by-destination history (x_t), the first implementation uses a finite-memory weighted average:

[
\tilde{x}_t = \frac{\sum_{\ell=0}^{\min(L,t)} w_\ell x_{t-\ell}}
{\sum_{\ell=0}^{\min(L,t)} w_\ell},\qquad
w_\ell \propto e^{-\ell/\tau}.
]

Here (L) is the maximum lag and (	au>0) controls decay. The weights are non-negative and normalized; early observations renormalize over available history. This is a transparent candidate feature transform, not yet a causal response kernel or a fitted dynamical law.

A later model may test whether lagged policy, economic, social-climate, or geopolitical signals improve forecasts of consistently defined migration flows. Fit and tune (	au) and (L) only inside each training window to avoid look-ahead leakage. Compare with no-memory and simple lagged-feature baselines.

## 2. Classical density-state foundation

A destination-choice probability vector (p_t) can be represented by a diagonal matrix:

[
\rho_t = \operatorname{diag}(p_t),\qquad p_i\geq0,\quad \sum_i p_i=1.
]

This gives a trace-one, positive semidefinite matrix while retaining a classical interpretation. Its von Neumann entropy equals Shannon entropy for this diagonal state:

[
S(\rho_t)=-\operatorname{Tr}(\rho_t\log\rho_t)
=-\sum_i p_i\log p_i.
]

The current functions validate and encode distributions; they do not estimate destination-choice probabilities from macro energy. Any such mapping requires an explicit calibrated model and out-of-sample evaluation.

## 3. Transition dynamics and data requirements

A candidate destination transition matrix (T) must be non-negative and row-stochastic. Empirical estimation requires consistent origin–destination transitions with stable definitions, dates, and denominators. Migrant stocks must not be silently substituted for annual flows, and forced-displacement series must remain distinct from voluntary economic migration.

The available data are uneven: bilateral stock tables and selected annual flow series cover different geographies, time periods, and definitions. The current functions therefore accept arrays but do not automatically assemble or fit a transition matrix.

## 4. Superdensity/process object: deliberately deferred

A superoperator (\mathcal{S}) that maps a state to another state is not the same object as a multi-time process/superdensity object. Before implementing the latter, the research specification must define the object, indices, normalization/positivity conditions, observable data, estimator, and a falsifiable benefit over standard Markov or state-space models. No multi-time quantum formalism is asserted by this PR.

## 5. Evaluation gates

1. Preserve the existing macro and social-climate rankings as baselines.
2. Check kernel behavior, state normalization, non-negativity, transition-matrix row sums, and numerical stability.
3. Use chronological expanding-origin evaluation with all preprocessing and hyperparameter selection confined to training data.
4. Compare against persistence and simple classical alternatives on the same target rows and dates.
5. Keep the extension experimental unless it improves held-out performance or yields independently testable explanatory value.

Passing unit tests verifies implementation properties only; it does not validate the migration model.
