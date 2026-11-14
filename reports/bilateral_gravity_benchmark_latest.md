# Bilateral gravity benchmark

Run: 2026-11-14T133218Z
Status: completed_expanding_origin_bilateral_benchmark
Complete-case OD-year rows: 6,132
Scored predictions: 5,196
Origins/destinations: 43 / 15
Scored folds: 12

Model metrics:
{
  "gravity_ppml": {
    "n": 5196,
    "mae": 1714.0506052398382,
    "rmse": 5211.439939116105,
    "poisson_deviance": 1453.779899052102,
    "spearman": 0.8856251843269166
  },
  "gravity_plus_eom_ppml": {
    "n": 5196,
    "mae": 1679.1395970408807,
    "rmse": 5123.243635668383,
    "poisson_deviance": 1407.929920639267,
    "spearman": 0.8857650109398114
  },
  "pair_persistence": {
    "n": 5101,
    "mae": 531.0690060772398,
    "rmse": 2536.643893204789,
    "poisson_deviance": 202.1804340068629,
    "spearman": 0.9909785363352955
  },
  "EOM_minus_gravity_MAE_cluster_bootstrap": {
    "clusters": 526,
    "repetitions": 300,
    "mean_mae_difference": 35.90575128748583,
    "ci95": [
      12.62295969052343,
      62.34226800598783
    ],
    "positive_favours_eom": true
  }
}

Only observed numeric pair-year cells with complete lagged features and CEPII covariates are scored. Missing/suppressed pairs are not imputed as zero. This is a predictive test, not a causal estimate.

Source failures:
[]
