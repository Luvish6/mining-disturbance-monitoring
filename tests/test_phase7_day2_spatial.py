import numpy as np
import pytest
from scipy.ndimage import label

from scripts import phase7_day2_spatial as day2


def test_signed_thresholds_and_directional_unions():
    a = dict(dVV=np.array([[-1., 1., -3., 0.]]), dVH=np.zeros((1,4)),
             dNDVI=np.array([[-.03, -.05, -.2, 0.]]), dNDTI=np.array([[0., 0., 0., .09]]))
    valid = np.array([[True, True, False, True]])
    low = day2.masks(a, valid, *day2.LEVELS["low"])
    high = day2.masks(a, valid, *day2.LEVELS["high"])
    assert low["joint"].tolist() == [[True, False, False, False]]
    assert low["dVV_up"].tolist() == [[False, True, False, False]]
    assert high["optical"].tolist() == [[False, False, False, True]]
    assert all(not (high[k] & ~low[k]).any() for k in low)


def test_perimeter_includes_hole_and_boundary_and_uses_grid_centres():
    mask = np.ones((3,3), dtype=bool)
    mask[1,1] = False
    result = day2.component_geometry(mask, (300000,2700000,300090,2700090))
    assert result == dict(cells=8, area_m2=7200, perimeter_m=480, centroid_easting_m=300045.,
                          centroid_northing_m=2700045., touches_tile_edge=True)


def test_overlap_denominator_and_undefined_cases():
    a = np.array([True, True, False, False, True])
    b = np.array([True, False, True, False, True])
    valid = np.array([True, True, True, True, False])
    result = day2.overlap(a,b,valid)
    assert [result[k] for k in ("joint","radar_only","optical_only","neither")] == [1,1,1,1]
    assert result["jaccard"] == pytest.approx(1/3)
    assert result["optical_given_radar"] == result["radar_given_optical"] == .5
    assert day2.overlap(a,b,np.zeros(5,dtype=bool))["jaccard"] is None


def test_four_neighbour_fragment_retention():
    high = np.eye(4, dtype=bool)
    labeled, count = label(high)
    assert count == 4
    assert day2.fragment_counts(np.ones_like(high), labeled) == (4,4,1)
    assert day2.persistence(16,1) == "threshold_sensitive"
    assert day2.persistence(16,4) == "persistent"
    assert day2.persistence(17,4) == "threshold_sensitive"
    assert day2.persistence(3,3) == "below_reporting_floor"


def test_nested_component_lineage_and_context():
    arrays = {k:np.zeros((4,4)) for k in day2.base.CHANGE}
    arrays["dVV"][:] = -1
    arrays["dNDVI"][:] = -.03
    arrays["dVV"][0:2,0:2] = -3
    arrays["dNDVI"][0:2,0:2] = -.09
    arrays.update(elevation=np.full((4,4),100), slope=np.full((4,4),20),
                  optical_min=np.full((4,4),15))
    result,_,_ = day2.analyze(dict(arrays=arrays, common=np.ones((4,4),dtype=bool),
        id="fixture", district="fixture", split="validation", block="1:2", bounds=(0,0,120,120)))
    row, = [r for r in result["threshold_sensitivity"] if r["pattern"] == "joint"]
    assert row["cells"] == 16 and row["high_largest"] == 4 and row["high_largest_fraction"] == .25
    assert row["persistence"] == "persistent" and row["median_slope_deg"] == 20
