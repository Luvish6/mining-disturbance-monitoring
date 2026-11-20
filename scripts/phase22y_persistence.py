"""Phase 22Y: persistence-based typology of the Phase 22X disturbance clusters.

A third, follow-up dry season (2025-11-01 to 2026-04-01, exclusive) is added with the unchanged Phase 22L
optical graph. Each cluster is classed PERSISTENT / PARTIAL / RECOVERING / UNOBSERVED relative to the
2023-24 baseline. "Persistent" is a mining-COMPATIBLE review-priority class, never a mining label.

  --preregister  -> docs/reports/phase22y-preregistration.json (offline)
  --acquire      locked, ledger-capped (<= 70 requests, <= 6 MB)
  --analyze      -> docs/reports/phase22y-summary.json (offline)
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import save, sha
from scripts.phase22r_product_agreement import BANDS as PBANDS, RECENT, background_mask, clusters
from scripts.phase22w_ablation import acquire_lock, ledger_usage
from scripts.phase22x_landscape import NODATA, OUT as X_OUT, PREREG as X_PREREG, S2_FIELDS, SIZE, STEP, CRS

PREREG = Path("docs/reports/phase22y-preregistration.json")
SUMMARY = Path("docs/reports/phase22y-summary.json")
OUT = Path("outputs/phase22y_persistence")
LEDGER = OUT / "ledger.jsonl"
FOLLOW_UP = ("2025-26", "2025-11-01", "2026-04-01")
BUDGET = dict(max_requests=70, max_bytes=6_000_000)
LUMSHNONG_BLOCKS = {"87:556", "87:557"}  # hard-commodity-dominant driver cells in Phase 22X
PERM, SEED = 10000, 48


# ------------------------------------------------------------------ pure logic
def classify(dndvi_follow, dbsi_follow, observed):
    """Cluster-mean change from the 2023-24 baseline to the 2025-26 follow-up season.
    Thresholds are the unchanged Phase 22L rule (-0.30 / +0.10) plus a fixed 0.10 recovery band."""
    if not observed:
        return "UNOBSERVED"
    if dndvi_follow <= -0.30 and dbsi_follow > 0.10:
        return "PERSISTENT"
    if dndvi_follow >= -0.10:
        return "RECOVERING"
    return "PARTIAL"


def within_aoi_permutation(labels, values, aois, draws=PERM, seed=SEED):
    """Mean(value | PERSISTENT) - mean(value | other), permuting class labels only within each AOI."""
    labels, values, aois = np.asarray(labels), np.asarray(values, float), np.asarray(aois)
    ok = np.isfinite(values)
    labels, values, aois = labels[ok], values[ok], aois[ok]
    pers = labels == "PERSISTENT"
    if pers.all() or not pers.any():
        return None
    stat = lambda p: float(values[p].mean() - values[~p].mean())
    obs, rng, null = stat(pers), np.random.default_rng(seed), np.empty(draws)
    groups = [np.flatnonzero(aois == a) for a in np.unique(aois)]
    for i in range(draws):
        p = pers.copy()
        for g in groups:
            p[g] = rng.permutation(pers[g])
        null[i] = stat(p) if p.any() and not p.all() else 0.0
    return dict(observed=obs, null_median=float(np.median(null)),
                p_two_sided=float((1 + np.sum(np.abs(null - np.median(null)) >= abs(obs - np.median(null)))) / (1 + draws)),
                n_persistent=int(pers.sum()), n_other=int((~pers).sum()))


def aoi_bootstrap_shares(labels, aois, draws=PERM, seed=SEED):
    labels, aois = np.asarray(labels), np.asarray(aois)
    ua = np.unique(aois)
    rng = np.random.default_rng(seed)
    classes = ("PERSISTENT", "PARTIAL", "RECOVERING", "UNOBSERVED")
    sims = {c: [] for c in classes}
    for _ in range(draws):
        pick = rng.choice(ua, len(ua))
        lab = np.concatenate([labels[aois == a] for a in pick])
        for c in classes:
            sims[c].append((lab == c).mean() if len(lab) else np.nan)
    return {c: dict(share=float((labels == c).mean()), ci95=[float(np.nanpercentile(sims[c], 2.5)),
                                                           float(np.nanpercentile(sims[c], 97.5))],
                    clusters=int((labels == c).sum())) for c in classes}


# ------------------------------------------------------------------ stages
def preregister():
    x = json.loads(X_PREREG.read_bytes())
    save(PREREG, dict(
        phase="22Y", date=datetime.now(timezone.utc).date().isoformat(), budget=BUDGET, follow_up_season=FOLLOW_UP,
        source=dict(phase22x_preregistration_sha256=sha(X_PREREG), aois=sorted(x["aois"]),
                    phase22x_summary_sha256=sha("docs/reports/phase22x-summary.json")),
        optical="unchanged Phase 22L seasonal_graph (SCL 4/5, cloud prob < 40, NDWI < 0, brightness >= 0.04, >= 2 obs) "
                "for the follow-up season on the identical 22X AOI grids",
        clusters="the 174 SAR-tested Phase 22X clusters (8-connected candidates of the unchanged 22L rule); no new detection",
        classes=dict(
            unit="cluster mean over its cells observed in the follow-up season; UNOBSERVED if < 50% of cells observed",
            PERSISTENT="NDVI(follow-up) - NDVI(2023-24) <= -0.30 AND BSI(follow-up) - BSI(2023-24) > +0.10",
            RECOVERING="NDVI(follow-up) - NDVI(2023-24) >= -0.10",
            PARTIAL="otherwise"),
        associations=dict(
            covariates=["hard-commodities probability (22R drivers)", "2024/25 GFC loss in cluster",
                        "cluster dVH minus AOI background (22X)", "mean slope", "Lumshnong blocks 87:556/87:557"],
            test=f"mean(PERSISTENT) - mean(other), class labels permuted within AOI, {PERM} draws, seed {SEED}",
            shares="class shares with AOI-bootstrap 95% CI (AOI = sampling unit)"),
        interpretation="PERSISTENT = non-revegetating, mining-COMPATIBLE disturbance for review priority; roads, "
                       "construction, quarries, dumps and slow fallows are all compatible; not a mining label",
        not_done="no threshold tuning, no model training, no TEST access, no accuracy metrics"))
    print("preregistered", len(x["aois"]), "AOIs")


def acquire():
    import ee
    import requests
    from affine import Affine
    from rasterio.io import MemoryFile
    from config.phase2_settings import Phase2Config
    from config.settings import Season
    from scripts.phase22l_temporal import seasonal_graph
    from src.gee_setup import initialize
    plan = json.loads(PREREG.read_bytes())
    x = json.loads(X_PREREG.read_bytes())
    if sha(X_PREREG) != plan["source"]["phase22x_preregistration_sha256"]:
        raise ValueError("22X preregistration changed")
    OUT.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock(OUT / ".acquire.lock")
    try:
        initialize()
        cfg, season = Phase2Config(), Season(*FOLLOW_UP)

        def gate(planned):
            n, b = ledger_usage(LEDGER)
            if n + 1 > BUDGET["max_requests"] or b + planned > BUDGET["max_bytes"]:
                raise SystemExit(f"Budget stop: {n} requests, {b} bytes")

        def log(e):
            with LEDGER.open("a") as fh:
                fh.write(json.dumps(e) + "\n")

        for key in plan["source"]["aois"]:
            target = OUT / f"{key.replace(':', '_')}.npy"
            if target.exists():
                continue
            x0, y0, x1, y1 = x["aois"][key]["bounds"]
            affine = Affine(STEP, 0, x0, 0, -STEP, y1)
            region = ee.Geometry.Rectangle([x0, y0, x1, y1], CRS, False)
            image, count, raw, joined = seasonal_graph(region, season, cfg)
            stack = image.select(list(S2_FIELDS)).addBands(count.rename("count"))
            gate(20_000)
            info = ee.Dictionary(dict(joined=joined.size(), raw=raw.size(), bands=stack.bandNames())).getInfo()
            log(dict(aoi=key, request="metadata", response_bytes=len(json.dumps(info).encode())))
            if info["bands"] != list(S2_FIELDS) + ["count"]:
                raise ValueError(f"{key}: bands {info['bands']}")
            gate(0)
            url = stack.toFloat().unmask(NODATA, False).getDownloadURL(
                dict(format="GEO_TIFF", crs=CRS, crs_transform=list(affine)[:6], dimensions=[SIZE, SIZE]))
            log(dict(aoi=key, request="url", response_bytes=0))
            gate(200_000)
            with requests.get(url, timeout=(15, 180)) as r:
                log(dict(aoi=key, request="download", response_bytes=len(r.content), status=r.status_code))
                if r.status_code != 200:
                    raise RuntimeError(f"{key}: HTTP {r.status_code}")
                content = r.content
            with MemoryFile(content) as mem, mem.open() as src:
                if (src.crs.to_string(), src.transform, src.shape, src.count) != (CRS, affine, (SIZE, SIZE), 7):
                    raise ValueError(f"{key}: grid")
                np.save(target, src.read())
            save(OUT / f"{key.replace(':', '_')}_meta.json", dict(joined=info["joined"], raw=info["raw"]))
            print(key, info["joined"], flush=True)
        n, b = ledger_usage(LEDGER)
        save(OUT / "acquisition.json", dict(requests=n, response_bytes=b))
        print("requests", n, "bytes", b)
    finally:
        lock.unlink(missing_ok=True)


def analyze():
    from scripts.phase22l_temporal import select_candidates
    plan = json.loads(PREREG.read_bytes())
    xs = json.loads(Path("docs/reports/phase22x-summary.json").read_bytes())
    prod = json.loads((X_OUT / "products.json").read_bytes())["grids"]
    rows = []
    for key in plan["source"]["aois"]:
        if "dVH_candidate_median_minus_background_db" not in xs["aois"][key]:
            continue  # same SAR-tested cluster set as 22X
        names = json.loads((X_OUT / f"{key.replace(':', '_')}_meta.json").read_bytes())["bands"]
        v = np.load(X_OUT / f"{key.replace(':', '_')}.npy").astype(float); v[v == NODATA] = np.nan
        g = dict(zip(names, v))
        b = np.stack([g[f"before_{k}"] for k in S2_FIELDS]); a = np.stack([g[f"after_{k}"] for k in S2_FIELDS])
        eligible, cand, _, _ = select_candidates(b, a, np.nan_to_num(g["before_count"]), np.nan_to_num(g["after_count"]), g["slope"])
        f = np.load(OUT / f"{key.replace(':', '_')}.npy").astype(float); f[f == NODATA] = np.nan
        fu = dict(zip(list(S2_FIELDS) + ["count"], f))
        obs = np.isfinite(fu["NDVI"]) & np.isfinite(fu["BSI"]) & (np.nan_to_num(fu["count"]) >= 2) & (np.nan_to_num(fu["NDWI"], nan=1) < 0)
        p = dict(zip(PBANDS, np.array(prod[key])))
        hp = np.where(p["hard_commodities_p250"] >= 0, p["hard_commodities_p250"] * .004, np.nan)
        recent = np.isin(p["lossyear"], RECENT)
        dvh = g["after_VH"] - g["before_VH"]
        bg = background_mask(eligible, cand) & (p["datamask"] == 1)  # same background as Phase 22X
        bg_vh = np.nanmedian(dvh[bg])
        for i, c in enumerate(clusters(cand), 1):
            r_, c_ = c[:, 0], c[:, 1]
            o = obs[r_, c_]
            observed = o.mean() >= 0.5
            dn = float(np.mean(fu["NDVI"][r_, c_][o] - g["before_NDVI"][r_, c_][o])) if o.any() else np.nan
            db = float(np.mean(fu["BSI"][r_, c_][o] - g["before_BSI"][r_, c_][o])) if o.any() else np.nan
            rows.append(dict(aoi=key, district=xs["aois"][key]["district"], cluster=i, cells=len(c),
                             follow_observed_fraction=float(o.mean()), dNDVI_followup=dn, dBSI_followup=db,
                             dNDVI_after=float(np.mean(g["after_NDVI"][r_, c_] - g["before_NDVI"][r_, c_])),
                             cls=classify(dn, db, observed), hard_commodities_p=float(np.nanmean(hp[r_, c_])),
                             recent_loss=float(recent[r_, c_].any()), dvh_minus_bg=float(np.mean(dvh[r_, c_]) - bg_vh),
                             slope=float(np.mean(g["slope"][r_, c_])), lumshnong=float(key in LUMSHNONG_BLOCKS)))
    labels, aois = [r["cls"] for r in rows], [r["aoi"] for r in rows]
    res = dict(phase="22Y", preregistration_sha256=sha(PREREG), clusters=len(rows), aois=len(set(aois)),
               shares=aoi_bootstrap_shares(labels, aois), associations={})
    for k in ("hard_commodities_p", "recent_loss", "dvh_minus_bg", "slope", "lumshnong"):
        res["associations"][k] = within_aoi_permutation(labels, [r[k] for r in rows], aois)
        res["associations"][k + "_by_class"] = {c: float(np.nanmean([r[k] for r in rows if r["cls"] == c]))
                                                for c in sorted(set(labels))}
    res["by_district"] = {d: {c: sum(1 for r in rows if r["district"] == d and r["cls"] == c) for c in sorted(set(labels))}
                          for d in sorted({r["district"] for r in rows})}
    res["lumshnong_blocks"] = {c: sum(1 for r in rows if r["lumshnong"] and r["cls"] == c) for c in sorted(set(labels))}
    res["per_aoi"] = {a: {c: sum(1 for r in rows if r["aoi"] == a and r["cls"] == c) for c in sorted(set(labels))}
                      for a in sorted(set(aois))}
    s = json.loads((OUT / "acquisition.json").read_bytes())
    res["cloud_usage"] = s
    res["interpretation"] = "PERSISTENT is mining-compatible review priority only; candidates remain UNKNOWN; no accuracy"
    save(SUMMARY, res)
    with open(OUT / "clusters.json", "w") as fh:
        json.dump(rows, fh, indent=1)
    print(json.dumps({k: res[k] for k in ("clusters", "shares", "by_district", "lumshnong_blocks")}, indent=1))
    print(json.dumps(res["associations"], indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--acquire", "--analyze"):
        g.add_argument(f, action="store_true")
    a = ap.parse_args()
    (preregister if a.preregister else acquire if a.acquire else analyze)()
