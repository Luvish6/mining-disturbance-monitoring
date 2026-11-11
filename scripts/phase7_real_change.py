"""Descriptive analysis of the six saved Phase 6B tiles. No network or fitting."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np
import rasterio
import scipy
from rasterio.transform import Affine
from scipy.stats import rankdata

from scripts import phase6b_multitile as pilot
from src.phase3.data import BANDS, digest, save_json

CHANGE = BANDS[8:12]
UNITS = dict(zip(CHANGE, ("dB", "dB", "unitless", "unitless")))
DISPLAY = dict(zip(CHANGE, (5, 5, .3, .3)))
CONTEXT = ("elevation", "slope", *pilot.COUNT_BANDS, "optical_min", "optical_count_change")
PERIOD = "Nov 2023–Mar 2024 vs Nov 2024–Mar 2025 · after minus before"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def raster(path, names, affine):
    with rasterio.open(path, "r") as src:
        if (src.crs is None or src.crs.to_epsg() != 32646 or src.transform != affine
                or src.descriptions != names or src.nodata != pilot.NODATA
                or src.shape != (64, 64) or set(src.dtypes) != {"float32"}):
            raise ValueError(f"Unexpected raster grid or schema in {path.name}")
        values = src.read()
        valid = (src.read_masks() > 0) & (values != pilot.NODATA) & np.isfinite(values)
    return np.where(valid, values, pilot.NODATA).astype("float32"), valid


def load_tiles(root):
    roster_path = root / "roster.json"
    roster_hash = digest(roster_path)
    roster = read(roster_path)
    rows = roster["selected"]
    if (roster["config"] != pilot.asdict(pilot.CFG) or len(rows) != 6
            or {(r["district"], r["split"]) for r in rows} != set(pilot.SLOTS)
            or len({r["id"] for r in rows}) != 6 or len({r["block"] for r in rows}) != 6
            or roster["geometry_sha256"] != digest(root / "districts.json")):
        raise ValueError("Expected the complete frozen Phase 6B roster")
    tiles = []
    for row in rows:
        folder = root / row["id"]
        quality = read(folder / "quality.json")
        source = read(folder / "sources.json")
        if (quality["tile"] != row or quality["status"] != "passed"
                or quality["roster_sha256"] != roster_hash
                or source["roster_sha256"] != roster_hash
                or source["config"] != roster["config"]
                or source["seasons"] != [pilot.asdict(s) for s in pilot.SEASONS]
                or any(digest(folder / name) != value for name, value in quality["hashes"].items())):
            raise ValueError(f"Original provenance check failed for {row['id']}")
        left, bottom, right, top = row["bounds"]
        if (pilot.block_for(row["bounds"]) != row["block"]
                or pilot.partition(row["block"]) != row["split"]
                or any(v % 30 for v in row["bounds"])
                or right-left != 1920 or top-bottom != 1920):
            raise ValueError("Frozen spatial assignment or bounds changed")
        affine = Affine(30, 0, left, 0, -30, top)
        if source["output_transform"] != list(affine)[:6] or source["output_crs"] != pilot.CRS:
            raise ValueError("Source receipt grid differs from roster")
        features, valid = raster(folder / "features.tif", BANDS, affine)
        qa, qa_valid = raster(folder / "diagnostics.tif", pilot.DIAGNOSTICS, affine)
        if not qa_valid.all():
            raise ValueError("Diagnostics must cover the complete tile footprint")
        pilot.validate_scene_rows(source["scenes"])
        limits = [len(s[key]) for key in ("s1", "s2") for s in source["scenes"]]
        checked = pilot.validate_pixels(np.concatenate((features, qa)), limits)
        if checked["valid_cells"] != quality["valid_cells"]:
            raise ValueError("Recomputed support differs from original receipt")
        common = valid.all(axis=0) & (qa[-1] == 1)
        arrays = dict(zip(BANDS + pilot.DIAGNOSTICS, np.concatenate((features, qa))))
        before, after = (arrays[f"optical_{s}_count"] for s in ("before", "after"))
        arrays.update(optical_min=np.minimum(before, after), optical_count_change=after-before)
        tiles.append(dict(row, arrays=arrays, common=common, valid=valid,
                          sources=source["scenes"], hashes=quality["hashes"],
                          quality_sha256=digest(folder / "quality.json")))
    return tiles, roster_hash


def pearson(x, y):
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def centre(a, ids):
    result = a.astype("float64", copy=True)
    for group in np.unique(ids):
        mask = ids == group
        result[mask] -= result[mask].mean()
    return result


def sign_agreement(x, y):
    nonzero = (x != 0) & (y != 0)
    sx, sy = x[nonzero] > 0, y[nonzero] > 0
    pp, pn, np_, nn = (int(mask.sum()) for mask in
                       (sx & sy, sx & ~sy, ~sx & sy, ~sx & ~sy))
    n = len(sx)
    observed = (pp + nn) / n if n else None
    expected = ((pp+pn)*(pp+np_) + (nn+np_)*(nn+pn)) / n**2 if n else None
    return dict(positive_positive=pp, positive_negative=pn, negative_positive=np_, negative_negative=nn,
                zero_excluded=len(x)-n, sign_n=n, same_sign=observed, expected_same_sign=expected,
                excess_percentage_points=100*(observed-expected) if n else None)


def statistics(values):
    n = len(values)
    quantiles = ("p05", "p25", "median", "p75", "p95")
    result = dict(n=n, negative=int((values < 0).sum()), zero=int((values == 0).sum()),
                  positive=int((values > 0).sum()), mean=float(np.mean(values)) if n else None,
                  sd=float(np.std(values, ddof=1)) if n > 1 else None,
                  minimum=float(values.min()) if n else None, maximum=float(values.max()) if n else None)
    result.update(zip(quantiles, np.percentile(values, [5,25,50,75,95], method="linear").tolist()
                      if n else [None]*5))
    return result


def groups(tiles):
    yield "combined", "all", tiles
    for field in ("district", "split", "id"):
        for value in dict.fromkeys(t[field] for t in tiles):
            yield {"split":"partition", "id":"tile"}.get(field, field), value, [t for t in tiles if t[field] == value]


def summarize(tiles):
    distribution, agreement, context, support = [], [], [], []
    for scope, group, members in groups(tiles):
        info = dict(scope=scope, group=group, tiles=len(members))
        total = sum(t["common"].size for t in members)
        vectors = {k: np.concatenate([t["arrays"][k][t["common"]] for t in members]).astype("float64")
                   for k in (*CHANGE, *CONTEXT)}
        ids = np.concatenate([np.full(int(t["common"].sum()), i) for i, t in enumerate(members)])
        centered = {k: centre(v, ids) for k, v in vectors.items()}
        for key in (*BANDS, *pilot.COUNT_BANDS, "common_valid"):
            if key in BANDS:
                n = sum(int(t["valid"][BANDS.index(key)].sum()) for t in members)
            elif key == "common_valid":
                n = len(ids)
            else:
                n = sum(int((t["arrays"][key] >= pilot.CFG.min_observations).sum()) for t in members)
            count_summary = (statistics(vectors[key]) if key in pilot.COUNT_BANDS else {})
            support.append(dict(info, field=key, footprint_n=total, supported_n=n, excluded_n=total-n,
                                count_min=count_summary.get("minimum"),
                                count_median=count_summary.get("median"),
                                count_max=count_summary.get("maximum")))
        for key in CHANGE:
            values = vectors[key]
            distribution.append(dict(info, band=key, unit=UNITS[key], footprint_n=total,
                                     **statistics(values)))
            for kind, response in (("signed", values), ("absolute", np.abs(values))):
                for covariate in CONTEXT:
                    context.append(dict(info, band=key, response=kind, covariate=covariate, n=len(ids),
                                        pearson=pearson(response, vectors[covariate]),
                                        tile_centred_pearson=pearson(centre(response, ids), centered[covariate])))
        for sar in CHANGE[:2]:
            for optical in CHANGE[2:]:
                x, y = vectors[sar], vectors[optical]
                agreement.append(dict(info, sar=sar, optical=optical, n=len(ids),
                    pearson=pearson(x,y), tile_centred_pearson=pearson(centered[sar],centered[optical]),
                    spearman=pearson(rankdata(x),rankdata(y)), **sign_agreement(x,y)))
    return dict(distributions=distribution, sar_optical_agreement=agreement,
                terrain_count_correlations=context, support=support)


def figures(tiles, output):
    fig, axes = plt.subplots(4, 6, figsize=(15, 10), layout="constrained")
    for i, band in enumerate(CHANGE):
        limit = DISPLAY[band]
        for j, t in enumerate(tiles):
            ax = axes[i,j]
            array = np.ma.array(t["arrays"][band], mask=~t["common"])
            img = ax.imshow(array, interpolation="nearest", cmap="RdBu_r", vmin=-limit, vmax=limit)
            if i == 0:
                ax.set_title(t["id"], fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.colorbar(img, ax=list(axes[i]), shrink=.85, label=f"{band} ({UNITS[band]})", extend="both")
    fig.suptitle(f"Seasonal change on six 1.92 km tiles · 30 m grid · north up\n{PERIOD}")
    fig.savefig(output/"change_maps.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(10,7), layout="constrained")
    for ax, band in zip(axes.flat, CHANGE):
        vals = [t["arrays"][band][t["common"]] for t in tiles]
        both = np.concatenate(vals)
        low, high = float(both.min()), float(both.max())
        bins = np.linspace(low, high, 61) if low < high else np.linspace(low-.5, high+.5, 61)
        for district, color in zip(pilot.DISTRICTS, ("#225d8b", "#af5418")):
            v = np.concatenate([a for t,a in zip(tiles, vals) if t["district"] == district])
            ax.hist(v, bins=bins, histtype="step", linewidth=1.6, color=color, label=district)
        ax.axvline(0, linewidth=.7, color="black")
        ax.set(xlabel=f"{band} ({UNITS[band]})", ylabel="Cell count")
    axes[0,0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"Signed-change distributions · identical bins between districts\n{PERIOD}")
    fig.savefig(output/"signed_histograms.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(10,7), layout="constrained")
    values = {k: np.concatenate([t["arrays"][k][t["common"]] for t in tiles]) for k in CHANGE}
    for ax, (sar, optical) in zip(axes.flat, [(a,b) for a in CHANGE[:2] for b in CHANGE[2:]]):
        x,y = values[sar],values[optical]
        img = ax.hexbin(x,y,gridsize=50,bins="log",mincnt=1,cmap="viridis")
        ax.axvline(0, linewidth=.7, color="gray")
        ax.axhline(0, linewidth=.7, color="gray")
        ax.set(xlabel=f"{sar} ({UNITS[sar]})", ylabel=f"{optical} ({UNITS[optical]})",
               title=f"n = {len(x):,} · Pearson r = {pearson(x,y):.3f}")
        fig.colorbar(img, ax=ax, label="Cells per hexagon (log scale)")
    fig.suptitle(f"SAR–optical change scatter density · all common-valid cells\n{PERIOD}")
    fig.savefig(output/"sar_optical_scatter.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("outputs/phase6b_multitile"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(args.input.resolve()):
        raise ValueError("Use a new output directory outside the source tree")
    tiles, roster_hash = load_tiles(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".phase7-", dir=args.output.parent) as temporary:
        stage = Path(temporary)/"results"
        stage.mkdir()
        for name, rows in summarize(tiles).items():
            with (stage/f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        figures(tiles, stage)
        verified_tiles, verified_hash = load_tiles(args.input)
        if verified_hash != roster_hash or any(a["quality_sha256"] != b["quality_sha256"]
                                                for a, b in zip(tiles, verified_tiles, strict=True)):
            raise ValueError("Frozen roster changed during analysis")
        save_json(stage/"provenance.json", dict(
            roster_sha256=roster_hash, analysis_script_sha256=digest(__file__),
            specification_sha256=sha256(
                (Path(__file__).resolve().parents[1]/"docs/reports/phase7-day1-real-change.md")
                .read_text(encoding="utf-8-sig").split("## Results", 1)[0].rstrip().encode()
            ).hexdigest(),
            versions=dict(numpy=np.__version__, scipy=scipy.__version__, matplotlib=matplotlib.__version__,
                          rasterio=rasterio.__version__),
            source="Phase 6B saved exploratory rasters", periods=[[s.start,s.end] for s in pilot.SEASONS],
            crs=pilot.CRS, grid_m=30, nodata=pilot.NODATA, display_half_ranges=DISPLAY,
            units=UNITS, methods=dict(percentiles="linear", sd_ddof=1, sign_zero="exact zero excluded",
                                      correlations="Pearson, average-tie Spearman, within-tile centered Pearson",
                                      sample="common 14-band finite valid footprint", weighting="one per cell"),
            inputs={t["id"]:dict(hashes=t["hashes"], quality_sha256=t["quality_sha256"],
                  scene_rows=t["sources"]) for t in tiles},
            output_sha256={p.name:digest(p) for p in sorted(stage.iterdir())}))
        stage.rename(args.output)


if __name__ == "__main__":
    main()
