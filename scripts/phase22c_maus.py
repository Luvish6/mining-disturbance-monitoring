"""Bounded Phase 22C development-only coverage QA. No fitting or label export."""

import csv
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

from affine import Affine
import ee
import numpy as np
import rasterio
from rasterio.io import MemoryFile

from config.phase2_settings import Phase2Config
from config.settings import Season
from scripts.phase22b_maus import ROOT, SIZE, digest, fetch, write_json
from scripts.phase22b_maus_qa import NODATA, WINDOW, development_sites, observations, read_grid
from src.gee_setup import initialize
from src.optical_preprocessing import collections
from src.sar_preprocessing import seasonal

SPLIT_SHA = "603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60"
DEST = Path("outputs/phase22c_maus")
OPTICAL = ("B3", "B4", "B8")
SAR = ("VV", "VH")
DEM = "elevation"
CONFIGS = {"optical": OPTICAL, "optical_dem": OPTICAL + (DEM,), "fused_dem": OPTICAL + SAR + (DEM,)}
DIRECTIONS = ("ASCENDING", "DESCENDING")
MIN_COVERAGE = .70


def verify_split(original, amended):
    if digest(original) != SPLIT_SHA or amended != original:
        raise ValueError("Phase 22B split bytes must remain identical")




def check_geographic_buffer(geometries, roster):
    from scripts.phase22b_maus import groups

    owner = {fid: key for key, row in roster.items() for fid in row["ids"]}
    if set(owner) != set(geometries) or len(owner) != sum(len(row["ids"]) for row in roster.values()):
        raise ValueError("Frozen spatial geometry and roster disagree")
    if any(len({owner[fid] for fid in group}) != 1 for group in groups(geometries)):
        raise ValueError("Cross-group projected buffer violation")


def check_seal(roster, seal, sites):
    test = {key: row["ids"] for key, row in roster.items() if row["split"] == "test"}
    if (not test or seal.get("sealed") is not True or seal.get("groups") != test
            or seal.get("split_sha256") != SPLIT_SHA):
        raise ValueError("Original sealed TEST roster mismatch")
    for site in sites:
        group = roster[site["group"]]
        if (site["split"] not in {"train", "validation"}
                or site["split"] != group["split"] or site["fid"] not in group["ids"]):
            raise ValueError("Invalid development roster entry")


def choose_pair(histograms):
    options = []
    for direction in DIRECTIONS:
        for key, count in histograms[direction].items():
            orbit = int(float(key))
            if count >= 2:
                options.append((-count, direction, orbit))
    if not options:
        return None
    _, direction, orbit = min(options)
    return direction, orbit


def check_composite(pair, records):
    if len(records) < 2 or len({row["id"] for row in records}) != len(records):
        raise ValueError("Require two or more unique SAR scenes")
    if any((row["direction"], row["orbit"]) != pair for row in records):
        raise ValueError("Mixed SAR orbit direction or relative orbit")


def eligibility(optical, sar, dem):
    support = {"optical": optical, "optical_dem": optical & dem,
               "fused_dem": optical & sar & dem}
    return {key: dict(valid_cells=int(mask.sum()), eligible=bool(mask.mean() >= MIN_COVERAGE))
            for key, mask in support.items()}


def verified_evaluation(role, evidence_status, independent_review, adjudicated):
    return (role in {"validation", "test"} and evidence_status == "VERIFIED_REFERENCE"
            and independent_review is True and adjudicated is True)


def sar_query(region, window):
    raw = ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(region).filterDate(window.start, window.end)
    iw = raw.filter(ee.Filter.eq("instrumentMode", "IW"))
    ten = iw.filter(ee.Filter.eq("resolution_meters", 10))
    dual = ten.filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV")).filter(
        ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
    by_direction = {d: dual.filter(ee.Filter.eq("orbitProperties_pass", d)) for d in DIRECTIONS}
    diagnostic = ee.Dictionary(dict(intersecting_all=raw.size(), iw=iw.size(),
        iw_10m=ten.size(), iw_10m_dual=dual.size(),
        orbits=ee.Dictionary({d: c.aggregate_histogram("relativeOrbitNumber_start")
                              for d, c in by_direction.items()}))).getInfo()
    return by_direction, diagnostic


def selected_records(collection):
    collection = collection.sort("system:index")
    props = ("system:index", "system:time_start", "orbitProperties_pass", "relativeOrbitNumber_start")
    ids, dates, directions, orbits = ee.List([collection.aggregate_array(k) for k in props]).getInfo()
    return [dict(id=i, date_ms=t, direction=d, orbit=o)
            for i, t, d, o in zip(ids, dates, directions, orbits, strict=True)]


