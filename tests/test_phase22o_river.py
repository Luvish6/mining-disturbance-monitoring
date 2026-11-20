import numpy as np
import pytest

from scripts.phase22o_river import (MNDWI_POS, VALID, antecedent, bootstrap_median_ci, date_ndti,
                                    difference_ci, downstream_of, interior_mask, season_summary, select_dates)


def _water(n=7):
    flags = np.full((n, n), VALID | MNDWI_POS, np.int16)
    return flags, np.full((n, n), 80, np.int16), np.ones((n, n), bool)


def test_erosion_removes_border_and_requires_every_screen():
    flags, jrc, corridor = _water()
    m = interior_mask(flags, jrc, corridor)
    assert m.sum() == 25 and not m[0].any() and not m[:, -1].any()
    flags[3, 3] = VALID  # MNDWI fails at centre -> its 8 neighbours lose interior status
    assert interior_mask(flags, jrc, corridor).sum() == 25 - 9
    jrc[:] = 49  # historical occurrence below 50% removes everything
    assert interior_mask(flags, jrc, corridor).sum() == 0
    flags, jrc, corridor = _water()
    jrc[:] = 255  # JRC no-data value is not water
    assert interior_mask(flags, jrc, corridor).sum() == 0


def test_narrow_channel_is_unresolved_not_zero():
    flags, jrc, corridor = _water()
    jrc[:] = 0
    jrc[:, 2:4] = 90  # two-pixel-wide channel vanishes after one-pixel erosion
    assert interior_mask(flags, jrc, corridor).sum() == 0
    assert season_summary([]) == dict(status="UNRESOLVED", usable_dates=0)


def test_date_ndti_minimum_pixels_and_formula():
    b3 = np.full((2, 2), 400); b4 = np.full((2, 2), 600)
    mask = np.array([[True, True], [True, False]])
    val, n = date_ndti(b3, b4, mask)
    assert n == 3 and val == pytest.approx(0.2)
    mask[1, 0] = False
    assert date_ndti(b3, b4, mask) == (None, 2)


def test_one_record_per_date_and_deterministic_tie():
    g = [dict(id="b", date="2024-01-01", pixels=5, ndti=.1), dict(id="a", date="2024-01-01", pixels=5, ndti=.2),
         dict(id="c", date="2024-01-01", pixels=9, ndti=.3), dict(id="d", date="2024-01-02", pixels=4, ndti=None)]
    assert [x["id"] for x in select_dates(g)] == ["c"]
    assert [x["id"] for x in select_dates(g[:2])] == ["a"]


def test_insufficient_dates_have_no_ci_and_supported_ci_brackets_median():
    four = [dict(ndti=v) for v in (.1, .2, .3, .4)]
    s = season_summary(four)
    assert s["status"] == "INSUFFICIENT_DATES" and "median_ci95" not in s
    s = season_summary(four + [dict(ndti=.5)])
    lo, hi = s["median_ci95"]
    assert s["status"] == "SUPPORTED" and lo <= s["median_ndti"] <= hi
    assert bootstrap_median_ci([1, 2, 3, 4, 5]) == bootstrap_median_ci([1, 2, 3, 4, 5])
    d, (lo, hi) = difference_ci([0, 0, 0, 0, 0], [1, 1, 1, 1, 1])
    assert d == 1 and lo == hi == 1


def test_antecedent_rain_excludes_acquisition_day_and_missing_days():
    daily = {"2024-01-09": 1.0, "2024-01-08": 2.0, "2024-01-07": 3.0, "2024-01-10": 100.0}
    assert antecedent(daily, "2024-01-10", 1) == 1.0
    assert antecedent(daily, "2024-01-10", 3) == 6.0
    assert antecedent(daily, "2024-01-10", 7) is None


def test_flow_topology_requires_chain():
    ndoid = {1: 2, 2: 3, 3: 0, 5: 6}
    assert downstream_of(1, 3, ndoid) == 2
    assert downstream_of(3, 1, ndoid) is None
    assert downstream_of(5, 3, ndoid) is None
