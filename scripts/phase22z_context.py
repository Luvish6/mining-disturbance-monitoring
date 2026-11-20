"""Phase 22Z: offline mining-context and alternative-explanation audit of the Phase 22Y PERSISTENT clusters.

Zero Earth Engine requests. Uses only cached Phase 22X/22Y rasters, Phase 22R product samples and the one
locally archived, non-TEST official mining-site geometry (MoEFCC application polygon, Lumshnong 70 ha).
Every cluster stays UNKNOWN; the shortlist is a review-priority order, not a classification.

  python -B -m scripts.phase22z_context
"""
import itertools
import json
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import save, sha
from scripts.phase22r_product_agreement import BANDS as PBANDS, DRIVER_CLASSES, RECENT, background_mask, clusters
from scripts.phase22x_landscape import NODATA, OUT as X_OUT, PREREG as X_PREREG, S2_FIELDS, STEP, CRS
from scripts.phase22y_persistence import LUMSHNONG_BLOCKS, OUT as Y_OUT, classify

SUMMARY = Path("docs/reports/phase22z-summary.json")
LOCAL = Path("outputs/phase22z_context")
SITE = Path("outputs/phase11b_reference_packages/lumshnong-70ha-kml-v1.json")
NEAR_KM = 1.0  # fixed before computation: "near the documented application perimeter"


def tier(r):
    """Fixed review-priority rule (not a label). Tier 1: independent mining-related context (inside / within
    1 km of the official application perimeter, or in a hard-commodity-dominant driver cell). Tier 2: persistent
    with 2024/25 GFC loss. Tier 3: other persistent."""
    if r["site_distance_km"] <= NEAR_KM or r["hard_commodity_dominant"]:
        return 1
    return 2 if r["recent_loss"] else 3


def pair_rank(shares, counts, target):
    """Share of PERSISTENT clusters pooled over the target AOI pair versus every pair of AOIs (descriptive rank)."""
    keys = sorted(shares)
    pooled = lambda pair: sum(shares[k] * counts[k] for k in pair) / sum(counts[k] for k in pair)
    allp = [pooled(p) for p in itertools.combinations(keys, 2)]
    obs = pooled(target)
    return dict(target_share=float(obs), pairs=len(allp), pairs_at_or_above=int(sum(v >= obs - 1e-12 for v in allp)),
                rank_fraction=float(np.mean([v >= obs - 1e-12 for v in allp])))


