"""Prepare a Phase 11C tile for regional inference using its cached observations."""
import argparse
import json
from pathlib import Path

from config.settings import BEFORE, AFTER
from src.phase3.regional_inference import digest, prepare


def fetch_terrain(cache, target):
    import ee
    import rasterio
    import requests
    from rasterio.io import MemoryFile

    from src.gee_setup import initialize
    from src.phase3.regional_inference import NODATA, write_tile, BAND_UNITS

    with rasterio.open(cache) as src:
        profile = src.profile
        expected = src.crs, src.transform, src.shape
    initialize()
    ee.data.setDeadline(90000)
    elevation = ee.Image("USGS/SRTMGL1_003").select("elevation")
    bands = ("elevation", "slope")
    image = elevation.addBands(ee.Terrain.slope(elevation)).toFloat().unmask(NODATA, False)
    crs, affine, (height, width) = expected
    url = image.getDownloadURL(dict(format="GEO_TIFF", crs=str(crs),
                                    crs_transform=list(affine)[:6], dimensions=[width, height]))
    with requests.get(url, timeout=(15, 90)) as response:
        if response.status_code != 200:
            raise RuntimeError(f"Terrain request returned HTTP {response.status_code}")
        content = response.content
    with MemoryFile(content) as memory, memory.open() as src:
        if (src.crs, src.transform, src.shape) != expected or src.count != 2 or (
                any(src.descriptions) and src.descriptions != bands):
            raise ValueError("Unexpected terrain grid or band order")
        values = src.read()
    write_tile(target, profile, bands, values, dict(source="USGS/SRTMGL1_003"), BAND_UNITS[-2:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--terrain", type=Path)
    options.add_argument("--fetch-terrain", action="store_true")
    args = parser.parse_args()
    item, = (item for item in json.loads(args.inventory.read_bytes()) if item["id"] == args.site)
    record = item["screen"]
    if record["state"] != "screened":
        raise ValueError("Site has no cached observations")
    cache = args.inventory.parent / args.site / "tile.tif"
    metadata = dict(region_id=args.site, crs=record["grid_crs"], bounds=record["bounds"],
                    windows=[[BEFORE.start, BEFORE.end], [AFTER.start, AFTER.end]],
                    source_receipt_sha256=digest(args.inventory), scene_sources=record["sources"],
                    processing=record["config"], terrain_method="SRTMGL1_003 with native ee.Terrain.slope"
                    if args.fetch_terrain else "supplied aligned terrain")
    args.output.mkdir()
    terrain = args.terrain or args.output/"terrain.tif"
    if args.fetch_terrain:
        fetch_terrain(cache, terrain)
    report = prepare(cache, terrain, metadata, args.output/"features.tif")
    (args.output/"receipt.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print({k: report[k] for k in ("region_id", "crs", "common_cells", "grid_cells", "status")})


if __name__ == "__main__":
    main()
