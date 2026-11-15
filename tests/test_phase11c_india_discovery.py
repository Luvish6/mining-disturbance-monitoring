from scripts.phase11c_india_discovery import SIZE, candidates, grid, priority


def test_coalfield_grouping_and_discovery_status(tmp_path):
    rows = list(candidates(tmp_path))
    assert len(rows) == len({row["id"] for row in rows}) == 5
    assert rows[0]["group"] == rows[1]["group"]
    for row in rows:
        assert row["status"] == "UNKNOWN" and row["split"] is None
        assert row["polygon"] is None and row["source"].startswith("https://")
        x, y = row["anchor"]
        w, s, e, n = row["published_bounds"]
        assert w < x < e and s < y < n


def test_local_projection_and_coverage_order():
    crs, affine, bounds = grid((82.6, 22.3))
    assert crs == "EPSG:32644"
    assert affine.a == 30 and affine.e == -30
    assert bounds[2] - bounds[0] == SIZE * 30
    items = [dict(id="a", screen={}), dict(id="z", screen={"common": 18})]
    assert sorted(items, key=priority)[0]["id"] == "z"
