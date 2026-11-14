import numpy as np

from scripts.minenetcd256_rf_multi import sample_training


def test_equal_mine_and_class_caps_without_duplicating_rare_pixels():
    x = np.arange(30).reshape(10, 3)
    mines = {"a": (x, np.array([0] * 5 + [1] * 5), {}),
             "b": (x, np.zeros(10, dtype=int), {})}
    features, labels, counts = sample_training(mines, cap=16)
    assert counts == {"a": [4, 4], "b": [4, 0]}
    assert len(labels) == 12
    np.testing.assert_array_equal(features, sample_training(mines, cap=16)[0])
