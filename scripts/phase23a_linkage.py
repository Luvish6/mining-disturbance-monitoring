"""Phase 23A Stage 2: drainage-path linkage of the 174 Phase 22X clusters to monitored river reaches.

Static terrain/hydrography only (HydroSHEDS 3 arc-second D8 flow direction + Free-Flowing-Rivers reaches).
No imagery, no TEST imagery/labels/predictions. Linkage is exposure geometry: it says where a cluster's
surface runoff is routed by a 90 m DEM model, NOT that the cluster affects the river. Clusters stay UNKNOWN.

  --preregister  -> docs/reports/phase23a-linkage-preregistration.json (offline)
  --acquire      locked, ledger-capped (<= 6 requests, <= 6 MB)
  --analyze      -> docs/reports/phase23a-linkage-summary.json
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.phase22p_sar_corroboration import save, sha
from scripts.phase22w_ablation import acquire_lock, ledger_usage

PREREG = Path("docs/reports/phase23a-linkage-preregistration.json")
SUMMARY = Path("docs/reports/phase23a-linkage-summary.json")
OUT = Path("outputs/phase23a_linkage")
LEDGER = OUT / "ledger.jsonl"
DIR_ASSET, FFR_ASSET = "WWF/HydroSHEDS/03DIR", "WWF/HydroSHEDS/v1/FreeFlowingRivers"
RES = 1 / 1200  # 3 arc-seconds
BBOX = (91.93, 24.98, 92.85, 25.80)  # district union bounds + ~0.05 deg, snapped below
STATIONS = {"Lukha-Khaddum-4315": 4103404, "Lukha-Sunapur-3376": 4110349,
            "Myntdu-Mihmyntdu-4316": 4090610, "Myntdu-Leshka-3379": 4100220}  # Phase 4A/22O reach GOIDs
SNAP_M, MAX_STEPS, MIN_UPSTREAM = 90.0, 3000, 3
BUDGET = dict(max_requests=6, max_bytes=6_000_000)
# ESRI D8 encoding used by HydroSHEDS DIR: value -> (drow, dcol)
D8 = {1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1), 64: (-1, 0), 128: (-1, 1)}


def grid():
    w, s, e, n = (np.floor(BBOX[0] / RES) * RES, np.floor(BBOX[1] / RES) * RES,
                  np.ceil(BBOX[2] / RES) * RES, np.ceil(BBOX[3] / RES) * RES)
    return dict(west=float(w), north=float(n), cols=int(round((e - w) / RES)), rows=int(round((n - s) / RES)))


def trace(dirs, r, c, stop, max_steps=MAX_STEPS):
    """Follow D8 from (r, c) until stop(r, c) is truthy. Returns (status, path)."""
    path = [(r, c)]
    for _ in range(max_steps):
        hit = stop(r, c)
        if hit:
            return hit, path
        v = int(dirs[r, c])
        if v not in D8:
            return "SINK_OR_NODATA", path
        dr, dc = D8[v]
        r, c = r + dr, c + dc
        if not (0 <= r < dirs.shape[0] and 0 <= c < dirs.shape[1]):
            return "LEFT_BBOX", path
        path.append((r, c))
    return "MAX_STEPS", path


def downstream_stations(goid, ndoid, station_goids, max_hops=1000):
    """Stations reached by following NDOID from goid (inclusive), in downstream order."""
    hits, node, hops = [], goid, 0
    while node and hops < max_hops:
        if node in station_goids:
            hits.append(station_goids[node])
        node, hops = ndoid.get(node, 0), hops + 1
    return hits


def preregister():
    g = grid()
    save(PREREG, dict(
        phase="23A-linkage", date=datetime.now(timezone.utc).date().isoformat(), budget=BUDGET,
        data=dict(flow_direction=f"{DIR_ASSET} band b1, native 3 arc-second EPSG:4326 grid (no reprojection: D8 codes "
                                 "are not resampled)", reaches=f"{FFR_ASSET}: GOID, NDOID, UPLAND_SKM, line geometry",
                  bbox_wgs84=BBOX, grid=g, expected_bytes=g["rows"] * g["cols"] + 2_000_000),
        inputs=dict(phase22x_prereg=sha("docs/reports/phase22x-preregistration.json"),
                    phase22z_summary=sha("docs/reports/phase22z-summary.json")),
        method=dict(start="each of the 174 SAR-tested 22X cluster centroids (cell-mean, local only)",
                    route=f"ESRI D8 steps on the DIR grid until a cell centre lies within {SNAP_M:.0f} m of an FFR reach line",
                    snap="nearest reach at the stop cell; AMBIGUOUS if a second reach is within 90 m too (nearest still used, flagged)",
                    downstream="follow NDOID from the snapped reach; record every monitored station reach on the chain",
                    stations=STATIONS),
        failure=dict(unrouted=f"SINK_OR_NODATA, LEFT_BBOX or > {MAX_STEPS} steps -> UNROUTED, reported",
                     station_exposure=f"a station with < {MIN_UPSTREAM} upstream clusters is INSUFFICIENT_EXPOSURE"),
        reporting="per station: upstream clusters, area and 22Y persistence classes; per cluster: path length, snapped reach, "
                  "AMBIGUOUS flag, TEST-block crossings (geometry only); no causal or degradation claim",
        guards="static DEM-derived hydrography only; only non-TEST 22X clusters are routed; TEST blocks crossed are recorded, "
               "nothing from TEST is read; mining attribution UNKNOWN"))
    print(g)


def acquire():
    import ee
    import requests
    from rasterio.io import MemoryFile
    from src.gee_setup import initialize
    plan = json.loads(PREREG.read_bytes())
    g = plan["data"]["grid"]
    OUT.mkdir(parents=True, exist_ok=True)
    lock = acquire_lock(OUT / ".acquire.lock")
    try:
        def gate(planned):
            n, b = ledger_usage(LEDGER)
            if n + 1 > BUDGET["max_requests"] or b + planned > BUDGET["max_bytes"]:
                raise SystemExit(f"Budget stop: {n} requests, {b} bytes")

        def log(e):
            with LEDGER.open("a") as fh:
                fh.write(json.dumps(e) + "\n")

        initialize()
        rect = ee.Geometry.Rectangle(list(BBOX), "EPSG:4326", False)
        if not (OUT / "reaches.json").exists():
            fc = ee.FeatureCollection(FFR_ASSET).filterBounds(rect).map(lambda f: f.select(["GOID", "NDOID", "UPLAND_SKM"]))
            # A FeatureCollection nested in ee.Dictionary serializes metadata only (22O/23A incident): fetch directly.
            gate(3_000_000)
            reaches = fc.getInfo()
            log(dict(request="reaches", response_bytes=len(json.dumps(reaches).encode())))
            gate(10_000)
            proj = ee.Image(DIR_ASSET).projection().getInfo()
            log(dict(request="dir_projection", response_bytes=len(json.dumps(proj).encode())))
            if abs(proj["transform"][0] - RES) > 1e-9 or proj["crs"] != "EPSG:4326":
                raise ValueError(f"DIR is not the expected native 3 arc-second grid: {proj}")
            save(OUT / "reaches.json", dict(reaches=reaches, dir_projection=proj))
        info = json.loads((OUT / "reaches.json").read_bytes())
        if "features" not in info["reaches"]:
            raise ValueError("Reach collection did not expand to features")
        if not (OUT / "dir.npy").exists():
            transform = [RES, 0, g["west"], 0, -RES, g["north"]]
            gate(0)
            url = ee.Image(DIR_ASSET).select(0).toUint8().getDownloadURL(
                dict(format="GEO_TIFF", crs="EPSG:4326", crs_transform=transform, dimensions=[g["cols"], g["rows"]]))
            log(dict(request="dir_url", response_bytes=0))
            gate(g["rows"] * g["cols"] + 100_000)
            with requests.get(url, timeout=(15, 300)) as r:
                log(dict(request="dir_download", response_bytes=len(r.content), status=r.status_code))
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                content = r.content
            with MemoryFile(content) as mem, mem.open() as src:
                if src.shape != (g["rows"], g["cols"]) or abs(src.transform.a - RES) > 1e-12:
                    raise ValueError(f"DIR grid mismatch {src.shape} {src.transform}")
                np.save(OUT / "dir.npy", src.read(1))
        n, b = ledger_usage(LEDGER)
        save(OUT / "acquisition.json", dict(requests=n, response_bytes=b, dir_projection=info["dir_projection"],
                                            reaches=len(info["reaches"]["features"])))
        print("requests", n, "bytes", b, "reaches", len(info["reaches"]["features"]))
    finally:
        lock.unlink(missing_ok=True)


def analyze():
    from pyproj import Transformer
    from shapely.geometry import Point, shape
    from shapely import STRtree, transform as gtransform
    from scripts.phase22n_temporal import guards
    from scripts.phase22z_context import cluster_rows
    from src.phase3.spatial import partition
    plan = json.loads(PREREG.read_bytes())
    g = plan["data"]["grid"]
    dirs = np.load(OUT / "dir.npy")
    feats = json.loads((OUT / "reaches.json").read_bytes())["reaches"]["features"]
    to_utm = Transformer.from_crs(4326, "EPSG:32646", always_xy=True).transform
    lines = [gtransform(shape(f["geometry"]), to_utm, interleaved=False) for f in feats]
    goids = [int(f["properties"]["GOID"]) for f in feats]
    ndoid = {int(f["properties"]["GOID"]): int(f["properties"]["NDOID"]) for f in feats}
    tree = STRtree(lines)
    station_goids = {v: k for k, v in STATIONS.items()}
    missing = [k for k, v in STATIONS.items() if v not in ndoid]
    _, protected = guards()
    test_geoms = [geom for _, geom in protected]

    def cell_xy(r, c):
        return to_utm(g["west"] + (c + .5) * RES, g["north"] - (r + .5) * RES)

    def stop(r, c):
        p = Point(*cell_xy(r, c))
        near = [i for i in tree.query(p.buffer(SNAP_M)) if lines[i].distance(p) <= SNAP_M]
        if not near:
            return None
        near.sort(key=lambda i: lines[i].distance(p))
        return ("SNAPPED", near)

    rows, _ = cluster_rows()
    out = []
    for row in rows:
        lon, lat = row["_centroid_wgs84"]
        r, c = int((g["north"] - lat) / RES), int((lon - g["west"]) / RES)
        status, path = trace(dirs, r, c, stop)
        rec = dict(id=row["id"], cls=row["cls"], ha=row["ha"], steps=len(path) - 1)
        if isinstance(status, tuple):
            near = status[1]
            reach = goids[near[0]]
            pts = [Point(*cell_xy(*rc)) for rc in path]
            crossed = sorted({k for k, geom in protected if any(geom.contains(p) for p in pts[::3])})
            rec.update(status="ROUTED", reach=reach, ambiguous=len({goids[i] for i in near}) > 1,
                       path_km=round(rec["steps"] * 0.09, 2), test_blocks_crossed=crossed,
                       stations=downstream_stations(reach, ndoid, station_goids))
        else:
            rec.update(status="UNROUTED", reason=status)
        out.append(rec)
    per_station = {}
    for st in STATIONS:
        up = [o for o in out if st in o.get("stations", [])]
        per_station[st] = dict(upstream_clusters=len(up), upstream_ha=round(sum(o["ha"] for o in up), 2),
                               persistent=sum(o["cls"] == "PERSISTENT" for o in up),
                               classes={c: sum(o["cls"] == c for o in up) for c in ("PERSISTENT", "PARTIAL", "RECOVERING")},
                               status="LINKED" if len(up) >= MIN_UPSTREAM else "INSUFFICIENT_EXPOSURE")
    routed = [o for o in out if o["status"] == "ROUTED"]
    res = dict(phase="23A-linkage", preregistration_sha256=sha(PREREG), stations_missing_in_reaches=missing,
               clusters=len(out), routed=len(routed), unrouted=len(out) - len(routed),
               unrouted_reasons={k: sum(o.get("reason") == k for o in out) for k in ("SINK_OR_NODATA", "LEFT_BBOX", "MAX_STEPS")},
               ambiguous_snaps=sum(o.get("ambiguous", False) for o in routed),
               reaching_any_station=sum(bool(o.get("stations")) for o in routed),
               not_reaching_monitored_station=sum(not o.get("stations") for o in routed),
               path_km_median=float(np.median([o["path_km"] for o in routed])) if routed else None,
               per_station=per_station,
               persistent_reaching_station=sum(bool(o.get("stations")) and o["cls"] == "PERSISTENT" for o in routed),
               paths_crossing_test_blocks=sum(bool(o.get("test_blocks_crossed")) for o in routed),
               interpretation="DEM-routed exposure geometry only; no effect, degradation or causation; clusters UNKNOWN")
    json.dump(out, open(OUT / "routes.json", "w"), indent=1)  # per-cluster detail stays local
    res["cloud_usage"] = json.loads((OUT / "acquisition.json").read_bytes())
    res["cloud_usage"].pop("dir_projection", None)
    save(SUMMARY, res)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    gg = ap.add_mutually_exclusive_group(required=True)
    for f in ("--preregister", "--acquire", "--analyze"):
        gg.add_argument(f, action="store_true")
    a = ap.parse_args()
    (preregister if a.preregister else acquire if a.acquire else analyze)()
