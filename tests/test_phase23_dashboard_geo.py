import json
from pathlib import Path

import pytest

from scripts.phase23_dashboard_geo import build, chain

TEST_TILES = ("east-91-561", "west-81-557")


def test_chain_follows_ndoid_and_fails_closed():
    nd = {1: 2, 2: 3, 3: 0}
    assert chain(1, 3, nd) == [1, 2, 3]
    assert chain(3, 1, nd) == []


@pytest.fixture(scope="module")
def geo():
    if not Path("outputs/phase23a_linkage/reaches.json").exists():
        pytest.skip("local Phase 23A cache unavailable")
    return build()


def test_layers_are_real_and_traceable(geo):
    assert {d["name"] for d in geo["districts"]} == {"East Jaintia Hills", "West Jaintia Hills"}
    assert len(geo["stations"]) == 4 and all(len(s["lonlat"]) == 2 for s in geo["stations"])
    assert [c["supported"] for c in geo["chains"]] == [True, True] and [c["reaches"] for c in geo["chains"]] == [15, 19]
    assert len(geo["rivers"]) > 100 and all(r["upland_km2"] >= 25 for r in geo["rivers"])
    for k in ("districts", "rivers", "stations", "aois"):
        assert geo["provenance"][k]["source"]


def test_no_test_split_or_candidate_locations(geo):
    assert len(geo["aois"]) == 20 and {a["split"] for a in geo["aois"]} <= {"train", "validation"}
    assert all(a["ring"][0] == a["ring"][-1] and len(a["ring"]) == 5 for a in geo["aois"])
    text = json.dumps(geo)
    assert not any(t in text for t in ("cluster_cells", "centroid", "crosswalk", "_centroid"))
    w, s, e, n = geo["view_bounds"]
    assert w < e and s < n


def test_dashboard_snapshots_exclude_test_tiles():
    for name in ("overview.json", "explorer.json"):
        p = Path("frontend/public/local") / name
        if p.exists():
            text = p.read_text(encoding="utf-8")
            assert not any(t in text for t in TEST_TILES), name
