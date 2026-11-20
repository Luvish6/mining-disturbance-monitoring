from scripts.phase23h_reach_priority import category, priority, river_observation, shift_detected


def _season(n, share):
    return dict(usable_dates=n, posthoc_diagnostics=dict(median_scl_water_share=share))


def test_observation_rules():
    assert river_observation({})[0] is False
    assert river_observation(dict(seasons=dict(before=_season(4, .9), after=_season(9, .9))))[0] is False
    assert river_observation(dict(seasons=dict(before=_season(9, 0.0), after=_season(9, 0.0))))[0] is False
    assert river_observation(dict(seasons=dict(before=_season(9, 1.0), after=_season(9, 0.06))))[0] is None
    assert river_observation(dict(seasons=dict(before=_season(9, .8), after=_season(9, .6))))[0] is True


def test_categories_never_forced():
    assert category(True, None, None) == "UNKNOWN"
    assert category(True, False, None) == "RIVER_UNOBSERVABLE"
    assert category(True, True, True) == "LINKED_CANDIDATE"
    assert category(True, True, False) == "LAND_DISTURBANCE_ONLY"
    assert category(False, True, True) == "RIVER_SHIFT_ONLY"
    assert category(False, True, False) == "UNKNOWN"
    assert shift_detected(dict(difference_ci95=[-0.1, 0.1])) is False
    assert shift_detected(dict(difference_ci95=[0.01, 0.1])) is True
    assert shift_detected({}) is None


def test_priority_levels():
    assert priority("RIVER_UNOBSERVABLE", 28) == "HIGH"
    assert priority("UNKNOWN", 28) == "MEDIUM"
    assert priority("RIVER_UNOBSERVABLE", 7) == "MEDIUM"
    assert priority("RIVER_UNOBSERVABLE", 1) == "LOW"
