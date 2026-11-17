import json

import numpy as np
import pytest
from shapely.geometry import box

from scripts import phase22c_maus as pilot


def test_split_bytes_and_roster_cannot_change(monkeypatch):
    original = json.dumps({"groups": {"A": {"split": "train"}, "B": {"split": "test"}}}).encode()
    monkeypatch.setattr(pilot, "SPLIT_SHA", pilot.digest(original))
    pilot.verify_split(original, original)
    for changed in (original.replace(b"train", b"valid"), original.replace(b'"B"', b'"C"')):
        with pytest.raises(ValueError, match="identical"):
            pilot.verify_split(original, changed)
        with pytest.raises(ValueError, match="identical"):
            pilot.verify_split(changed, changed)


def test_orbit_priority_is_label_independent_and_deterministic():
    history = {"DESCENDING": {"90": 3, "11": 4}, "ASCENDING": {"5.0": 4, "1": 4}}
    assert pilot.choose_pair(history) == ("ASCENDING", 1)
    inverted = {direction: dict(reversed(list(counts.items()))) for direction, counts in
                reversed(list(history.items()))}
    assert pilot.choose_pair(inverted) == ("ASCENDING", 1)
    assert pilot.choose_pair({"ASCENDING": {"1": 1}, "DESCENDING": {}}) is None


def test_sar_receipt_rejects_mixed_direction_or_orbit():
    best = ("ASCENDING", 1)
    pair = [dict(id=str(i), direction="ASCENDING", orbit=1) for i in range(2)]
    pilot.check_composite(best, pair)
    for change in (dict(direction="DESCENDING"), dict(orbit=2), dict(id="0")):
        with pytest.raises(ValueError):
            pilot.check_composite(best, [pair[0], pair[1] | change])


def test_missing_sar_preserves_optical_eligibility():
    optical = np.array([True, True, True, False])
    sar = np.zeros_like(optical)
    dem = np.ones_like(optical)
    result = pilot.eligibility(optical, sar, dem)
    assert result["optical"] == {"valid_cells": 3, "eligible": True}
    assert result["optical_dem"]["eligible"]
    assert result["fused_dem"] == {"valid_cells": 0, "eligible": False}


def test_weak_labels_never_qualify_for_verified_evaluation():
    for role in ("train", "validation", "test"):
        assert not pilot.verified_evaluation(role, "WEAK_UNVERIFIED", True, True)
    assert not pilot.verified_evaluation("validation", "VERIFIED_REFERENCE", True, False)
    assert pilot.verified_evaluation("validation", "VERIFIED_REFERENCE", True, True)


def test_geographic_buffer_detects_cross_split_contact():
    geometry = {1: box(0, 0, 10, 10), 2: box(2060, 0, 2070, 10)}
    roster = {"a": dict(ids=[1], split="train"), "b": dict(ids=[2], split="test")}
    with pytest.raises(ValueError, match="buffer"):
        pilot.check_geographic_buffer(geometry, roster)
    geometry[2] = box(2061, 0, 2071, 10)
    pilot.check_geographic_buffer(geometry, roster)


def test_development_seal_rejects_test_and_test_roster_changes():
    roster = {"a": dict(ids=[1], split="train"), "b": dict(ids=[2], split="test")}
    seal = dict(sealed=True, split_sha256=pilot.SPLIT_SHA, groups={"b": [2]})
    pilot.check_seal(roster, seal, [dict(fid=1, group="a", split="train")])
    with pytest.raises(ValueError, match="sealed"):
        pilot.check_seal(roster, seal | {"groups": {"b": [9]}}, [])
    with pytest.raises(ValueError, match="development"):
        pilot.check_seal(roster, seal, [dict(fid=2, group="b", split="test")])
