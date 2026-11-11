"""Bounded, exploratory Phase 6B feature acquisition. Run from the project root."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

import ee
import matplotlib
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.transform import Affine
import requests
from shapely.geometry import box, shape
from shapely import transform

from config.phase2_settings import Phase2Config
from config.settings import AFTER, BEFORE, DISTRICTS
from src import optical_preprocessing as optical, sar_preprocessing as sar
from src.coverage_diagnostics import COUNT_BANDS, COVERAGE_BANDS, validity_image
from src.gee_setup import initialize
from src.phase3.data import BANDS, digest, save_json
from src.phase3.ee_inputs import paired_graph
from src.phase3.spatial import block_for, partition
from src.study_area import get_study_area

SIZE = 64
STEP = 30
NODATA = -9999
CRS = "EPSG:32646"
CFG = Phase2Config(relative_orbit=77)
SEASONS = (BEFORE, AFTER)
DIAGNOSTICS = COUNT_BANDS + COVERAGE_BANDS
SCHEMA = BANDS + DIAGNOSTICS
PLAN = "phase6a-multitile-v1"
COLLECTIONS = ("COPERNICUS/S1_GRD", "COPERNICUS/S2_SR_HARMONIZED",
               "COPERNICUS/S2_CLOUD_PROBABILITY", "USGS/SRTMGL1_003")
SLOTS = {
    (DISTRICTS[0], "train"): ("slope", True),
    (DISTRICTS[0], "validation"): ("ndvi", True),
    (DISTRICTS[0], "test"): ("paired_count", False),
    (DISTRICTS[1], "train"): ("slope", False),
    (DISTRICTS[1], "validation"): ("ndvi", False),
    (DISTRICTS[1], "test"): ("paired_count", True),
}


def snap(value):
    return STEP * math.ceil(value / STEP - 0.5)


def candidates(districts):
    eligible = {slot: [] for slot in SLOTS}
    rejected = []
    for district in DISTRICTS:
        polygon = districts[district]
        xmin, ymin, xmax, ymax = polygon.bounds
        for bx in range(math.floor(xmin / 5000), math.ceil(xmax / 5000)):
            for by in range(math.floor(ymin / 5000), math.ceil(ymax / 5000)):
                x = snap(bx * 5000 + 2500 - SIZE * STEP / 2)
                y = snap(by * 5000 + 2500 - SIZE * STEP / 2)
                bounds = [x, y, x + SIZE * STEP, y + SIZE * STEP]
                block = f"{bx}:{by}"
                split = partition(block)
                item = dict(id=f"{district.split()[0].lower()}-{bx}-{by}",
                            district=district, block=block, split=split, bounds=bounds,
                            rank=hashlib.sha256(f"{PLAN}:{block}".encode()).hexdigest())
                tile = box(*bounds)
                covers = [name for name, geom in districts.items() if geom.covers(tile)]
                if covers != [district] or block_for(bounds) != block:
                    rejected.append(dict(item, reason="outside unique district or buffered block"))
                else:
                    eligible[district, split].append(item)
    shortlist = []
    for rows in eligible.values():
        rows.sort(key=lambda row: (row["rank"], row["block"]))
        shortlist.extend(rows[:3])
        rejected.extend(dict(row, reason="outside first three hash ranks") for row in rows[3:])
    return shortlist, rejected


def select(shortlist, metrics):
    selected, rejected, missing = [], [], []
    for (district, split), (key, high) in SLOTS.items():
        valid = []
        for row in shortlist:
            if (row["district"], row["split"]) != (district, split):
                continue
            qa = metrics[row["id"]]
            row = dict(row, preflight=qa)
            value = qa.get(key)
            if not all(qa["sar_scenes"]) or value is None or not math.isfinite(value):
                rejected.append(dict(row, reason="missing pinned orbit or ranking metric"))
            else:
                valid.append(row)
        valid.sort(key=lambda row: ((-1 if high else 1) * row["preflight"][key], row["rank"]))
        if valid:
            selected.append(dict(valid[0], rationale=f"{'higher' if high else 'lower'} {key}"))
            rejected.extend(dict(row, reason="lower preference within slot") for row in valid[1:])
        else:
            missing.append(dict(district=district, split=split, reason="no eligible screened tile"))
    return selected, rejected, missing


def region_for(bounds):
    return ee.Geometry.Rectangle(bounds, proj=CRS, geodesic=False)


def seasonal_sources(region, season):
    radar = sar.collection(region, season, CFG).filter(
        ee.Filter.eq("relativeOrbitNumber_start", CFG.relative_orbit))
    _, joined = optical.collections(region, season, CFG)
    return radar, joined


def preflight(shortlist):
    if not shortlist:
        return {}
    rows = ee.FeatureCollection([ee.Feature(region_for(row["bounds"]), {"id": row["id"]})
                                 for row in shortlist])

    def screen(feature):
        region = feature.geometry()
        radar, joined = zip(*(seasonal_sources(region, s) for s in SEASONS))
        # A masked placeholder preserves the schema for empty joined collections.
        placeholder = ee.Image.constant([0, 0]).rename(["NDVI", "NDTI"]).selfMask()
        prepared = [collection.map(lambda img: optical.prepare(img, CFG)).merge(
                    ee.ImageCollection.fromImages([placeholder])) for collection in joined]
        counts = [images.select("NDVI").count().unmask(0, sameFootprint=False)
                  for images in prepared]
        elevation = ee.Image(COLLECTIONS[3]).select("elevation")
        image = ee.Image.cat([
            ee.Terrain.slope(elevation).rename("slope"),
            prepared[0].median().select("NDVI").updateMask(counts[0].gte(CFG.min_observations)).rename("ndvi"),
            counts[0].rename("before_count"), counts[1].rename("after_count"),
        ])
        reducer = ee.Reducer.median().combine(ee.Reducer.count(), sharedInputs=True)
        stats = image.reduceRegion(reducer, region, crs=CRS,
                                   crsTransform=[120, 0, 0, 0, -120, 0], maxPixels=2048)
        return ee.Feature(None, stats).set({"id": feature.get("id"),
                          "sar_scenes": [collection.size() for collection in radar],
                          "optical_scenes": [collection.size() for collection in joined]})

    result = {}
    for feature in rows.map(screen).getInfo()["features"]:
        qa = feature["properties"]
        counts = [qa.get(f"{season}_count_median") for season in ("before", "after")]
        result[qa["id"]] = dict(qa, slope=qa.get("slope_median"), ndvi=qa.get("ndvi_median"),
                                paired_count=None if None in counts else min(counts))
    return result


def geometry(output):
    path = output / "districts.json"
    if not path.exists():
        save_json(path, get_study_area().getInfo())
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    project = Transformer.from_crs(4326, CRS, always_xy=True).transform
    districts = {f["properties"]["GAUL2_NAME"]: transform(shape(f["geometry"]), project, interleaved=False)
                 for f in features}
    if len(features) != 2 or set(districts) != set(DISTRICTS) or not all(
        geom.is_valid and not geom.is_empty for geom in districts.values()
    ):
        raise ValueError("Expected two valid GAUL district geometries")
    return districts


def freeze(output):
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'roster.json').exists():
        raise ValueError('Frozen roster already exists')
    districts = geometry(output)
    shortlist, rejected = candidates(districts)
    geometry_receipt = output / "geometry_preflight.json"
    expected = dict(shortlist=shortlist, rejected=rejected)
    if geometry_receipt.exists():
        if json.loads(geometry_receipt.read_text(encoding="utf-8")) != expected:
            raise ValueError("Geometry preflight changed across retry")
    else:
        save_json(geometry_receipt, expected)
    try:
        metrics = preflight(shortlist)
    except ee.EEException as error:
        receipt = output / f"preflight_failure_{time.time_ns()}.json"
        save_json(receipt, dict(status="failed", error=str(error)))
        raise
    selected, excluded, missing = select(shortlist, metrics)
    save_json(output / "roster.json", dict(plan=PLAN, config=asdict(CFG),
              grid=dict(crs=CRS, origin=[0, 0], spacing=STEP, size=SIZE, diagnostic_spacing=120),
              geometry_source="FAO/GAUL/2025/level2", geometry_sha256=digest(output / "districts.json"),
              selected=selected, rejected=rejected + excluded, missing=missing,
              coverage_gate="No matching successful district coverage receipt used. Exploratory only."))


def tile_graph(region):
    pair = paired_graph(region, CFG)
    radar_counts, optical_counts, metadata = [], [], []
    for season in SEASONS:
        radar, joined = seasonal_sources(region, season)
        radar_counts.append(sar.seasonal(radar, CFG.relative_orbit, region, CFG)[1])
        optical_counts.append(optical.seasonal(joined, region, CFG)[1])

        def scene_rows(collection):
            ordered = collection.sort("system:index")
            return ordered.aggregate_array("system:index").zip(
                ordered.aggregate_array("system:time_start"))

        metadata.append(ee.Dictionary(dict(s1=scene_rows(radar), s2=scene_rows(joined),
            s2_cloud=scene_rows(ee.ImageCollection(joined.map(
                lambda img: ee.Image(img.get("clouds"))))))))
    counts = ee.Image.cat(radar_counts + optical_counts).rename(list(COUNT_BANDS)).unmask(0, False)
    changes = pair.select(list(BANDS[8:]))
    diagnostic = validity_image(changes, counts, CFG)
    return ee.Image.cat([pair, counts, diagnostic]).toFloat().unmask(NODATA, False), metadata


def validate_scene_rows(metadata):
    for season, sources in zip(SEASONS, metadata, strict=True):
        for sensor in ("s1", "s2", "s2_cloud"):
            rows = sources[sensor]
            if len(rows) < CFG.min_observations or len({row[0] for row in rows}) != len(rows):
                raise ValueError(f"Insufficient or duplicate {sensor} scene provenance")
            for scene_id, milliseconds in rows:
                acquired = datetime.fromtimestamp(milliseconds / 1000, timezone.utc)
                if not scene_id or not season.start <= acquired.date().isoformat() < season.end:
                    raise ValueError(f"Invalid {sensor} acquisition provenance")
        if {row[0] for row in sources["s2"]} != {row[0] for row in sources["s2_cloud"]}:
            raise ValueError("S2/cloud scene join provenance mismatch")


def validate_pixels(data, scene_limits):
    if data.shape != (len(SCHEMA), SIZE, SIZE) or data.dtype != np.float32 or not np.isfinite(data).all():
        raise ValueError("Unexpected pixel schema")
    features = data[:14]
    counts, seasonal, common = data[14:18], data[18:22], data[22]
    if not np.all((counts >= 0) & (counts == np.floor(counts)) &
                  (counts <= np.array(scene_limits)[:, None, None])):
        raise ValueError("Observation counts outside scene provenance")
    for mask, count, channels in zip(seasonal, counts, ((0, 1), (4, 5), (2, 3), (6, 7))):
        if not np.array_equal(mask, count >= CFG.min_observations) or not all(
            np.array_equal(features[c] != NODATA, mask) for c in channels
        ):
            raise ValueError("Seasonal mask mismatch")
    for before, after, delta in zip(features[:4], features[4:8], features[8:12]):
        shared = (before != NODATA) & (after != NODATA)
        if not np.array_equal(delta != NODATA, shared) or not np.allclose(
            delta[shared], after[shared] - before[shared], atol=1e-5, rtol=0
        ):
            raise ValueError("After-minus-before value or mask mismatch")
    slope = features[13][features[13] != NODATA]
    elevation = features[12][features[12] != NODATA]
    if not slope.size or not elevation.size or not np.all((slope >= 0) & (slope <= 90)):
        raise ValueError("Unexpected SRTM terrain support or slope units")
    if not np.array_equal(common, (features != NODATA).all(axis=0)):
        raise ValueError("Common footprint mismatch")
    return dict(denominator=SIZE**2, valid_cells={name: int(mask.sum())
                for name, mask in zip(COVERAGE_BANDS, data[18:])},
                count_ranges={name: [int(count.min()), int(count.max())]
                              for name, count in zip(COUNT_BANDS, counts)},
                terrain_ranges=dict(elevation_m=[float(elevation.min()), float(elevation.max())],
                                    slope_degrees=[float(slope.min()), float(slope.max())]))


def write_raster(path, data, bands, affine):
    with rasterio.open(path, "w", driver="GTiff", width=SIZE, height=SIZE,
                       count=len(bands), dtype="float32", crs=CRS, transform=affine,
                       nodata=NODATA, compress="deflate") as dst:
        dst.write(data)
        dst.descriptions = bands
        dst.update_tags(data_kind="real", purpose="exploratory feature QA")
    with rasterio.open(path) as src:
        if (src.crs.to_string(), src.transform, src.descriptions, src.nodata) != (
            CRS, affine, bands, NODATA
        ) or not np.array_equal(src.read(), data) or not np.array_equal(
            src.read_masks() > 0, data != NODATA
        ):
            raise ValueError("GeoTIFF round-trip mismatch")


def alignment(data):
    """Screen stable-looking radar texture, without independent control."""
    before, after, slope = data[0], data[4], data[13]
    rows = []
    for y in (4, 24, 44):
        for x in (4, 24, 44):
            a = before[y:y+12, x:x+12]
            around = after[y-2:y+14, x-2:x+14]
            terrain = slope[y:y+12, x:x+12]
            if any(np.any(v == NODATA) for v in (a, around, terrain)) or a.std() < 1:
                continue
            scores = []
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    b = around[dy+2:dy+14, dx+2:dx+14]
                    if b.std() > 0:
                        scores.append((float(np.corrcoef(a.ravel(), b.ravel())[0, 1]), dy, dx))
            if not scores:
                continue
            score, dy, dx = max(scores)
            rows.append(dict(row=y, col=x, dy=dy, dx=dx, r=score,
                             median_slope=float(np.median(terrain))))
    coherent = [row for row in rows if row["r"] >= .75]
    zero = sum(row["dx"] == row["dy"] == 0 for row in coherent)
    status = "pass" if len(coherent) >= 3 and zero > len(coherent) / 2 else "inconclusive"
    return dict(status=status, windows=rows, coherent_windows=len(coherent), zero_shift_windows=zero,
                interpretation="VV texture consistency screen only. No independent positional control.")


def preview(path, data):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    figure, axes = plt.subplots(2, 3, figsize=(11, 7), layout="constrained")
    for ax, index, name, limits in zip(axes.flat, (0, 4, 8, 9, 10, 11),
                                      ("VV before", "VV after", *BANDS[8:12]),
                                      ((-26, 0), (-26, 0), (-5, 5), (-5, 5), (-.3, .3), (-.3, .3))):
        rendered = ax.imshow(np.ma.masked_equal(data[index], NODATA), vmin=limits[0],
                             vmax=limits[1], cmap="gray" if index < 8 else "RdBu_r",
                             interpolation="nearest")
        ax.set_title(name)
        ax.set_axis_off()
        figure.colorbar(rendered, ax=ax, shrink=.65)
    figure.suptitle("Exploratory seasonal features · no reference labels")
    figure.savefig(path, dpi=130)
    plt.close(figure)


def acquire(row, output, roster_hash):
    bounds = row["bounds"]
    if block_for(bounds) != row["block"] or partition(row["block"]) != row["split"] or any(
        coordinate % STEP for coordinate in bounds
    ) or bounds[2] - bounds[0] != SIZE * STEP or bounds[3] - bounds[1] != SIZE * STEP:
        raise ValueError("Roster grid or block mismatch")
    affine = Affine(STEP, 0, bounds[0], 0, -STEP, bounds[3])
    image, summaries = tile_graph(region_for(bounds))
    metadata, names = ee.List([ee.List(summaries), image.bandNames()]).getInfo()
    validate_scene_rows(metadata)
    if tuple(names) != SCHEMA:
        raise ValueError("Unexpected Earth Engine graph bands")
    save_json(output / "sources.json", dict(collections=COLLECTIONS,
              seasons=[asdict(s) for s in SEASONS], config=asdict(CFG), scenes=metadata,
              scene_time="UTC epoch milliseconds", terrain_units=["metres", "degrees"],
              nominal_source_spacing_m=dict(s1=10, s2_indices=10, s2_scl=20, srtm=30),
              output_crs=CRS, output_transform=list(affine)[:6], roster_sha256=roster_hash))
    url = image.getDownloadURL(dict(format="GEO_TIFF", crs=CRS,
                                    crs_transform=list(affine)[:6], dimensions=[SIZE, SIZE]))
    raw = output / "source.tif"
    with requests.get(url, timeout=(15, 180), stream=True) as response:
        if response.status_code != 200:
            raise RuntimeError(f"Earth Engine download HTTP {response.status_code}")
        with raw.open("xb") as stream:
            for chunk in response.iter_content(65536):
                if stream.tell() + len(chunk) > 2 * 1024**2:
                    raise ValueError("Raw download exceeds the tile byte budget")
                stream.write(chunk)
    with rasterio.open(raw) as src:
        if (src.crs.to_string(), src.transform, src.shape, src.count) != (CRS, affine, (SIZE, SIZE), len(SCHEMA)):
            raise ValueError("Unexpected source grid")
        if any(src.descriptions) and src.descriptions != SCHEMA:
            raise ValueError("Unexpected source band order")
        data = src.read()
    limits = [len(item[sensor]) for sensor in ("s1", "s2") for item in metadata]
    quality = validate_pixels(data, limits)
    quality["support_percent"] = {name: cells * 100 / quality["denominator"]
                                  for name, cells in quality["valid_cells"].items()}
    quality["missing_cells"] = {name: quality["denominator"] - cells
                                for name, cells in quality["valid_cells"].items()}
    save_json(output / "structural_checks.json", quality)
    write_raster(output / "features.tif", data[:14], BANDS, affine)
    write_raster(output / "diagnostics.tif", data[14:], DIAGNOSTICS, affine)
    preview(output / "exploratory.png", data)
    inspection = alignment(data)
    save_json(output / "alignment.json", inspection)
    if inspection["status"] != "pass":
        raise ValueError("Inconclusive relative VV texture inspection")
    return dict(quality, raw_bytes=raw.stat().st_size, export_id=f"{PLAN}:{row['id']}:{digest(raw)[:16]}",
                hashes={name: digest(output / name) for name in
                        ("source.tif", "features.tif", "diagnostics.tif", "sources.json", "alignment.json", "structural_checks.json")})


def run(output, remaining):
    roster_path = output / "roster.json"
    roster_hash = digest(roster_path)
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    districts = geometry(output)
    tiles = roster["selected"]
    if (roster["plan"] != PLAN or roster["config"] != asdict(CFG)
            or roster["geometry_sha256"] != digest(output / "districts.json")
            or not 1 <= len(tiles) <= len(SLOTS) or len({row["block"] for row in tiles}) != len(tiles)
            or len({(row["district"], row["split"]) for row in tiles}) != len(tiles)):
        raise ValueError("Invalid frozen roster")
    if remaining:
        first = json.loads((output / tiles[0]["id"] / "quality.json").read_text(encoding="utf-8"))
        if first["status"] != "passed" or first["roster_sha256"] != roster_hash or any(
            digest(output / tiles[0]["id"] / name) != sha for name, sha in first["hashes"].items()
        ):
            raise ValueError("First tile must pass with matching evidence before expansion")
    for row in tiles[1:] if remaining else tiles[:1]:
        target = output / row["id"]
        target.mkdir(exist_ok=False)
        start = time.monotonic()
        receipt = dict(tile=row, roster_sha256=roster_hash)
        try:
            if shutil.disk_usage(output).free < 100 * 1024**2:
                raise ValueError("Insufficient local disk reserve")
            if [name for name, geom in districts.items() if geom.covers(box(*row["bounds"]))] != [row["district"]]:
                raise ValueError("Tile is outside the uniquely assigned original district")
            receipt.update(acquire(row, target, roster_hash), status="passed")
        except Exception as error:
            receipt.update(status="failed", error_type=type(error).__name__,
                           # Network exception strings can embed temporary download URLs.
                           error=str(error) if isinstance(error, (ValueError, RuntimeError)) else "Request or local processing failed")
            raise
        finally:
            receipt["elapsed_seconds"] = round(time.monotonic() - start, 2)
            save_json(target / "quality.json", receipt)
            print(row["id"], receipt["status"], receipt.get("valid_cells"), receipt["elapsed_seconds"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--first", action="store_true")
    mode.add_argument("--remaining", action="store_true")
    args = parser.parse_args()
    initialize()
    ee.data.setDeadline(180000)
    if args.first or args.remaining:
        run(args.output, args.remaining)
    else:
        freeze(args.output)


if __name__ == "__main__":
    main()
