"""Check the EuroMineNet development grids and report image-grid review support."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from shapely.geometry import box
from shapely.ops import transform
from pyproj import Transformer
from PIL import Image

from scripts.eurominenet_acquire import SITES, digest, save, windows

BANDS = ("B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12")


def verified(path):
    receipt = json.loads(path.with_suffix(".json").read_bytes())
    if digest(path.read_bytes()) != receipt["sha256"]:
        raise ValueError("Member hash differs")
    return receipt["sha256"]


def load_images(site):
    images, valid, grids, hashes, metadata = [], [], [], [], []
    for year in (2023, 2024):
        path = site / "image" / f"Year{year}.tif"
        hashes.append(verified(path))
        with rasterio.open(path) as ds:
            if (not ds.crs or ds.descriptions != BANDS or ds.dtypes != ("int16",)*10
                    or ds.transform.b != 0 or ds.transform.d != 0
                    or ds.transform.a <= 0 or ds.transform.e >= 0):
                raise ValueError("Unexpected optical schema or grid")
            values = ds.read()
            support = (ds.read_masks() > 0).all(0) & np.any(values != 0, axis=0)
            images.append(values)
            valid.append(support)
            grids.append((ds.crs, ds.transform, ds.shape, ds.scales, ds.offsets))
            metadata.append(dict(nodata=ds.nodata, tags=ds.tags(), scale=ds.scales, offset=ds.offsets,
                                 min=int(values.min()), max=int(values.max()),
                                 all_zero_pixels=int((values==0).all(0).sum()),
                                 negative_cells=int((values<0).any(0).sum())))
            bbox = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds)
    if grids[0] != grids[1]:
        raise ValueError("Image year grids or scaling differ")
    return images, valid[0] & valid[1], grids[0], bbox, hashes, metadata


def load_labels(site, shape):
    labels, info, hashes = [], [], []
    for year in (2023, 2024):
        path = site / "label" / f"Year{year}.tif"
        hashes.append(verified(path))
        with Image.open(path) as picture:
            label = np.asarray(picture)
            if label.shape != shape or label.dtype != np.uint8 or not np.isin(label, [0, 255]).all():
                raise ValueError("Mask dimensions or binary encoding differ")
            labels.append(label == 255)
            info.append(dict(model_pixel_scale=picture.tag_v2.get(33550),
                             model_tiepoint=picture.tag_v2.get(33922),
                             model_transform=picture.tag_v2.get(34264),
                             geo_key_directory=picture.tag_v2.get(34735)))
    return labels, hashes, info


def support(windows_, common, labels):
    before, after = labels
    expansion, contraction = ~before & after, before & ~after
    output = []
    for r,c in windows_:
        view = np.s_[r:r+128,c:c+128]
        n = int(common[view].sum())
        add, remove = (int((v[view] & common[view]).sum()) for v in (expansion, contraction))
        output.append(dict(row=r, col=c, signal_cells=n, expansion=add,
                           contraction=remove, unchanged=n-add-remove))
    return output


def overlay(path, arrays, labels, common):
    fig, axes = plt.subplots(1, 2, figsize=(7, 4), layout="constrained")
    for year, ax, a, binary in zip((2023, 2024), axes, arrays, labels, strict=True):
        rgb = np.moveaxis(np.clip(a[[2,1,0]]/3500,0,1),0,-1)
        rgb[~common] = (1, 0, 1)
        ax.imshow(rgb, interpolation="nearest")
        if binary.any() and not binary.all():
            ax.contour(binary, levels=[.5], colors=["cyan"], linewidths=.6)
        ax.set_title(str(year))
        ax.set_axis_off()
    fig.savefig(path,dpi=105)
    plt.close(fig)


def nearby(sites):
    project = Transformer.from_crs(4326, 3035, always_xy=True).transform
    records = list(sites.items())
    pairs = []
    for i,(a,ar) in enumerate(records):
        for b,br in records[i+1:]:
            if ar["split"]==br["split"]:
                continue
            first = transform(project, box(*ar["bounds"]))
            second = transform(project, box(*br["bounds"]))
            pairs.append(dict(sites=[a,b], overlap=first.intersection(second).area,
                              distance_m=first.distance(second)))
    return sorted(pairs, key=lambda pair:pair["distance_m"])


def validate(root):
    sites, errors = {}, {}
    panels = root/"overlays"
    panels.mkdir(exist_ok=True)
    for split in ("train", "val"):
        for name in SITES[split]:
            site = root/"EuroMineNet"/name
            try:
                a, common, grid, bbox, image_hashes, metadata = load_images(site)
                origins = windows(name, grid[2])  # fixed before accessing labels
                labels, label_hashes, label_geo = load_labels(site, grid[2])
            except (ValueError, OSError) as error:
                errors[name] = str(error)
                continue
            sites[name] = dict(split=split, crs=str(grid[0]), transform=list(grid[1])[:6],
                               shape=grid[2], bounds=bbox, image_sha256=image_hashes,
                               label_sha256=label_hashes, label_geo=label_geo, image_metadata=metadata,
                               common_signal=int(common.sum()), total_pixels=common.size,
                               expansion=int((common & ~labels[0] & labels[1]).sum()),
                               contraction=int((common & labels[0] & ~labels[1]).sum()),
                               windows=support(origins, common, labels))
            overlay(panels/f"{name}.png", a, labels, common)
    save(root/"development_diagnostics.json", dict(sites=sites, errors=errors, cross_split=nearby(sites)))
    print("Structurally checked sites:", len(sites), "errors:", errors)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root",type=Path)
    validate(cli.parse_args().root)


if __name__ == "__main__":
    main()
