"""Phase 22O guarded relative-NDTI river feasibility pilot (Lukha / Myntdu).

Stages (run from the checkout root):
  --preregister  offline guards + JRC pre-screen -> docs/reports/phase22o-preregistration.json
  --acquire      bounded Earth Engine fetch into a local cache (budget-capped)
  --analyze      offline screen, date-level NDTI and seasonal summaries

NDTI = (B4 - B3) / (B4 + B3) is a relative spectral proxy only. It is not NTU,
suspended sediment, acidity or contamination, and no causal claim is made.
"""
import argparse
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion

PHASE4A = Path("outputs/phase4a_river_feasibility")
PREREG = Path("docs/reports/phase22o-preregistration.json")
SUMMARY = Path("docs/reports/phase22o-summary.json")
OUT = Path("outputs/phase22o_river")
CRS = "EPSG:32646"
SIZE, STEP, NODATA = 72, 10, -9999
SEASONS = {"before": ("2023-11-01", "2024-04-01"), "after": ("2024-11-01", "2025-04-01")}
STATIONS = {  # CPCB register coordinates, reused verbatim from Phase 4A
    "Lukha-Khaddum-4315": (92.422355, 25.224359),
    "Lukha-Sunapur-3376": (92.361445, 25.108633),
    "Myntdu-Mihmyntdu-4316": (92.204576, 25.434337),
    "Myntdu-Leshka-3379": (92.19829, 25.268735),
}
RULES = dict(
    jrc_occurrence_min=50, mndwi_gt=0.0, erosion="3x3 8-neighbour, one 10 m pixel, window border fails",
    min_interior_pixels=3, min_dates_per_season=5, bootstrap_resamples=10000, bootstrap_seed=42,
    corridor="nearest intersecting HydroSHEDS FFR line buffered 80 m, within 260 m of station, clipped to window",
    duplicate_dates="keep granule with most interior pixels; tie -> lowest scene id",
    masks="Phase 2 prepare(): cloud probability <40, SCL 4/5/6, B3/B4/B8/B8A/B9 edge masks; plus B11 present",
)
BUDGET = dict(max_requests=40, max_bytes=50_000_000)
# flag bits of the downloaded per-scene flag band
VALID, MNDWI_POS, SCL_WATER = 1, 2, 4


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- pure logic
def interior_mask(flags, jrc, corridor):
    """Final 10 m interior water mask for one granule."""
    water = ((flags & VALID) > 0) & ((flags & MNDWI_POS) > 0) & (jrc >= RULES["jrc_occurrence_min"]) & (jrc <= 100)
    eroded = binary_erosion(water, structure=np.ones((3, 3), bool), border_value=0)
    return eroded & corridor


def date_ndti(b3, b4, mask):
    """Median per-pixel NDTI over masked pixels with positive denominator, or None."""
    g, r = b3.astype(float), b4.astype(float)
    ok = mask & (g >= 0) & (r >= 0) & (g + r > 0)
    if ok.sum() < RULES["min_interior_pixels"]:
        return None, int(ok.sum())
    return float(np.median((r[ok] - g[ok]) / (r[ok] + g[ok]))), int(ok.sum())


def select_dates(granules):
    """granules: dicts with id, date, pixels, ndti. One record per UTC date."""
    best = {}
    for g in sorted(granules, key=lambda g: g["id"]):
        if g["ndti"] is None:
            continue
        cur = best.get(g["date"])
        if cur is None or g["pixels"] > cur["pixels"]:
            best[g["date"]] = g
    return [best[d] for d in sorted(best)]


def bootstrap_median_ci(values, n=RULES["bootstrap_resamples"], seed=RULES["bootstrap_seed"]):
    v = np.asarray(values, float)
    idx = np.random.default_rng(seed).integers(0, len(v), (n, len(v)))
    meds = np.median(v[idx], axis=1)
    return [float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))]


def season_summary(dates):
    values = [d["ndti"] for d in dates]
    if not values:
        return dict(status="UNRESOLVED", usable_dates=0)
    out = dict(usable_dates=len(values), median_ndti=float(np.median(values)))
    if len(values) < RULES["min_dates_per_season"]:
        out["status"] = "INSUFFICIENT_DATES"
    else:
        out.update(status="SUPPORTED", median_ci95=bootstrap_median_ci(values))
    return out


