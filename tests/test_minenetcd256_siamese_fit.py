import pytest

from scripts.minenetcd256_siamese_fit import score, verify_rows


def test_no_positive_site_and_fixed_threshold():
    result = score([0, 0], [.49, .5])
    assert result["fpr"] == .5
    assert result["classes"][1]["recall"] is None
    assert result["average_precision"] is None


def test_frozen_rows_reject_duplicate_identity():
    rows = [dict(site="mine", group=0, row=i) for i in range(5)]
    source = {"sites": {"mine": {"rows": [[0, i] for i in range(5)]}}}
    verify_rows(rows, source, ["mine"])
    with pytest.raises(ValueError, match="Frozen rows"):
        verify_rows(rows[:-1] + rows[:1], source, ["mine"])
