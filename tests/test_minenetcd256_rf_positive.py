import pytest

from scripts.minenetcd256_rf_positive import select_rows


def test_patch_selection_is_deterministic_and_validation_is_label_blind():
    candidates = {"mine": [((0, i), i >= 5) for i in range(10)]}
    assert select_rows("train", candidates)["mine"] == [(0, i) for i in range(5, 10)]
    flipped = {"mine": [(row, not mixed) for row, mixed in candidates["mine"]]}
    assert select_rows("val", candidates) == select_rows("val", flipped)
    with pytest.raises(ValueError, match="eligible"):
        select_rows("train", {"mine": [((0, 0), False)]})
