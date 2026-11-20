"""Phase 22R: agreement of the 18 frozen temporal disturbance clusters with independently
published products (Hansen/UMD GFC v1.13 forest loss; WRI/Google DeepMind drivers of forest
loss 1 km v1.2). Agreement study only: no mining precision/recall/F1/accuracy.

  --preregister  freeze clusters, background and protocol (offline)
  --acquire      <= 8 EE requests, <= 1 MB (planned: 2 requests)
  --analyze      offline statistics -> docs/reports/phase22r-summary.json

Candidates remain UNKNOWN. Agreement does not establish mining, illegality or confirmed loss.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, label

from scripts.phase22p_sar_corroboration import save, sha

PREREG = Path("docs/reports/phase22r-preregistration.json")
SUMMARY = Path("docs/reports/phase22r-summary.json")
OUT = Path("outputs/phase22r_products")
CRS, SIZE, STEP = "EPSG:32646", 64, 30
HANSEN = "UMD/hansen/global_forest_change_2025_v1_13"
DRIVERS = "projects/landandcarbon/assets/wri_gdm_drivers_forest_loss_1km/v1_2_2001_2024"
DRIVER_CLASSES = {1: "Permanent agriculture", 2: "Hard commodities", 3: "Shifting cultivation", 4: "Logging",
                  5: "Wildfire", 6: "Settlements and infrastructure", 7: "Other natural disturbances"}
BANDS = ("lossyear", "treecover2000", "datamask", "driver_class", "hard_commodities_p250")
BUDGET = dict(max_requests=8, max_bytes=1_000_000)
BUFFER_CELLS, DRAWS, SEED = 2, 10000, 46
RECENT = (24, 25)  # GFC lossyear codes for 2024 and 2025


# ------------------------------------------------------------------ pure logic
def background_mask(eligible, cand, buffer_cells=BUFFER_CELLS):
    """Eligible cells farther than buffer_cells (Chebyshev) from any candidate cell."""
    near = binary_dilation(cand, structure=np.ones((3, 3), bool), iterations=buffer_cells) if cand.any() else cand
    return eligible & ~near


def clusters(cand):
    ids, n = label(cand, structure=np.ones((3, 3), int))
    return [np.argwhere(ids == i) for i in range(1, n + 1)]


def valid_offsets(cells, pool):
    """All translations placing every cell of a cluster inside the background pool."""
    r, c = np.nonzero(pool)
    out = []
    for r0, c0 in zip(r, c):
        dr, dc = r0 - cells[0, 0], c0 - cells[0, 1]
        t = cells + (dr, dc)
        if (t >= 0).all() and (t < pool.shape).all() and pool[t[:, 0], t[:, 1]].all():
            out.append((dr, dc))
    return np.array(out)


def translation_null(aois, stat, draws=DRAWS, seed=SEED):
    """Shape-preserving translation permutation, stratified by AOI.
    aois: list of (cluster_cell_arrays, pool_mask, value_grid); stat(list of per-cluster values) -> float.
    per-cluster value = value_grid over the cluster cells reduced by `reduce` inside stat inputs."""
    rng = np.random.default_rng(seed)
    offs = [[valid_offsets(c, pool) for c in cl] for cl, pool, _ in aois]
    null = np.empty(draws)
    for i in range(draws):
        vals = []
        for (cl, _, grid), o in zip(aois, offs):
            for cells, oo in zip(cl, o):
                dr, dc = oo[rng.integers(len(oo))]
                t = cells + (dr, dc)
                vals.append(grid[t[:, 0], t[:, 1]])
        null[i] = stat(vals)
    obs = stat([grid[c[:, 0], c[:, 1]] for cl, _, grid in aois for c in cl])
    centre = np.median(null)
    p = float((1 + np.sum(np.abs(null - centre) >= abs(obs - centre))) / (1 + draws))
    return float(obs), dict(null_median=float(centre), null_p2_5=float(np.percentile(null, 2.5)),
                            null_p97_5=float(np.percentile(null, 97.5)), p_two_sided=p)


def frac_any(vals):
    return float(np.mean([v.any() for v in vals]))


def mean_of_means(vals):
    return float(np.mean([v.mean() for v in vals]))


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]


# ------------------------------------------------------------------ frozen inputs
def load_aois():
    import rasterio
    from scripts.phase22l_temporal import select_candidates
    q = json.loads(Path("docs/reports/phase22q-preregistration.json").read_bytes())
    with rasterio.open("outputs/phase22l_temporal_pilot/change.tif") as src:
        ch, b = src.read(), list(src.bounds)
    aois = {"east-94-559-c74": dict(bounds=[float(x) for x in b], eligible=ch[0] == 1, cand=ch[1] == 1,
                                    source="outputs/phase22l_temporal_pilot/change.tif")}
    for aoi, row in q["aois"].items():
        src = Path(f"outputs/phase22q_multi_aoi/{aoi}_s2.npy")
        v = np.load(src).astype(float)
        v[v == -9999] = np.nan
        eligible, cand, _, _ = select_candidates(v[:6], v[7:13], v[6], v[13], v[14])
        aois[aoi] = dict(bounds=[float(x) for x in row["guard"]["bounds"]], eligible=eligible, cand=cand, source=str(src))
    return aois


def preregister():
    from scripts.phase22n_temporal import guards
    from scripts.phase22q_multi_aoi import guard
    area, protected = guards()
    aois, rows = load_aois(), {}
    OUT.mkdir(parents=True, exist_ok=True)
    for aoi, a in aois.items():
        g = guard(a["bounds"], area, protected)
        if not g["eligible"]:
            raise ValueError(f"{aoi} fails the full-footprint guard")
        bg = background_mask(a["eligible"], a["cand"])
        np.savez_compressed(OUT / f"{aoi}_frozen.npz", eligible=a["eligible"], cand=a["cand"], background=bg)
        rows[aoi] = dict(guard=g, source=a["source"], source_sha256=sha(a["source"]),
                         frozen_masks_sha256=sha(OUT / f"{aoi}_frozen.npz"),
                         eligible_cells=int(a["eligible"].sum()), candidate_cells=int(a["cand"].sum()),
                         clusters=len(clusters(a["cand"])), background_cells=int(bg.sum()))
    n = sum(r["clusters"] for r in rows.values())
    if n != 18:
        raise ValueError(f"Expected 18 frozen clusters, found {n}")
    save(PREREG, dict(
        phase="22R", date=datetime.now(timezone.utc).date().isoformat(), budget=BUDGET, aois=rows, total_clusters=n,
        products=dict(
            hansen=dict(asset=HANSEN, bands=["lossyear", "treecover2000", "datamask"], native_m=27.83,
                        lossyear="1-25 = 2001-2025; 0/no loss masked -> unmasked to 0", coverage="2000-2025",
                        licence="CC-BY-4.0", citation="Hansen et al. 2013 Science 342:850; GFC v1.13"),
            drivers=dict(asset=DRIVERS, bands=["classification", "probability_2"], native_m=1111.95,
                         classes=DRIVER_CLASSES, probability_scale="0-250, x0.004", coverage="dominant driver of GFC v1.12 loss 2001-2024",
                         licence="CC-BY-4.0", citation="Sims et al. 2025 ERL 20:074027"),
            catalog_verified="Earth Engine catalog pages read 2026-11-20; asset metadata re-checked by the first acquisition request"),
        sampling="both products sampled on the frozen 30 m EPSG:32646 AOI grids by Earth Engine default nearest-neighbour "
                 "reprojection (cell-centre rule); 1 km driver cells identified locally from the driver projection",
        background=f"eligible AOI cells more than {BUFFER_CELLS} cells (60 m, Chebyshev) from any candidate cell",
        units=dict(primary="cluster (n=18)", secondary="30 m cell (descriptive)", drivers_effective="distinct 1 km driver cells"),
        hypotheses=dict(
            H1="clusters overlap GFC loss in 2024 or 2025 (lossyear 24/25) more often than shape-preserving random placements",
            H2="clusters have higher mean hard-commodities probability than random placements",
            context="loss before 2024 (lossyear 1-23) and treecover2000 reported descriptively"),
        uncertainty=f"shape-preserving translation permutation within each AOI's background, stratified by AOI, {DRAWS} draws, "
                    f"seed {SEED}; two-sided p around the null median; Wilson 95% CI for cluster fractions",
        null_outcomes="zero overlap, equal or lower agreement, masked driver cells and AOIs without driver data are reported as measured",
        exclusions=dict(test="all TEST blocks/tiles; never opened", not_tuned="22L rule thresholds unchanged; no classifier trained"),
        forbidden_metrics="no mining precision, recall, F1 or accuracy",
        limitations=["1 km driver cells are larger than the 1.92 km AOI's internal structure: candidates and background share few cells, "
                     "so H2 has very low power and is expected to be near null",
                     "drivers describe 2001-2024 dominant driver, not the 2023-25 seasonal change; hard commodities include energy infrastructure",
                     "GFC loss needs prior tree cover and Landsat-scale stand-replacement; small, partial or non-forest change is missed",
                     "GFC annual years do not match the Nov-Mar seasons; 2024 and 2025 are pooled",
                     "east-90-562 and west-85-563 share Sentinel-2 acquisitions; cells within AOIs are spatially dependent"],
        interpretation="independent-product agreement; candidates remain UNKNOWN; not mining or loss confirmation"))
    print(json.dumps({k: (v["candidate_cells"], v["clusters"], v["background_cells"]) for k, v in rows.items()}))


# ------------------------------------------------------------------ acquisition
def acquire():
    import ee
    from src.gee_setup import initialize
    plan = json.loads(PREREG.read_bytes())
    for aoi, r in plan["aois"].items():
        if sha(r["source"]) != r["source_sha256"] or sha(OUT / f"{aoi}_frozen.npz") != r["frozen_masks_sha256"]:
            raise ValueError(f"{aoi}: frozen input changed")
    if (OUT / "products.json").exists():
        raise ValueError("Products already acquired")
    initialize()
    log = []

    def get(what, obj):
        if len(log) + 1 > BUDGET["max_requests"]:
            raise RuntimeError("request cap")
        out = obj.getInfo()
        log.append(dict(request=what, response_bytes=len(json.dumps(out).encode())))
        if sum(x["response_bytes"] for x in log) > BUDGET["max_bytes"]:
            raise RuntimeError("byte cap")
        return out

    h, d = ee.Image(HANSEN), ee.Image(DRIVERS)
    meta = get("catalog_metadata", ee.Dictionary(dict(
        hansen_bands=h.bandNames(), drivers_bands=d.bandNames(),
        drivers_projection=d.select("classification").projection(), hansen_scale=h.select("lossyear").projection().nominalScale())))
    if not {"lossyear", "treecover2000", "datamask"} <= set(meta["hansen_bands"]) or \
            not {"classification", "probability_2"} <= set(meta["drivers_bands"]):
        raise ValueError(f"Unexpected bands: {meta}")
    img = ee.Image.cat([h.select("lossyear").unmask(0), h.select("treecover2000"), h.select("datamask"),
                        d.select("classification").unmask(0), d.select("probability_2").unmask(-1)]).rename(list(BANDS)).toInt16()
    samples = {}
    for aoi, r in plan["aois"].items():
        x0, y0, x1, y1 = r["guard"]["bounds"]
        region = ee.Geometry.Rectangle([x0, y0, x1, y1], CRS, False)
        samples[aoi] = img.reproject(crs=CRS, crsTransform=[STEP, 0, x0, 0, -STEP, y1]).sampleRectangle(region=region, defaultValue=-9)
    data = get("aoi_samples", ee.Dictionary(samples))
    grids = {}
    for aoi, feat in data.items():
        arr = np.array([feat["properties"][b] for b in BANDS])
        if arr.shape != (len(BANDS), SIZE, SIZE):
            raise ValueError(f"{aoi}: unexpected sample shape {arr.shape}")
        grids[aoi] = arr.tolist()
    save(OUT / "products.json", dict(metadata=meta, bands=list(BANDS), grids=grids, log=log,
                                     requests=len(log), response_bytes=sum(x["response_bytes"] for x in log)))
    print("requests", len(log), "bytes", sum(x["response_bytes"] for x in log))


# ------------------------------------------------------------------ analysis
def driver_cell_ids(bounds, projection):
    """1 km driver-cell (col,row) index for each 30 m cell centre, from the driver projection."""
    from pyproj import Transformer
    a, b, c, d, e, f = projection["transform"]
    x0, y0, x1, y1 = bounds
    xs = x0 + (np.arange(SIZE) + .5) * STEP
    ys = y1 - (np.arange(SIZE) + .5) * STEP
    X, Y = np.meshgrid(xs, ys)
    lon, lat = Transformer.from_crs(CRS, projection["crs"], always_xy=True).transform(X, Y)
    col = np.floor((lon - c) / a).astype(int)
    row = np.floor((lat - f) / e).astype(int)
    return col * 100000 + row


def analyze():
    plan = json.loads(PREREG.read_bytes())
    prod = json.loads((OUT / "products.json").read_bytes())
    res = dict(phase="22R", preregistration_sha256=sha(PREREG), aois={},
               cloud_usage=dict(requests=prod["requests"], response_bytes=prod["response_bytes"]),
               products=dict(hansen=HANSEN, drivers=DRIVERS))
    strata_h, strata_d, all_h, all_d = [], [], [], []
    for aoi, r in plan["aois"].items():
        m = np.load(OUT / f"{aoi}_frozen.npz")
        cand, bg = m["cand"], m["background"]
        g = dict(zip(BANDS, np.array(prod["grids"][aoi])))
        land = g["datamask"] == 1
        bg = bg & land
        recent = np.isin(g["lossyear"], RECENT)
        prior = (g["lossyear"] >= 1) & (g["lossyear"] <= 23)
        hp = np.where(g["hard_commodities_p250"] >= 0, g["hard_commodities_p250"] * 0.004, np.nan)
        ids = driver_cell_ids(r["guard"]["bounds"], prod["metadata"]["drivers_projection"])
        for cid in np.unique(ids):  # nearest-neighbour samples must be constant within a driver cell
            vals = g["driver_class"][ids == cid]
            if len(np.unique(vals)) > 1:
                raise ValueError(f"{aoi}: driver values vary within cell {cid}; grid assumption broken")
        cl = clusters(cand)
        per = []
        for i, c in enumerate(cl, 1):
            rr, cc = c[:, 0], c[:, 1]
            per.append(dict(cluster=f"C{i:03d}", cells=len(c), recent_loss_cells=int(recent[rr, cc].sum()),
                            loss_2024_cells=int((g["lossyear"][rr, cc] == 24).sum()), loss_2025_cells=int((g["lossyear"][rr, cc] == 25).sum()),
                            prior_loss_cells=int(prior[rr, cc].sum()), treecover2000_mean=float(g["treecover2000"][rr, cc].mean()),
                            driver_classes=sorted({DRIVER_CLASSES.get(int(v), "masked/none") for v in g["driver_class"][rr, cc]}),
                            hard_commodities_p_mean=float(np.nanmean(hp[rr, cc])) if np.isfinite(hp[rr, cc]).any() else None,
                            driver_cells=sorted({int(v) for v in ids[rr, cc]})))
        cand_cells = cand & land
        out = dict(clusters=per, candidate_cells=int(cand.sum()), background_cells=int(bg.sum()),
                   cell_level=dict(candidate_recent_loss_fraction=float(recent[cand_cells].mean()),
                                   background_recent_loss_fraction=float(recent[bg].mean()),
                                   candidate_prior_loss_fraction=float(prior[cand_cells].mean()),
                                   background_prior_loss_fraction=float(prior[bg].mean()),
                                   candidate_treecover2000_mean=float(g["treecover2000"][cand_cells].mean()),
                                   background_treecover2000_mean=float(g["treecover2000"][bg].mean())),
                   drivers=dict(aoi_driver_cells=int(len(np.unique(ids))),
                                candidate_driver_cells=int(len(np.unique(ids[cand]))),
                                aoi_cells_by_class={DRIVER_CLASSES.get(int(k), "masked/none"): int(v) for k, v in
                                                    zip(*np.unique(g["driver_class"], return_counts=True))},
                                candidate_hard_commodities_p_mean=float(np.nanmean(hp[cand])) if np.isfinite(hp[cand]).any() else None,
                                background_hard_commodities_p_mean=float(np.nanmean(hp[bg])) if np.isfinite(hp[bg]).any() else None,
                                hard_commodities_dominant_cells=int((g["driver_class"] == 2).sum())))
        k = sum(p["recent_loss_cells"] > 0 for p in per)
        out["clusters_with_recent_loss"] = [int(k), len(per)]
        res["aois"][aoi] = out
        strata_h.append((cl, bg, recent))
        if np.isfinite(hp[bg]).any() and np.isfinite(hp[cand]).all():
            strata_d.append((cl, bg & np.isfinite(hp), np.nan_to_num(hp)))
        else:
            res["aois"][aoi]["drivers"]["H2_status"] = "INSUFFICIENT_DATA (masked driver cells)"
    k = sum(v["clusters_with_recent_loss"][0] for v in res["aois"].values())
    n = sum(v["clusters_with_recent_loss"][1] for v in res["aois"].values())
    obs, null = translation_null(strata_h, frac_any)
    res["H1_recent_loss"] = dict(clusters_with_2024_2025_loss=[k, n], fraction=obs, wilson95=wilson(k, n), translation_null=null)
    if strata_d:
        obs, null = translation_null(strata_d, mean_of_means)
        res["H2_hard_commodities"] = dict(aois=len(strata_d), clusters=sum(len(s[0]) for s in strata_d),
                                          mean_cluster_probability=obs, translation_null=null,
                                          distinct_candidate_driver_cells=int(sum(v["drivers"]["candidate_driver_cells"] for v in res["aois"].values())))
    else:
        res["H2_hard_commodities"] = dict(status="INSUFFICIENT_DATA")
    res["interpretation"] = "independent-product agreement only; candidates remain UNKNOWN; no mining accuracy metrics"
    save(SUMMARY, res)
    print(json.dumps({k: res[k] for k in ("H1_recent_loss", "H2_hard_commodities", "cloud_usage")}, indent=1))
    for aoi, v in res["aois"].items():
        print(aoi, v["clusters_with_recent_loss"], v["cell_level"], v["drivers"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--acquire", "--analyze"):
        g.add_argument(f, action="store_true")
    x = ap.parse_args()
    (preregister if x.preregister else acquire if x.acquire else analyze)()
