"""Offline connected-component analysis of the six existing real Phase 6B tiles."""
import argparse
import csv
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import scipy
from scipy.ndimage import label
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from scripts import phase7_real_change as base
from src.phase3.data import digest, save_json

LEVELS = {"low": (1., .03), "middle": (2., .06), "high": (3., .09)}
STEP = 30
MIN_CELLS = 4
RETAIN = .25


def masks(arrays, common, radar_cut, optical_cut):
    result = {}
    for band in base.CHANGE:
        cut = radar_cut if band in base.CHANGE[:2] else optical_cut
        result[f"{band}_down"] = common & (arrays[band] <= -cut)
        result[f"{band}_up"] = common & (arrays[band] >= cut)
    result["radar"] = result["dVV_down"] | result["dVH_down"]
    result["optical"] = result["dNDVI_down"] | result["dNDTI_up"]
    result["joint"] = result["radar"] & result["optical"]
    return result


def overlap(a, b, valid):
    joint = int((a & b & valid).sum())
    a_only = int((a & ~b & valid).sum())
    b_only = int((b & ~a & valid).sum())
    n = int(valid.sum())
    union = joint + a_only + b_only

    def ratio(num, den):
        return num / den if den else None

    return dict(valid_cells=n, joint=joint, radar_only=a_only, optical_only=b_only,
                neither=n-union, union=union, jaccard=ratio(joint, union),
                optical_given_radar=ratio(joint, joint+a_only),
                radar_given_optical=ratio(joint, joint+b_only))


def component_geometry(mask, bounds):
    y, x = np.nonzero(mask)
    left, _, _, top = bounds
    n = len(x)
    shared = (mask[1:] & mask[:-1]).sum() + (mask[:,1:] & mask[:,:-1]).sum()
    return dict(cells=n, area_m2=n*STEP**2, perimeter_m=int((4*n-2*shared)*STEP),
                centroid_easting_m=float(left+(x.mean()+.5)*STEP),
                centroid_northing_m=float(top-(y.mean()+.5)*STEP),
                touches_tile_edge=bool(mask[0].any() or mask[-1].any() or
                                       mask[:,0].any() or mask[:,-1].any()))


def fragment_counts(low, other):
    labels = other[low]
    counts = np.bincount(labels)[1:]
    return int(counts.sum()), int(np.count_nonzero(counts)), int(counts.max(initial=0))


def persistence(cells, high_largest):
    if cells < MIN_CELLS:
        return "below_reporting_floor"
    return "persistent" if high_largest >= MIN_CELLS and high_largest/cells >= RETAIN else "threshold_sensitive"


def analyze(tile):
    arrays, valid = tile["arrays"], tile["common"]
    info = dict(tile=tile["id"], district=tile["district"], split=tile["split"], block=tile["block"])
    levels = {key: masks(arrays, valid, *cuts) for key, cuts in LEVELS.items()}
    components, sensitivity, overlaps, sizes = [], [], [], []
    labeled = {}
    for level, fields in levels.items():
        labeled[level] = {}
        for key, mask in fields.items():
            labels, count = label(mask)
            labeled[level][key] = labels
            pixel_counts = np.bincount(labels.ravel())[1:]
            sizes.append(dict(info, level=level, pattern=key, cells=int(mask.sum()),
                              components=count, largest_cells=int(pixel_counts.max(initial=0))))
            for number in range(1, count+1):
                mask = labels == number
                geometry = component_geometry(mask, tile["bounds"])
                components.append(dict(info, level=level, pattern=key, component=number, **geometry,
                    median_elevation_m=float(np.median(arrays["elevation"][mask])),
                    median_slope_deg=float(np.median(arrays["slope"][mask])),
                    median_min_optical_count=float(np.median(arrays["optical_min"][mask]))))
        overlaps.append(dict(info, level=level, comparison="directional_unions",
                             **overlap(fields["radar"], fields["optical"], valid)))
        for a in base.CHANGE[:2]:
            for b in base.CHANGE[2:]:
                overlaps.append(dict(info, level=level, comparison=f"absolute_{a}_{b}",
                    **overlap(fields[f"{a}_up"] | fields[f"{a}_down"],
                              fields[f"{b}_up"] | fields[f"{b}_down"], valid)))
    for row in components:
        if row["level"] != "low":
            continue
        key = row["pattern"]
        mask = labeled["low"][key] == row["component"]
        m, mparts, mmax = fragment_counts(mask, labeled["middle"][key])
        h, hparts, hmax = fragment_counts(mask, labeled["high"][key])
        sensitivity.append(dict(row, middle_cells=m, middle_fragments=mparts, middle_largest=mmax,
            high_cells=h, high_fragments=hparts, high_largest=hmax,
            high_largest_fraction=hmax/row["cells"], persistence=persistence(row["cells"], hmax)))
    return dict(components=components, threshold_sensitivity=sensitivity,
                overlap=overlaps, pattern_sizes=sizes), levels, labeled


