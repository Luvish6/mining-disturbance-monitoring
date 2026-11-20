from scripts.phase23a_river_audit import window_status


def test_window_status_thresholds():
    assert window_status(0, 0) == "NO_INTERIOR_WATER"
    assert window_status(1, 0) == "INSUFFICIENT_DATES"
    assert window_status(4, 9) == "INSUFFICIENT_DATES"
    assert window_status(5, 5) == "INTERIOR_SUPPORTED"
