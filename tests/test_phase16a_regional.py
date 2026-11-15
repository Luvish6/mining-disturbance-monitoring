import json

import numpy as np
import pytest
import rasterio
import torch
from rasterio.transform import from_origin

from src.phase3.alerts import run
from src.phase3.data import BANDS, BAND_UNITS
from src.phase3.model import SiameseUNet
from src.phase3.regional_inference import NODATA, map_tiles, prepare, write_tile

CRS = "EPSG:32644"


def profile(x=663870):
    return dict(width=9, height=9, crs=CRS, transform=from_origin(x, 2470800, 30, 30))


class FixedForest:
    """Deterministic RF interface fixture with six signed/terrain features."""
    classes_ = [0, 1]

    def predict_proba(self, values):
        assert values.shape[1] == 6
        return np.tile([.1, .9], (len(values), 1))


@pytest.mark.parametrize("family", ["siamese", "rf"])
def test_tiled_synthetic_models_and_alert_gate(tmp_path, family):
    source, mapped = (tmp_path / name for name in ("features.tif", "map.tif"))
    values = np.ones((14, 9, 9), dtype="float32")
    values[8:12] = 0
    values[:, 0, 0] = NODATA
    write_tile(source, profile(), BANDS, values, dict(data_kind="synthetic"), BAND_UNITS)
    if family == "siamese":
        model = SiameseUNet(width=2).eval()
        with torch.no_grad():
            for param in model.parameters():
                param.zero_()
            model.head.bias.fill_(2)
    else:
        model = FixedForest()
    map_tiles(source, mapped, model, family=family, model_kind="synthetic", model_sha256="test-fixture",
              crs=CRS, stats=dict(mean=[0]*4, std=[1]*4), tile_size=4)
    with rasterio.open(mapped) as src:
        assert src.transform == profile()["transform"] and src.crs.to_epsg() == 32644
        assert src.read(1)[0, 0] == NODATA
        assert src.read(3).sum() == 80
        assert (src.read(1)[src.read(3) == 1] > .5).all()
    spec = tmp_path/"alerts-input.json"
    spec.write_text(json.dumps(dict(observations=[dict(
        raster=mapped.name, region_id="synthetic-fixture", before_date="2024-01-01",
        after_date="2025-01-01", model_validation="VALIDATED")])))
    result = run(spec, tmp_path/"alerts")
    [feature] = result["data"]["features"]
    assert feature["properties"]["status"] == "NOT_VALIDATED"
    assert feature["properties"]["cells"] == 80


def test_missing_bands_invalid_origin_and_real_synthetic_mix(tmp_path):
    target = tmp_path/"map.tif"
    for name, bands, units, x, kind, message in (
        ("missing", BANDS[:-1], BAND_UNITS[:-1], 663870, "synthetic", "14-band"),
        ("offset", BANDS, BAND_UNITS, 663871, "synthetic", "lattice"),
        ("real", BANDS, BAND_UNITS, 663870, "real", "domains differ"),
    ):
        src = tmp_path/f"{name}.tif"
        write_tile(src, profile(x), bands, np.zeros((len(bands), 9, 9), dtype="float32"),
                   dict(data_kind=kind), units)
        with pytest.raises(ValueError, match=message):
            map_tiles(src, target, FixedForest(), family="rf", model_kind="synthetic",
                      model_sha256="test-fixture", crs=CRS)
    assert not target.exists()


def test_prepares_cached_bands_without_changing_src_mask(tmp_path):
    source, terrain, target = (tmp_path / name for name in ("source.tif", "terrain.tif", "ready.tif"))
    names = tuple(f"{name.split('_')[1]}_{name.split('_')[0]}" for name in BANDS[:8])
    values = np.ones((13, 9, 9), dtype="float32")
    values[8:12] = 0
    values[:12, 0, 0] = NODATA
    values[12, 0, 0] = 0
    write_tile(source, profile(), (*names, *BANDS[8:12], "common_valid"), values, {})
    write_tile(terrain, profile(), BANDS[-2:], np.ones((2, 9, 9), dtype="float32"), {})
    with rasterio.open(source) as src:
        bounds = tuple(src.bounds)
    metadata = dict(region_id="fixture", crs=CRS, bounds=bounds, source_receipt_sha256="fixture",
                    scene_sources=[{"id": "fixture"}], windows=[["2023-11-01", "2024-04-01"],
                                                               ["2024-11-01", "2025-04-01"]])
    report = prepare(source, terrain, metadata, target)
    assert report["common_cells"] == 80 and report["status"] == "INPUT_READY_NO_MODEL"
    with rasterio.open(target) as src:
        assert src.descriptions == BANDS
        assert src.read(1, masked=True).mask[0, 0]
