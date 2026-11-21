import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts import phase24b_india_screening as m

NAMES = m.DELTAS + m.COUNTS + ("common_valid",)


def tile(path, dndvi=-0.4):
    data = np.zeros((len(NAMES), 32, 32), "float32")
    data[NAMES.index("dVH")] = -1.0
    data[NAMES.index("dNDVI")] = 0.0
    data[NAMES.index("dNDVI"), :4] = dndvi
    for c in m.COUNTS:
        data[NAMES.index(c)] = 5
    data[NAMES.index("common_valid")] = 1
    data[NAMES.index("common_valid"), -1] = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", width=32, height=32, count=len(NAMES), dtype="float32",
                       crs="EPSG:32644", transform=from_origin(0, 960, 30, 30), nodata=-9999) as dst:
        dst.write(data)
        dst.descriptions = NAMES


def test_shipped_config_is_valid_and_has_no_coordinates():
    cfg, aois = m.load_config()
    assert len(aois) == 6 and len({a["id"] for a in aois}) == 6
    assert all("anchor" not in a for a in aois)
    assert cfg["budget"]["max_requests_per_run"] <= 20


def test_config_rejects_duplicates_and_ambiguous_anchor(tmp_path):
    base = dict(version="t", seasons={}, tile_cells=32, cell_m=30, budget={})
    for aois in ([{"id": "a", "anchor": [85, 21]}, {"id": "a", "anchor": [85, 21]}],
                 [{"id": "a", "anchor": [85, 21], "anchor_from": "phase11c"}]):
        p = tmp_path / "c.json"
        p.write_text(json.dumps(dict(base, regions=[dict(region="r", state="s", aois=aois)])))
        with pytest.raises(ValueError):
            m.load_config(p)


def test_resolve_rejects_anchor_outside_india():
    with pytest.raises(ValueError):
        m.resolve(dict(id="x", anchor=[120, 25]), [])
    assert m.resolve(dict(id="x", anchor=[85, 21]), [])["anchor"] == [85, 21]


def test_summary_statistics_use_common_valid_cells_only(tmp_path):
    p = tmp_path / "t.tif"
    tile(p)
    s = m.summarise_tile(p)
    assert s["common_cells"] == 32 * 31
    assert s["changes"]["dVH"]["median"] == -1.0
    assert s["ndvi_loss_fraction"] == round(4 * 32 / (32 * 31), 4)
    assert s["ndvi_loss_and_vh_drop_fraction"] == s["ndvi_loss_fraction"]


def test_plan_counts_missing_tiles_without_earth_engine(monkeypatch):
    cfg = dict(budget=dict(requests_per_aoi_estimate=3, bytes_per_aoi_estimate=10,
                           max_requests_per_run=5, max_response_bytes_per_run=100))
    monkeypatch.setattr(m, "tile_path", lambda i: None)
    r = m.plan(cfg, [dict(id="a", state="s", region="r"), dict(id="b", state="s", region="r")])
    assert r["missing"] == 2 and r["estimated_requests"] == 6 and not r["within_budget"]


def test_summarise_checkpoints_resume_and_never_claims_detections(tmp_path, monkeypatch):
    p = tmp_path / "tiles" / "a" / "tile.tif"
    tile(p)
    monkeypatch.setattr(m, "tile_path", lambda i: p if i == "a" else None)
    monkeypatch.chdir(tmp_path)
    cfg = dict(version="t", seasons={})
    aois = [dict(id="a", state="Odisha", region="r"), dict(id="b", state="Odisha", region="r")]
    r = m.summarise(cfg, aois, "cfg1", tmp_path / "out")
    assert r["claims"]["verified_detections"] == 0 and r["claims"]["attribution"] == "UNKNOWN"
    assert r["coverage"]["national_coverage"] is False and r["coverage"]["aois_screened"] == 1
    assert r["skipped"][0]["id"] == "b"
    assert r["sites"][0]["status"] == "UNKNOWN" and r["sites"][0]["tier"] == "UNVERIFIED_LEAD"
    ck = tmp_path / "out" / "a.json"
    marked = json.loads(ck.read_text())
    marked["marker"] = 1
    ck.write_text(json.dumps(marked))
    assert m.summarise(cfg, aois, "cfg1", tmp_path / "out")["sites"][0].get("marker") == 1  # resumed
    assert "marker" not in m.summarise(cfg, aois, "cfg2", tmp_path / "out")["sites"][0]  # config changed


def test_execute_is_noop_when_all_tiles_cached(monkeypatch, tmp_path):
    monkeypatch.setattr(m, "tile_path", lambda i: tmp_path)
    r = m.execute(dict(budget={}), [dict(id="a")], 5, tmp_path / "out")
    assert r["requests"] == 0 and not (tmp_path / "out").exists()


def test_committed_report_matches_claims_and_omits_coordinates():
    if not m.REPORT.is_file():
        pytest.skip("report not generated")
    r = json.loads(m.REPORT.read_text())
    assert r["claims"]["verified_detections"] == 0 and r["coverage"]["national_coverage"] is False
    text = m.REPORT.read_text()
    assert "anchor" not in text and "latitude" not in text
    assert all(s["status"] == "UNKNOWN" for s in r["sites"])
