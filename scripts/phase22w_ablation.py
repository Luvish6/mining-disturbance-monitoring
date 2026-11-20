"""Phase 22W: Sentinel-1 vs Sentinel-2 vs fusion Random Forest ablation on Maus v2 weak labels.

Static mining-footprint classification on peninsular-Indian weak labels (2019 Q1).
NOT temporal change detection, NOT verified ground truth, NOT Meghalaya performance.

  --preregister  freeze cohort, features, RF, metrics -> docs/reports/phase22w-preregistration.json
  --acquire      S1 VV/VH/count + SRTM elevation/slope on each patch grid (resumable, <=300 req, <=40 MB)
  --run          fit four RFs + fixed rule baseline; evaluate on VAL -> docs/reports/phase22w-metrics.json
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import save, sha

PREREG = Path("docs/reports/phase22w-preregistration.json")
METRICS = Path("docs/reports/phase22w-metrics.json")
AVAIL = Path("outputs/phase22v_sar_pilot/availability.json")
PILOT = Path("outputs/phase22v_sar_pilot")
OUT = Path("outputs/phase22w_ablation")
LEDGER = OUT / "ledger.jsonl"
MANIFESTS = {s: Path(f"outputs/phase22h_maus/{s}_manifest.json") for s in ("train", "validation")}
SIZE, NODATA = 128, -9999
BUDGET = dict(max_requests=300, max_bytes=40_000_000)
ARMS = {"A_sar": ["VV", "VH"], "B_optical": ["B3", "B4", "B8"], "C_fusion": ["VV", "VH", "B3", "B4", "B8"],
        "D_fusion_terrain": ["VV", "VH", "B3", "B4", "B8", "elevation", "slope"]}
GATES = dict(min_scenes_single_orbit=2, min_observations_per_pixel=2, min_sar_valid_fraction=0.70)
CUTOFF, BOOT, SEED = 0.50, 10000, 42


# ------------------------------------------------------------------ pure logic
def eligible_patches(rows, avail, min_scenes=GATES["min_scenes_single_orbit"]):
    keep, drop = [], []
    for r in rows:
        best = max(avail[r["patch_id"]]["desc"].values(), default=0)
        (keep if best >= min_scenes else drop).append(r["patch_id"])
    return keep, drop


def confusion(y, pred):
    tp = int((pred & (y == 1)).sum()); fp = int((pred & (y == 0)).sum())
    fn = int((~pred & (y == 1)).sum()); tn = int((~pred & (y == 0)).sum())
    return np.array([tn, fp, fn, tp])


def scores(c):
    tn, fp, fn, tp = (int(v) for v in c)
    div = lambda a, b: a / b if b else None
    p, r = div(tp, tp + fp), div(tp, tp + fn)
    f1 = div(2 * tp, 2 * tp + fp + fn)
    # background class treated as the positive class for its own scores
    pb, rb = div(tn, tn + fn), div(tn, tn + fp)
    return dict(confusion=[[tn, fp], [fn, tp]], precision=p, recall=r, f1=f1, iou=div(tp, tp + fp + fn),
                fpr=div(fp, fp + tn), background_precision=pb, background_recall=rb,
                background_f1=div(2 * tn, 2 * tn + fn + fp), background_iou=div(tn, tn + fn + fp))


def group_bootstrap(per_group, draws=BOOT, seed=SEED):
    """per_group: {arm: {group: confusion array}}. Resample groups with replacement; pooled F1/IoU
    per arm and paired differences vs every other arm on the same resamples."""
    arms, groups = list(per_group), sorted(next(iter(per_group.values())))
    rng = np.random.default_rng(seed)
    mats = {a: np.array([per_group[a][g] for g in groups]) for a in arms}
    out = {a: dict(f1=[], iou=[]) for a in arms}
    for _ in range(draws):
        ix = rng.integers(0, len(groups), len(groups))
        for a in arms:
            tn, fp, fn, tp = mats[a][ix].sum(axis=0)
            out[a]["f1"].append(2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else np.nan)
            out[a]["iou"].append(tp / (tp + fp + fn) if (tp + fp + fn) else np.nan)
    ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
    res = {a: {m: ci(out[a][m]) for m in ("f1", "iou")} for a in arms}
    diffs = {}
    for i, a in enumerate(arms):
        for b in arms[i + 1:]:
            d = np.array(out[b]["f1"]) - np.array(out[a]["f1"])
            diffs[f"{b}-minus-{a}"] = dict(f1_diff_ci95=ci(d), f1_diff_median=float(np.nanmedian(d)),
                                           share_resamples_positive=float(np.nanmean(d > 0)))
    return res, diffs


# ------------------------------------------------------------------ stages
def preregister():
    avail = json.loads(AVAIL.read_bytes())["counts"]
    cohort = {}
    for split, path in MANIFESTS.items():
        rows = json.loads(path.read_bytes())["patches"]
        keep, drop = eligible_patches(rows, avail)
        cohort[split] = dict(manifest_sha256=sha(path), eligible=sorted(keep), excluded_no_sar=sorted(drop),
                             excluded_states=sorted({r["state"] for r in rows if r["patch_id"] in drop}))
    if (len(cohort["train"]["eligible"]), len(cohort["validation"]["eligible"])) != (108, 33):
        raise ValueError("Cohort differs from the expected 108 TRAIN + 33 VAL")
    save(PREREG, dict(
        phase="22W", date=datetime.now(timezone.utc).date().isoformat(), budget=BUDGET, gates=GATES, cohort=cohort,
        availability_sha256=sha(AVAIL), pilot_reuse=sorted(json.loads((PILOT / "receipt.json").read_bytes())["receipts"]),
        window=["2019-01-01", "2019-04-01"],
        sar="Phase 2 sar.seasonal: S1 GRD IW 10 m VV+VH DESCENDING; relative orbit = Phase 2 choose_orbit on the "
            "frozen 22V availability histogram; 20 m linear-power focal mean; median dB; pixel count >= 2",
        terrain="USGS/SRTMGL1_003 elevation (bilinear) and ee.Terrain.slope (degrees, bilinear) on the patch 10 m grid; "
                "native 30 m",
        post_fetch_gate="patch excluded from ALL arms if SAR-valid fraction < 0.70; decided before any model is fit; "
                        "failing patches are never replaced",
        pixels="pixel enters fitting/scoring only if optical valid, weak label known (0/1, not 255), SAR valid, terrain finite",
        arms=ARMS, rf="Phase 22F RF dict: 100 trees, max_depth 16, min_samples_leaf 2, sqrt features, seed 42, n_jobs 1; "
                      "no class_weight; balanced sampling = Phase 22F balanced_pixels (<=50,000 per class, seed 42) drawn "
                      "ONCE from the common-support TRAIN pixels and shared by all arms",
        cutoff=CUTOFF, baseline="Phase 22K Rule A (NDVI < 0.10), TRAIN-selected in 22K, applied unchanged",
        metrics="VAL weak labels: precision, recall, F1, IoU, FPR, background-class precision/recall/F1/IoU, confusion; "
                "per group; group bootstrap (11 groups, 10,000 resamples, seed 42) CIs and paired arm differences",
        forbidden="no VAL/TEST tuning, feature selection, threshold optimisation, cohort change after VAL; TEST sealed",
        label_status="Maus v2 weak static footprint labels; agreement, not independent accuracy; not Meghalaya; not change"))
    print({s: (len(c["eligible"]), len(c["excluded_no_sar"]), c["excluded_states"]) for s, c in cohort.items()})


def acquire():
    import ee
    import requests
    from rasterio.io import MemoryFile
    from config.phase2_settings import Phase2Config
    from config.settings import Season
    from src.gee_setup import initialize
    from src import sar_preprocessing as sar
    plan = json.loads(PREREG.read_bytes())
    if sha(AVAIL) != plan["availability_sha256"]:
        raise ValueError("Availability receipt changed")
    avail = json.loads(AVAIL.read_bytes())["counts"]
    rows = {r["patch_id"]: r for p in MANIFESTS.values() for r in json.loads(p.read_bytes())["patches"]}
    OUT.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock(OUT / ".acquire.lock")  # one writer only (Phase 22W duplicate-run incident)
    try:
        _acquire(plan, avail, rows, ee, requests, MemoryFile, Phase2Config, Season, initialize, sar)
    finally:
        lock.unlink(missing_ok=True)


def acquire_lock(path):
    import os
    try:
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        raise SystemExit(f"Another acquisition holds {path}; refusing to run concurrently") from None
    return path


def ledger_usage(path=None):
    """Budget is always computed from the shared on-disk ledger, never from process memory."""
    path = path or LEDGER
    rows = [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []
    return len(rows), sum(x.get("response_bytes", 0) for x in rows)


def _acquire(plan, avail, rows, ee, requests, MemoryFile, Phase2Config, Season, initialize, sar):
    used = ledger_usage
    initialize()
    cfg, season = Phase2Config(), Season("2019-Q1", *plan["window"])
    dem = ee.Image("USGS/SRTMGL1_003").select("elevation")
    terrain = dem.resample("bilinear").rename("elevation").addBands(ee.Terrain.slope(dem).resample("bilinear").rename("slope"))

    def log(entry):
        with LEDGER.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")

    pilot = set(plan["pilot_reuse"])
    for pid in plan["cohort"]["train"]["eligible"] + plan["cohort"]["validation"]["eligible"]:
        target = OUT / f"{pid}.npy"
        if target.exists():
            continue
        r = rows[pid]
        n, b = used()
        if n + 2 > BUDGET["max_requests"] or b + 300_000 > BUDGET["max_bytes"]:
            raise SystemExit(f"Budget stop before {pid}: requests {n}, bytes {b}")
        region = ee.Geometry.Rectangle(r["bounds"], f"EPSG:{r['crs']}", False)
        orbit = sar.choose_orbit(avail[pid]["desc"], avail[pid]["desc"])
        reuse = pid in pilot and (PILOT / f"{pid}_sar.npy").exists()
        if reuse:
            img = terrain
        else:
            col = sar.collection(region, season, cfg).filter(ee.Filter.eq("relativeOrbitNumber_start", orbit))
            db, count = sar.seasonal(col, orbit, region, cfg)
            img = db.addBands(count).addBands(terrain)
        log(dict(patch=pid, request="url", response_bytes=0))
        url = img.toFloat().unmask(NODATA, sameFootprint=False).getDownloadURL(
            dict(format="GEO_TIFF", crs=f"EPSG:{r['crs']}", crs_transform=r["affine"], dimensions=[SIZE, SIZE]))
        with requests.get(url, timeout=(15, 180)) as resp:
            if resp.status_code != 200:
                log(dict(patch=pid, request="download", response_bytes=len(resp.content), status=resp.status_code))
                raise RuntimeError(f"{pid}: HTTP {resp.status_code}")
            content = resp.content
        log(dict(patch=pid, request="download", response_bytes=len(content), orbit=int(orbit), reused_pilot_sar=reuse))
        with MemoryFile(content) as mem, mem.open() as src:
            if (src.crs.to_epsg(), list(src.transform)[:6], src.shape) != (r["crs"], r["affine"], (SIZE, SIZE)):
                raise ValueError(f"{pid}: grid mismatch")
            data = src.read()
        if reuse:
            data = np.concatenate([np.load(PILOT / f"{pid}_sar.npy"), data])
        if data.shape[0] != 5:
            raise ValueError(f"{pid}: expected 5 bands, got {data.shape[0]}")
        np.save(target, data)
    n, b = used()
    save(OUT / "acquisition.json", dict(requests=n, response_bytes=b, patches=len(list(OUT.glob("*.npy")))))
    print("requests", n, "bytes", b)


def run():
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    from scripts.phase22f_maus import RF, balanced_pixels
    from scripts.phase22h_maus_train import training_data
    plan = json.loads(PREREG.read_bytes())
    samples = training_data()[0]
    cohort = {s: set(plan["cohort"][k]["eligible"]) for s, k in (("train", "train"), ("validation", "validation"))}
    gate_log, data = {}, {}
    for split in ("train", "validation"):
        feats, ys, groups, ok_patches = [], [], [], []
        for row, x, v, y in samples[split]:
            pid = row["patch_id"]
            if pid not in cohort[split]:
                continue
            s = np.load(OUT / f"{pid}.npy").astype(float)
            vv, vh, cnt, elev, slope = s
            sar_ok = (vv != NODATA) & (vh != NODATA) & (cnt >= GATES["min_observations_per_pixel"])
            gate_log[pid] = float(sar_ok.mean())
            if sar_ok.mean() < GATES["min_sar_valid_fraction"]:
                continue
            use = v & (y != 255) & sar_ok & np.isfinite(elev) & (elev != NODATA) & np.isfinite(slope) & (slope != NODATA)
            stack = dict(VV=vv, VH=vh, B3=x[0], B4=x[1], B8=x[2], elevation=elev, slope=slope)
            feats.append(np.stack([stack[k][use] for k in ARMS["D_fusion_terrain"]], axis=1))
            ys.append(y[use].astype(int)); groups += [row["group_id"]] * int(use.sum()); ok_patches.append(pid)
        data[split] = (np.concatenate(feats), np.concatenate(ys), np.array(groups), ok_patches)
    xt, yt, _, tp = data["train"]
    xv, yv, gv, vp = data["validation"]
    order = ARMS["D_fusion_terrain"]
    ix = balanced_pixels(yt)
    res = dict(phase="22W", preregistration_sha256=sha(PREREG), cutoff=CUTOFF,
               cohort=dict(train_patches=len(tp), validation_patches=len(vp), train_pixels=int(len(yt)),
                           validation_pixels=int(len(yv)), fit_pixels=int(len(ix)), validation_groups=int(len(set(gv))),
                           sar_gate_failures=sorted(p for p, f in gate_log.items() if f < GATES["min_sar_valid_fraction"])),
               arms={})
    per_group = {}
    OUT.joinpath("models").mkdir(exist_ok=True)
    for arm, cols in ARMS.items():
        c = [order.index(k) for k in cols]
        model = RandomForestClassifier(**RF).fit(xt[ix][:, c], yt[ix])
        joblib.dump(model, OUT / "models" / f"{arm}.joblib", compress=3)
        pred = model.predict_proba(xv[:, c])[:, 1] >= CUTOFF
        per_group[arm] = {g: confusion(yv[gv == g], pred[gv == g]) for g in np.unique(gv)}
        res["arms"][arm] = dict(features=cols, pooled=scores(confusion(yv, pred)),
                                per_group={g[:12]: scores(m) for g, m in per_group[arm].items()},
                                importances=dict(zip(cols, map(float, model.feature_importances_))))
    b3, b4, b8 = (xv[:, order.index(k)] for k in ("B3", "B4", "B8"))
    den = b8 + b4
    ndvi = np.divide(b8 - b4, den, out=np.full_like(den, np.nan), where=den != 0)
    rule = np.isfinite(ndvi) & (ndvi < 0.10)
    per_group["R_rule_ndvi_lt_0.10"] = {g: confusion(yv[gv == g], rule[gv == g]) for g in np.unique(gv)}
    res["arms"]["R_rule_ndvi_lt_0.10"] = dict(features=["NDVI"], pooled=scores(confusion(yv, rule)),
                                              per_group={g[:12]: scores(m) for g, m in per_group["R_rule_ndvi_lt_0.10"].items()})
    ci, diffs = group_bootstrap(per_group)
    for arm in ci:
        res["arms"][arm]["group_bootstrap_ci95"] = ci[arm]
    res["paired_differences"] = diffs
    res["interpretation"] = "agreement with Maus v2 weak static footprint labels on Odisha VAL; not independent accuracy, " \
                            "not change detection, not Meghalaya"
    save(METRICS, res)
    for arm, v in res["arms"].items():
        p = v["pooled"]
        print(arm, {k: round(p[k], 4) for k in ("precision", "recall", "f1", "iou", "fpr")}, v["group_bootstrap_ci95"]["f1"])
    for k, v in diffs.items():
        print(k, v)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--acquire", "--run"):
        g.add_argument(f, action="store_true")
    a = ap.parse_args()
    (preregister if a.preregister else acquire if a.acquire else run)()
