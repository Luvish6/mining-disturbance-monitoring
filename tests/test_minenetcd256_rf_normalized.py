import numpy as np

from scripts.minenetcd256_rf_normalized import normalized_rgb


def test_robust_rgb_removes_affine_tone_change_and_handles_constant_channels():
    image = np.arange(16).reshape(4, 4, 1) * np.array([1, 2, 0])
    transformed = image * np.array([2, 3, 1]) + np.array([12, 19, 35])
    np.testing.assert_array_equal(normalized_rgb(image), normalized_rgb(transformed))
    assert np.all(normalized_rgb(image)[..., 2] == 0)
