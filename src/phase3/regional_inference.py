"""Regional inference without changing supervised Meghalaya dataset admission."""
import argparse
from datetime import date
import json
from pathlib import Path

import numpy as np
from pyproj import CRS
import rasterio
from rasterio.windows import Window
import torch

from .alerts import MAX_PIXELS
from .data import BANDS, BAND_UNITS, TEMPORAL, digest, normalized, read_manifest
from .model import SiameseUNet
from .rf_experiments import indices, load_model

NODATA = -9999
PREDICTION_BANDS = ("disturbance_probability", "disturbance_binary", "common_valid", "predictive_entropy")


def check_grid(src, crs):
    grid = src.transform
    projected = CRS.from_user_input(crs)
    if (not projected.is_projected or any(a.unit_conversion_factor != 1 for a in projected.axis_info)
            or src.crs != projected or (grid.a, grid.b, grid.d, grid.e) != (30, 0, 0, -30)
            or not all(np.isfinite(tuple(grid))) or grid.c % 30 or grid.f % 30
            or not 0 < src.width*src.height <= MAX_PIXELS):
        raise ValueError("Expected the configured north-up 30 m metre lattice")


def read_values(src):
    data = src.read(out_dtype="float32", masked=True).filled(np.nan)
    return np.where(np.isfinite(data), data, NODATA).astype("float32")


def write_tile(path, profile, bands, data, tags, units=None):
    if path.exists():
        raise ValueError("Choose a new output raster")
    with rasterio.open(path, "w", **dict(profile, driver="GTiff", count=len(bands),
                       dtype="float32", nodata=NODATA, compress="deflate")) as dst:
        dst.write(data)
        dst.descriptions = bands
        if units:
            dst.units = units
        dst.update_tags(**tags)


def validate_values(values):
    if np.any((values[13] != NODATA) & ((values[13] < 0) | (values[13] > 90))):
        raise ValueError("Slope must be in degrees")
    for before, after, delta in zip(values[:4], values[4:8], values[8:12], strict=True):
        valid = (before != NODATA) & (after != NODATA)
        if not np.array_equal(delta != NODATA, valid) or not np.allclose(
            delta[valid], (after-before)[valid], atol=1e-5, rtol=1e-5
        ):
            raise ValueError("Signed change or temporal masks disagree")


def prepare(cache, terrain, metadata, target):
    """Reorder Phase 11C bands and add exactly aligned terrain without resampling."""
    windows = metadata["windows"]
    if len(windows) != 2 or len(windows[0]) != 2 or len(windows[1]) != 2:
        raise ValueError("Two dated windows required")
    dates = [date.fromisoformat(d) for dates in windows for d in dates]
    if not dates[0] < dates[1] <= dates[2] < dates[3] or not metadata["region_id"]:
        raise ValueError("Invalid observation windows or AOI")
    if not metadata.get("source_receipt_sha256") or not metadata.get("scene_sources"):
        raise ValueError("Source scenes and receipt required")
    requested = tuple(f"{band}_{season}" for season in ("before", "after") for band in TEMPORAL) + BANDS[8:12]
    with rasterio.open(cache) as src, rasterio.open(terrain) as dem:
        for dataset in (src, dem):
            check_grid(dataset, metadata["crs"])
        if (src.transform, src.shape) != (dem.transform, dem.shape) or tuple(src.bounds) != tuple(metadata["bounds"]):
            raise ValueError("Source and terrain must share the declared AOI grid")
        if (any(src.descriptions.count(band) != 1 for band in (*requested, "common_valid"))
                or dem.descriptions != ("elevation", "slope")):
            raise ValueError("Missing or ambiguous required feature bands")
        data = read_values(src)
        stack = np.concatenate((data[[src.descriptions.index(b) for b in requested]], read_values(dem)))
        observed = data[src.descriptions.index("common_valid")]
        if not np.isin(observed, [0, 1]).all() or not np.array_equal(observed == 1, (stack[:12] != NODATA).all(0)):
            raise ValueError("Cached common-valid mask disagrees with feature support")
        validate_values(stack)
        common = (stack != NODATA).all(0)
        provenance = dict(metadata, cache_sha256=digest(cache), terrain_sha256=digest(terrain),
                          transform=list(src.transform)[:6], shape=list(src.shape), data_kind="real",
                          common_cells=int(common.sum()), grid_cells=int(common.size),
                          coverage=float(common.mean()), band_valid_cells=dict(zip(BANDS, (stack != NODATA).sum((1, 2)).tolist())))
        write_tile(target, src.profile, BANDS, stack,
                   dict(data_kind="real", provenance=json.dumps(provenance)), BAND_UNITS)
    return dict(provenance, raster_sha256=digest(target), status="INPUT_READY_NO_MODEL")