def cluster_rows():
    from pyproj import Transformer
    from shapely.geometry import Point, shape
    from shapely import transform as gtransform
    from scripts.phase22l_temporal import select_candidates
    x = json.loads(X_PREREG.read_bytes())
    xs = json.loads(Path("docs/reports/phase22x-summary.json").read_bytes())
    prod = json.loads((X_OUT / "products.json").read_bytes())["grids"]
    site = json.loads(SITE.read_bytes())
    if site["split"] == "test":
        raise ValueError("Refusing TEST reference geometry")
    to_utm = Transformer.from_crs(4326, CRS, always_xy=True).transform
    to_ll = Transformer.from_crs(CRS, 4326, always_xy=True).transform
    poly = gtransform(shape(site["geometry"]), to_utm, interleaved=False)
    rows = []
    for key in sorted(x["aois"]):
        if "dVH_candidate_median_minus_background_db" not in xs["aois"][key]:
            continue
        stem = key.replace(":", "_")
        names = json.loads((X_OUT / f"{stem}_meta.json").read_bytes())["bands"]
        v = np.load(X_OUT / f"{stem}.npy").astype(float); v[v == NODATA] = np.nan
        g = dict(zip(names, v))
        b = np.stack([g[f"before_{k}"] for k in S2_FIELDS]); a = np.stack([g[f"after_{k}"] for k in S2_FIELDS])
        eligible, cand, _, _ = select_candidates(b, a, np.nan_to_num(g["before_count"]), np.nan_to_num(g["after_count"]), g["slope"])
        f = np.load(Y_OUT / f"{stem}.npy").astype(float); f[f == NODATA] = np.nan
        fu = dict(zip(list(S2_FIELDS) + ["count"], f))
        obs = np.isfinite(fu["NDVI"]) & np.isfinite(fu["BSI"]) & (np.nan_to_num(fu["count"]) >= 2) & (np.nan_to_num(fu["NDWI"], nan=1) < 0)
        p = dict(zip(PBANDS, np.array(prod[key])))
        hp = np.where(p["hard_commodities_p250"] >= 0, p["hard_commodities_p250"] * .004, np.nan)
        dvh = g["after_VH"] - g["before_VH"]
        bg_vh = np.nanmedian(dvh[background_mask(eligible, cand) & (p["datamask"] == 1)])
        x0, y1 = x["aois"][key]["bounds"][0], x["aois"][key]["bounds"][3]
        for i, c in enumerate(clusters(cand), 1):
            r_, c_ = c[:, 0], c[:, 1]
            o = obs[r_, c_]
            dn = float(np.mean(fu["NDVI"][r_, c_][o] - g["before_NDVI"][r_, c_][o])) if o.any() else np.nan
            db = float(np.mean(fu["BSI"][r_, c_][o] - g["before_BSI"][r_, c_][o])) if o.any() else np.nan
            cx, cy = x0 + (c_.mean() + .5) * STEP, y1 - (r_.mean() + .5) * STEP
            classes = [int(k) for k in p["driver_class"][r_, c_]]
            dom = max(set(classes), key=classes.count)
            rows.append(dict(
                id=f"{key}/C{i:03d}", aoi=key, district=xs["aois"][key]["district"], split=x["aois"][key]["split"],
                cells=len(c), ha=len(c) * .09, cls=classify(dn, db, o.mean() >= .5), dNDVI_followup=dn, dBSI_followup=db,
                dvh_minus_bg_db=float(np.mean(dvh[r_, c_]) - bg_vh), slope_deg=float(np.mean(g["slope"][r_, c_])),
                recent_loss=bool(np.isin(p["lossyear"][r_, c_], RECENT).any()),
                prior_loss=bool(((p["lossyear"][r_, c_] >= 1) & (p["lossyear"][r_, c_] <= 23)).any()),
                treecover2000=float(p["treecover2000"][r_, c_].mean()),
                driver_dominant=DRIVER_CLASSES.get(dom, "masked/none"), hard_commodity_dominant=dom == 2,
                hard_commodities_p=float(np.nanmean(hp[r_, c_])), lumshnong_locality=key in LUMSHNONG_BLOCKS,
                site_distance_km=float(poly.distance(Point(cx, cy)) / 1000), _centroid_wgs84=list(to_ll(cx, cy))))
    return rows, site


