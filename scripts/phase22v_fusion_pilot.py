"""Phase 22V: Sentinel-1 pairing pilot for the frozen Phase 22H Maus weak-label patches.

Weak static mining-footprint labels (Maus v2, 2019) - NOT verified Meghalaya mining-change labels.
No model is trained or evaluated here. VAL and TEST are never selected or read.

  --preregister  fixed deterministic TRAIN pilot selection -> docs/reports/phase22v-preregistration.json
  --acquire      <= 12 EE requests, <= 2 MB: S1 Q1-2019 VV/VH/count on each pilot patch's exact grid
  --verify       offline pairing / quality checks -> docs/reports/phase22v-pilot-summary.json
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import save, sha

MANIFEST = Path("outputs/phase22h_maus/train_manifest.json")
PATCH_DIRS = [Path(f"outputs/{d}/patches") for d in ("phase22h_maus", "phase22e_r_maus", "phase22e_maus")]
PREREG = Path("docs/reports/phase22v-preregistration.json")
SUMMARY = Path("docs/reports/phase22v-pilot-summary.json")
OUT = Path("outputs/phase22v_sar_pilot")
WINDOW = ("2019-01-01", "2019-04-01")  # identical to the Phase 22B/22H optical Q1 window
SIZE, NODATA = 128, -9999
BUDGET = dict(max_requests=12, max_bytes=2_000_000)
GATES = dict(min_observations=2, min_valid_fraction=0.70, single_relative_orbit=True, pass_="DESCENDING",
             db_range=(-35.0, 10.0))


def optical_path(patch_id, image_sha256):
    """Frozen optical patch located by content hash across the existing caches."""
    for d in PATCH_DIRS:
        f = d / f"{patch_id}_image.tif"
        if f.exists() and sha(f) == image_sha256:
            return f
    raise ValueError(f"{patch_id}: no cached optical patch matches the frozen hash")


def rank(patch_id):
    return hashlib.sha256(f"22V:{patch_id}".encode()).hexdigest()


def select_pilot(rows, n_pos=2, n_bg=2):
    """Deterministic: hash order; distinct groups; distinct states where possible; TRAIN only."""
    if any(r["split"] != "train" for r in rows):
        raise ValueError("Pilot selection must use TRAIN rows only")
    picked, groups, states = [], set(), set()
    for want_pos, n in ((True, n_pos), (False, n_bg)):
        pool = sorted((r for r in rows if (r["positive_pixels"] > 0) == want_pos and r.get("image_sha256")),
                      key=lambda r: rank(r["patch_id"]))
        for strict in (True, False):
            for r in pool:
                if sum((p["positive_pixels"] > 0) == want_pos for p in picked) >= n:
                    break
                if r["group_id"] in groups or (strict and r["state"] in states):
                    continue
                picked.append(r); groups.add(r["group_id"]); states.add(r["state"])
    return picked


def quality(vv, vh, count, valid_s2):
    ok = (vv != NODATA) & (vh != NODATA) & (count >= GATES["min_observations"])
    lo, hi = GATES["db_range"]
    in_range = ok & (vv >= lo) & (vv <= hi) & (vh >= lo) & (vh <= hi)
    joint = ok & valid_s2
    return dict(sar_valid_fraction=float(ok.mean()), joint_valid_fraction=float(joint.mean()),
                in_db_range_fraction=float(in_range[ok].mean()) if ok.any() else None,
                vh_below_vv_fraction=float((vh[ok] < vv[ok]).mean()) if ok.any() else None,
                count_range=[int(count.min()), int(count.max())],
                passes=bool(ok.mean() >= GATES["min_valid_fraction"] and joint.mean() >= GATES["min_valid_fraction"]))


def preregister():
    rows = json.loads(MANIFEST.read_bytes())["patches"]
    pilot = select_pilot(rows)
    save(PREREG, dict(
        phase="22V", date=datetime.now(timezone.utc).date().isoformat(), budget=BUDGET, gates=GATES, window=WINDOW,
        manifest_sha256=sha(MANIFEST),
        pilot=[dict(patch_id=r["patch_id"], group_id=r["group_id"], state=r["state"], crs=r["crs"], affine=r["affine"],
                    bounds=r["bounds"], weak_class="positive" if r["positive_pixels"] > 0 else "background",
                    image_sha256=r["image_sha256"]) for r in pilot],
        selection="TRAIN only; sha256('22V:'+patch_id) order; 2 weak-positive + 2 weak-background patches; distinct groups, "
                  "distinct states where possible; no VAL/TEST inspection",
        sar="COPERNICUS/S1_GRD IW 10 m VV+VH, DESCENDING, per patch the relative orbit with most Q1-2019 scenes "
            "(Phase 2 choose_orbit tie rule), linear-power 20 m focal mean, median in dB (Phase 2 sar.seasonal), "
            "exported on the patch's exact UTM 10 m grid",
        pairing="same Q1-2019 window as the optical median; static footprint pairing, not acquisition-matched",
        stop_rules="stop full-run recommendation if any pilot patch lacks DESCENDING coverage, fails valid/joint gates, "
                   "grid mismatch, or out-of-range dB",
        not_done="no RF training, no evaluation, no VAL/TEST access, no U-Net retraining",
        label_status="Maus v2 weak static footprint labels; not Meghalaya mining-change labels"))
    for r in pilot:
        optical_path(r["patch_id"], r["image_sha256"])
    print([(r["patch_id"], r["positive_pixels"] > 0) for r in pilot])


def acquire():
    import ee
    import rasterio
    import requests
    from rasterio.io import MemoryFile
    from config.phase2_settings import Phase2Config
    from config.settings import Season
    from src.gee_setup import initialize
    from src import sar_preprocessing as sar
    plan = json.loads(PREREG.read_bytes())
    if sha(MANIFEST) != plan["manifest_sha256"]:
        raise ValueError("Manifest changed")
    if OUT.exists():
        raise ValueError(f"{OUT} exists")
    initialize()
    cfg, season, log = Phase2Config(), Season("2019-Q1", *WINDOW), []

    def charge(what, n):
        log.append(dict(request=what, response_bytes=n))
        if len(log) > BUDGET["max_requests"] or sum(x["response_bytes"] for x in log) > BUDGET["max_bytes"]:
            raise RuntimeError("Budget exceeded")

    regions = {p["patch_id"]: ee.Geometry.Rectangle(p["bounds"], f"EPSG:{p['crs']}", False) for p in plan["pilot"]}
    meta = ee.Dictionary({pid: ee.Dictionary(dict(
        orbits=sar.collection(g, season, cfg).aggregate_histogram("relativeOrbitNumber_start"),
        ascending=sar.collection(g, season, cfg.__class__(orbit_pass="ASCENDING")).size()))
        for pid, g in regions.items()}).getInfo()
    charge("orbit_metadata", len(json.dumps(meta).encode()))
    OUT.mkdir(parents=True)
    receipts = {}
    for p in plan["pilot"]:
        pid, m = p["patch_id"], meta[p["patch_id"]]
        if not m["orbits"]:
            receipts[pid] = dict(status="NO_DESCENDING_COVERAGE", ascending_scenes=m["ascending"])
            continue
        orbit = sar.choose_orbit(m["orbits"], m["orbits"])
        col = sar.collection(regions[pid], season, cfg).filter(ee.Filter.eq("relativeOrbitNumber_start", orbit))
        db, count = sar.seasonal(col, orbit, regions[pid], cfg)
        img = db.addBands(count).toFloat().unmask(NODATA, sameFootprint=False)
        url = img.getDownloadURL(dict(format="GEO_TIFF", crs=f"EPSG:{p['crs']}", crs_transform=p["affine"],
                                      dimensions=[SIZE, SIZE]))
        charge(f"{pid}/url", 0)
        with requests.get(url, timeout=(15, 180)) as r:
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            content = r.content
        charge(f"{pid}/download", len(content))
        with MemoryFile(content) as mem, mem.open() as src:
            if (src.crs.to_epsg(), list(src.transform)[:6], src.shape, src.count) != (p["crs"], p["affine"], (SIZE, SIZE), 3):
                raise ValueError(f"{pid}: grid mismatch")
            np.save(OUT / f"{pid}_sar.npy", src.read())
        receipts[pid] = dict(status="ACQUIRED", orbit=int(orbit), orbit_histogram=m["orbits"],
                             ascending_scenes=m["ascending"], bytes=len(content))
    save(OUT / "receipt.json", dict(receipts=receipts, log=log, requests=len(log),
                                    response_bytes=sum(x["response_bytes"] for x in log)))
    print(json.dumps(receipts), len(log), sum(x["response_bytes"] for x in log))


def verify():
    import rasterio
    plan, rec = json.loads(PREREG.read_bytes()), json.loads((OUT / "receipt.json").read_bytes())
    res = dict(phase="22V", preregistration_sha256=sha(PREREG), patches={},
               cloud_usage=dict(requests=rec["requests"], response_bytes=rec["response_bytes"]))
    for p in plan["pilot"]:
        pid, r = p["patch_id"], rec["receipts"][p["patch_id"]]
        row = dict(state=p["state"], weak_class=p["weak_class"], **{k: v for k, v in r.items() if k != "bytes"})
        if r["status"] == "ACQUIRED":
            vv, vh, count = np.load(OUT / f"{pid}_sar.npy")
            with rasterio.open(optical_path(pid, p["image_sha256"])) as src:
                if list(src.transform)[:6] != p["affine"]:
                    raise ValueError(f"{pid}: optical patch mismatch")
                opt = src.read()
            valid_s2 = np.isfinite(opt[:3]).all(axis=0) & (opt[3] >= 2)
            row.update(quality(vv, vh, count, valid_s2), s2_valid_fraction=float(valid_s2.mean()))
        res["patches"][pid] = row
    res["all_pass"] = all(v.get("passes") for v in res["patches"].values())
    save(SUMMARY, res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--acquire", "--verify"):
        g.add_argument(f, action="store_true")
    a = ap.parse_args()
    (preregister if a.preregister else acquire if a.acquire else verify)()
