import numpy as np
from scripts.phase22n_temporal import rectangle, check, cluster_stats
from shapely.geometry import box


def test_full_rectangle_guard_rejects_test_overlap_and_outside_district():
    p = rectangle(92.8486306, 25.3517647)
    area = p.buffer(10000)
    protected = [("test", p.buffer(-100))]
    r = check(92.8486306, 25.3517647, area, protected)
    assert not r["eligible"] and r["test_intersections"] == ["test"]
    assert r["rectangle_test_buffer_distance_m"] == 0
    r = check(92.8486306, 25.3517647, p.buffer(-1), [("far", box(0, 0, 1, 1))])
    assert not r["district_contained"] and not r["eligible"]


def test_components_and_low_ndvi_denominators():
    b = np.zeros((6, 2, 2)); a = b.copy()
    b[3] = [[.1, .6], [.15, .8]]
    a[3] = .05; b[4] = -.1; a[4] = .2
    eligible = np.array([[True, True], [False, True]])
    candidates = np.array([[True, False], [False, True]])
    ids, rows, background = cluster_stats(b, a, eligible, candidates, np.ones((2, 2)))
    assert len(rows) == 1 and rows[0]["cells"] == 2
    assert rows[0]["before_ndvi_lt_020_fraction"] == .5
    assert background == 1 / 3
    assert rows[0]["hectares"] == .18


def test_no_candidate_fraction_is_not_zero_measurement():
    b = np.zeros((6, 1, 1))
    _, rows, fraction = cluster_stats(b, b, np.zeros((1, 1), bool), np.zeros((1, 1), bool), np.ones((1, 1)))
    assert rows == [] and fraction is None


def test_actual_roster_rejects_control_without_processing_it():
    import json
    from pathlib import Path
    from scripts.phase22n_temporal import guards, check
    plan = json.loads(Path("docs/reports/phase22n-preregistration.json").read_bytes())
    area, protected = guards()
    for row in plan["eligible_aois"] + plan["rejected_aois"]:
        assert check(*row["anchor"], area, protected) == row["guard"]
    control = next(r for r in plan["rejected_aois"] if r["id"] == "proposed-forest-control")
    assert not control["guard"]["eligible"]
    assert "96:560" in control["guard"]["test_intersections"]
    assert not control["guard"]["district_contained"]
    assert control["guard"]["center_inside_nearest_test_buffer"]


def test_complete_footprint_required_even_with_development_center():
    from shapely.geometry import box
    from scripts.phase22n_temporal import check
    area = box(400000, 2700000, 600000, 2900000)
    # Exact control is not admitted by treating only the center as the AOI.
    guarded = check(92.8486306, 25.3517647, area, [("synthetic-test-edge", box(485500, 2800000, 486000, 2810000))])
    assert guarded["test_intersections"] == ["synthetic-test-edge"]
    assert not guarded["eligible"]
