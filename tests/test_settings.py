from config.settings import BEFORE, AFTER

def test_seasons_are_non_overlapping_and_correct():
    assert BEFORE.start == '2023-11-01'
    assert BEFORE.end == '2024-04-01'
    assert AFTER.start == '2024-11-01'
    assert AFTER.end == '2025-04-01'
    assert BEFORE.end < AFTER.start
