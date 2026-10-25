"""Small, testable memory-kernel primitives for EOM research experiments.

These functions are descriptive transforms, not a fitted migration model.
They intentionally do not modify the production ranking pipeline.
"""
from __future__ import annotations

import numpy as np


def exponential_kernel(max_lag: int, decay: float) -> np.ndarray:
    """Return normalized non-negative lag weights, with lag 0 most recent.

    Parameters
    ----------
    max_lag:
        Largest included lag. A value of 0 uses only the current observation.
    decay:
        Positive decay scale in time steps. Larger values retain more history.
    """
    if not isinstance(max_lag, (int, np.integer)) or max_lag < 0:
        raise ValueError("max_lag must be a non-negative integer")
    if not np.isfinite(decay) or decay <= 0:
        raise ValueError("decay must be finite and positive")
    lags = np.arange(max_lag + 1, dtype=float)
    weights = np.exp(-lags / float(decay))
    return weights / weights.sum()


def apply_memory_kernel(history: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Smooth a time-by-destination matrix using available past observations.

    At each time t, weight lag 0 is applied to t, lag 1 to t-1, and so on.
    At the beginning of a series, unavailable lags are dropped and the
    remaining weights are renormalized. Inputs must be finite and 2-D.
    """
    values = np.asarray(history, dtype=float)
    kernel = np.asarray(weights, dtype=float)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] == 0:
        raise ValueError("history must be a non-empty 2-D time-by-destination array")
    if not np.isfinite(values).all():
        raise ValueError("history must contain only finite values")
    if kernel.ndim != 1 or kernel.size == 0 or not np.isfinite(kernel).all():
        raise ValueError("weights must be a non-empty finite 1-D array")
    if (kernel < 0).any() or kernel.sum() <= 0:
        raise ValueError("weights must be non-negative with a positive sum")
    kernel = kernel / kernel.sum()

    result = np.empty_like(values, dtype=float)
    for t in range(values.shape[0]):
        available = min(t + 1, kernel.size)
        local_weights = kernel[:available]
        local_weights = local_weights / local_weights.sum()
        past = values[t - np.arange(available)]
        result[t] = local_weights @ past
    return result
