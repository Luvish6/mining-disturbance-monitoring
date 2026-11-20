import numpy as np
import pytest

from scripts.phase22p_sar_corroboration import co_change, percentile_rank, permutation_p, tile_overlap


def test_permutation_detects_shift_and_not_null():
    pool = np.random.default_rng(0).normal(0, 1, 2000)
    obs, p = permutation_p(np.full(9, -3.0), pool)
    assert obs < -2.5 and p < 0.001
    _, p = permutation_p(pool[:9], pool)
    assert p > 0.05
    assert permutation_p([1, 2, 3], pool) == permutation_p([1, 2, 3], pool)


def test_percentile_rank_and_co_change_bounds():
    pool = np.arange(100.0)
    assert percentile_rank([-1, 49, 200], pool) == [0.0, 50.0, 100.0]
    assert co_change([50, 50, 99.5], [50, -10, 50], pool, pool) == [False, True, True]


def test_tile_overlap_matches_phase22l_and_6b_grids():
    a, t = tile_overlap([470640, 2796330, 472560, 2798250], [471540, 2796540, 473460, 2798460])
    assert (a[0].start, a[0].stop, a[1].start, a[1].stop) == (0, 57, 30, 64)
    assert (t[0].start, t[0].stop, t[1].start, t[1].stop) == (7, 64, 0, 34)
    assert tile_overlap([0, 0, 30, 30], [60, 60, 90, 90]) is None
    with pytest.raises(ValueError):
        tile_overlap([0, 0, 300, 300], [15, 0, 315, 300])