def optical_graph(region, cfg):
    _, optical = collections(region, WINDOW, cfg)

    def mask_scene(image):
        probability = ee.Image(image.get("clouds")).select("probability")
        scl = image.select("SCL")
        rgb = image.select(list(OPTICAL))
        valid = (probability.lt(cfg.cloud_probability).And(scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)))
                 .And(image.select("B8A").mask()).And(image.select("B9").mask())
                 .And(rgb.mask().reduce(ee.Reducer.min())))
        return rgb.divide(10000).updateMask(valid)

    stack = optical.map(mask_scene)
    count = stack.select("B3").count().unmask(0).rename("optical_count")
    return stack.median().updateMask(count.gte(2)), count, observations(optical.sort("system:index")).getInfo()


def download(image, bands, site, path):
    if image.bandNames().getInfo() != list(bands):
        raise ValueError("Incorrect export graph band order")
    url = image.toFloat().unmask(NODATA, False).getDownloadURL(
        dict(crs=f"EPSG:{site['crs']}", crs_transform=site["affine"],
             dimensions=[SIZE, SIZE], format="GEO_TIFF"))
    raw = fetch(url, 2 * 1024**2)
    with MemoryFile(raw) as mem, mem.open() as ds:
        if (ds.shape != (SIZE, SIZE) or ds.count != len(bands)
                or ds.crs is None or ds.crs.to_epsg() != site["crs"]
                or ds.transform != Affine(*site["affine"])
                or ds.dtypes != ("float32",) * len(bands)
                or (any(ds.descriptions) and ds.descriptions != bands)):
            raise ValueError("Unexpected raster grid, type or bands")
        arrays, profile = ds.read(), ds.profile
    profile.update(nodata=NODATA, compress="deflate")
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(arrays)
        ds.descriptions = bands
    with rasterio.open(path) as ds:
        if ds.nodata != NODATA or ds.descriptions != bands or not np.array_equal(ds.read(), arrays):
            raise ValueError("Written QA raster changed")
    return dict(zip(bands, arrays)), dict(bytes=len(raw), raw_sha256=digest(raw),
                                            tiff_sha256=digest(path.read_bytes()))


def sensor_support(arrays, bands, count_name):
    count = arrays[count_name]
    valid = count >= 2
    if (not np.isfinite(count).all() or (count < 0).any() or (count != np.floor(count)).any()
            or any(not np.array_equal(np.isfinite(arrays[b]) & (arrays[b] != NODATA), valid)
                   for b in bands)):
        raise ValueError("Sensor values do not match valid observation counts")
    return valid


def run_tile(site, root, dest):
    crs = f"EPSG:{site['crs']}"
    region = ee.Geometry.Rectangle(site["bounds"], crs, False)
    cfg = Phase2Config(analysis_crs=crs)
    direction_collections, diagnostic = sar_query(region, WINDOW)
    pair = choose_pair(diagnostic["orbits"])
    records = []
    if pair is not None:
        direction, orbit = pair
        selected = direction_collections[direction].filter(ee.Filter.eq("relativeOrbitNumber_start", orbit))
        records = selected_records(selected)
        check_composite(pair, records)
        histogram = {int(float(key)): count for key, count in diagnostic["orbits"][direction].items()}
        if len(records) != histogram[orbit]:
            raise ValueError("Selected scene count disagrees with orbit histogram")
    optical, count, optical_sources = optical_graph(region, cfg)
    if len(optical_sources["ids"]) < 2:
        raise ValueError("Bounded QA window has insufficient optical scenes")
    dem = ee.Image("USGS/SRTMGL1_003").select(DEM)
    cache = root / "qa" / f"{site['split']}.tif"
    old = json.loads(cache.with_suffix(".json").read_bytes())
    reused = (old.get("site") == site and old.get("dates") == [WINDOW.start, WINDOW.end]
              and pair == ("DESCENDING", old["sources"].get("relative_orbit"))
              and old.get("tiff_sha256") is not None
              and set(optical_sources["ids"]) == set(old["sources"]["optical"]["ids"])
              and {r["id"] for r in records} == set(old["sources"]["radar"]["ids"]))
    target = dest / f"{site['split']}_qa.tif"
    if reused:
        if digest(cache.read_bytes()) != old["tiff_sha256"]:
            raise ValueError("Frozen Phase 22B QA cache hash mismatch")
        values, _ = read_grid(cache, site)
        from scripts.phase22b_maus import BANDS
        arrays = {name: np.where(np.isnan(a), NODATA, a) for name, a in zip(BANDS, values, strict=True)}
        new, transfer = download(dem, (DEM,), site, target)
        arrays.update(new)
        transfer["phase22b_cache_sha256"] = old["tiff_sha256"]
    else:
        image = optical.addBands(count).addBands(dem)
        bands = OPTICAL + ("optical_count", DEM)
        if pair is not None:
            sar, sar_count = seasonal(selected, orbit, region, replace(cfg, orbit_pass=direction))
            image = image.addBands(sar).addBands(sar_count)
            bands += SAR + ("sar_count",)
        arrays, transfer = download(image.select(list(bands)), bands, site, target)

    optical_valid = sensor_support(arrays, OPTICAL, "optical_count")
    sar_valid = sensor_support(arrays, SAR, "sar_count") if pair else np.zeros_like(optical_valid)
    dem_valid = np.isfinite(arrays[DEM]) & (arrays[DEM] != NODATA)
    result = dict(site=site, window=[WINDOW.start, WINDOW.end], radar_filters=diagnostic,
                  selected_orbit=pair, radar_scenes=records, optical_scenes=optical_sources,
                  support=eligibility(optical_valid, sar_valid, dem_valid),
                  sar_valid_cells=int(sar_valid.sum()), dem_valid_cells=int(dem_valid.sum()),
                  optical_count_range=[int(arrays["optical_count"].min()), int(arrays["optical_count"].max())],
                  sar_count_range=[int(arrays["sar_count"].min()), int(arrays["sar_count"].max())] if pair else None,
                  transfer=transfer, qa_file=target.name)
    if pair is None:
        _, alternative = sar_query(region, Season("2019-Q4", "2019-10-01", "2020-01-01"))
        result["alternative_metadata_only"] = alternative
    return result