def difference_ci(before, after, n=RULES["bootstrap_resamples"], seed=RULES["bootstrap_seed"]):
    b, a = np.asarray(before, float), np.asarray(after, float)
    rng = np.random.default_rng(seed)
    diffs = (np.median(a[rng.integers(0, len(a), (n, len(a)))], axis=1)
             - np.median(b[rng.integers(0, len(b), (n, len(b)))], axis=1))
    return float(np.median(a) - np.median(b)), [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]


def antecedent(daily, day, k):
    """Sum of the k complete UTC days before `day` (acquisition day excluded); None if any missing."""
    d0 = date.fromisoformat(day)
    vals = [daily.get((d0 - timedelta(days=i)).isoformat()) for i in range(1, k + 1)]
    return None if any(v is None for v in vals) else float(sum(vals))


def downstream_of(start, target, ndoid, max_hops=500):
    """Follow HydroSHEDS NDOID links from start; return hop count to target or None."""
    node, hops = start, 0
    while node in ndoid and hops < max_hops:
        if node == target:
            return hops
        node, hops = ndoid[node], hops + 1
    return hops if node == target else None


# ---------------------------------------------------------------- stage 1
def window(station):
    return json.loads((PHASE4A / "receipt.json").read_bytes())["stations"][station]["extent"]


def preregister():
    import rasterio
    from shapely.geometry import box
    from scripts.phase22n_temporal import guards
    from src.phase3.spatial import partition
    area, protected = guards()
    rows = {}
    for st, xy in STATIONS.items():
        x0, y0, x1, y1 = ext = window(st)
        w = box(*ext)
        hits = [k for k, g in protected if w.intersects(g)]
        blocks = sorted({f"{math.floor(x / 5000)}:{math.floor(y / 5000)}" for x in (x0, x1 - 1e-6) for y in (y0, y1 - 1e-6)})
        jrc_path = PHASE4A / st / "historical_water.tif"
        with rasterio.open(jrc_path) as src:
            if (src.transform.c, src.transform.f, src.shape) != (x0, y1, (SIZE, SIZE)):
                raise ValueError(f"{st}: cached JRC grid does not match window")
            jrc = src.read(1)
        yy, xx = np.mgrid[0:SIZE, 0:SIZE]
        circle = ((x0 + (xx + .5) * STEP - (x0 + x1) / 2) ** 2 + (y1 - (yy + .5) * STEP - (y0 + y1) / 2) ** 2) <= 260 ** 2
        upper = int((binary_erosion((jrc >= 50) & (jrc <= 100), np.ones((3, 3), bool), border_value=0) & circle).sum())
        eligible = area.covers(w) and not hits
        rows[st] = dict(cpcb_coordinates=list(xy), window_epsg32646=ext, district_contained=area.covers(w),
                        test_buffer_intersections=hits, distance_to_nearest_test_buffer_m=round(min(w.distance(g) for _, g in protected), 1),
                        blocks={b: partition(b) for b in blocks}, jrc_cache_sha256=sha(jrc_path),
                        eroded_jrc50_pixels_within_260m_upper_bound=upper, geometry_eligible=eligible,
                        acquire=eligible and upper >= RULES["min_interior_pixels"],
                        pre_acquisition_status=None if upper >= RULES["min_interior_pixels"] else "UNRESOLVED")
    save(PREREG, dict(
        phase="22O", date=datetime.now(timezone.utc).date().isoformat(), seasons=SEASONS, rules=RULES, budget=BUDGET,
        ndti="(B4-B3)/(B4+B3) on L2A SR; relative spectral proxy, not NTU/sediment/contamination",
        flow_topology_rule="upstream/downstream only if the HydroSHEDS FFR NDOID chain from one station reach reaches the other",
        regulated_water="Leshka is potentially impounded (Myntdu-Leshka Stage I); never pooled with flowing reaches",
        comparison_reach="none independently source-backed beyond the four CPCB stations; none assumed mining-free",
        station_source="CPCB WQMN register coordinates via Phase 4A receipt sha256 " + sha(PHASE4A / "receipt.json"),
        stations=rows))
    print(json.dumps({k: (v["geometry_eligible"], v["eroded_jrc50_pixels_within_260m_upper_bound"], v["acquire"]) for k, v in rows.items()}))


