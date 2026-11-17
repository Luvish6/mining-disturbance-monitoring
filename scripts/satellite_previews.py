"""Deterministic seasonal previews and provenance for the local Indian Explorer."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import matplotlib
import matplotlib.image
import numpy as np
from PIL import Image
import rasterio

from src.phase3.data import digest

SITES = ("gevra", "bhubaneswari")
LAYERS = ("optical", "VV", "VH")
SEASONS = ("before", "after")
RADAR = {"VV": (-25, 0), "VH": (-32, -5)}
OPTICAL = ("B8", "B4", "B3")


def settings(layer, season):
    bands = OPTICAL if layer == "optical" else (layer,)
    return dict(bands=[f"{band}_{season}" for band in bands],
                stretch=list((0, .35) if layer == "optical" else RADAR[layer]),
                normalization="linear clip to [0,1]",
                input_units="surface reflectance" if layer == "optical" else "dB",
                colormap="RGB in band order" if layer == "optical" else "gray",
                alpha="all contributing bands differ from raster NoData",
                origin="upper", resampling="none", output="RGBA PNG")


def render(arrays, layer, season, nodata):
    """Use the Phase 3G display stretches without modifying the raster."""
    spec = settings(layer, season)
    low, high = spec["stretch"]
    if layer == "optical":
        rgb = np.stack([arrays[band] for band in spec["bands"]], axis=-1)
        return np.dstack((np.clip(rgb / high, 0, 1), np.all(rgb != nodata, axis=-1)))
    values = arrays[spec["bands"][0]]
    rgba = matplotlib.colormaps["gray"](np.clip((values - low) / (high - low), 0, 1))
    rgba[..., 3] = values != nodata
    return rgba


def png(pixels):
    with BytesIO() as stream:
        matplotlib.image.imsave(stream, pixels, format="png", origin="upper")
        return stream.getvalue()


def rgba(content):
    with Image.open(BytesIO(content)) as image:
        if image.format != "PNG" or image.mode != "RGBA":
            raise ValueError("Expected an RGBA PNG")
        return np.asarray(image).copy()


def inputs(outputs, site):
    return (outputs / "phase11c_india_discovery" / site / "tile.tif",
            outputs / f"phase16a_{site}" / "receipt.json",
            outputs / "phase11c_india_discovery" / "inventory.json")


def expected(outputs, site):
    source, receipt_path, inventory = inputs(outputs, site)
    receipt = json.loads(receipt_path.read_bytes())
    source_hash, inventory_hash = digest(source), digest(inventory)
    if (receipt["region_id"], receipt["cache_sha256"], receipt["source_receipt_sha256"]) != (
            site, source_hash, inventory_hash):
        raise ValueError("Preview source hashes or site disagree with the preparation receipt")
    items = [item for item in json.loads(inventory.read_bytes()) if item["id"] == site]
    if len(items) != 1 or items[0]["screen"]["state"] != "screened":
        raise ValueError("Preview site missing from the screened source inventory")
    item = items[0]
    if (receipt["scene_sources"] != item["screen"]["sources"]
            or receipt["windows"] != [[row["start"], row["end"]] for row in item["windows"]]):
        raise ValueError("Preview acquisition inventory disagrees")
    with rasterio.open(source) as grid:
        geometry = dict(crs=str(grid.crs), transform=list(grid.transform)[:6],
                        shape=list(grid.shape), bounds=list(grid.bounds), nodata=grid.nodata)
        if (not grid.crs or grid.nodata is None
                or any(geometry[k] != receipt[k] for k in ("crs", "transform", "shape", "bounds"))):
            raise ValueError("Preview CRS, affine or dimensions disagree with the receipt")
        specs = {f"{layer}_{season}.png": settings(layer, season)
                 for layer in LAYERS for season in SEASONS}
        names = sorted({band for spec in specs.values() for band in spec["bands"]})
        if any(grid.descriptions.count(band) != 1 for band in names):
            raise ValueError("Missing or ambiguous preview source bands")
        arrays = dict(zip(names, grid.read([grid.descriptions.index(band)+1 for band in names]), strict=True))
    entries, renders = {}, {}
    acquisitions = dict(zip(SEASONS, receipt["scene_sources"], strict=True))
    windows = dict(zip(SEASONS, receipt["windows"], strict=True))
    for filename, spec in specs.items():
        layer, season = Path(filename).stem.split("_")
        sensor = "s2" if layer == "optical" else "s1"
        scene = acquisitions[season]
        scenes = [dict(id=key, acquired_utc=datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat())
                  for key, ms in zip(scene[f"{sensor}_ids"], scene[f"{sensor}_time_start_ms"], strict=True)]
        start, end = windows[season]
        if (not scenes or any(not s["id"] or not start <= s["acquired_utc"][:10] < end for s in scenes)):
            raise ValueError("Missing or out-of-window preview scene")
        content = png(render(arrays, layer, season, geometry["nodata"]))
        entries[filename] = dict(site=site, layer=layer, season=season, window=windows[season],
                                 scenes=scenes, render=spec, png_sha256=sha256(content).hexdigest())
        renders[filename] = content
    manifest = dict(schema=1, site=site, source_raster=source.relative_to(outputs).as_posix(),
                    source_sha256=source_hash, feature_receipt_sha256=digest(receipt_path),
                    inventory_sha256=inventory_hash, grid=geometry, previews=entries)
    return manifest, renders


def build(outputs, output, site):
    manifest, renders = expected(outputs, site)
    output.mkdir(parents=True, exist_ok=True)
    for filename, content in renders.items():
        (output / filename).write_bytes(content)
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def verify(outputs, folder, site):
    manifest, renders = expected(outputs, site)
    path = folder / "manifest.json"
    if json.loads(path.read_bytes()) != manifest:
        raise ValueError("Preview manifest does not match the frozen raster, grid or render settings")
    verified = {}
    for filename, expected_png in renders.items():
        content = (folder / filename).read_bytes()
        if (sha256(content).hexdigest() != manifest["previews"][filename]["png_sha256"]
                or not np.array_equal(rgba(content), rgba(expected_png))):
            raise ValueError(f"Preview PNG pixels or hash differ: {site}/{filename}")
        verified[filename] = content
    return digest(path), verified


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--outputs", type=Path, default=Path("outputs"))
    cli.add_argument("--sites", nargs="+", choices=SITES, default=SITES)
    args = cli.parse_args()
    for site in args.sites:
        folder = args.outputs / "phase18b_previews" / site
        build(args.outputs, folder, site)
        print(site, verify(args.outputs, folder, site)[0])


if __name__ == "__main__":
    main()
