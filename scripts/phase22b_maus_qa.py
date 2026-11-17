"""Export at most two frozen development windows for Phase 22B QA."""

import json

from affine import Affine
import ee
import numpy as np
from PIL import Image
import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom

from config.phase2_settings import Phase2Config
from config.settings import Season
from scripts.phase22b_maus import BANDS, SIZE, digest, fetch, write_json
from src.gee_setup import initialize
from src.optical_preprocessing import collections
from src.sar_preprocessing import choose_orbit, collection, seasonal

WINDOW = Season("2019-Q1", "2019-01-01", "2019-04-01")
NODATA = -9999


def read_grid(path, site):
    with rasterio.open(path) as ds:
        if (ds.width != SIZE or ds.height != SIZE or ds.crs is None
                or ds.crs.to_epsg() != site["crs"]
                or ds.transform != Affine(*site["affine"]) or ds.descriptions != BANDS
                or ds.dtypes != ("float32",) * len(BANDS) or ds.nodata != NODATA):
            raise ValueError("Static raster grid, bands or NoData mismatch")
        cells = ds.read(masked=True)
    values = cells.filled(np.nan)
    counts = values[-2:]
    if not (np.isfinite(counts).all() and (counts >= 0).all()
            and np.equal(counts, np.floor(counts)).all()):
        raise ValueError("Invalid observation counts")
    supported = counts >= 2
    if not np.array_equal(np.isfinite(values[:3]).all(axis=0), supported[0]):
        raise ValueError("Optical support disagrees with exported observations")
    if not np.array_equal(np.isfinite(values[3:5]).all(axis=0), supported[1]):
        raise ValueError("SAR support disagrees with exported observations")
    return values, supported.all(axis=0)


def development_sites(root):
    split_bytes = (root / "split.json").read_bytes()
    roster = json.loads(split_bytes)["groups"]
    manifest = json.loads((root / "development.json").read_bytes())
    if manifest["split_sha256"] != digest(split_bytes):
        raise ValueError("Development split hash mismatch")
    if not any(group["split"] == "test" for group in roster.values()):
        raise ValueError("Frozen roster has no sealed TEST group")
    chosen = {}
    for site in manifest["sites"]:
        role = site["split"]
        if role not in {"train", "validation"}:
            raise ValueError("TEST or unknown role in development manifest")
        group = roster[site["group"]]
        if group["split"] != role or site["fid"] not in group["ids"]:
            raise ValueError("Development row does not belong to its frozen split")
        chosen.setdefault(role, site)
    if set(chosen) != {"train", "validation"}:
        raise ValueError("Both development roles must exist")
    return chosen.values()


def observations(images):
    return ee.Dictionary(dict(ids=images.aggregate_array("system:index"),
                         dates_ms=images.aggregate_array("system:time_start")))


def export(site, target):
    crs = f"EPSG:{site['crs']}"
    region = ee.Geometry.Rectangle(site["bounds"], crs, False)
    cfg = Phase2Config(analysis_crs=crs)
    _, optical = collections(region, WINDOW, cfg)
    radar = collection(region, WINDOW, cfg)
    metadata = ee.Dictionary(dict(
        optical=observations(optical),
        orbit_counts=radar.aggregate_histogram("relativeOrbitNumber_start"),
    )).getInfo()
    if len(metadata["optical"]["ids"]) < 2 or not metadata["orbit_counts"]:
        return metadata, None, 0
    orbit = choose_orbit(metadata["orbit_counts"], metadata["orbit_counts"])
    selected = radar.filter(ee.Filter.eq("relativeOrbitNumber_start", orbit))
    metadata["radar"] = observations(selected).getInfo()
    metadata["relative_orbit"] = orbit
    if len(metadata["radar"]["ids"]) < 2:
        return metadata, None, 0

    def optical_scene(image):
        prob = ee.Image(image.get("clouds")).select("probability")
        scl = image.select("SCL")
        rgb = image.select(list(BANDS[:3]))
        valid = (prob.lt(cfg.cloud_probability).And(scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)))
                 .And(image.select("B8A").mask()).And(image.select("B9").mask())
                 .And(rgb.mask().reduce(ee.Reducer.min())))
        return rgb.divide(10000).updateMask(valid)

    stack = optical.map(optical_scene)
    optical_count = stack.select("B3").count().unmask(0).rename("optical_count")
    reflectance = stack.median().updateMask(optical_count.gte(2))
    sar, sar_count = seasonal(radar, orbit, region, cfg)
    image = (reflectance.addBands(sar).addBands(optical_count).addBands(sar_count)
             .select(list(BANDS)).toFloat().unmask(NODATA, False))
    if image.bandNames().getInfo() != list(BANDS):
        raise ValueError("Unexpected Earth Engine graph band order")
    url = image.getDownloadURL(dict(crs=crs, crs_transform=site["affine"],
                                     dimensions=[SIZE, SIZE], format="GEO_TIFF"))
    raw = fetch(url, 2 * 1024**2)
    with target.open("xb") as stream:
        stream.write(raw)
    # Earth Engine files need an explicit local NoData declaration.
    with rasterio.open(target, "r+") as ds:
        if any(ds.descriptions) and ds.descriptions != BANDS:
            raise ValueError("Earth Engine export band descriptions did not match")
        ds.descriptions = BANDS
        ds.nodata = NODATA
    return metadata, digest(raw), len(raw)


