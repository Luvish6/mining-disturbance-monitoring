"""Prepare a local PlanetScope comparison from authorized files and documented controls."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import rasterio
from rasterio.plot import plotting_extent
from rasterio.windows import Window, from_bounds
from pyproj import Transformer
from shapely import transform as project_geometry
from shapely.geometry import MultiPoint, box, shape

from config.settings import BEFORE, AFTER
from src.phase3.data import digest, save_json

IDS = ("20240325_043545_49_24dd", "20250326_044548_96_2521")
BANDS = ("coastalblue", "blue", "greeni", "green", "yellow", "red", "rededge", "nir")


def normalized(text):
    return "".join(c for c in text.lower() if c.isalnum())


def metadata(path, scene_id, season):
    item = json.loads(path.read_text(encoding="utf-8-sig"))
    props = item["properties"]
    acquired = datetime.fromisoformat(props["acquired"].replace("Z", "+00:00"))
    if acquired.tzinfo is None:
        raise ValueError("Planet acquisition timestamp requires a timezone")
    acquired = acquired.astimezone(timezone.utc)
    if (item["id"] != scene_id or f"{acquired:%Y%m%d_%H%M%S}_{acquired.microsecond // 10000:02d}" != scene_id[:18]
            or not season.start <= acquired.date().isoformat() < season.end):
        raise ValueError("Scene ID or acquisition time differs from the selected season")
    return acquired.isoformat()


def clear_pixels(sr, udm):
    if udm.shape[0] != 8 or (udm[:6] > 1).any() or (udm[6] > 100).any():
        raise ValueError("Unexpected UDM2 flag or confidence values")
    valid = (sr > 0).all(axis=0)
    clear = valid & (udm[0] == 1) & (udm[1:6] == 0).all(axis=0) & (udm[7] == 0)
    return clear, dict(cells=clear.size, clear=int(clear.sum()), cloud=int((valid & (udm[5] == 1)).sum()),
                       cloud_shadow=int((valid & (udm[2] == 1)).sum()), missing_sr=int((~valid).sum()))


def load_scene(directory, scene_id, season, bounds):
    paths = {key: directory / name for key, name in dict(
        sr=f"{scene_id}_3B_AnalyticMS_SR_8b.tif", udm=f"{scene_id}_3B_udm2.tif",
        item=f"{scene_id}.json").items()}
    missing = [p.name for p in paths.values() if not p.is_file()]
    if missing:
        raise ValueError(f"Missing authorized Planet files: {', '.join(missing)}")
    acquired = metadata(paths["item"], scene_id, season)
    footprint = shape(json.loads(paths["item"].read_text(encoding="utf-8-sig"))["geometry"])
    if footprint.geom_type not in ("Polygon", "MultiPolygon") or not footprint.is_valid or footprint.is_empty:
        raise ValueError("Invalid provider scene footprint")
    with rasterio.open(paths["sr"], "r") as src, rasterio.open(paths["udm"], "r") as udm:
        if (src.driver != "GTiff" or udm.driver != "GTiff" or src.count != 8 or udm.count != 8
                or set(src.dtypes) != {"uint16"} or set(udm.dtypes) != {"uint8"}
                or src.nodata not in (None, 0) or src.crs is None or not src.crs.is_projected
                or src.crs.linear_units.lower() not in ("metre", "meter")
                or src.crs != udm.crs or src.transform != udm.transform or src.shape != udm.shape):
            raise ValueError("Invalid 8-band Planet SR/UDM2 pair or mismatched grids")
        a = src.transform
        if a.b or a.d or a.a <= 0 or a.e >= 0:
            raise ValueError("Expected a north-up native grid")
        if any(src.descriptions) and tuple(normalized(s or "").replace("nearinfrared", "nir") for s in src.descriptions) != BANDS:
            raise ValueError("GeoTIFF descriptions conflict with Planet's eight-band order")
        project = Transformer.from_crs(4326, src.crs.to_string(), always_xy=True)
        footprint = project_geometry(footprint, project.transform, interleaved=False)
        if not box(*src.bounds).covers(box(*bounds)) or not footprint.covers(box(*bounds)):
            raise ValueError("Review bounds are outside the scene footprint")
        w = from_bounds(*bounds, transform=a)
        col, row = max(0, math.floor(w.col_off)), max(0, math.floor(w.row_off))
        right = min(src.width, math.ceil(w.col_off + w.width))
        bottom = min(src.height, math.ceil(w.row_off + w.height))
        window = Window(col, row, right-col, bottom-row)
        if not 1 <= window.width * window.height <= 1_000_000:
            raise ValueError("Choose a review area of at most one million native cells per scene")
        values = src.read(window=window, masked=True).filled(0)
        flags = udm.read(window=window)
        # An explicit dataset mask marks missing observations. Band-wise zeros
        # encode UDM classes and are intentionally interpreted as flag values.
        invalid = udm.dataset_mask(window=window) == 0 if udm.nodata is None else np.zeros(values.shape[1:], bool)
        flags[7, invalid] = 255
        transform = src.window_transform(window)
        clear, qa = clear_pixels(values, flags)
        if not clear.any():
            raise ValueError("No clear native cells in the review area")
        info = dict(id=scene_id, acquired_utc=acquired, crs=src.crs.to_string(),
                    source_bounds=list(src.bounds), provider_footprint_bounds=list(footprint.bounds), crop_transform=list(transform)[:6],
                    band_order=BANDS, descriptions=src.descriptions, qa=qa)
    info["sha256"] = {p.name:digest(p) for p in paths.values()}
    return values, clear, transform, info


def check_controls(controls, scenes, bounds):
    """Compare manually verified stable controls in metres without warping."""
    if len(controls) < 3:
        raise ValueError("At least three distributed stable controls are required")
    reference = []
    offsets = []
    for point in controls:
        xy = point["reference_xy"]
        if not box(*bounds).covers(MultiPoint([xy])):
            raise ValueError("Reference control outside review bounds")
        reference.append(xy)
        measured = [point["before_xy"], point["after_xy"]]
        for coords, (_, clear, transform, _) in zip(measured, scenes, strict=True):
            col, row = (~transform) * tuple(coords)
            if not (0 <= col < clear.shape[1] and 0 <= row < clear.shape[0]
                    and clear[math.floor(row), math.floor(col)]):
                raise ValueError("Control is outside clear native support")
        offsets.append(dict(relative_m=math.dist(*measured),
                            before_to_control_m=math.dist(measured[0], xy),
                            after_to_control_m=math.dist(measured[1], xy)))
    if MultiPoint(reference).convex_hull.area <= 0:
        raise ValueError("Stable controls must be non-collinear")
    return offsets


def common_clear(scenes, bounds):
    _, before, first, _ = scenes[0]
    _, after, second, _ = scenes[1]
    row, col = np.nonzero(before)
    x, y = first * (col + .5, row + .5)
    u, v = (~second) * (x, y)
    ix, iy = np.floor(u).astype(int), np.floor(v).astype(int)
    inside = ((x >= bounds[0]) & (x < bounds[2]) & (y >= bounds[1]) & (y < bounds[3])
              & (ix >= 0) & (ix < after.shape[1]) & (iy >= 0) & (iy < after.shape[0]))
    if not inside.any():
        return 0
    return int(after[iy[inside], ix[inside]].sum())


def prepare(directory, plan_path, output):
    if output.exists():
        raise ValueError("Use a new output directory")
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    bounds = plan["bounds"]
    if len(bounds) != 4 or not all(math.isfinite(v) for v in bounds) or not (
        bounds[0] < bounds[2] and bounds[1] < bounds[3]
    ):
        raise ValueError("Invalid review bounds")
    if (plan.get("local_review_permitted") is not True or not plan.get("usage_document")
            or not plan.get("control_source")):
        raise ValueError("Document usage rights and independent control provenance")
    error = plan["control_error_m"]
    if isinstance(error, bool) or not math.isfinite(error) or not 0 <= error <= 30:
        raise ValueError("Document finite control positional uncertainty of at most 30 m")
    scenes = [load_scene(directory, scene_id, season, bounds)
              for scene_id, season in zip(IDS, (BEFORE, AFTER), strict=True)]
    if any(scene[3]["crs"] != plan["crs"] for scene in scenes):
        raise ValueError("Both scenes and controls must use the declared projected CRS")
    paired_clear = common_clear(scenes, bounds)
    if not paired_clear:
        raise ValueError("No sampled overlap of clear native cells")
    offsets = check_controls(plan["controls"], scenes, bounds)
    max_residual = max(max(row.values()) for row in offsets)
    if error + max_residual > 30:
        raise ValueError("Observed control residuals plus documented control error exceed 30 m")

    # Compare native windows side by side. No resampling or registration correction.
    from matplotlib import pyplot as plt
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / "review"
        stage.mkdir()
        figure, axes = plt.subplots(1, 2, figsize=(10, 5), layout="constrained")
        for ax, (values, clear, transform, info) in zip(axes, scenes, strict=True):
            rgb = np.clip(values[[5, 3, 1]].transpose(1,2,0)/3500, 0, 1)
            rgb[~clear] = .35
            ax.imshow(rgb, extent=plotting_extent(clear, transform), interpolation="nearest")
            ax.set(xlim=(bounds[0], bounds[2]), ylim=(bounds[1], bounds[3]),
                   title=info["acquired_utc"], xlabel="Easting (m)")
        axes[0].set_ylabel("Northing (m)")
        figure.suptitle("PlanetScope local manual review · fixed RGB display stretch\n"
                        "Grey indicates excluded UDM2 or missing SR cells")
        figure.savefig(stage / "comparison.png", dpi=150)
        plt.close(figure)
        save_json(stage / "review.json", dict(
            status="awaiting independent interpretation", scenes=[scene[3] for scene in scenes],
            review_bounds=bounds, crs=plan["crs"], plan_sha256=digest(plan_path),
            paired_clear_before_cell_centres=paired_clear,
            usage_document=plan["usage_document"], control_source=plan["control_source"],
            control_error_m=error, control_residuals=offsets,
            limitation="Sampled controls do not establish polygon-wide positional accuracy. "
                       "Cloud-shadow masks do not resolve terrain shadow. Independent admission remains pending."))
        stage.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.directory.resolve()):
        parser.error("Use a separate output directory outside the source tree")
    try:
        prepare(args.directory, args.plan, args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Planet preflight stopped: {exc}\n")


if __name__ == "__main__":
    main()
