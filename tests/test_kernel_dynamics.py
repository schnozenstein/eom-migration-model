import numpy as np
import pytest

from eom_empirical.kernel_dynamics import apply_memory_kernel, exponential_kernel


def test_exponential_kernel_is_normalized_and_decreases_with_lag():
    weights = exponential_kernel(4, decay=2.0)
    assert np.isclose(weights.sum(), 1.0)
    assert np.all(weights >= 0)
    assert np.all(np.diff(weights) < 0)


def test_memory_kernel_uses_current_and_previous_values():
    history = np.array([[1.0], [3.0], [5.0]])
    result = apply_memory_kernel(history, np.array([0.5, 0.5]))
    np.testing.assert_allclose(result[:, 0], [1.0, 2.0, 4.0])


def test_memory_kernel_preserves_constant_series():
    history = np.full((5, 3), 7.0)
    result = apply_memory_kernel(history, exponential_kernel(3, 1.5))
    np.testing.assert_allclose(result, history)


@pytest.mark.parametrize("max_lag,decay", [(-1, 1), (1, 0), (1, np.inf)])
def test_exponential_kernel_rejects_invalid_parameters(max_lag, decay):
    with pytest.raises(ValueError):
        exponential_kernel(max_lag, decay)


def test_memory_kernel_rejects_negative_weights():
    with pytest.raises(ValueError):
        apply_memory_kernel(np.ones((2, 1)), np.array([1.0, -0.1]))
