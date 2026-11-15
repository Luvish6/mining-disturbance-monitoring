from scripts.phase12a_river import spectral_summary

import pytest


PAIRS = [["2023-11-08", "2024-11-10"], ["2024-02-10", "2025-02-07"]]


def test_withholds_below_fixed_support_floor():
    result = spectral_summary(dict(matched_pairs=PAIRS, common_pixels=12, reportable=False), [])
    assert result == dict(common_10m_pixels=12, matched_pairs=2, matched_months=2)


def test_uses_matched_dates_and_signed_difference():
    rows = [
        dict(acquired_utc=day, fixed_pixels=25, common_ratio=value,
             status="matched, fixed-footprint screen passed")
        for day, value in zip((day for pair in PAIRS for day in pair), [0.1, 0.2, 0.3, 0.4])
    ]
    receipt = dict(matched_pairs=PAIRS, common_pixels=25, reportable=True)
    assert spectral_summary(receipt, rows)["ndti_change"] == pytest.approx(0.1)
    with pytest.raises(ValueError, match="Missing eligible"):
        spectral_summary(receipt, rows[:-1])


def test_rejects_out_of_window_dates():
    with pytest.raises(ValueError, match="Invalid matched dates"):
        spectral_summary(dict(matched_pairs=[["2022-11-08", "2024-11-10"]]), [])
