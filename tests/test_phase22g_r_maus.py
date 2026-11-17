import pytest
from shapely.geometry import box
from shapely.strtree import STRtree

from scripts import phase22g_r_maus as recovery


def test_positive_coverage_is_pixel_center_only():
    spec = recovery.grid_spec(500000, 2400000, 32644, "slot")
    left, bottom, _, _ = spec["bounds"]
    assert recovery.positive_support(spec,[box(left,bottom,left+4,bottom+10)]) == 0
    assert recovery.positive_support(spec,[box(left,bottom,left+6,bottom+10)]) == 1
    assert recovery.positive_support(spec,[]) == 0


def test_center_enumeration_stays_inside_polygon_and_grid():
    spec = recovery.grid_spec(500000,2400000,32644,"slot")
    group = recovery.reproject(box(499985,2399985,500015,2400015),spec["crs"],4326)
    candidates = recovery.centers([group])
    assert len(candidates)==9
    assert (32644,500000,2400000) in candidates
    assert all(x%10==y%10==0 for _,x,y in candidates)
    assert recovery.centers([group,group]) == candidates


def test_relocation_exhausts_group_when_center_guard_cannot_pass():
    spec = recovery.grid_spec(500000,2400000,32644,"slot")
    group = recovery.reproject(box(499985,2399985,500015,2400015),spec["crs"],4326)
    pos, pair, result = recovery.relocate(spec,[group],recovery.metric(spec),STRtree([]),
                                          STRtree([]),[])
    assert pos is None and pair is None
    assert result["exhausted"] and result["total_centers"] == 9
    assert result["rejection_counts"]["ADM1_CENTER_GUARD_NECESSARY"] == 9
