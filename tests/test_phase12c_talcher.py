import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase12c_talcher import downstream_path, summarize


def test_downstream_path_requires_reciprocal_links_and_correct_direction():
    features = {
        10: {"properties": {"NDOID": 11}},
        11: {"properties": {"NDOID": 12, "NUOID": "10"}},
        12: {"properties": {"NDOID": 0, "NUOID": "11"}},
    }
    assert downstream_path(features, 10, 12) == [10, 11, 12]
    assert downstream_path(features, 12, 10) == []
    features[12]["properties"]["NUOID"] = "9"
    assert downstream_path(features, 10, 12) == []


def test_seasonal_change_and_paired_range_keep_sign():
    result = summarize([{"before_ndti": 0.1, "after_ndti": -0.3},
                        {"before_ndti": 0.3, "after_ndti": 0.4}])
    assert result["ndti_change"] == pytest.approx(-0.15)
    assert result["paired_change_min"] == pytest.approx(-0.4)
    assert result["paired_change_max"] == pytest.approx(0.1)