# ---------------------------------------------------------------- stage 2
class Budget:
    def __init__(self):
        self.requests, self.bytes, self.log = 0, 0, []

    def charge(self, what, nbytes, planned_bytes=0):
        if self.requests + 1 > BUDGET["max_requests"] or self.bytes + max(nbytes, planned_bytes) > BUDGET["max_bytes"]:
            raise RuntimeError(f"Budget would be exceeded by {what}")
        self.requests += 1
        self.bytes += nbytes
        self.log.append(dict(request=what, response_bytes=nbytes))

    def info(self, what, obj):
        if self.requests + 1 > BUDGET["max_requests"]:
            raise RuntimeError(f"Request cap reached before {what}")
        result = obj.getInfo()
        self.charge(what, len(json.dumps(result).encode()))
        return result


def acquire():
    import ee
    import rasterio
    import requests
    from rasterio.io import MemoryFile
    from config.phase2_settings import Phase2Config
    from config.settings import BEFORE, AFTER
    from src.gee_setup import initialize
    from src import optical_preprocessing as optical
    if OUT.exists():
        raise ValueError(f"{OUT} exists; refusing to overwrite")
    plan = json.loads(PREREG.read_bytes())
    cfg, budget = Phase2Config(), Budget()
    initialize()
    ee.data.setDeadline(180000)
    cache = OUT / "cache"
    cache.mkdir(parents=True)
    targets = [s for s, r in plan["stations"].items() if r["acquire"]]
    # topology + reach lines
    lons, lats = zip(*STATIONS.values())
    bbox = ee.Geometry.Rectangle([min(lons) - .05, min(lats) - .05, max(lons) + .05, max(lats) + .05])
    ffr = ee.FeatureCollection("WWF/HydroSHEDS/v1/FreeFlowingRivers").filterBounds(bbox)
    topo = budget.info("ffr_topology", ee.Dictionary(dict(goid=ffr.aggregate_array("GOID"), ndoid=ffr.aggregate_array("NDOID"))))
    regions = {s: ee.Geometry.Rectangle(plan["stations"][s]["window_epsg32646"], CRS, False) for s in targets}
    lines = budget.info("ffr_window_lines", ee.Dictionary({s: ee.FeatureCollection("WWF/HydroSHEDS/v1/FreeFlowingRivers")
                        .filterBounds(g).map(lambda f: f.select(["GOID", "NDOID"])) for s, g in regions.items()}))
    save(cache / "hydrosheds.json", dict(topology=topo, lines=lines))
    pts = ee.Geometry.MultiPoint([list(STATIONS[s]) for s in targets])
    rain = budget.info("chirps_daily", ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate("2023-10-20", "2025-04-01").getRegion(pts, 5566))
    save(cache / "chirps.json", dict(points={s: STATIONS[s] for s in targets}, rows=rain))

    def bands(img):
        valid = ee.Image(optical.prepare(img, cfg)).select("NDTI").mask().And(img.select("B11").mask()).gt(0)
        b3, b11 = img.select("B3").toFloat(), img.select("B11").toFloat()
        den = b3.add(b11)
        mndwi_pos = b3.subtract(b11).divide(den).gt(RULES["mndwi_gt"]).And(den.gt(0)).unmask(0)
        flags = (valid.unmask(0).multiply(VALID).add(mndwi_pos.multiply(MNDWI_POS))
                 .add(img.select("SCL").eq(6).unmask(0).multiply(SCL_WATER))).toInt16().rename("flags")
        return img.select(["B3", "B4"]).toInt16().unmask(NODATA, sameFootprint=False).addBands(flags)

    receipts = {}
    for st in targets:
        x0, y0, x1, y1 = plan["stations"][st]["window_epsg32646"]
        affine = rasterio.Affine(STEP, 0, x0, 0, -STEP, y1)
        for season, (start, end) in SEASONS.items():
            _, joined = optical.collections(regions[st], {"before": BEFORE, "after": AFTER}[season], cfg)
            joined = joined.sort("system:index")
            meta = budget.info(f"{st}/{season}/ids", ee.Dictionary(dict(ids=joined.aggregate_array("system:index"),
                                                                         times=joined.aggregate_array("system:time_start"))))
            if not meta["ids"] or len(meta["ids"]) > 160:
                raise ValueError(f"Unexpected scene count {st}/{season}: {len(meta['ids'])}")
            planned = len(meta["ids"]) * 3 * SIZE * SIZE * 2 + 100_000
            url = (joined.map(lambda i: bands(i).clip(regions[st])).toBands().getDownloadURL(
                dict(format="GEO_TIFF", crs=CRS, crs_transform=list(affine)[:6], dimensions=[SIZE, SIZE])))
            budget.charge(f"{st}/{season}/url", 0, planned)  # URL creation is itself a request
            with requests.get(url, timeout=(15, 300)) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code} for {st}/{season}")
                content = resp.content
            budget.charge(f"{st}/{season}/download", len(content))
            with MemoryFile(content) as mem, mem.open() as src:
                if (src.transform, src.shape, src.count) != (affine, (SIZE, SIZE), 3 * len(meta["ids"])):
                    raise ValueError(f"Unexpected raster for {st}/{season}")
                np.save(cache / f"{st}_{season}.npy", src.read())
            receipts[f"{st}/{season}"] = meta
            print(st, season, len(meta["ids"]), "scenes", len(content), "bytes", flush=True)
    save(cache / "scenes.json", receipts)
    save(OUT / "budget.json", dict(requests=budget.requests, response_bytes=budget.bytes, log=budget.log,
                                   note="getInfo bytes are serialized JSON sizes; download bytes are exact"))
    print("requests", budget.requests, "bytes", budget.bytes)


