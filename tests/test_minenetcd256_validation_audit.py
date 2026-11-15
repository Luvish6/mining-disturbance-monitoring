import numpy as np
import pyarrow as pa
import pytest

from scripts.minenetcd256_validation_audit import calibration, select, summarize


class DomainsOnly:
    num_row_groups = 2

    def read_row_group(self, group, *, columns, use_threads):
        assert columns == ["domain"]
        return pa.table({"domain": [["B", "A", "B", "B"], ["B", "B", "A"]][group]})


def test_selection_preserves_first_rows_and_checks_entire_roster():
    assert select(DomainsOnly(), {"A": 2, "B": 5}) == {
        "A": [(0, 1), (1, 2)], "B": [(0, 0), (0, 2), (0, 3), (1, 0)]}
    with pytest.raises(ValueError, match="official inventory"):
        select(DomainsOnly(), {"A": 2, "B": 4})


def test_zero_support_and_calibration():
    y, score = np.array([False, False]), np.array([0., 1.])
    result = summarize(y, score, .5)
    assert result["fpr"] == .5 and result["predicted_positive_pixels"] == 1
    assert result["classes"][1]["recall"] is None
    assert result["classes"][1]["f1"] is None
    assert calibration(y, score)["ece"] == .5
    assert calibration(y, score)["brier"] == .5
