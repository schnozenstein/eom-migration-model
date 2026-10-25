import numpy as np
import pytest

from eom_empirical.density_state import (
    diagonal_density_state,
    normalize_probabilities,
    shannon_von_neumann_entropy,
    validate_transition_matrix,
)


def test_probability_normalization_and_density_state():
    state = diagonal_density_state(np.array([2.0, 1.0, 1.0]))
    np.testing.assert_allclose(np.trace(state), 1.0)
    np.testing.assert_allclose(np.diag(state), [0.5, 0.25, 0.25])
    np.testing.assert_allclose(state, np.diag(np.diag(state)))


def test_entropy_uniform_exceeds_concentrated_distribution():
    uniform = shannon_von_neumann_entropy(np.array([1.0, 1.0, 1.0]))
    concentrated = shannon_von_neumann_entropy(np.array([1.0, 0.0, 0.0]))
    assert uniform > concentrated
    assert np.isclose(concentrated, 0.0)


def test_transition_matrix_must_be_row_stochastic():
    matrix = validate_transition_matrix(np.array([[0.8, 0.2], [0.1, 0.9]]))
    np.testing.assert_allclose(matrix.sum(axis=1), [1.0, 1.0])
    with pytest.raises(ValueError):
        validate_transition_matrix(np.array([[0.8, 0.3], [0.1, 0.9]]))


@pytest.mark.parametrize("values", [[0, 0], [-1, 2], [1, np.nan], []])
def test_invalid_probability_vectors_are_rejected(values):
    with pytest.raises(ValueError):
        normalize_probabilities(np.asarray(values, dtype=float))