def main():
    rows, site = cluster_rows()
    ref = json.loads((Y_OUT / "clusters.json").read_bytes())
    if [r["cls"] for r in rows] != [r["cls"] for r in ref]:
        raise ValueError("Cluster classes differ from Phase 22Y")
    pers = [r for r in rows if r["cls"] == "PERSISTENT"]
    for r in pers:
        r["tier"] = tier(r)
    counts = {a: sum(r["aoi"] == a for r in rows) for a in {r["aoi"] for r in rows}}
    shares = {a: sum(r["aoi"] == a and r["cls"] == "PERSISTENT" for r in rows) / n for a, n in counts.items()}
    lum, other = [r for r in rows if r["lumshnong_locality"]], [r for r in rows if not r["lumshnong_locality"]]
    share = lambda rs: [sum(r["cls"] == "PERSISTENT" for r in rs), len(rs)]
    other_aoi_shares = sorted(v for k, v in shares.items() if k not in LUMSHNONG_BLOCKS)
    pk = lambda rs, k: float(np.mean([r[k] for r in rs])) if rs else None
    res = dict(
        phase="22Z", earth_engine_requests=0,
        inputs=dict(phase22x_prereg=sha(X_PREREG), phase22y_summary=sha("docs/reports/phase22y-summary.json"),
                    site_package_sha256=sha(SITE), site=dict(name=site["provenance"]["site_name"],
                    kind=site["geometry_kind"], source=site["provenance"]["source_organization"], split=site["split"],
                    note="administrative application perimeter; positional accuracy and activity unverified")),
        persistent=dict(total=len(pers), by_district={d: sum(r["district"] == d for r in pers) for d in sorted({r["district"] for r in pers})},
                        by_aoi={a: sum(r["aoi"] == a for r in pers) for a in sorted({r["aoi"] for r in pers})},
                        inside_site=sum(r["site_distance_km"] == 0 for r in pers),
                        within_1km_site=sum(r["site_distance_km"] <= NEAR_KM for r in pers),
                        hard_commodity_dominant=sum(r["hard_commodity_dominant"] for r in pers),
                        driver_dominant={k: sum(r["driver_dominant"] == k for r in pers) for k in sorted({r["driver_dominant"] for r in pers})},
                        tiers={t: sum(r["tier"] == t for r in pers) for t in (1, 2, 3)}),
        lumshnong=dict(locality_blocks=sorted(LUMSHNONG_BLOCKS), adjacent=True,
                       persistent_share_locality=share(lum), persistent_share_elsewhere=share(other),
                       other_aoi_persistent_shares=other_aoi_shares,
                       other_aois_at_or_above_locality=int(sum(v >= share(lum)[0] / share(lum)[1] for v in other_aoi_shares)),
                       pair_rank=pair_rank(shares, counts, tuple(sorted(LUMSHNONG_BLOCKS))),
                       slope_mean=dict(locality=pk(lum, "slope_deg"), elsewhere=pk(other, "slope_deg")),
                       persistent_slope=dict(locality=pk([r for r in lum if r["cls"] == "PERSISTENT"], "slope_deg"),
                                             elsewhere=pk([r for r in other if r["cls"] == "PERSISTENT"], "slope_deg"))),
        alternatives_outside_lumshnong={c: dict(n=sum(r["cls"] == c for r in other),
                                                slope=pk([r for r in other if r["cls"] == c], "slope_deg"),
                                                treecover2000=pk([r for r in other if r["cls"] == c], "treecover2000"),
                                                prior_loss=pk([r for r in other if r["cls"] == c], "prior_loss"),
                                                recent_loss=pk([r for r in other if r["cls"] == c], "recent_loss"),
                                                shifting_cultivation_dominant=pk([dict(v=float(r["driver_dominant"] == "Shifting cultivation")) for r in other if r["cls"] == c], "v"))
                                        for c in ("PERSISTENT", "PARTIAL", "RECOVERING")},
        shortlist=[{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if not k.startswith("_")}
                   for r in sorted(pers, key=lambda r: (r["tier"], r["site_distance_km"], -r["ha"]))],
        offline_answerable=["spatial distribution", "Lumshnong vs elsewhere shares", "distance to the one archived official "
                            "application perimeter", "terrain, GFC loss, tree-cover and 1 km driver context", "persistence"],
        requires_unavailable_data=["active excavation footprints (DMR/MBDA drone survey, IBM georeferenced plans)",
                                   "roads and settlements at 30 m (OSM or Bhuvan not cached)", "field or expert verification",
                                   "dated lease boundaries beyond the single application polygon"],
        decision="NO-GO for mining attribution: no independent activity-footprint evidence; only one administrative perimeter",
        status="all clusters UNKNOWN; shortlist is review priority only")
    save(SUMMARY, res)
    LOCAL.mkdir(parents=True, exist_ok=True)
    with open(LOCAL / "shortlist_with_centroids.json", "w") as fh:  # exact locations stay local
        json.dump([dict(id=r["id"], tier=r["tier"], centroid_wgs84=r["_centroid_wgs84"]) for r in pers], fh, indent=1)
    print(json.dumps({k: res[k] for k in ("persistent", "lumshnong", "alternatives_outside_lumshnong")}, indent=1)[:5000])


if __name__ == "__main__":
    main()
