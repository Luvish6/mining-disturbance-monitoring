import numpy as np

from scripts.phase23a_linkage import downstream_stations, grid, trace


def test_trace_follows_d8_and_reports_failures():
    d = np.full((5, 5), 4, np.uint8)  # all south
    status, path = trace(d, 0, 2, lambda r, c: ("SNAPPED", [0]) if r == 3 else None)
    assert status[0] == "SNAPPED" and path[-1] == (3, 2) and len(path) == 4
    assert trace(d, 0, 2, lambda r, c: None)[0] == "LEFT_BBOX"
    d[1, 2] = 0
    assert trace(d, 0, 2, lambda r, c: None)[0] == "SINK_OR_NODATA"
    loop = np.array([[1, 4], [64, 16]], np.uint8)  # E, S, W, N cycle
    assert trace(loop, 0, 0, lambda r, c: None, max_steps=20)[0] == "MAX_STEPS"


def test_downstream_station_chain():
    nd = {1: 2, 2: 3, 3: 4, 4: 0}
    assert downstream_stations(1, nd, {3: "B", 4: "C"}) == ["B", "C"]
    assert downstream_stations(4, nd, {3: "B"}) == []


def test_grid_is_snapped_to_3_arcsec():
    g = grid()
    assert abs(g["west"] * 1200 - round(g["west"] * 1200)) < 1e-6 and g["rows"] > 900 and g["cols"] > 1000
