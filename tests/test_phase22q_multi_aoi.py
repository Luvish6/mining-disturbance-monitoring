import json
from pathlib import Path

import numpy as np
from shapely.geometry import box

from scripts.phase22q_multi_aoi import guard, stratified_pooled_p


def test_guard_rejects_test_overlap_and_outside_district():
    b = [451530, 2811540, 453450, 2813460]
    area = box(*b).buffer(5000)
    assert guard(b, area, [("far", box(0, 0, 1, 1))])["eligible"]
    r = guard(b, area, [("t", box(*b).buffer(-100))])
    assert not r["eligible"] and r["test_intersections"] == ["t"]
    assert not guard(b, box(*b).buffer(-1), [("far", box(0, 0, 1, 1))])["eligible"]


def test_stratified_pooled_uses_own_background():
    rng = np.random.default_rng(1)
    s1 = (np.full(5, -3.0), rng.normal(0, 1, 500))
    s2 = (np.full(4, 7.0), rng.normal(10, 1, 500))  # shifted background must not dominate
    obs, p = stratified_pooled_p([s1, s2])
    assert obs < -2.5 and p < .001
    obs, p = stratified_pooled_p([(s1[1][:5], s1[1]), (s2[1][:4], s2[1])])
    assert p > .05


def test_preregistration_never_admits_test_tiles():
    plan = json.loads(Path("docs/reports/phase22q-preregistration.json").read_bytes())
    assert all(v["guard"]["split"] != "test" for v in plan["aois"].values())
    assert {"east-91-561", "west-81-557"} <= set(plan["excluded"])
