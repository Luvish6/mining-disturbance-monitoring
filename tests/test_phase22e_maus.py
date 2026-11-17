import json

import numpy as np
import pytest
from shapely.geometry import box
from shapely.strtree import STRtree

from scripts import phase22e_maus as planner
from scripts import phase22e_maus_export as exporter


def test_pixel_center_and_unknown_masking():
    affine = [10, 0, 0, 0, -10, 20]
    valid = np.array([[True, True], [True, False]])
    positive = planner.label_mask([box(0, 10, 9, 20), box(10, 10, 14, 20)], affine, valid)
    assert positive.tolist() == [[1, 255], [255, 255]]
    assert planner.label_mask([], affine, valid, True).tolist() == [[0, 0], [0, 255]]


def test_full_geometry_guard_and_all_split_exclusions():
    window = box(0, 0, 1280, 1280)
    broad = box(-3000, -3000, 4000, 4000)
    empty = STRtree([])
    assert planner.safe_window(window, broad, empty, empty, [], True)
    assert not planner.safe_window(window, box(-100, -100, 1380, 1380), empty, empty, [], True)
    nearby = STRtree([box(3300, 0, 4000, 500)])
    assert not planner.safe_window(window, broad, nearby, empty, [], True)
    assert not planner.safe_window(window, broad, empty, STRtree([box(5, 5, 20, 20)]), [], True)
    assert not planner.safe_window(window, broad, empty, empty, [box(1279, 0, 1400, 100)], False)


def test_proxy_math_and_tie_break_inputs():
    assert planner.score([.3, .3, .1], "sand_riverbed") == pytest.approx(.2)
    assert planner.score([.3, .3, .1], "bare_soil") == pytest.approx(-.2)
    assert planner.score([1., 0., 0.], "exposed_rock") is None
    assert planner.stable("tile-id") == planner.stable("tile-id")


def test_frozen_plan_rejects_test_and_modified_split(tmp_path, monkeypatch):
    root = tmp_path / "original"
    root.mkdir()
    split = dict(groups={"a": dict(split="train", ids=[1], states=["Goa"]), "t": dict(split="test", ids=[2])})
    payload = json.dumps(split).encode()
    (root / "split.json").write_bytes(payload)
    sha = planner.digest(payload)
    monkeypatch.setattr("scripts.phase22c_maus.SPLIT_SHA", sha)
    proto = tmp_path / "protocol.md"
    proto.write_text("amendment")
    monkeypatch.setattr(exporter, "PROTO", proto)
    plan = dict(split_sha_before=sha, split_sha_after=sha, test_sealed=True,
                protocol_sha256=planner.digest(proto.read_bytes()), max_download_bytes=planner.MAX_TIFF,
                patches=[dict(patch_id="a-pos", group_id="a", split="train", label_source_fids=[1], state="Goa", weak_label_type="WEAK_UNVERIFIED_POSITIVE", negative_stratum=None)])
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    assert exporter.read_plan(root, tmp_path)[0] == plan
    plan["patches"] = [dict(patch_id="t-pos", group_id="t", split="test", label_source_fids=[2])]
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="TEST"):
        exporter.read_plan(root, tmp_path)
    (root / "split.json").write_bytes(payload+b" ")
    with pytest.raises(ValueError, match="identical"):
        exporter.read_plan(root, tmp_path)


def test_download_requests_and_validates_128_cell_grid(tmp_path, monkeypatch):
    from affine import Affine
    from rasterio.io import MemoryFile

    class Graph:
        def bandNames(self):
            return self

        def getInfo(self):
            return list(planner.BANDS)

        def toFloat(self):
            return self

        def unmask(self, *_):
            return self

        def getDownloadURL(self, params):
            assert params["dimensions"] == [128, 128]
            assert params["crs_transform"] == [10, 0, 270000, 0, -10, 2350000]
            return "fixture"

    row = {"crs": 32645, "affine": [10, 0, 270000, 0, -10, 2350000]}

    def tiff(size):
        with MemoryFile() as memory:
            with memory.open(driver="GTiff", width=size, height=size, count=4, dtype="float32",
                             crs="EPSG:32645", transform=Affine(*row["affine"])) as ds:
                ds.write(np.zeros((4, size, size), dtype="float32"))
            return memory.read()

    monkeypatch.setattr(exporter, "fetch", lambda *_: tiff(64))
    with pytest.raises(ValueError, match="128-cell"):
        exporter.download(Graph(), planner.BANDS, row, tmp_path / "bad.tif")
    assert not (tmp_path / "bad.tif").exists()
    monkeypatch.setattr(exporter, "fetch", lambda *_: tiff(128))
    arrays, _ = exporter.download(Graph(), planner.BANDS, row, tmp_path / "good.tif")
    assert arrays["B3"].shape == (128, 128)
