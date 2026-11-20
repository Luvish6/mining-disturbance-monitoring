"""Phase 22X: systematic, district-stratified random sample of guarded TRAIN/VAL blocks in
East/West Jaintia Hills. Applies the unchanged Phase 22L optical rule, the Phase 22P Sentinel-1
check and the Phase 22R independent-product comparison. Candidates remain UNKNOWN.

  --preregister  offline sample + protocol -> docs/reports/phase22x-preregistration.json
  --acquire      locked, ledger-capped (<=160 requests, <=10 MB)
  --analyze      offline -> docs/reports/phase22x-summary.json
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import save, sha
from scripts.phase22r_product_agreement import (BANDS as PBANDS, DRIVERS, HANSEN, RECENT, background_mask, clusters,
                                                frac_any, mean_of_means, translation_null, wilson)
from scripts.phase22w_ablation import acquire_lock, ledger_usage

PREREG = Path("docs/reports/phase22x-preregistration.json")
SUMMARY = Path("docs/reports/phase22x-summary.json")
OUT = Path("outputs/phase22x_landscape")
LEDGER = OUT / "ledger.jsonl"
DISTRICTS = Path("outputs/phase6b_multitile/districts.json")
CRS, SIZE, STEP, NODATA = "EPSG:32646", 64, 30, -9999
PER_DISTRICT = 10
USED_BLOCKS = {"94:559", "90:562", "82:563", "85:563"}  # earlier AOIs (22L/22Q): excluded for independence
BUDGET = dict(max_requests=160, max_bytes=10_000_000)
S2_FIELDS = ("B4", "B3", "B2", "NDVI", "BSI", "NDWI")
SAR_BANDS = ("before_VV", "before_VH", "after_VV", "after_VH", "before_sar_count", "after_sar_count")


def block_rect(key):
    """1,920 m AOI centred in a 5 km block, snapped to the 30 m grid (position fixed before measurement)."""
    bx, by = map(int, key.split(":"))
    cx, cy = bx * 5000 + 2500, by * 5000 + 2500
    left, bottom = round((cx - 960) / STEP) * STEP, round((cy - 960) / STEP) * STEP
    return [left, bottom, left + SIZE * STEP, bottom + SIZE * STEP]


def rank(key):
    return hashlib.sha256(f"22X:{key}".encode()).hexdigest()


def draw_sample(candidates, per_district=PER_DISTRICT):
    """candidates: {key: district}. Deterministic hash order within each district."""
    out = {}
    for d in sorted(set(candidates.values())):
        keys = sorted((k for k, v in candidates.items() if v == d), key=rank)
        out[d] = keys[:per_district]
    return out


def bootstrap_mean_ci(values, draws=10000, seed=47):
    v = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    m = v[rng.integers(0, len(v), (draws, len(v)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def preregister():
    from pyproj import Transformer
    from shapely.geometry import box, shape
    from shapely import transform as gtransform
    from scripts.phase22n_temporal import guards
    from scripts.phase22q_multi_aoi import guard
    from src.phase3.spatial import partition
    area, protected = guards()
    t = Transformer.from_crs(4326, CRS, always_xy=True).transform
    dist = {f["properties"]["GAUL2_NAME"]: gtransform(shape(f["geometry"]), t, interleaved=False)
            for f in json.loads(DISTRICTS.read_bytes())["features"]}
    x0, y0, x1, y1 = area.bounds
    cand = {}
    for bx in range(math.floor(x0 / 5000), math.ceil(x1 / 5000)):
        for by in range(math.floor(y0 / 5000), math.ceil(y1 / 5000)):
            key = f"{bx}:{by}"
            if key in USED_BLOCKS or partition(key) == "test":
                continue
            g = guard(block_rect(key), area, protected)
            if not g["eligible"]:
                continue
            owner = [d for d, geom in dist.items() if geom.covers(box(*block_rect(key)))]
            if len(owner) == 1:
                cand[key] = owner[0]
    sample = draw_sample(cand)
    aois = {k: dict(district=d, bounds=block_rect(k), split=partition(k), guard=guard(block_rect(k), area, protected))
            for d, ks in sample.items() for k in ks}
    save(PREREG, dict(
        phase="22X", date=datetime.now(timezone.utc).date().isoformat(), budget=BUDGET,
        frame=dict(eligible_blocks={d: sum(v == d for v in cand.values()) for d in sorted(set(cand.values()))},
                   rule="non-TEST seed-42 5 km blocks whose centred 1,920 m AOI passes the full-footprint guard and lies wholly "
                        "in one district; earlier AOI blocks excluded"),
        sampling=f"{PER_DISTRICT} per district in sha256('22X:'+block) order; AOI fixed at block centre; no relocation or replacement",
        aois=aois,
        optical="unchanged Phase 22L seasonal_graph + select_candidates (NDVI drop <= -0.30, BSI rise > +0.10, >=2 obs/season)",
        sar="Phase 2 sar.seasonal, DESCENDING relative orbit 77, 20 m focal mean, seasonal median dB, >=2 obs/season "
            "(Phase 6B/22P graph), same request as optical",
        products=dict(hansen=HANSEN, drivers=DRIVERS, rule="Phase 22R sampling and statistics unchanged"),
        background="eligible, SAR-valid cells > 60 m from candidates (Phase 22R background_mask)",
        estimands=dict(
            density="candidate ha per 100 eligible ha per AOI; mean over AOIs with AOI-bootstrap 95% CI (AOI = sampling unit), "
                    "overall and per district",
            sar="pooled stratified shape-preserving translation permutation of cluster mean dVH (and dVV) minus own-AOI "
                "background (Phase 22R translation_null, seed 46); per-AOI direction reported descriptively",
            products="Phase 22R H1 (2024/25 GFC loss) and H2 (hard-commodities probability) on all sampled clusters"),
        null_outcomes="AOIs with zero candidates, missing SAR or masked products are reported as measured; none replaced",
        not_done="no threshold change, no model training, no TEST access, no accuracy metrics",
        interpretation="landscape-scale screening statistics; candidates UNKNOWN; not mining, legality or river evidence"))
    print({d: ks for d, ks in sample.items()}, {d: sum(v == d for v in cand.values()) for d in set(cand.values())})


def acquire():
    import ee
    import requests
    from affine import Affine
    from rasterio.io import MemoryFile
    from config.phase2_settings import Phase2Config
    from config.settings import BEFORE, AFTER
    from scripts.phase22l_temporal import seasonal_graph
    from src.gee_setup import initialize
    from src import sar_preprocessing as sar
    plan = json.loads(PREREG.read_bytes())
    OUT.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock(OUT / ".acquire.lock")
    try:
        initialize()
        cfg = Phase2Config(relative_orbit=77)

        def charge(entry):
            n, b = ledger_usage(LEDGER)
            if n + 1 > BUDGET["max_requests"] or b + entry.get("planned", 0) > BUDGET["max_bytes"]:
                raise SystemExit(f"Budget stop: {n} requests, {b} bytes")

        def log(entry):
            with LEDGER.open("a") as fh:
                fh.write(json.dumps(entry) + "\n")

        for key, a in plan["aois"].items():
            target = OUT / f"{key.replace(':', '_')}.npy"
            if target.exists():
                continue
            x0, y0, x1, y1 = a["bounds"]
            affine = Affine(STEP, 0, x0, 0, -STEP, y1)
            region = ee.Geometry.Rectangle([x0, y0, x1, y1], CRS, False)
            parts, names, meta = [], [], {}
            for name, season in (("before", BEFORE), ("after", AFTER)):
                image, count, raw, joined = seasonal_graph(region, season, cfg)
                col = sar.collection(region, season, cfg).filter(ee.Filter.eq("relativeOrbitNumber_start", 77))
                db, sc = sar.seasonal(col, 77, region, cfg)
                meta[name] = dict(s2_joined=joined.size(), s2_days=joined.aggregate_array("system:time_start"), s1_scenes=col.size())
                n = [f"{name}_{k}" for k in S2_FIELDS]
                parts.append(image.select(list(S2_FIELDS)).rename(n).addBands(count.rename(f"{name}_count"))
                             .addBands(db.select(["VV", "VH"]).rename([f"{name}_VV", f"{name}_VH"]))
                             .addBands(sc.rename(f"{name}_sar_count")))
                names += n + [f"{name}_count", f"{name}_VV", f"{name}_VH", f"{name}_sar_count"]
            slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003").select("elevation")).rename("slope")
            stack = parts[0].addBands(parts[1]).addBands(slope)
            names += ["slope"]
            charge(dict(planned=50_000))
            info = ee.Dictionary(dict(meta=meta, bands=stack.bandNames())).getInfo()
            log(dict(aoi=key, request="metadata", response_bytes=len(json.dumps(info).encode())))
            if info["bands"] != names:
                raise ValueError(f"{key}: band order")
            charge(dict(planned=0))
            url = stack.toFloat().unmask(NODATA, False).getDownloadURL(
                dict(format="GEO_TIFF", crs=CRS, crs_transform=list(affine)[:6], dimensions=[SIZE, SIZE]))
            log(dict(aoi=key, request="url", response_bytes=0))
            charge(dict(planned=400_000))
            with requests.get(url, timeout=(15, 180)) as r:
                log(dict(aoi=key, request="download", response_bytes=len(r.content), status=r.status_code))
                if r.status_code != 200:
                    raise RuntimeError(f"{key}: HTTP {r.status_code}")
                content = r.content
            with MemoryFile(content) as mem, mem.open() as src:
                if (src.crs.to_string(), src.transform, src.shape, src.count) != (CRS, affine, (SIZE, SIZE), len(names)):
                    raise ValueError(f"{key}: grid")
                np.save(target, src.read())
            save(OUT / f"{key.replace(':', '_')}_meta.json", dict(bands=names, meta=info["meta"]))
            print(key, {s: (info["meta"][s]["s2_joined"], info["meta"][s]["s1_scenes"]) for s in ("before", "after")}, flush=True)
        if not (OUT / "products.json").exists():
            h, d = ee.Image(HANSEN), ee.Image(DRIVERS)
            img = ee.Image.cat([h.select("lossyear").unmask(0), h.select("treecover2000"), h.select("datamask"),
                                d.select("classification").unmask(0), d.select("probability_2").unmask(-1)]
                               ).rename(list(PBANDS)).toInt16()
            samples = {k: img.reproject(crs=CRS, crsTransform=[STEP, 0, a["bounds"][0], 0, -STEP, a["bounds"][3]])
                       .sampleRectangle(region=ee.Geometry.Rectangle(a["bounds"], CRS, False), defaultValue=-9)
                       for k, a in plan["aois"].items()}
            charge(dict(planned=2_000_000))
            data = ee.Dictionary(samples).getInfo()
            log(dict(request="products", response_bytes=len(json.dumps(data).encode())))
            grids = {k: np.array([f["properties"][b] for b in PBANDS]).tolist() for k, f in data.items()}
            if any(np.array(g).shape != (len(PBANDS), SIZE, SIZE) for g in grids.values()):
                raise ValueError("product sample shape")
            save(OUT / "products.json", dict(bands=list(PBANDS), grids=grids))
        n, b = ledger_usage(LEDGER)
        save(OUT / "acquisition.json", dict(requests=n, response_bytes=b))
        print("requests", n, "bytes", b)
    finally:
        lock.unlink(missing_ok=True)


def analyze():
    from scripts.phase22l_temporal import select_candidates
    plan = json.loads(PREREG.read_bytes())
    prod = json.loads((OUT / "products.json").read_bytes())["grids"]
    res = dict(phase="22X", preregistration_sha256=sha(PREREG), aois={})
    strata = dict(dvh=[], dvv=[], loss=[], hc=[])
    for key, a in plan["aois"].items():
        f = OUT / f"{key.replace(':', '_')}.npy"
        names = json.loads((OUT / f"{key.replace(':', '_')}_meta.json").read_bytes())["bands"]
        v = np.load(f).astype(float)
        v[v == NODATA] = np.nan
        g = dict(zip(names, v))
        b = np.stack([g[f"before_{k}"] for k in S2_FIELDS]); af = np.stack([g[f"after_{k}"] for k in S2_FIELDS])
        eligible, cand, _, _ = select_candidates(b, af, np.nan_to_num(g["before_count"]), np.nan_to_num(g["after_count"]), g["slope"])
        sar_ok = np.all([np.isfinite(g[k]) for k in ("before_VV", "before_VH", "after_VV", "after_VH")], axis=0) & \
            (np.nan_to_num(g["before_sar_count"]) >= 2) & (np.nan_to_num(g["after_sar_count"]) >= 2)
        dvv, dvh = g["after_VV"] - g["before_VV"], g["after_VH"] - g["before_VH"]
        p = dict(zip(PBANDS, np.array(prod[key])))
        land = p["datamask"] == 1
        bg = background_mask(eligible, cand) & sar_ok & land
        cl = clusters(cand)
        n_el = int(eligible.sum())
        out = dict(district=a["district"], split=a["split"], eligible_cells=n_el, candidate_cells=int(cand.sum()),
                   clusters=len(cl), candidate_ha=float(cand.sum() * .09),
                   density_ha_per_100ha=float(cand.sum() / n_el * 100) if n_el else None,
                   sar_valid_fraction=float(sar_ok.mean()), background_cells=int(bg.sum()))
        if cl and all(sar_ok[c[:, 0], c[:, 1]].all() for c in cl) and bg.sum() > 100:
            out["dVH_candidate_median_minus_background_db"] = float(np.median(dvh[cand]) - np.median(dvh[bg]))
            out["dVV_candidate_median_minus_background_db"] = float(np.median(dvv[cand]) - np.median(dvv[bg]))
            strata["dvh"].append((cl, bg, np.nan_to_num(dvh - np.median(dvh[bg]))))
            strata["dvv"].append((cl, bg, np.nan_to_num(dvv - np.median(dvv[bg]))))
            recent = np.isin(p["lossyear"], RECENT)
            strata["loss"].append((cl, bg, recent))
            hp = np.where(p["hard_commodities_p250"] >= 0, p["hard_commodities_p250"] * .004, np.nan)
            if np.isfinite(hp[cand]).all() and np.isfinite(hp[bg]).any():
                strata["hc"].append((cl, bg & np.isfinite(hp), np.nan_to_num(hp)))
            out["clusters_with_2024_25_loss"] = int(sum(recent[c[:, 0], c[:, 1]].any() for c in cl))
            out["hard_commodity_dominant_cells_in_aoi"] = int((p["driver_class"] == 2).sum())
        elif cl:
            out["status"] = "SAR_OR_BACKGROUND_INSUFFICIENT"
        else:
            out["status"] = "ZERO_CANDIDATES"
        res["aois"][key] = out
    dens = {d: [v["density_ha_per_100ha"] for v in res["aois"].values() if v["district"] == d and v["density_ha_per_100ha"] is not None]
            for d in sorted({v["district"] for v in res["aois"].values()})}
    alld = [x for v in dens.values() for x in v]
    res["density"] = dict(overall=dict(mean=float(np.mean(alld)), ci95=bootstrap_mean_ci(alld), aois=len(alld),
                                       aois_with_candidates=sum(x > 0 for x in alld)),
                          by_district={d: dict(mean=float(np.mean(v)), ci95=bootstrap_mean_ci(v), aois=len(v),
                                               aois_with_candidates=sum(x > 0 for x in v)) for d, v in dens.items()})
    n_cl = sum(len(s[0]) for s in strata["dvh"])
    res["clusters_tested"] = n_cl
    if strata["dvh"]:
        for k in ("dvh", "dvv"):
            obs, null = translation_null(strata[k], mean_of_means)
            res[f"sar_{k}"] = dict(aois=len(strata[k]), clusters=n_cl, mean_cluster_minus_background_db=obs, translation_null=null)
        dirs = [v["dVH_candidate_median_minus_background_db"] for v in res["aois"].values() if "dVH_candidate_median_minus_background_db" in v]
        res["sar_dvh"]["aois_negative_direction"] = [int(sum(x < 0 for x in dirs)), len(dirs)]
        obs, null = translation_null(strata["loss"], frac_any)
        k = sum(v.get("clusters_with_2024_25_loss", 0) for v in res["aois"].values())
        res["products_H1"] = dict(clusters_with_recent_loss=[int(k), n_cl], fraction=obs, wilson95=wilson(k, n_cl), translation_null=null)
        if strata["hc"]:
            obs, null = translation_null(strata["hc"], mean_of_means)
            res["products_H2"] = dict(aois=len(strata["hc"]), mean_cluster_probability=obs, translation_null=null,
                                      hard_commodity_dominant_cells_total=int(sum(v.get("hard_commodity_dominant_cells_in_aoi", 0)
                                                                                  for v in res["aois"].values())))
    n, b = ledger_usage(LEDGER)
    res["cloud_usage"] = dict(requests=n, response_bytes=b)
    res["interpretation"] = "landscape screening; candidates UNKNOWN; not mining, legality or river evidence; no accuracy"
    save(SUMMARY, res)
    print(json.dumps({k: res[k] for k in res if k not in ("aois",)}, indent=1)[:3000])
    for k, v in res["aois"].items():
        print(k, v["district"][:4], v["candidate_cells"], v["clusters"], round(v["density_ha_per_100ha"] or 0, 3),
              v.get("dVH_candidate_median_minus_background_db"), v.get("status"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--acquire", "--analyze"):
        g.add_argument(f, action="store_true")
    x = ap.parse_args()
    (preregister if x.preregister else acquire if x.acquire else analyze)()
