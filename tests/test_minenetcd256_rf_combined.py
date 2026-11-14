import numpy as np
import pytest

from scripts.minenetcd256_rf_combined import combine
from scripts.minenetcd256_rf_multi import sample_training


def test_combination_preserves_sampling_and_rejects_label_mismatch():
    y = np.tile([0, 1], 10)
    raw = {"a": (np.arange(60).reshape(20, 3), y, {})}
    normalized = {"a": (raw["a"][0] / 10, y.copy(), {})}
    x, labels, _ = sample_training(combine(raw, normalized), cap=8)
    expected, expected_labels, _ = sample_training(raw, cap=8)
    np.testing.assert_array_equal(x[:, :3], expected)
    np.testing.assert_array_equal(labels, expected_labels)
    normalized["a"][1][0] = 1
    with pytest.raises(ValueError, match="pixel support"):
        combine(raw, normalized)
