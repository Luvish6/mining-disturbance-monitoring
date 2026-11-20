"""Phase 22Q: replicate the Phase 22L optical rule + Phase 22P Sentinel-1 corroboration on
pre-existing non-TEST Phase 6B tiles (selected in Phase 6B by coverage, before any detection).

  --preregister  offline full-footprint guards -> docs/reports/phase22q-preregistration.json
  --acquire      Sentinel-2 seasonal stacks via the unchanged Phase 22L graph (budget-capped)
  --analyze      unchanged 22L rule + 22P statistics vs cached Phase 6B dVV/dVH (offline)

Candidates remain UNKNOWN - not validated. SAR agreement is corroboration, not a label.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import co_change, percentile_rank, permutation_p, sha, save

TILES = Path("outputs/phase6b_multitile")
PREREG = Path("docs/reports/phase22q-preregistration.json")
SUMMARY = Path("docs/reports/phase22q-summary.json")
OUT = Path("outputs/phase22q_multi_aoi")
P22P = Path("docs/reports/phase22p-summary.json")
CRS, SIZE, STEP, NODATA = "EPSG:32646", 64, 30, -9999
FIELDS = ("B4", "B3", "B2", "NDVI", "BSI", "NDWI")
BUDGET = dict(max_requests=20, max_bytes=5_000_000)
MIN_CANDIDATES_FOR_TEST = 3


def guard(bounds, area, protected):
    from shapely.geometry import box
    from src.phase3.spatial import block_for, partition
    p = box(*bounds)
    hits = [k for k, g in protected if p.intersects(g)]
    key = block_for(p.bounds)
    return dict(bounds=list(bounds), block=key, split=partition(key) if key else None,
                district_contained=area.covers(p), test_intersections=hits,
                rectangle_test_buffer_distance_m=round(min(p.distance(g) for _, g in protected), 1),
                eligible=area.covers(p) and not hits and key is not None and partition(key) != "test")


def stratified_pooled_p(strata, draws=10000, seed=44):
    """strata: list of (candidate_values, pool_values). Statistic: mean over all candidates of
    (value - own-AOI background median). Null: per stratum, draw the same number of pool cells."""
    rng = np.random.default_rng(seed)
    meds = [np.median(p) for _, p in strata]
    obs = float(np.mean(np.concatenate([np.asarray(c) - m for (c, _), m in zip(strata, meds)])))
    null = np.empty(draws)
    for i in range(draws):
        null[i] = np.mean(np.concatenate([rng.choice(p, len(c), replace=False) - m for (c, p), m in zip(strata, meds)]))
    return obs, float((1 + np.sum(np.abs(null) >= abs(obs))) / (1 + draws))


def preregister():
    from scripts.phase22n_temporal import guards
    area, protected = guards()
    roster = json.loads((TILES / "roster.json").read_bytes())
    rows, excluded = {}, {}
    for t in roster["selected"]:
        if t["split"] == "test":
            excluded[t["id"]] = "TEST tile in Phase 6B roster: never opened or processed"
            continue
        if t["id"] == "east-94-559":
            excluded[t["id"]] = "overlaps the Phase 22L/22P AOI (1,938 shared cells): not independent"
            continue
        g = guard(t["bounds"], area, protected)
        rows[t["id"]] = dict(guard=g, district=t["district"],
                             sar_features_sha256=sha(TILES / t["id"] / "features.tif"),
                             sar_diagnostics_sha256=sha(TILES / t["id"] / "diagnostics.tif"))
    save(PREREG, dict(
        phase="22Q", date=datetime.now(timezone.utc).date().isoformat(), budget=BUDGET, aois=rows, excluded=excluded,
        selection="all non-TEST Phase 6B roster tiles (coverage-selected in Phase 6B, before any disturbance detection), "
                  "minus the tile overlapping the Phase 22L AOI; no relocation, no additions",
        optical="unchanged Phase 22L seasonal_graph + select_candidates: NDVI decrease <= -0.30, BSI increase > +0.10, "
                ">=2 obs/season, NDWI<0, brightness>=0.04, SCL 4/5, cloud prob<40",
        sar="cached Phase 6B dVV/dVH (orbit 77, same graph reproduced to 1.8e-6 dB in Phase 22P); SAR-valid = "
            "sar_before_valid & sar_after_valid",
        statistics=dict(per_aoi="Phase 22P cell-level permutation (seed 42) and 5-95 co-change, only if >= 3 candidate cells",
                        pooled_primary="stratified permutation over the new AOIs (seed 44): mean of candidate dVH minus own-AOI "
                                       "background median",
                        pooled_secondary="same, adding the Phase 22L AOI from the 22P cache"),
        validation_split_note="VAL tiles are used for evaluation only; no rule, threshold or parameter is fitted or tuned",
        interpretation="descriptive corroboration of UNKNOWN candidates; zero candidates is a measured outcome"))
    print(json.dumps({k: v["guard"]["eligible"] for k, v in rows.items()}), excluded)


def acquire():
    import ee
    import rasterio
    import requests
    from affine import Affine
    from rasterio.io import MemoryFile
    from config.phase2_settings import Phase2Config
    from config.settings import BEFORE, AFTER
    from scripts.phase22l_temporal import seasonal_graph
    from src.gee_setup import initialize
    plan = json.loads(PREREG.read_bytes())
    if OUT.exists():
        raise ValueError(f"{OUT} exists")
    initialize()
    cfg, log = Phase2Config(), []

    def charge(what, nbytes):
        log.append(dict(request=what, response_bytes=nbytes))
        if len(log) > BUDGET["max_requests"] or sum(x["response_bytes"] for x in log) > BUDGET["max_bytes"]:
            raise RuntimeError("Budget exceeded")

    OUT.mkdir(parents=True)
    for aoi, row in plan["aois"].items():
        if not row["guard"]["eligible"]:
            continue
        x0, y0, x1, y1 = row["guard"]["bounds"]
        affine = Affine(STEP, 0, x0, 0, -STEP, y1)
        region = ee.Geometry.Rectangle([x0, y0, x1, y1], CRS, False)
        parts, names, meta = [], [], {}
        for name, season in (("before", BEFORE), ("after", AFTER)):
            image, count, raw, joined = seasonal_graph(region, season, cfg)
            meta[name] = dict(raw_count=raw.size(), joined_count=joined.size(),
                              ids=joined.aggregate_array("system:index"), dates_ms=joined.aggregate_array("system:time_start"))
            n = [f"{name}_{k}" for k in FIELDS]
            parts.append(image.select(list(FIELDS)).rename(n).addBands(count.rename(f"{name}_count")))
            names += n + [f"{name}_count"]
        slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003").select("elevation")).rename("slope")
        stack = parts[0].addBands(parts[1]).addBands(slope)
        names += ["slope"]
        info = ee.Dictionary(dict(scenes=meta, bands=stack.bandNames())).getInfo()
        charge(f"{aoi}/metadata", len(json.dumps(info).encode()))
        if info["bands"] != names or min(info["scenes"][s]["joined_count"] for s in ("before", "after")) < 2:
            raise ValueError(f"{aoi}: unexpected bands or insufficient scenes")
        url = stack.toFloat().unmask(NODATA, False).getDownloadURL(
            dict(format="GEO_TIFF", crs=CRS, crs_transform=list(affine)[:6], dimensions=[SIZE, SIZE]))
        charge(f"{aoi}/url", 0)
        with requests.get(url, timeout=(15, 180)) as r:
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            content = r.content
        charge(f"{aoi}/download", len(content))
        with MemoryFile(content) as mem, mem.open() as src:
            if (src.crs.to_string(), src.transform, src.shape, src.count) != (CRS, affine, (SIZE, SIZE), 15):
                raise ValueError(f"{aoi}: unexpected grid")
            np.save(OUT / f"{aoi}_s2.npy", src.read())
        save(OUT / f"{aoi}_scenes.json", info["scenes"])
        print(aoi, {s: info["scenes"][s]["joined_count"] for s in ("before", "after")}, len(content), flush=True)
    save(OUT / "budget.json", dict(requests=len(log), response_bytes=sum(x["response_bytes"] for x in log), log=log))


def analyze():
    import rasterio
    from scipy.ndimage import label
    from scripts.phase22l_temporal import select_candidates
    plan = json.loads(PREREG.read_bytes())
    res, strata = dict(phase="22Q", preregistration_sha256=sha(PREREG), aois={}), {}
    for aoi, row in plan["aois"].items():
        if not row["guard"]["eligible"]:
            res["aois"][aoi] = dict(status="NOT_ELIGIBLE", guard=row["guard"])
            continue
        for k, f in (("sar_features_sha256", "features.tif"), ("sar_diagnostics_sha256", "diagnostics.tif")):
            if sha(TILES / aoi / f) != row[k]:
                raise ValueError(f"{aoi}: {f} hash changed")
        v = np.load(OUT / f"{aoi}_s2.npy").astype(float)
        v[v == NODATA] = np.nan
        b, a, bc, ac, slope = v[:6], v[7:13], v[6], v[13], v[14]
        eligible, cand, dndvi, dbsi = select_candidates(b, a, bc, ac, slope)
        with rasterio.open(TILES / aoi / "features.tif") as src:
            feats, names = src.read().astype(float), src.descriptions
            if list(src.bounds) != row["guard"]["bounds"]:
                raise ValueError(f"{aoi}: SAR grid differs")
        with rasterio.open(TILES / aoi / "diagnostics.tif") as src:
            diag, dnames = src.read(), src.descriptions
        sar_valid = (diag[dnames.index("sar_before_valid")] == 1) & (diag[dnames.index("sar_after_valid")] == 1)
        dvv, dvh = feats[names.index("dVV")], feats[names.index("dVH")]
        sar_valid &= np.isfinite(dvv) & np.isfinite(dvh) & (dvv != NODATA) & (dvh != NODATA)
        pool, cm = eligible & sar_valid & ~cand, cand & sar_valid
        scenes = json.loads((OUT / f"{aoi}_scenes.json").read_bytes())
        ids, n = label(cand, structure=np.ones((3, 3), int))
        out = dict(split=row["guard"]["split"], block=row["guard"]["block"],
                   s2_scenes={s: scenes[s]["joined_count"] for s in ("before", "after")},
                   s2_capture_days={s: len({datetime.fromtimestamp(t / 1000, timezone.utc).date() for t in scenes[s]["dates_ms"]})
                                    for s in ("before", "after")},
                   cells=dict(total=SIZE * SIZE, eligible=int(eligible.sum()), candidates=int(cand.sum()), clusters=int(n),
                              candidate_ha=float(cand.sum() * .09), sar_valid_eligible=int((eligible & sar_valid).sum()),
                              sar_valid_candidates=int(cm.sum()), background=int(pool.sum())),
                   candidate_slope_deg=[float(slope[cand].min()), float(slope[cand].max())] if cand.any() else None)
        if cm.sum() >= MIN_CANDIDATES_FOR_TEST:
            for pol, d in (("dVV", dvv), ("dVH", dvh)):
                obs, p = permutation_p(d[cm], d[pool])
                out[pol] = dict(candidate_median_db=float(np.median(d[cm])), background_median_db=float(np.median(d[pool])),
                                median_difference_db=obs, permutation_p_two_sided=p,
                                candidate_percentile_ranks=[round(x, 1) for x in percentile_rank(d[cm], d[pool])])
            out["co_change_outside_5_95"] = [int(sum(co_change(dvv[cm], dvh[cm], dvv[pool], dvh[pool]))), int(cm.sum())]
            out["status"] = "TESTED"
        else:
            out["status"] = "TOO_FEW_CANDIDATES" if cm.sum() else "ZERO_CANDIDATES"
        if cm.any():
            strata[aoi] = (dvh[cm], dvh[pool])
        res["aois"][aoi] = out
    new = [s for s in strata]
    if new:
        obs, p = stratified_pooled_p([strata[s] for s in new])
        res["pooled_primary"] = dict(aois=new, candidate_cells=int(sum(len(strata[s][0]) for s in new)),
                                     mean_dVH_minus_background_median_db=obs, permutation_p_two_sided=p)
    else:
        res["pooled_primary"] = dict(status="NO_CANDIDATES_IN_NEW_AOIS")
    # secondary: add the Phase 22L AOI from the 22P cache
    sar = np.load("outputs/phase22p_sar/sar.npy").astype(float)
    with rasterio.open("outputs/phase22l_temporal_pilot/change.tif") as src:
        ch = src.read()
    valid = np.all(sar[:4] != -9999, axis=0) & (sar[4] >= 2) & (sar[5] >= 2)
    dvh22 = sar[3] - sar[1]
    c22, p22 = (ch[1] == 1) & valid, (ch[0] == 1) & valid & (ch[1] != 1)
    allstrata = [strata[s] for s in new] + [(dvh22[c22], dvh22[p22])]
    obs, p = stratified_pooled_p(allstrata)
    res["pooled_secondary_with_22L"] = dict(candidate_cells=int(sum(len(c) for c, _ in allstrata)),
                                            mean_dVH_minus_background_median_db=obs, permutation_p_two_sided=p)
    bud = json.loads((OUT / "budget.json").read_bytes())
    res["cloud_usage"] = dict(requests=bud["requests"], response_bytes=bud["response_bytes"])
    res["interpretation"] = "descriptive corroboration of UNKNOWN candidates; not validation or mining evidence"
    save(SUMMARY, res)
    print(json.dumps(res, indent=1)[:4000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--acquire", "--analyze"):
        g.add_argument(f, action="store_true")
    x = ap.parse_args()
    (preregister if x.preregister else acquire if x.acquire else analyze)()
