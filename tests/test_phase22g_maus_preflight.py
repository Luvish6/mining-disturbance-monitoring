import pytest
from shapely.geometry import box
from shapely.strtree import STRtree

from scripts import phase22g_maus_preflight as pilot


def test_blockers_check_full_footprint_and_opposing_buffer():
    tile = box(0, 0, 1280, 1280)
    state = box(-3000, -3000, 4000, 4000)
    empty = STRtree([])
    assert pilot.blockers(tile, state, empty, empty, [], True) == []
    opposing = STRtree([box(3330, 0, 3400, 10)])
    assert pilot.blockers(tile, state, opposing, empty, [], True) == [
        "OPPOSING_OR_EXCLUDED_GROUP_BUFFER"]
    assert "ADM1_FULL_FOOTPRINT_BUFFER" in pilot.blockers(
        tile, box(-2000, -2000, 4000, 4000), empty, empty, [], False)


def test_background_rejects_mining_and_overlap():
    tile = box(0, 0, 1280, 1280)
    state = box(-3000, -3000, 4000, 4000)
    candidate = STRtree([box(20, 20, 25, 25)])
    assert pilot.blockers(tile, state, STRtree([]), candidate, [tile], True) == [
        "PATCH_OVERLAP", "MAUS_OR_PROJECT_MINING_EXCLUSION"]


def test_pair_candidates_require_disjoint_and_stable():
    a = ({"patch_id":"a"}, box(0,0,10,10))
    b = ({"patch_id":"b"}, box(9,0,19,10))
    c = ({"patch_id":"c"}, box(20,0,30,10))
    assert pilot.pair_candidates([a,b]) == (None, [])
    chosen, remaining = pilot.pair_candidates([a,b,c])
    assert remaining and all(not chosen[1].intersects(item[1]) for item in remaining)
    assert (chosen,remaining) == pilot.pair_candidates([c,b,a])


def test_authentication_rejects_mutation(tmp_path):
    p=tmp_path/"proposal.json"
    original=b'{"groups":[]}'
    p.write_bytes(original)
    sha=pilot.digest(original)
    assert pilot.authenticated(p,sha)=={"groups":[]}
    p.write_bytes(original+b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        pilot.authenticated(p,sha)