def tile_maps(tile, levels, output):
    fig, axes = base.plt.subplots(2, 3, figsize=(12,8), layout="constrained")
    x0,y0,x1,y1 = tile["bounds"]
    extent = (x0,x1,y0,y1)
    for ax, key in zip(axes.flat, base.CHANGE):
        values = np.ma.array(tile["arrays"][key], mask=~tile["common"])
        cut = base.DISPLAY[key]
        image = ax.imshow(values, extent=extent, interpolation="nearest", cmap="RdBu_r",
                          vmin=-cut, vmax=cut)
        ax.set_title(key)
        fig.colorbar(image, ax=ax, label=base.UNITS[key], extend="both", shrink=.75)
    for ax, level in zip(axes.flat[4:], ("low", "high")):
        fields = levels[level]
        categories = fields["radar"].astype(int) + 2*fields["optical"]
        ax.imshow(np.ma.array(categories, mask=~tile["common"]), extent=extent,
                  interpolation="nearest", vmin=0, vmax=3,
                  cmap=ListedColormap(["#eeeeee","#3266a1","#d08a25","#4d346e"]))
        r, o = LEVELS[level]
        ax.set_title(f"{level.title()} directional masks · {r:g} dB / {o:g}")
    for ax in axes.flat:
        ax.set_xticks([x0,x1])
        ax.set_yticks([y0,y1])
        ax.ticklabel_format(style="plain", useOffset=False)
        ax.tick_params(labelsize=7)
    fig.legend(handles=[Patch(color=c,label=n) for c,n in zip(
        ("#eeeeee","#3266a1","#d08a25","#4d346e"), ("Neither","Radar only","Optical only","Both"))],
        loc="outside lower center", ncols=4, frameon=False)
    fig.suptitle(f"{tile['id']} · {tile['split']} · EPSG:32646, metres · 30 m cells, north up\n{base.PERIOD}")
    fig.savefig(output / f"{tile['id']}_patterns.png", dpi=150)
    base.plt.close(fig)


def examples(sensitivity, indexed, output):
    chosen = []
    for status in ("persistent", "threshold_sensitive"):
        eligible = [r for r in sensitivity if r["pattern"] == "joint" and r["persistence"] == status]
        if not eligible:
            continue
        row = min(eligible, key=lambda r: (-r["cells"], r["tile"], r["component"]))
        tile, labels = indexed[row["tile"]]
        region = labels["low"]["joint"] == row["component"]
        y,x = np.nonzero(region)
        crop = (slice(max(0,y.min()-3),min(region.shape[0],y.max()+4)),
                slice(max(0,x.min()-3),min(region.shape[1],x.max()+4)))
        cropped = region[crop]
        fig, axes = base.plt.subplots(1, 3, figsize=(10,4), layout="constrained")
        for ax, level in zip(axes, LEVELS):
            current = cropped & (labels[level]["joint"][crop] > 0)
            image = cropped.astype(int) + current.astype(int)
            ax.imshow(image, interpolation="nearest", vmin=0, vmax=2,
                      cmap=ListedColormap(["#ffffff","#ccd0d5","#4d346e"]))
            ax.set_title(f"{level.title()} · {int(current.sum())} cells")
            ax.set_xticks([])
            ax.set_yticks([])
        fig.legend(handles=[Patch(color="#ccd0d5",label="Low footprint only"),
                            Patch(color="#4d346e",label="Joint mask at shown level")],
                   loc="outside lower center", ncols=2, frameon=False)
        fig.suptitle(f"{tile['id']} · joint component {row['component']} · {status.replace('_',' ')}\n"
                     f"30 m cells · median slope {row['median_slope_deg']:.1f}° · "
                     f"largest high fragment {row['high_largest']} cells")
        fig.savefig(output / f"example_{status}.png", dpi=150)
        base.plt.close(fig)
        chosen.append(row)
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("outputs/phase6b_multitile"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(args.input.resolve()):
        raise ValueError("Use a new output directory outside the source tree")
    tiles, roster_hash = base.load_tiles(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".phase7-day2-", dir=args.output.parent) as temporary:
        stage = Path(temporary)/"results"
        stage.mkdir()
        rows = {key: [] for key in ("components","threshold_sensitivity","overlap","pattern_sizes")}
        indexed = {}
        for tile in tiles:
            results, levels, labeled = analyze(tile)
            for key in rows:
                rows[key].extend(results[key])
            indexed[tile["id"]] = (tile, labeled)
            tile_maps(tile, levels, stage)
        rows["examples"] = examples(rows["threshold_sensitivity"], indexed, stage)
        for key, records in rows.items():
            with (stage/f"{key}.csv").open("w", encoding="utf-8", newline="") as stream:
                if records:
                    writer = csv.DictWriter(stream, fieldnames=list(records[0]))
                    writer.writeheader()
                    writer.writerows(records)
        verified, verified_hash = base.load_tiles(args.input)
        if verified_hash != roster_hash or any(
            a["quality_sha256"] != b["quality_sha256"] for a,b in zip(tiles,verified,strict=True)
        ):
            raise ValueError("Original receipts changed during analysis")
        spec = Path(__file__).resolve().parents[1]/"docs/reports/phase7-day2-spatial-patterns.md"
        methods = spec.read_text(encoding="utf-8-sig").split("## Results",1)[0].rstrip()
        save_json(stage/"provenance.json", dict(
            roster_sha256=roster_hash, script_sha256=digest(__file__), loader_sha256=digest(base.__file__),
            specification_sha256=sha256(methods.encode()).hexdigest(), levels=LEVELS,
            minimum_cells=MIN_CELLS, retention_fraction=RETAIN, connectivity=4, grid_m=STEP,
            crs="EPSG:32646", windows=[[s.start,s.end] for s in base.pilot.SEASONS],
            versions=dict(numpy=np.__version__, scipy=scipy.__version__,
                          matplotlib=base.matplotlib.__version__, rasterio=base.rasterio.__version__),
            sources={t["id"]:dict(hashes=t["hashes"], quality_sha256=t["quality_sha256"],
                                  scene_rows=t["sources"], extent=t["bounds"], split=t["split"]) for t in tiles},
            output_sha256={p.name:digest(p) for p in sorted(stage.iterdir())}))
        stage.rename(args.output)


if __name__ == "__main__":
    main()
