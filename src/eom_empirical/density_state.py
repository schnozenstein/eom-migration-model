"""Classical probability-state foundations for EOM experiments.

A diagonal density matrix here is a mathematical encoding of a classical
probability vector; it does not imply that migration is a quantum process.
"""
from __future__ import annotations

import numpy as np


def normalize_probabilities(values: np.ndarray) -> np.ndarray:
    """Validate and normalize a finite, non-negative probability vector."""
    probabilities = np.asarray(values, dtype=float)
    if probabilities.ndim != 1 or probabilities.size == 0:
        raise ValueError("probabilities must be a non-empty 1-D vector")
    if not np.isfinite(probabilities).all():
        raise ValueError("probabilities must be finite")
    if (probabilities < 0).any():
        raise ValueError("probabilities cannot be negative")
    total = probabilities.sum()
    if total <= 0:
        raise ValueError("probabilities must have a positive sum")
    return probabilities / total


def diagonal_density_state(values: np.ndarray) -> np.ndarray:
    """Encode a classical distribution as a diagonal, trace-one matrix."""
    probabilities = normalize_probabilities(values)
    return np.diag(probabilities)


def shannon_von_neumann_entropy(values: np.ndarray) -> float:
    """Compute entropy in nats for a classical distribution/diagonal state."""
    probabilities = normalize_probabilities(values)
    positive = probabilities[probabilities > 0]
    return float(-np.sum(positive * np.log(positive)))


def validate_transition_matrix(matrix: np.ndarray, *, atol: float = 1e-8) -> np.ndarray:
    """Validate a row-stochastic transition matrix and return a copy."""
    transition = np.asarray(matrix, dtype=float)
    if transition.ndim != 2 or transition.shape[0] == 0 or transition.shape[0] != transition.shape[1]:
        raise ValueError("transition matrix must be non-empty and square")
    if not np.isfinite(transition).all():
        raise ValueError("transition matrix must be finite")
    if (transition < -atol).any():
        raise ValueError("transition probabilities cannot be negative")
    if not np.allclose(transition.sum(axis=1), 1.0, atol=atol, rtol=0):
        raise ValueError("each transition-matrix row must sum to 1")
    return transition.copy()