def review_sheets(root, dest, by_site):
    fields = ["model_input_source", "model_input_dates_utc", "source_receipt", "locator_license",
              "positive_criteria", "negative_criteria", "reference_source_license"]
    with (root / "review.csv").open(encoding="utf-8", newline="") as src:
        reader = csv.DictReader(src)
        with (dest / "review.csv").open("x", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=reader.fieldnames + fields)
            writer.writeheader()
            for row in reader:
                receipt = by_site.get(int(row["fid"]))
                dates = "" if receipt is None else ";".join(
                    datetime.fromtimestamp(t / 1000, tz=timezone.utc).date().isoformat()
                    for t in sorted(set(receipt["optical_scenes"]["dates_ms"])))
                writer.writerow(row | dict(
                    model_input_source="" if not receipt else "COPERNICUS/S2_SR_HARMONIZED (model-input context)",
                    model_input_dates_utc=dates, source_receipt="" if not receipt else f"{receipt['site']['split']}.json",
                    locator_license="Maus v2 CC BY-SA 4.0; PANGAEA.942325",
                    positive_criteria="Dated independent evidence of visible surface mining; digitize conservative interior",
                    negative_criteria="Dated independent non-mining evidence; no negative inferred outside Maus",
                    reference_source_license=""))


def run(root=ROOT, dest=DEST):
    original = (root / "split.json").read_bytes()
    verify_split(original, original)
    sites = list(development_sites(root))
    all_sites = json.loads((root / "development.json").read_bytes())["sites"]
    check_seal(json.loads(original)["groups"],
               json.loads((root / "sealed_test.json").read_bytes()), all_sites)
    initialize()
    dest.mkdir(parents=True, exist_ok=False)
    (dest / "split.json").write_bytes(original)
    verify_split(original, (dest / "split.json").read_bytes())
    receipts = {}
    for site in sites:
        receipt = run_tile(site, root, dest)
        write_json(dest / f"{site['split']}.json", receipt)
        receipts[site["fid"]] = receipt
        print(site["split"], receipt["radar_filters"], receipt["selected_orbit"], receipt["support"], flush=True)
    (dest / "development_overlay.geojson").write_bytes((root / "development_overlay.geojson").read_bytes())
    review_sheets(root, dest, receipts)
    write_json(dest / "coverage.json", dict(split_sha256=SPLIT_SHA, test_sealed=True,
        configs=CONFIGS, sites=[dict(fid=s["fid"], group=s["group"], split=s["split"],
            status="QA_MEASURED" if s["fid"] in receipts else "UNASSESSED",
            support=receipts[s["fid"]]["support"] if s["fid"] in receipts else None)
            for s in all_sites]))


if __name__ == "__main__":
    run()