def run(root):
    sites = list(development_sites(root))
    overlays = {row["properties"]["fid"]: row["geometry"] for row in
                json.loads((root / "development_overlay.geojson").read_bytes())["features"]}
    initialize()
    output = root / "qa"
    output.mkdir(exist_ok=True)
    for site in sites:
        path = output / f"{site['split']}.tif"
        receipt_path = path.with_suffix(".json")
        if receipt_path.exists():
            existing = json.loads(receipt_path.read_bytes())
            if existing["site"] != site or existing["dates"] != [WINDOW.start, WINDOW.end]:
                raise ValueError("Existing QA receipt is for a different frozen site")
            if existing.get("status") != "INSUFFICIENT_SOURCE_SCENES":
                read_grid(path, site)
                if digest(path.read_bytes()) != existing["tiff_sha256"]:
                    raise ValueError("Existing QA TIFF hash mismatch")
                if digest(path.with_suffix(".png").read_bytes()) != existing["png_sha256"]:
                    raise ValueError("Existing QA preview hash mismatch")
            continue
        metadata, raw_hash, transferred = export(site, path)
        if raw_hash is None:
            receipt = dict(site=site, dates=[WINDOW.start, WINDOW.end], sources=metadata,
                           status="INSUFFICIENT_SOURCE_SCENES", valid_cells=None,
                           reference_labels_admitted=0, input_tiff_bytes=0)
            write_json(path.with_suffix(".json"), receipt)
            print(site["split"], receipt["status"], len(metadata["optical"]["ids"]),
                  metadata["orbit_counts"], flush=True)
            continue
        values, valid = read_grid(path, site)
        footprint = transform_geom("EPSG:4326", f"EPSG:{site['crs']}", overlays[site["fid"]])
        outline = rasterize([(footprint, 1)], out_shape=(SIZE, SIZE),
                            transform=Affine(*site["affine"])).astype(bool)
        color = np.nan_to_num(values[[1, 2, 0]].transpose(1, 2, 0))
        display = (np.clip(color / .3, 0, 1) * 255).astype("uint8")
        display[~np.isfinite(values[:3]).all(axis=0)] = (45, 45, 45)
        interior = outline.copy()
        interior[1:-1, 1:-1] &= (outline[:-2, 1:-1] & outline[2:, 1:-1]
                                  & outline[1:-1, :-2] & outline[1:-1, 2:])
        interior[[0, -1], :] = False
        interior[:, [0, -1]] = False
        display[outline & ~interior] = (255, 190, 0)
        preview = path.with_suffix(".png")
        Image.fromarray(display).save(preview)
        receipt = dict(site=site, dates=[WINDOW.start, WINDOW.end], sources=metadata,
                       collections=["COPERNICUS/S2_SR_HARMONIZED", "COPERNICUS/S2_CLOUD_PROBABILITY",
                                    "COPERNICUS/S1_GRD"],
                       bands=BANDS, valid_cells=int(valid.sum()), total_cells=valid.size,
                       meets_coverage_gate=bool(valid.mean() >= .70),
                       locator_overlay_cells=int(outline.sum()), reference_labels_admitted=0,
                       raw_sha256=raw_hash, input_tiff_bytes=transferred,
                       tiff_sha256=digest(path.read_bytes()), png_sha256=digest(preview.read_bytes()))
        write_json(path.with_suffix(".json"), receipt)
        print(site["split"], receipt["valid_cells"], receipt["meets_coverage_gate"], flush=True)
