"""Phase 22P: Sentinel-1 corroboration of the Phase 22L/22N optical disturbance candidates.

Question: do the nine optical candidate cells (NDVI drop <= -0.30 and BSI rise > +0.10)
show seasonal Sentinel-1 VV/VH change that is unusual relative to the same AOI?
Candidates remain UNKNOWN - not validated. SAR agreement is corroboration, not a label.

  --preregister  write docs/reports/phase22p-preregistration.json (offline)
  --acquire      bounded S1 fetch on the frozen Phase 22L grid (<= 8 requests, <= 2 MB)
  --analyze      offline statistics -> docs/reports/phase22p-summary.json
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

AOI = Path("outputs/phase22l_temporal_pilot")
TILE = Path("outputs/phase6b_multitile/east-94-559")
PREREG = Path("docs/reports/phase22p-preregistration.json")
SUMMARY = Path("docs/reports/phase22p-summary.json")
OUT = Path("outputs/phase22p_sar")
CRS, SIZE, STEP = "EPSG:32646", 64, 30
BANDS = ("before_VV", "before_VH", "after_VV", "after_VH", "before_count", "after_count")
RULES = dict(
    sar="Phase 2 sar.seasonal: S1 GRD IW 10 m, DESCENDING, relative orbit 77 (as Phase 6B), linear-power 20 m circular "
        "focal mean, seasonal median in dB, >=2 observations per season",
    change="dVV = after_VV - before_VV, dVH = after_VH - before_VH (dB)",
    background="Phase 22L eligible cells with valid SAR in both seasons, excluding candidate cells",
    statistic="median(candidate) - median(background), per polarisation; two-sided",
    permutation="10,000 random draws of n_candidate cells from the SAR-valid eligible pool, seed 42; "
                "p = (1 + #|null| >= |obs|) / (1 + draws)",
    cluster_level="six 8-connected cluster means vs 10,000 random draws of six background cells (seed 43)",
    co_change="candidate cell with dVH or dVV outside the background 5th-95th percentile range",
    reproduction_gate="on cells shared with Phase 6B tile east-94-559, |dVV|,|dVH| differences <= 0.01 dB else STOP",
    caveat="cells are spatially autocorrelated; permutation p-values are descriptive, not confirmatory",
)
BUDGET = dict(max_requests=8, max_bytes=2_000_000)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ pure logic
def permutation_p(cand, pool, draws=10000, seed=42):
    cand, pool = np.asarray(cand, float), np.asarray(pool, float)
    obs = np.median(cand) - np.median(pool)
    rng = np.random.default_rng(seed)
    null = np.array([np.median(rng.choice(pool, len(cand), replace=False)) for _ in range(draws)]) - np.median(pool)
    return float(obs), float((1 + np.sum(np.abs(null) >= abs(obs))) / (1 + draws))


def percentile_rank(values, pool):
    pool = np.sort(np.asarray(pool, float))
    return [float(np.searchsorted(pool, v, side="right") / len(pool) * 100) for v in values]


def co_change(cand_vv, cand_vh, pool_vv, pool_vh):
    lo_vv, hi_vv = np.percentile(pool_vv, [5, 95])
    lo_vh, hi_vh = np.percentile(pool_vh, [5, 95])
    return [bool(not (lo_vv <= a <= hi_vv) or not (lo_vh <= b <= hi_vh)) for a, b in zip(cand_vv, cand_vh)]


def tile_overlap(aoi_bounds, tile_bounds, step=STEP):
    """Row/col slices (aoi, tile) of the shared grid-aligned window."""
    ax0, ay0, ax1, ay1 = aoi_bounds
    tx0, ty0, tx1, ty1 = tile_bounds
    x0, x1, y0, y1 = max(ax0, tx0), min(ax1, tx1), max(ay0, ty0), min(ay1, ty1)
    if x1 <= x0 or y1 <= y0:
        return None
    for v in (ax0 - tx0, ay1 - ty1):
        if abs(v / step - round(v / step)) > 1e-9:
            raise ValueError("Grids are not aligned")
    a = (slice(round((ay1 - y1) / step), round((ay1 - y0) / step)), slice(round((x0 - ax0) / step), round((x1 - ax0) / step)))
    t = (slice(round((ty1 - y1) / step), round((ty1 - y0) / step)), slice(round((x0 - tx0) / step), round((x1 - tx0) / step)))
    return a, t


# ------------------------------------------------------------------ stages
def preregister():
    save(PREREG, dict(phase="22P", date=datetime.now(timezone.utc).date().isoformat(), rules=RULES, budget=BUDGET,
                      aoi="east-94-559-c74 (Phase 22L/22N TRAIN development AOI; full-footprint guard passed in 22N)",
                      inputs={p: sha(p) for p in (str(AOI / "change.tif"), str(AOI / "receipt.json"),
                                                   str(TILE / "features.tif"), str(TILE / "diagnostics.tif"))},
                      optical_rule_unchanged="NDVI decrease <= -0.30 and BSI increase > +0.10 (Phase 22L)",
                      interpretation="SAR co-change is multi-sensor corroboration of UNKNOWN candidates, not validation"))


def acquire():
    import ee
    import rasterio
    import requests
    from rasterio.io import MemoryFile
    from config.phase2_settings import Phase2Config
    from config.settings import BEFORE, AFTER
    from src.gee_setup import initialize
    from src import sar_preprocessing as sar
    plan = json.loads(PREREG.read_bytes())
    for p, h in plan["inputs"].items():
        if sha(p) != h:
            raise ValueError(f"Input hash changed: {p}")
    if OUT.exists():
        raise ValueError(f"{OUT} exists")
    with rasterio.open(AOI / "change.tif") as src:
        affine, bounds = src.transform, list(src.bounds)
    cfg = Phase2Config(relative_orbit=77)
    initialize()
    region = ee.Geometry.Rectangle(bounds, proj=CRS, geodesic=False)
    images, meta = [], {}
    for name, season in (("before", BEFORE), ("after", AFTER)):
        col = sar.collection(region, season, cfg).filter(ee.Filter.eq("relativeOrbitNumber_start", 77))
        db, count = sar.seasonal(col, 77, region, cfg)
        images += [db.select("VV").rename(f"{name}_VV"), db.select("VH").rename(f"{name}_VH")]
        meta[name] = col.sort("system:index").aggregate_array("system:index")
        images.append(count.rename(f"{name}_count"))
    image = ee.Image.cat([images[i] for i in (0, 1, 3, 4, 2, 5)]).toFloat().unmask(-9999, sameFootprint=False)
    log = []
    info = ee.Dictionary(dict(scenes=ee.Dictionary(meta), bands=image.bandNames())).getInfo()
    log.append(dict(request="scene_ids_and_bands", response_bytes=len(json.dumps(info).encode())))
    if tuple(info["bands"]) != BANDS:
        raise ValueError(f"Unexpected bands {info['bands']}")
    url = image.getDownloadURL(dict(format="GEO_TIFF", crs=CRS, crs_transform=list(affine)[:6], dimensions=[SIZE, SIZE]))
    log.append(dict(request="download_url", response_bytes=0))
    with requests.get(url, timeout=(15, 180)) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        content = r.content
    log.append(dict(request="download", response_bytes=len(content)))
    total = sum(x["response_bytes"] for x in log)
    if len(log) > BUDGET["max_requests"] or total > BUDGET["max_bytes"]:
        raise RuntimeError("Budget exceeded")
    with MemoryFile(content) as mem, mem.open() as src:
        if (src.crs.to_string(), src.transform, src.shape, src.count) != (CRS, affine, (SIZE, SIZE), len(BANDS)):
            raise ValueError("Unexpected grid")
        data = src.read()
    OUT.mkdir(parents=True)
    np.save(OUT / "sar.npy", data)
    save(OUT / "receipt.json", dict(scenes=info["scenes"], bands=list(BANDS), affine=list(affine)[:6],
                                    requests=len(log), response_bytes=total, log=log, sar_sha256=sha(OUT / "sar.npy")))
    print("scenes", {k: len(v) for k, v in info["scenes"].items()}, "requests", len(log), "bytes", total)


def analyze():
    import rasterio
    from scipy.ndimage import label
    rec = json.loads((OUT / "receipt.json").read_bytes())
    data = np.load(OUT / "sar.npy").astype(float)
    if sha(OUT / "sar.npy") != rec["sar_sha256"]:
        raise ValueError("SAR cache hash mismatch")
    b = dict(zip(BANDS, data))
    valid = np.all([b[k] != -9999 for k in BANDS[:4]], axis=0) & (b["before_count"] >= 2) & (b["after_count"] >= 2)
    dvv, dvh = b["after_VV"] - b["before_VV"], b["after_VH"] - b["before_VH"]
    with rasterio.open(AOI / "change.tif") as src:
        ch, aoi_bounds = src.read(), list(src.bounds)
    eligible, cand = ch[0] == 1, ch[1] == 1
    with rasterio.open(TILE / "features.tif") as src:
        tile, tile_bounds = src.read(), list(src.bounds)
        names = src.descriptions
    with rasterio.open(TILE / "diagnostics.tif") as src:
        common = src.read(9) == 1
    a, t = tile_overlap(aoi_bounds, tile_bounds)
    shared = valid[a] & common[t]
    diff_vv = np.abs(dvv[a] - tile[names.index("dVV")][t])[shared]
    diff_vh = np.abs(dvh[a] - tile[names.index("dVH")][t])[shared]
    repro = dict(shared_cells=int(shared.sum()), max_abs_dVV_db=float(diff_vv.max()), max_abs_dVH_db=float(diff_vh.max()))
    if max(repro["max_abs_dVV_db"], repro["max_abs_dVH_db"]) > 0.01:
        save(SUMMARY, dict(phase="22P", status="STOPPED_REPRODUCTION_GATE", reproduction=repro))
        raise SystemExit(f"Reproduction gate failed: {repro}")
    pool_mask = eligible & valid & ~cand
    cmask = cand & valid
    pv, ph, cv, chh = dvv[pool_mask], dvh[pool_mask], dvv[cmask], dvh[cmask]
    res = dict(phase="22P", status="COMPLETED", preregistration_sha256=sha(PREREG), reproduction=repro,
               cells=dict(eligible=int(eligible.sum()), sar_valid_eligible=int((eligible & valid).sum()),
                          candidates=int(cand.sum()), sar_valid_candidates=int(cmask.sum()), background=int(pool_mask.sum())),
               scenes={k: len(v) for k, v in rec["scenes"].items()},
               cloud_usage=dict(requests=rec["requests"], response_bytes=rec["response_bytes"]))
    for pol, c, p in (("dVV", cv, pv), ("dVH", chh, ph)):
        obs, pval = permutation_p(c, p)
        res[pol] = dict(candidate_median_db=float(np.median(c)), background_median_db=float(np.median(p)),
                        background_p5_p95_db=[float(x) for x in np.percentile(p, [5, 95])],
                        median_difference_db=obs, permutation_p_two_sided=pval,
                        candidate_percentile_ranks=[round(x, 1) for x in percentile_rank(c, p)])
    flags = co_change(cv, chh, pv, ph)
    res["co_change"] = dict(cells_outside_background_5_95=int(sum(flags)), of=len(flags),
                            expected_by_chance_upper_bound=round(0.20 * len(flags), 2),
                            note="union bound: a random background cell is outside 5-95 in either polarisation with probability <= 0.20")
    ids, n = label(cand, structure=np.ones((3, 3), int))
    rng = np.random.default_rng(43)
    clusters = []
    for i in range(1, n + 1):
        m = (ids == i) & valid
        clusters.append(dict(cluster=f"C{i:03d}", cells=int((ids == i).sum()), dVV_mean_db=float(dvv[m].mean()) if m.any() else None,
                             dVH_mean_db=float(dvh[m].mean()) if m.any() else None))
    cl_vh = np.array([c["dVH_mean_db"] for c in clusters if c["dVH_mean_db"] is not None])
    null = np.array([np.median(rng.choice(ph, len(cl_vh), replace=False)) for _ in range(10000)])
    res["cluster_level"] = dict(clusters=clusters, dVH_median_of_cluster_means_db=float(np.median(cl_vh)),
                                dVH_permutation_p_two_sided=float((1 + np.sum(np.abs(null - np.median(ph)) >= abs(np.median(cl_vh) - np.median(ph)))) / 10001))
    res["interpretation"] = "descriptive multi-sensor corroboration of UNKNOWN candidates; not validation or mining evidence"
    save(SUMMARY, res)
    print(json.dumps({k: res[k] for k in ("reproduction", "cells", "dVV", "dVH", "co_change")}, indent=1))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--acquire", "--analyze"):
        g.add_argument(f, action="store_true")
    a = p.parse_args()
    (preregister if a.preregister else acquire if a.acquire else analyze)()
