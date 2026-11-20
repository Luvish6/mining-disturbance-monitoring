"""Phase 22AA: OpenStreetMap infrastructure alternative-explanation audit of the Phase 22X/22Y clusters.

Zero Earth Engine requests. One Overpass request for highway/building ways inside the 20 guarded 22X AOIs
expanded by 500 m (each expanded WGS84 envelope verified outside TEST buffers and inside the districts).
OSM data (c) OpenStreetMap contributors, ODbL 1.0. Absence of mapped infrastructure is NOT absence.

  --preregister  -> docs/reports/phase22aa-preregistration.json (offline)
  --download     one Overpass request -> outputs/phase22aa_osm/osm.json (local only)
  --analyze      -> docs/reports/phase22aa-summary.json
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import save, sha
from scripts.phase22r_product_agreement import translation_null, frac_any, mean_of_means
from scripts.phase22x_landscape import CRS, OUT as X_OUT, PREREG as X_PREREG, STEP
from scripts.phase22y_persistence import LUMSHNONG_BLOCKS, within_aoi_permutation

PREREG = Path("docs/reports/phase22aa-preregistration.json")
SUMMARY = Path("docs/reports/phase22aa-summary.json")
OUT = Path("outputs/phase22aa_osm")
ENDPOINT = "https://overpass-api.de/api/interpreter"
EXPAND_M, ADJ_M, CAP_M = 500, 60, 500
MAX_BYTES = 20_000_000


def query(bboxes):
    parts = "".join(f'way["highway"]({s},{w},{n},{e});way["building"]({s},{w},{n},{e});' for s, w, n, e in bboxes)
    return f"[out:json][timeout:120];({parts});out geom;"


def envelope_wgs84(bounds, expand=EXPAND_M):
    from pyproj import Transformer
    t = Transformer.from_crs(CRS, 4326, always_xy=True).transform
    x0, y0, x1, y1 = bounds
    xs, ys = zip(*[t(x, y) for x in (x0 - expand, x1 + expand) for y in (y0 - expand, y1 + expand)])
    return [min(ys), min(xs), max(ys), max(xs)]  # south, west, north, east


def censored_distance(geom, features, cap=CAP_M):
    d = min((geom.distance(f) for f in features), default=np.inf)
    return float(min(d, cap))


def preregister():
    from pyproj import Transformer
    from shapely.geometry import box
    from scripts.phase22n_temporal import guards
    area, protected = guards()
    x = json.loads(X_PREREG.read_bytes())
    back = Transformer.from_crs(4326, CRS, always_xy=True).transform
    rows = {}
    for key, a in sorted(x["aois"].items()):
        s, w, n, e = envelope_wgs84(a["bounds"])
        env = box(*[back(w, s)[0], back(w, s)[1], back(e, n)[0], back(e, n)[1]]).envelope
        corners = [back(lon, lat) for lon in (w, e) for lat in (s, n)]
        env = box(min(c[0] for c in corners), min(c[1] for c in corners), max(c[0] for c in corners), max(c[1] for c in corners))
        hits = [k for k, g in protected if env.intersects(g)]
        if hits or not area.covers(env):
            raise ValueError(f"{key}: query envelope intersects TEST {hits} or leaves districts")
        rows[key] = dict(bbox_swne=[round(v, 6) for v in (s, w, n, e)], test_buffer_distance_m=round(min(env.distance(g) for _, g in protected), 1))
    save(PREREG, dict(
        phase="22AA", date=datetime.now(timezone.utc).date().isoformat(),
        source=dict(endpoint=ENDPOINT, query_template='way["highway"](bbox); way["building"](bbox); out geom;',
                    requests=1, max_bytes=MAX_BYTES, licence="ODbL 1.0; (c) OpenStreetMap contributors",
                    user_agent="generic research client; no personal data"),
        query_extents=rows, expand_m=EXPAND_M,
        inputs=dict(phase22x_prereg=sha(X_PREREG), phase22y_summary=sha("docs/reports/phase22y-summary.json"),
                    phase22z_summary=sha("docs/reports/phase22z-summary.json")),
        units="the 174 SAR-tested 22X clusters with frozen 22Y classes and 22Z tiers; cluster = union of its 30 m cells",
        metrics=dict(distance=f"distance from cluster polygon to nearest highway way / building way, right-censored at {CAP_M} m",
                     adjacent=f"road or building within {ADJ_M} m (2 cells) of the cluster polygon"),
        tests=dict(
            background="shape-preserving translation of each cluster within its AOI's 22X background (Phase 22R "
                       "translation_null, 10,000 draws, seed 46), statistic = share adjacent, per class",
            classes="PERSISTENT vs other: class labels permuted within AOI (Phase 22Y), share adjacent and mean censored distance",
            lumshnong="87:556+87:557 reported as one locality, separately from the other 16 AOIs"),
        completeness=dict(per_aoi="mapped road length and building count inside each AOI reported",
                          sparse_rule="AOI is OSM-SPARSE if it has 0 mapped buildings AND < 1 km mapped highway inside the AOI",
                          sensitivity="all tests repeated excluding OSM-SPARSE AOIs"),
        priority_rule="Tier-1/2 clusters adjacent to mapped infrastructure are flagged INFRASTRUCTURE_ADJACENT (alternative "
                      "explanation to check first); tiers are not changed and no cluster is relabelled",
        go_rule="GO for infrastructure assessment only if >= 12 of the 18 cluster-bearing AOIs are not OSM-SPARSE",
        not_done="no EE requests, no training, no thresholds changed, no TEST geography, all clusters UNKNOWN"))
    print(json.dumps(rows)[:400])


def download():
    import requests
    plan = json.loads(PREREG.read_bytes())
    target = OUT / "osm.json"
    if target.exists():
        raise SystemExit("OSM cache exists; refusing a second request")
    OUT.mkdir(parents=True, exist_ok=True)
    q = query([v["bbox_swne"] for v in plan["query_extents"].values()])
    stamp = datetime.now(timezone.utc).isoformat()
    r = requests.post(ENDPOINT, data={"data": q}, timeout=(15, 180),
                      headers={"User-Agent": "mining-disturbance-research/1.0 (academic, non-commercial)"})
    if r.status_code != 200 or len(r.content) > MAX_BYTES:
        raise RuntimeError(f"HTTP {r.status_code}, {len(r.content)} bytes")
    target.write_bytes(r.content)
    d = r.json()
    save(OUT / "receipt.json", dict(requested_utc=stamp, endpoint=ENDPOINT, query=q, http=r.status_code,
                                    response_bytes=len(r.content), sha256=sha(target),
                                    osm_base=d.get("osm3s", {}).get("timestamp_osm_base"), elements=len(d["elements"]),
                                    licence="ODbL 1.0; (c) OpenStreetMap contributors"))
    print("bytes", len(r.content), "elements", len(d["elements"]), d.get("osm3s", {}).get("timestamp_osm_base"))


def analyze():
    from pyproj import Transformer
    from rasterio.features import rasterize
    from affine import Affine
    from shapely.geometry import LineString, Polygon, box
    from shapely.ops import unary_union
    from shapely import transform as gtransform
    from scripts.phase22l_temporal import select_candidates
    from scripts.phase22r_product_agreement import background_mask, clusters, BANDS as PBANDS
    from scripts.phase22x_landscape import NODATA, S2_FIELDS
    plan = json.loads(PREREG.read_bytes())
    rec = json.loads((OUT / "receipt.json").read_bytes())
    if sha(OUT / "osm.json") != rec["sha256"]:
        raise ValueError("OSM cache hash mismatch")
    osm = json.loads((OUT / "osm.json").read_bytes())["elements"]
    t = Transformer.from_crs(4326, CRS, always_xy=True).transform
    roads, builds = [], []
    for el in osm:
        pts = [t(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        if len(pts) < 2:
            continue
        tags = el.get("tags", {})
        if "building" in tags:
            builds.append(Polygon(pts) if len(pts) >= 4 and pts[0] == pts[-1] else LineString(pts))
        elif "highway" in tags:
            roads.append(LineString(pts))
    x = json.loads(X_PREREG.read_bytes())
    xs = json.loads(Path("docs/reports/phase22x-summary.json").read_bytes())
    y = json.loads(Path("outputs/phase22y_persistence/clusters.json").read_bytes())
    z = {r["id"]: r for r in json.loads(Path("docs/reports/phase22z-summary.json").read_bytes())["shortlist"]}
    prod = json.loads((X_OUT / "products.json").read_bytes())["grids"]
    rows, strata, aoi_info, yi = [], {}, {}, 0
    for key in sorted(x["aois"]):
        a = x["aois"][key]
        x0, y0, x1, y1 = a["bounds"]
        aoi_box = box(*a["bounds"])
        rl = sum(r.intersection(aoi_box).length for r in roads) / 1000
        nb = sum(b.intersects(aoi_box) for b in builds)
        sparse = nb == 0 and rl < 1.0
        aoi_info[key] = dict(road_km_in_aoi=round(rl, 3), buildings_in_aoi=int(nb), osm_sparse=bool(sparse))
        if "dVH_candidate_median_minus_background_db" not in xs["aois"][key]:
            continue
        stem = key.replace(":", "_")
        names = json.loads((X_OUT / f"{stem}_meta.json").read_bytes())["bands"]
        v = np.load(X_OUT / f"{stem}.npy").astype(float); v[v == NODATA] = np.nan
        g = dict(zip(names, v))
        b = np.stack([g[f"before_{k}"] for k in S2_FIELDS]); af = np.stack([g[f"after_{k}"] for k in S2_FIELDS])
        eligible, cand, _, _ = select_candidates(b, af, np.nan_to_num(g["before_count"]), np.nan_to_num(g["after_count"]), g["slope"])
        p = dict(zip(PBANDS, np.array(prod[key])))
        bg = background_mask(eligible, cand) & (p["datamask"] == 1)
        affine = Affine(STEP, 0, x0, 0, -STEP, y1)
        near = [f.buffer(ADJ_M) for f in roads + builds if f.distance(aoi_box) <= ADJ_M]
        adj_grid = rasterize([(u, 1) for u in near], out_shape=bg.shape, transform=affine, fill=0, all_touched=False).astype(bool) \
            if near else np.zeros(bg.shape, bool)  # cell-centre rule
        local_roads = [r for r in roads if r.distance(aoi_box) <= CAP_M]
        local_builds = [f for f in builds if f.distance(aoi_box) <= CAP_M]
        cl = clusters(cand)
        labels = []
        for i, c in enumerate(cl, 1):
            ref = y[yi]; yi += 1
            if (ref["aoi"], ref["cluster"]) != (key, i):
                raise ValueError("cluster order differs from Phase 22Y")
            poly = unary_union([box(x0 + cc * STEP, y1 - (rr + 1) * STEP, x0 + (cc + 1) * STEP, y1 - rr * STEP) for rr, cc in c])
            dr, db = censored_distance(poly, local_roads), censored_distance(poly, local_builds)
            cid = f"{key}/C{i:03d}"
            rows.append(dict(id=cid, aoi=key, cls=ref["cls"], tier=z.get(cid, {}).get("tier"), road_m=dr, building_m=db,
                             adjacent=bool(min(dr, db) <= ADJ_M), lumshnong=key in LUMSHNONG_BLOCKS, osm_sparse=sparse))
            labels.append(ref["cls"])
        strata[key] = (cl, labels, bg, adj_grid)
    if yi != len(y):
        raise ValueError("not all Phase 22Y clusters matched")

    def tests(keys):
        out = {}
        for c in ("PERSISTENT", "PARTIAL", "RECOVERING"):
            st = [([cc for cc, l in zip(strata[k][0], strata[k][1]) if l == c], strata[k][2], strata[k][3]) for k in keys]
            st = [s for s in st if s[0]]
            if st:
                obs, null = translation_null(st, frac_any)
                out[c] = dict(clusters=sum(len(s[0]) for s in st), share_adjacent=obs, background_translation_null=null)
        sub = [r for r in rows if r["aoi"] in keys]
        lab, aois = [r["cls"] for r in sub], [r["aoi"] for r in sub]
        out["persistent_vs_other_adjacent"] = within_aoi_permutation(lab, [float(r["adjacent"]) for r in sub], aois)
        out["persistent_vs_other_min_distance_m"] = within_aoi_permutation(lab, [min(r["road_m"], r["building_m"]) for r in sub], aois)
        return out

    allk = sorted(strata)
    dense = [k for k in allk if not aoi_info[k]["osm_sparse"]]
    nonlum = [k for k in allk if k not in LUMSHNONG_BLOCKS]
    share = lambda rs: [int(sum(r["adjacent"] for r in rs)), len(rs)]
    res = dict(phase="22AA", preregistration_sha256=sha(PREREG), earth_engine_requests=0,
               osm=dict(requests=1, response_bytes=rec["response_bytes"], osm_base=rec["osm_base"], elements=rec["elements"],
                        roads=len(roads), buildings=len(builds), licence=rec["licence"]),
               aoi_coverage=aoi_info,
               coverage_summary=dict(cluster_aois=len(allk), osm_sparse_cluster_aois=sum(aoi_info[k]["osm_sparse"] for k in allk)),
               adjacency_by_class={c: share([r for r in rows if r["cls"] == c]) for c in ("PERSISTENT", "PARTIAL", "RECOVERING")},
               adjacency_by_tier={t: share([r for r in rows if r["tier"] == t]) for t in (1, 2, 3)},
               lumshnong=dict(persistent=share([r for r in rows if r["lumshnong"] and r["cls"] == "PERSISTENT"]),
                              other_classes=share([r for r in rows if r["lumshnong"] and r["cls"] != "PERSISTENT"]),
                              buildings_in_locality=sum(aoi_info[k]["buildings_in_aoi"] for k in LUMSHNONG_BLOCKS),
                              road_km_in_locality=round(sum(aoi_info[k]["road_km_in_aoi"] for k in LUMSHNONG_BLOCKS), 3)),
               tests_all=tests(allk), tests_excluding_osm_sparse=tests(dense) if dense else None,
               tests_excluding_lumshnong=tests(nonlum),
               flagged_tier12=[dict(id=r["id"], tier=r["tier"], road_m=round(r["road_m"]), building_m=round(r["building_m"]))
                               for r in rows if r["tier"] in (1, 2) and r["adjacent"]],
               decision=None, status="all clusters UNKNOWN; adjacency is an alternative explanation to check, not a label")
    res["decision"] = ("GO" if len(allk) - res["coverage_summary"]["osm_sparse_cluster_aois"] >= 12 else "NO-GO") + \
        ": infrastructure explanations can be assessed only where OSM maps infrastructure; absence is not proof of absence"
    save(SUMMARY, res)
    print(json.dumps({k: res[k] for k in ("osm", "coverage_summary", "adjacency_by_class", "adjacency_by_tier", "lumshnong", "decision")}, indent=1))
    print(json.dumps(res["tests_all"], indent=1)[:3000])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--download", "--analyze"):
        g.add_argument(f, action="store_true")
    a = ap.parse_args()
    (preregister if a.preregister else download if a.download else analyze)()