# ---------------------------------------------------------------- stage 3
def analyze():
    import rasterio
    from rasterio.features import geometry_mask
    from pyproj import Transformer
    from shapely.geometry import Point, box, mapping, shape
    from shapely import transform as gtransform
    plan = json.loads(PREREG.read_bytes())
    cache = OUT / "cache"
    hydro = json.loads((cache / "hydrosheds.json").read_bytes())
    scenes = json.loads((cache / "scenes.json").read_bytes())
    chirps = json.loads((cache / "chirps.json").read_bytes())
    project = Transformer.from_crs(4326, CRS, always_xy=True).transform
    header, rows = chirps["rows"][0], chirps["rows"][1:]
    ilon, ilat, itime, ival = (header.index(k) for k in ("longitude", "latitude", "time", "precipitation"))
    phase4a = json.loads((PHASE4A / "receipt.json").read_bytes())["stations"]
    result, products = {}, []
    for st, pre in plan["stations"].items():
        if not pre["acquire"]:
            result[st] = dict(status=pre["pre_acquisition_status"] or "NOT_ELIGIBLE",
                              reason="eroded JRC>=50 upper bound below 3 interior pixels; no imagery requested")
            continue
        x0, y0, x1, y1 = ext = pre["window_epsg32646"]
        affine = rasterio.Affine(STEP, 0, x0, 0, -STEP, y1)
        center = Point(*project(*STATIONS[st]))
        feats = hydro["lines"][st]["features"]
        lines = [(gtransform(shape(f["geometry"]), project, interleaved=False).intersection(box(*ext)), f) for f in feats]
        lines = [(g, f) for g, f in lines if g.length > 0]
        reach, feat = min(lines, key=lambda gf: gf[0].distance(center))
        corridor = geometry_mask([mapping(reach.buffer(80).intersection(center.buffer(260)).intersection(box(*ext)))],
                                 out_shape=(SIZE, SIZE), transform=affine, invert=True)
        with rasterio.open(PHASE4A / st / "historical_water.tif") as src:
            jrc = src.read(1)
        # nearest CHIRPS series to station
        lon, lat = STATIONS[st]
        keyed = {}
        for r in rows:
            keyed.setdefault((r[ilon], r[ilat]), {})[datetime.fromtimestamp(r[itime] / 1000, timezone.utc).date().isoformat()] = r[ival]
        daily = keyed[min(keyed, key=lambda k: (k[0] - lon) ** 2 + (k[1] - lat) ** 2)]
        out = dict(reach_goid=feat["properties"]["GOID"], reach_ndoid=feat["properties"]["NDOID"],
                   corridor_pixels=int(corridor.sum()), seasons={})
        if feat["properties"]["GOID"] != phase4a[st]["reach_properties"]["GOID"]:
            raise ValueError(f"{st}: reach differs from Phase 4A")
        values = {}
        for season in SEASONS:
            arr = np.load(cache / f"{st}_{season}.npy")
            meta = scenes[f"{st}/{season}"]
            granules = []
            for i, (sid, t) in enumerate(zip(meta["ids"], meta["times"], strict=True)):
                b3, b4, flags = arr[3 * i:3 * i + 3]
                mask = interior_mask(flags, jrc, corridor)
                ndti, n = date_ndti(b3, b4, mask)
                granules.append(dict(id=sid, date=datetime.fromtimestamp(t / 1000, timezone.utc).date().isoformat(),
                                     pixels=n, ndti=ndti, valid_corridor=int(((flags & VALID) > 0)[corridor].sum()),
                                     water_corridor=int((((flags & VALID) > 0) & ((flags & MNDWI_POS) > 0) & (jrc >= 50))[corridor].sum())))
            dates = select_dates(granules)
            for d in dates:
                d.update(rain_1d_mm=antecedent(daily, d["date"], 1), rain_3d_mm=antecedent(daily, d["date"], 3),
                         rain_7d_mm=antecedent(daily, d["date"], 7))
            s, e = SEASONS[season]
            season_days = [(date.fromisoformat(s) + timedelta(days=i)).isoformat()
                           for i in range((date.fromisoformat(e) - date.fromisoformat(s)).days)]
            summ = season_summary(dates)
            summ.update(granules=len(granules), granule_dates=len({g["date"] for g in granules}),
                        chirps_season_total_mm=float(sum(daily[d] for d in season_days)) if all(d in daily for d in season_days) else None,
                        chirps_days=sum(d in daily for d in season_days), dates=dates)
            out["seasons"][season] = summ
            values[season] = [d["ndti"] for d in dates]
            with open(OUT / f"{st}_{season}_granules.csv", "w", encoding="utf-8") as fh:
                fh.write("id,date,interior_pixels,ndti,valid_corridor,water_corridor\n")
                for g in granules:
                    fh.write(f"{g['id']},{g['date']},{g['pixels']},{'' if g['ndti'] is None else round(g['ndti'], 6)},{g['valid_corridor']},{g['water_corridor']}\n")
        if all(len(values[s]) >= RULES["min_dates_per_season"] for s in SEASONS):
            diff, ci = difference_ci(values["before"], values["after"])
            out.update(status="SUPPORTED", after_minus_before_median=diff, difference_ci95=ci)
        elif any(values[s] for s in SEASONS):
            out["status"] = "INSUFFICIENT_DATES"
        else:
            out["status"] = "UNRESOLVED"
        result[st] = out
    ndoid = {int(g): int(n) for g, n in zip(hydro["topology"]["goid"], hydro["topology"]["ndoid"])}
    goid = {st: r.get("reach_goid") or phase4a[st]["reach_properties"]["GOID"] for st, r in result.items()}
    topology = {}
    for up, down in (("Lukha-Khaddum-4315", "Lukha-Sunapur-3376"), ("Myntdu-Mihmyntdu-4316", "Myntdu-Leshka-3379")):
        hops = downstream_of(goid[up], goid[down], ndoid)
        rev = downstream_of(goid[down], goid[up], ndoid)
        topology[f"{up}->{down}"] = dict(downstream_hops=hops, reverse_hops=rev,
                                         supported=hops is not None and rev is None)
    budget = json.loads((OUT / "budget.json").read_bytes())
    save(SUMMARY, dict(phase="22O", preregistration_sha256=sha(PREREG), rules=RULES, stations=result, flow_topology=topology,
                       cloud_usage=dict(requests=budget["requests"], response_bytes=budget["response_bytes"]),
                       interpretation="relative spectral proxy; no NTU, contamination, degradation or causal claim"))
    for st, r in result.items():
        print(st, r["status"], {s: (v["usable_dates"], v["status"], round(v.get("median_ndti", float("nan")), 4))
                                 for s, v in r.get("seasons", {}).items()})
    print(json.dumps(topology))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--preregister", action="store_true")
    g.add_argument("--acquire", action="store_true")
    g.add_argument("--analyze", action="store_true")
    a = p.parse_args()
    preregister() if a.preregister else acquire() if a.acquire else analyze()
