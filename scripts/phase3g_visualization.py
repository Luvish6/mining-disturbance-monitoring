"""Build a local real-observation viewer for the fixed Phase 3G demonstration tile."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import ee
import matplotlib
import matplotlib.image
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.io import MemoryFile
import requests

sys.path.insert(0, str(Path.cwd()))
from config.phase2_settings import Phase2Config
from config.settings import BEFORE, AFTER
from src import optical_preprocessing as optical, sar_preprocessing as sar
from src.change_features import build_stack
from src.coverage_diagnostics import COUNT_BANDS, COVERAGE_BANDS, validity_image
from src.gee_setup import initialize
from src.study_area import get_study_area, verify_boundary

SIZE = 32
NODATA = -9999
OPTICAL = ("B8", "B4", "B3")
SEASONS = (("before", BEFORE), ("after", AFTER))
CENTER = (92.35, 25.35)


def graph(region, cfg):
    seasonal, counts, sources = [], [], []
    for label, season in SEASONS:
        s1 = sar.collection(region, season, cfg)
        chosen = s1.filter(ee.Filter.eq("relativeOrbitNumber_start", cfg.relative_orbit))
        raw, joined = optical.collections(region, season, cfg)
        summary = ee.Dictionary({
            "orbit_histogram": s1.aggregate_histogram("relativeOrbitNumber_start"),
            "s1_ids": chosen.aggregate_array("system:index"),
            "s1_time_start_ms": chosen.aggregate_array("system:time_start"),
            "s2_ids": joined.aggregate_array("system:index"),
            "s2_time_start_ms": joined.aggregate_array("system:time_start"),
            "s2_raw_count": raw.size(),
        }).getInfo()
        sources.append(summary)
        if len(summary["s1_ids"]) < cfg.min_observations or len(summary["s2_ids"]) < cfg.min_observations:
            raise ValueError(f"Insufficient scenes for {label}")
        radar, radar_count = sar.seasonal(s1, cfg.relative_orbit, region, cfg)
        indices, optical_count = optical.seasonal(joined, region, cfg)

        def false_color(image):
            mask = ee.Image(optical.prepare(image, cfg)).select("NDVI").mask()
            return image.select(list(OPTICAL)).divide(10000).updateMask(mask)

        composite = joined.map(false_color).median().updateMask(indices.select("NDVI").mask()).clip(region)
        seasonal.append((radar, indices, composite))
        counts.extend((radar_count, optical_count))
    sar.choose_orbit(*(s["orbit_histogram"] for s in sources), cfg.relative_orbit)
    stack = build_stack(seasonal[0][0], seasonal[1][0], seasonal[0][1], seasonal[1][1], region)
    diagnostics = ee.Image.cat([counts[0], counts[2], counts[1], counts[3]]).rename(list(COUNT_BANDS))
    images, names = [], []
    for (label, _), (radar, indices, composite) in zip(SEASONS, seasonal):
        names_for_season = [f"{band}_{label}" for band in ("VV", "VH", "NDVI", "NDTI", *OPTICAL)]
        images.append(radar.addBands(indices).addBands(composite).rename(names_for_season))
        names.extend(names_for_season)
    change = ["dVV", "dVH", "dNDVI", "dNDTI"]
    images += [stack.select(change), diagnostics, validity_image(stack, diagnostics, cfg)]
    names += change + list(COUNT_BANDS) + list(COVERAGE_BANDS)
    return ee.Image.cat(images).toFloat().unmask(NODATA, sameFootprint=False), names, sources


def download(image, names, cfg, transform, target):
    if image.bandNames().getInfo() != names:
        raise ValueError("Unexpected Earth Engine graph band order")
    url = image.select(names).getDownloadURL(dict(format="GEO_TIFF", crs=cfg.analysis_crs,
                                    crs_transform=list(transform)[:6], dimensions=[SIZE, SIZE]))
    with requests.get(url, timeout=(15, 180)) as response:
        if response.status_code != 200:
            raise RuntimeError(f"Earth Engine raster download returned HTTP {response.status_code}")
        content = response.content
    with MemoryFile(content) as memory, memory.open() as src:
        if (src.crs.to_string(), src.transform, src.shape, src.count) != (
                cfg.analysis_crs, transform, (SIZE, SIZE), len(names)):
            raise ValueError("Earth Engine returned an unexpected raster grid or band count")
        if any(src.descriptions) and tuple(src.descriptions) != tuple(names):
            raise ValueError(f"Unexpected Earth Engine band order: {src.descriptions}")
        data = src.read()
        profile = src.profile
    profile.update(nodata=NODATA, compress="deflate")
    with rasterio.open(target, "w", **profile) as dst:
        dst.write(data)
        dst.descriptions = tuple(names)
        dst.update_tags(purpose="Real Earth Engine demonstration; no reference labels or predictions")
    with rasterio.open(target) as dst:
        if dst.transform != transform or dst.crs.to_string() != cfg.analysis_crs or dst.nodata != NODATA:
            raise ValueError("Written GeoTIFF grid or NoData changed")
        if tuple(dst.descriptions) != tuple(names) or not np.array_equal(dst.read(), data):
            raise ValueError("Written GeoTIFF band names or data changed")
    return dict(zip(names, data))


def validate(arrays, minimum):
    for sensor, bands in (("sar", ("VV", "VH")), ("optical", ("NDVI", "NDTI", *OPTICAL))):
        for season, _ in SEASONS:
            valid = arrays[f"{sensor}_{season}_valid"]
            count = arrays[f"{sensor}_{season}_count"]
            if not np.all(np.isfinite(count) & (count >= 0) & (count == np.floor(count))):
                raise ValueError("Invalid observation counts")
            if not np.array_equal(valid, count >= minimum):
                raise ValueError("Seasonal validity differs from observation threshold")
            for band in bands:
                if not np.array_equal(arrays[f"{band}_{season}"] != NODATA, valid):
                    raise ValueError(f"Unexpected mask for {band}_{season}")
        for band in bands[:2]:
            before, after, delta = (arrays[name] for name in (f"{band}_before", f"{band}_after", f"d{band}"))
            joint = (before != NODATA) & (after != NODATA)
            if not joint.any() or not np.array_equal(delta != NODATA, joint):
                raise ValueError(f"Missing or inconsistent change support for {band}")
            if not np.allclose(delta[joint], (after - before)[joint], atol=1e-5):
                raise ValueError(f"Change is not after minus before for {band}")
    common = arrays["common_valid"]
    if not np.isin(common, [0, 1]).all() or np.any((common == 1) & np.any(
            [arrays[k] == NODATA for k in ("dVV", "dVH", "dNDVI", "dNDTI")], axis=0)):
        raise ValueError("Invalid common mask")


def save_layers(arrays, output):
    layers = []

    def save(key, title, period, pixels, legend, colors=()):
        matplotlib.image.imsave(output / f"{key}.png", pixels)
        layers.append(dict(key=key, title=title, period=period, legend=legend, colors=colors))

    for label, season in SEASONS:
        period = f"{season.start} to {season.end} (end exclusive)"
        rgb = np.stack([arrays[f"{band}_{label}"] for band in OPTICAL], axis=-1)
        alpha = np.all(rgb != NODATA, axis=-1)
        rgba = np.dstack((np.clip(rgb / .35, 0, 1), alpha))
        save(f"optical_{label}", f"Sentinel-2 false colour · {label}", period, rgba,
             "RGB = B8 / B4 / B3; shared surface reflectance stretch 0–0.35")
    specs = {"VV": (-25, 0, "gray", "dB"), "VH": (-32, -5, "gray", "dB"),
             "NDVI": (-.2, .9, "YlGn", "index"), "NDTI": (-.4, .4, "BrBG_r", "index")}
    periods = {label: f"{s.start} to {s.end} (end exclusive)" for label, s in SEASONS}
    periods["change"] = f"After minus before · {periods['after']} / {periods['before']}"
    for key, values in arrays.items():
        band, _, label = key.partition("_")
        if band in OPTICAL:
            continue
        if key.startswith("d"):
            hi = 5 if key in ("dVV", "dVH") else .4
            lo, cmap, unit, period = -hi, "RdBu_r", "dB" if hi == 5 else "index difference", "change"
        elif key in COUNT_BANDS:
            lo, hi, cmap, unit = 0, max(1, int(values.max())), "viridis", "observations"
            period = key.split("_")[1]
        elif key in COVERAGE_BANDS:
            lo, hi, cmap, unit = 0, 1, "RdYlGn", "0 unsupported / 1 valid"
            period = "change" if key == "common_valid" else key.split("_")[1]
        else:
            lo, hi, cmap, unit = specs[band]
            period = label
        palette = matplotlib.colormaps[cmap]
        rgba = palette(np.clip((values - lo) / (hi - lo), 0, 1))
        rgba[..., 3] = values != NODATA
        colors = [matplotlib.colors.to_hex(palette(v)) for v in (0., .5, 1.)]
        save(key, key.replace("_", " "), periods[period], rgba, f"{lo:g} to {hi:g} · {unit}", colors)
    return layers


def viewer(layers, output, bounds):
    template = Path(__file__).with_name("phase3g_viewer.txt").read_text(encoding="utf-8")
    (output / "index.html").write_text(
        template.replace("__LAYERS__", json.dumps(layers)).replace("__BOUNDS__", str(bounds)),
        encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output directory")
    cfg = Phase2Config(relative_orbit=77)
    scale = cfg.analysis_scale_m
    x, y = Transformer.from_crs(4326, cfg.analysis_crs, always_xy=True).transform(*CENTER)
    left = round(x / scale) * scale - SIZE // 2 * scale
    top = round(y / scale) * scale + SIZE // 2 * scale
    bounds = (left, top - SIZE * scale, left + SIZE * scale, top)
    affine = rasterio.Affine(scale, 0, left, 0, -scale, top)
    initialize()
    ee.data.setDeadline(180000)
    region = ee.Geometry.Rectangle(list(bounds), cfg.analysis_crs, False)
    if not verify_boundary(get_study_area()).contains(region, 1).getInfo():
        raise ValueError("Tile lies outside the verified district boundary")
    image, names, sources = graph(region, cfg)
    with TemporaryDirectory(dir=args.output.parent) as temp:
        output = Path(temp) / "visualization"
        output.mkdir()
        arrays = download(image, names, cfg, affine, output / "tile.tif")
        validate(arrays, cfg.min_observations)
        layers = save_layers(arrays, output)
        viewer(layers, output, bounds)
        receipt = dict(purpose="real satellite visualization only", config=asdict(cfg),
                       seasons=[asdict(s) for _, s in SEASONS], bounds=bounds, transform=list(affine)[:6],
                       shape=[SIZE, SIZE], nodata=NODATA, layer_count=len(layers), bands=names,
                       collections=["COPERNICUS/S1_GRD", "COPERNICUS/S2_SR_HARMONIZED",
                                    "COPERNICUS/S2_CLOUD_PROBABILITY", "USGS/SRTMGL1_003"],
                       source_pixel_spacing_m={"S1_IW": 10, "S2_B8_B4_B3": 10, "S2_SCL": 20,
                                               "S2_B8A": 20, "S2_B9": 60, "SRTM_nominal": 30},
                       sources=sources, band_definitions={
                           "optical": "Median masked B8/B4/B3 surface reflectance, divide source DN by 10000",
                           "NDVI": "(B8-B4)/(B8+B4); median per-observation index",
                           "NDTI": "(B4-B3)/(B4+B3); median per-observation index",
                           "VV_VH": "Seasonal median smoothed linear power converted to dB",
                           "change": "After minus before for each seasonal index or dB band",
                           "counts": "Per-sensor valid seasonal observations",
                           "valid": "Seasonal minimum-count threshold; common includes terrain support"},
                       valid_pixels={b: int((arrays[b] == 1).sum()) for b in COVERAGE_BANDS},
                       count_ranges={b: [int(arrays[b].min()), int(arrays[b].max())] for b in COUNT_BANDS})
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        output.rename(args.output)
    print(json.dumps({k: receipt[k] for k in ("shape", "layer_count", "valid_pixels", "count_ranges")}))


if __name__ == "__main__":
    main()
