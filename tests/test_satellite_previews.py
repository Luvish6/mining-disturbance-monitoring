from hashlib import sha256
import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts import satellite_previews as previews


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def tiles(tmp_path):
    nodata = -9999
    inventory_items = []
    receipts = {}
    for index, site in enumerate(previews.SITES):
        tile, receipt, inventory = previews.inputs(tmp_path, site)
        tile.parent.mkdir(parents=True)
        receipt.parent.mkdir()
        cards = []
        windows = []
        for season, year in zip(previews.SEASONS, (2023, 2024), strict=True):
            from datetime import datetime, timezone
            utc_ms = int(datetime(year, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)
            cards.append({key: value for sensor in ("s1", "s2") for key, value in
                          ((f"{sensor}_ids", [f"{site}-{sensor}-{season}"]),
                           (f"{sensor}_time_start_ms", [utc_ms]))})
            windows.append(dict(start=f"{year}-11-01", end=f"{year+1}-04-01"))
        inventory_items.append(dict(id=site, windows=windows, screen=dict(state="screened", sources=cards)))
        names = [f"{b}_{s}" for s in previews.SEASONS for b in (*previews.OPTICAL, "VV", "VH")]
        affine = from_origin(600000 + 30 * index, 2400000, 30, 30)
        with rasterio.open(tile, "w", driver="GTiff", count=len(names), height=2, width=2,
                           dtype="float32", crs="EPSG:32644", transform=affine, nodata=nodata) as grid:
            for n, name in enumerate(names, 1):
                v = (-30 + n + index) if name.startswith("V") else .025 * (n + index)
                grid.write(np.array([[v, nodata], [v, v]], dtype="float32"), n)
                grid.set_band_description(n, name)
            bounds = list(grid.bounds)
        receipts[receipt] = dict(region_id=site, cache_sha256=previews.digest(tile),
                                 scene_sources=cards, windows=[[w["start"], w["end"]] for w in windows],
                                 crs="EPSG:32644", transform=list(affine)[:6], shape=[2, 2], bounds=bounds)
    write_json(inventory, inventory_items)
    for path, r in receipts.items():
        write_json(path, dict(r, source_receipt_sha256=previews.digest(inventory)))
    for site in previews.SITES:
        previews.build(tmp_path, tmp_path / site, site)
    return tmp_path


def test_correct_source_and_deterministic_pngs(tiles):
    site = "gevra"
    folder = tiles / site
    digest, verified = previews.verify(tiles, folder, site)
    metadata = json.loads((folder/"manifest.json").read_bytes())
    opt = metadata["previews"]["optical_before.png"]
    assert opt["site"] == site and opt["season"] == "before"
    assert opt["render"]["bands"] == ["B8_before", "B4_before", "B3_before"]
    assert opt["scenes"][0]["acquired_utc"] == "2023-11-01T00:00:00+00:00"
    assert opt["png_sha256"] == sha256(verified["optical_before.png"]).hexdigest()
    raster, _, _ = previews.inputs(tiles, site)
    assert metadata["source_sha256"] == previews.digest(raster)
    pixels = previews.rgba(verified["optical_before.png"])
    assert pixels[0, 0].tolist() == [18, 36, 54, 255]
    assert pixels[0, 1].tolist() == [0, 0, 0, 0]
    second = tiles/"rerender"
    previews.build(tiles, second, site)
    assert previews.verify(tiles, second, site) == (digest, verified)


@pytest.mark.parametrize("kind", ["wrong site", "swapped season", "altered pixels"])
def test_reject_same_dimensions(tiles, kind):
    site = "gevra"
    target = tiles/site/"optical_before.png"
    if kind == "wrong site":
        content = (tiles/"bhubaneswari"/target.name).read_bytes()
    elif kind == "swapped season":
        content = (tiles/site/"optical_after.png").read_bytes()
    else:
        pixels = previews.rgba(target.read_bytes())
        pixels[0, 0, 0] += 1
        content = previews.png(pixels)
    assert previews.rgba(content).shape == (2, 2, 4)
    target.write_bytes(content)
    with pytest.raises(ValueError, match="PNG pixels or hash"):
        previews.verify(tiles, tiles/site, site)


@pytest.mark.parametrize("field,value", [("crs", "EPSG:32645"), ("transform", [30, 0, 0, 0, -30, 0])])
def test_reject_changed_grid_metadata(tiles, field, value):
    site = "gevra"
    manifest = tiles/site/"manifest.json"
    data = json.loads(manifest.read_bytes())
    data["grid"][field] = value
    write_json(manifest, data)
    with pytest.raises(ValueError, match="frozen raster, grid"):
        previews.verify(tiles, tiles/site, site)


@pytest.mark.parametrize("index", [0, 1, 2])
def test_missing_source_or_receipt_fails_closed(tiles, index):
    site = "gevra"
    previews.inputs(tiles, site)[index].unlink()
    with pytest.raises(FileNotFoundError):
        previews.verify(tiles, tiles/site, site)