def predict_tile(values, model, family, stats=None, experiment=None):
    valid = values != NODATA
    common = valid.all(0) & np.isfinite(values).all(0)
    scores = np.full(common.shape, NODATA, dtype="float32")
    if not common.any():
        return scores, common
    if family == "siamese":
        if (stats is None or any(np.shape(stats[k]) != (4,) or not np.isfinite(stats[k]).all()
                                 for k in ("mean", "std")) or np.min(stats["std"]) <= 0):
            raise ValueError("Expected four train-only normalization statistics")
        a, b = normalized(dict(before=values[:4], after=values[4:8], valid=valid), stats)
        pad = [(0, 0), *( (0, max(0, 4-n)) for n in common.shape )]
        with torch.inference_mode():
            result = model(*(torch.from_numpy(np.pad(v, pad))[None] for v in (a, b))).sigmoid()[0, 0].numpy()
        scores[common] = result[:common.shape[0], :common.shape[1]][common]
    elif family == "rf":
        features = values[8:] if experiment is None else values[8:][indices(experiment)]
        scores[common] = model.predict_proba(features[:, common].T)[:, list(model.classes_).index(1)]
    else:
        raise ValueError("Unknown model family")
    if not np.all(np.isfinite(scores[common]) & (scores[common] >= 0) & (scores[common] <= 1)):
        raise ValueError("Invalid model scores")
    return scores, common


def map_tiles(source, output, model, *, family, model_kind, model_sha256, crs,
              stats=None, experiment=None, tile_size=64, threshold=.5):
    if not 4 <= tile_size <= 256 or not 0 < threshold < 1:
        raise ValueError("Invalid tile size or screening threshold")
    with rasterio.open(source) as src:
        check_grid(src, crs)
        if src.descriptions != BANDS or src.units != BAND_UNITS or src.nodata != NODATA:
            raise ValueError("Expected exact 14-band model schema, units and NoData")
        if model_kind not in ("synthetic", "real") or src.tags().get("data_kind") != model_kind:
            raise ValueError("Model and raster domains differ")
        provenance = json.loads(src.tags().get("provenance", "{}"))
        if model_kind == "real" and (not provenance.get("scene_sources") or not provenance.get("region_id")):
            raise ValueError("Missing regional input provenance")
        if output.exists():
            raise ValueError("Choose a new output raster")
        profile = dict(src.profile, count=4, dtype="float32", compress="deflate")
        with rasterio.open(output, "w", **profile) as dst:
            dst.descriptions = PREDICTION_BANDS
            dst.update_tags(data_kind=model_kind, model_sha256=model_sha256, experiment=experiment or family,
                            feature_sha256=digest(source), region_id=provenance.get("region_id", ""),
                            windows=json.dumps(provenance.get("windows")), model_validation="NOT_VALIDATED",
                            tile_size=tile_size)
            for y in range(0, src.height, tile_size):
                for x in range(0, src.width, tile_size):
                    window = Window(x, y, min(tile_size, src.width-x), min(tile_size, src.height-y))
                    values = src.read(window=window, masked=True).filled(NODATA)
                    scores, valid = predict_tile(values, model, family, stats, experiment)
                    q = np.clip(scores[valid].astype(float), 1e-7, 1-1e-7)
                    entropy = np.full(scores.shape, NODATA, dtype="float32")
                    entropy[valid] = -(q*np.log2(q)+(1-q)*np.log2(1-q))
                    dst.write(np.stack([scores, np.where(valid, scores >= threshold, NODATA),
                                        valid, entropy]).astype("float32"), window=window)


def map_reviewed(source, output, directory, manifest, approval, family):
    """Use a trusted local Indian run with explicit approval for this region."""
    dataset = read_manifest(manifest, require_splits=True)
    meta = json.loads((directory/"run.json").read_text(encoding="utf-8"))
    with rasterio.open(source) as src:
        provenance = json.loads(src.tags()["provenance"])
    artifact = directory / ("best.pt" if family == "siamese" else meta["experiments"][meta["selected_experiment"]]["artifact"])
    model_hash = digest(artifact)
    if (dataset["data_kind"] != "real" or meta["data_kind"] != "real"
            or meta["manifest_sha256"] != digest(manifest)
            or approval != dict(region_id=provenance["region_id"], model_sha256=model_hash,
                                regional_inference_approved=True)):
        raise ValueError("A region-approved real Indian checkpoint is required")
    if family == "siamese":
        state = torch.load(artifact, map_location="cpu", weights_only=True)
        if state["metadata"] != meta:
            raise ValueError("Checkpoint metadata mismatch")
        model = SiameseUNet(width=meta["width"]).eval()
        model.load_state_dict(state["state_dict"])
        experiment = None
    elif family == "rf":
        experiment = meta["selected_experiment"]
        model, _ = load_model(directory, experiment)
    else:
        raise ValueError("Unknown model family")
    map_tiles(source, output, model, family=family, model_kind="real", model_sha256=model_hash,
              crs=provenance["crs"], stats=meta.get("stats"), experiment=experiment, threshold=meta["threshold"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "output", "directory", "manifest", "approval"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--family", choices=("siamese", "rf"), required=True)
    args = vars(parser.parse_args())
    args["approval"] = json.loads(args["approval"].read_bytes())
    map_reviewed(**args)


if __name__ == "__main__":
    main()
