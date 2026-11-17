import math

import pytest

from scripts.smallminesds_spatial import buffered_split, radar_conversion


def square(x):
    return x, 0, x + 1280, 1280


def test_spatial_quarantine_and_order():
    footprints = {"test": square(0), "overlap": square(1), "touch": square(1280),
                  "buffer": square(3840), "outside": square(6401)}
    for i in range(20):
        footprints[str(i)] = square(10000 + 5000 * i)
    train = set(footprints) - {"test"}
    result = buffered_split(footprints, train, {"test"})
    assert result == buffered_split(dict(reversed(list(footprints.items()))), train, {"test"})
    assert result["test"]["split"] == "test"
    for patch_id in ("overlap", "touch", "buffer"):
        assert result[patch_id]["split"] == "quarantine"
        assert result[patch_id]["group"] == result["test"]["group"]
    assert result["outside"]["group"] != result["test"]["group"]


def test_incomplete_or_collapsed_split_fails():
    with pytest.raises(ValueError, match="Complete"):
        buffered_split({"a": square(0)}, {"a"}, {"b"})
    with pytest.raises(ValueError, match="empty"):
        buffered_split({"a": square(0), "b": square(1280)}, {"a"}, {"b"})


def test_radar_requires_verified_units_and_valid_power():
    assert radar_conversion([0.1], "linear_power")[0] == pytest.approx(-10)
    assert radar_conversion([-10], "dB")[0] == -10
    for values, unit in (([0.1], None), ([0], "linear_power"), ([math.nan], "dB")):
        with pytest.raises(ValueError):
            radar_conversion(values, unit)
