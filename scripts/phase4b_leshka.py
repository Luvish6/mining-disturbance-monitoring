"""Matched-month, fixed-water-footprint Sentinel-2 feasibility pilot at Leshka."""
import argparse
from collections import Counter
import csv
from datetime import date, timedelta
from itertools import combinations
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import ee
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, label
from shapely import transform
from shapely.geometry import Point, box, mapping, shape
from pyproj import Transformer

sys.path.insert(0, str(Path.cwd() / "scripts"))
from phase4a_river import (
    BANDS, CRS, NODATA, RAIN, RIVERS, SIZE, STATIONS, STEP, WATER,
    AFTER, BEFORE, Phase2Config, fetch, geometry_mask, initialize,
    optical, save_raster, scene_bands, screen,
)

SITE = "Myntdu-Leshka-3379"
SEASONS = (("before", BEFORE), ("after", AFTER))


def match_dates(before, after, max_days=15):
    """Maximize same-month pairs, then minimize day-of-month gaps, without reuse."""
    for count in range(min(len(before), len(after)), 0, -1):
        candidates = (
            list(zip(a, b)) for a in combinations(before, count)
            for b in combinations(after, count)
        )
        eligible = [pairs for pairs in candidates if all(
            abs(a.day-b.day) <= max_days for a, b in pairs)]
        if eligible:
            return min(eligible, key=lambda pairs: (sum(abs(a.day-b.day) for a,b in pairs), pairs))
    return []


def largest_component(mask):
    groups, count = label(mask)
    if count == 0:
        return mask
    return groups == (1 + np.argmax(np.bincount(groups.ravel())[1:]))


def native_cells(mask, x0, y0):
    """Indices of whole 20 m source cells within the common 10 m mask."""
    aligned = mask[y0:y0+2*((SIZE-y0)//2), x0:x0+2*((SIZE-x0)//2)]
    return aligned.reshape(aligned.shape[0]//2, 2, aligned.shape[1]//2, 2).all(axis=(1,3))


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader()
        writer.writerows(rows)


def rainfall(xy):
    point = ee.Geometry.Point(xy)
    daily = ee.ImageCollection(RAIN).filterDate("2023-10-25", AFTER.end)
    native = ee.Image(daily.first()).projection()
    grid = native.getInfo()
    header, *rows = daily.getRegion(point, crs=grid["crs"], crsTransform=grid["transform"]).getInfo()
    values = {}
    for row in rows:
        entry = dict(zip(header,row))
        day = date(1970,1,1) + timedelta(days=entry["time"]//86400000)
        values[day] = entry["precipitation"]
    return values


def preceding(values, day, length):
    days = [values.get(day - timedelta(days=i)) for i in range(1,length+1)]
    return None if any(v is None for v in days) else float(sum(days))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output directory")
    prior = json.loads(Path("outputs/phase4a_river_feasibility/receipt.json").read_text())
    anchor = prior["stations"][SITE]
    xy = STATIONS[SITE]
    if list(xy) != anchor["coordinates"]:
        raise ValueError("Station differs from Phase 4A")
    xmin,ymin,xmax,ymax = anchor["extent"]
    affine = rasterio.Affine(STEP,0,xmin,0,-STEP,ymax)
    initialize()
    ee.data.setDeadline(180000)
    region = ee.Geometry.Rectangle(anchor["extent"], CRS, False)
    project = Transformer.from_crs(4326,CRS,always_xy=True).transform
    station = Point(*project(*xy))
    goid = anchor["reach_properties"]["GOID"]
    source = ee.FeatureCollection(RIVERS).filterBounds(region).filter(ee.Filter.eq("GOID",goid))
    feature, = source.getInfo()["features"]
    reach = transform(shape(feature["geometry"]),project,interleaved=False).intersection(box(*anchor["extent"]))
    corridor = geometry_mask([mapping(reach.buffer(80).intersection(station.buffer(260)))],
                             out_shape=(SIZE,SIZE),transform=affine,invert=True)
    if int(corridor.sum()) != anchor["corridor_pixels"] or round(reach.distance(station),2) != anchor["station_to_reach_m"]:
        raise ValueError("Phase 4A geometry did not reproduce")
    historical, = fetch(ee.Image(WATER).select("occurrence").clip(region),affine)
    rain = rainfall(xy)
    records, data_by_id, native_by_id = [], {}, {}
    for name, season in SEASONS:
        phase4a = anchor["seasons"][name]["scenes"]
        ids = [r["id"] for r in phase4a if r["core_10m"] > 0]
        _, joined = optical.collections(region,season,Phase2Config())
        chosen = joined.filter(ee.Filter.inList("system:index",ids)).sort("system:index")
        actual = chosen.aggregate_array("system:index").getInfo()
        if actual != sorted(ids):
            raise ValueError("Missing Phase 4A candidate scenes")
        cfg = Phase2Config()
        def stack(img):
            return scene_bands(img,cfg).addBands(img.select("B11")).clip(region)
        bands = fetch(chosen.map(stack).toBands(),affine)
        if len(bands) != len(ids)*(len(BANDS)+1):
            raise ValueError("Unexpected stacked band count")
        for index, scene_id in enumerate(actual):
            stride = len(BANDS)+1
            data, b11 = bands[index*stride:(index+1)*stride-1], bands[(index+1)*stride-1]
            scene = ee.Image(chosen.filter(ee.Filter.eq("system:index",scene_id)).first())
            projections = ee.Dictionary({b: scene.select(b).projection() for b in ("B3","B4","SCL","B11")}).getInfo()
            data_by_id[scene_id] = data
            native_by_id[scene_id] = (b11,projections)
        for old in phase4a:
            record = dict(old, season=name, status="no interior support in Phase 4A")
            if old["id"] in data_by_id:
                record["status"] = "unmatched candidate date"
            records.append(record)

    candidates = {}
    for record in records:
        if record["id"] not in data_by_id:
            continue
        key = (record["season"],date.fromisoformat(record["acquired_utc"][:10]))
        current = candidates.get(key)
        if current is None or (record["core_10m"],record["id"]) > (current["core_10m"],current["id"]):
            candidates[key] = record
    for record in records:
        key = (record["season"],date.fromisoformat(record["acquired_utc"][:10]))
        if record["id"] in data_by_id and candidates[key] is not record:
            record["status"] = "duplicate UTC date; lower interior support or tie"
    days = {s: sorted(d for label,d in candidates if label == s) for s,_ in SEASONS}
    pairs = []
    for month in (11,12,1,2,3):
        subsets = [[d for d in days[s] if d.month==month] for s,_ in SEASONS]
        pairs.extend(match_dates(*subsets))
    matched = [candidates[key] for pair in pairs for key in zip(("before","after"),pair)]
    masks, strict_masks, wider_masks = [], [], []
    for record in matched:
        scene_id = record["id"]
        data = data_by_id[scene_id]
        metrics,water,core = screen(data,corridor)
        if metrics["core_10m"] != record["core_10m"]:
            raise ValueError("Phase 4A water screen did not reproduce")
        green,red,nir = data[1:4].astype(float)
        ndwi = np.divide(green-nir,green+nir,out=np.zeros_like(green),where=green+nir>0)
        distance = distance_transform_edt(np.pad(water,1))[1:-1,1:-1]*STEP
        strict_distance = distance_transform_edt(np.pad(water & (ndwi>.1),1))[1:-1,1:-1]*STEP
        base = (green+red>0)
        masks.append(core & base)
        strict_masks.append(corridor & (strict_distance>=20) & base)
        wider_masks.append(corridor & (distance>=30) & base)
    empty = np.zeros(corridor.shape,dtype=bool)
    common = largest_component(np.logical_and.reduce(masks)) if masks else empty
    strict = common & np.logical_and.reduce(strict_masks) if masks else empty
    wider = common & np.logical_and.reduce(wider_masks) if masks else empty
    persistent = common & (historical>=50)
    support = int(common.sum())
    leave_one_pair_out = []
    for index in range(len(pairs)):
        reduced = masks[:2*index] + masks[2*index+2:]
        leave_one_pair_out.append(int(largest_component(np.logical_and.reduce(reduced)).sum())
                                  if reduced else 0)
    reportable = support>=25 and len({a.month for a,_ in pairs})>=2

    native_support = {}
    for record in matched:
        scene_id = record["id"]
        b11,projections = native_by_id[scene_id]
        transforms = {b: rasterio.Affine(*p["transform"]) for b,p in projections.items()}
        if any(projections[b]["crs"]!=CRS for b in projections):
            raise ValueError("Scene projection differs from pilot grid")
        for b,step in (("B3",10),("B4",10),("SCL",20),("B11",20)):
            a = transforms[b]
            if (a.a,a.b,a.d,a.e) != (step,0,0,-step) or (a.c-xmin)%10 or (a.f-ymax)%10:
                raise ValueError(f"Noncongruent source projection: {scene_id}/{b}")
        for b in ("SCL","B11"):
            a = transforms[b]
            x0,y0 = int((a.c-xmin)%20/10),int((ymax-a.f)%20/10)
            complete = native_cells(common,x0,y0)
            arr = data_by_id[scene_id][4] if b=="SCL" else b11
            patch = arr[y0:y0+2*complete.shape[0],x0:x0+2*complete.shape[1]]
            cells = patch.reshape(complete.shape[0],2,complete.shape[1],2)
            if not np.all(cells == cells[:,0,:,0][:,None,:,None]):
                raise ValueError(f"Expected nearest-neighbour native cell replication: {b}")
            native_support.setdefault(scene_id,{})[b] = int((complete & (cells[:,0,:,0]!=NODATA)).sum())
        native_support[scene_id]["projections"] = projections

    for record in records:
        day = date.fromisoformat(record["acquired_utc"][:10])
        record.update({f"rain_{n}d_mm":preceding(rain,day,n) for n in (1,3,7)})
        if record not in matched:
            continue
        record["status"] = "matched, fixed-footprint screen passed" if reportable else "matched, insufficient common support"
        record["fixed_pixels"] = support
        if support:
            data = data_by_id[record["id"]]
            for key,mask in (("common",common),("strict",strict),("wider",wider),("historical",persistent)):
                if mask.any():
                    red,green = data[2][mask].astype(float), data[1][mask].astype(float)
                    record.update({f"{key}_red":float(np.median(red)/10000),
                                   f"{key}_green":float(np.median(green)/10000),
                                   f"{key}_ratio":float(np.median((red-green)/(red+green)))})
    differences = []
    if reportable:
        for index,(a,b) in enumerate(zip(matched[::2],matched[1::2]),1):
            row = dict(pair=index,before=a["acquired_utc"],after=b["acquired_utc"])
            for key in ("common","strict","wider","historical"):
                for band in ("red","green","ratio"):
                    field = f"{key}_{band}"
                    if field in a and field in b:
                        row[field+"_difference"] = b[field]-a[field]
            for n in (1,3,7):
                key = f"rain_{n}d_mm"
                row[key+"_difference"] = None if None in (a[key],b[key]) else b[key]-a[key]
            differences.append(row)

    with TemporaryDirectory(dir=args.output.parent) as temp:
        out = Path(temp)/"pilot"
        out.mkdir()
        write_csv(out/"observations.csv",records)
        if differences:
            write_csv(out/"matched_differences.csv",differences)
            fig,axes = plt.subplots(3,1,figsize=(9,7),layout="constrained")
            for ax,key,title in zip(axes,("common_red","common_green","common_ratio"),
                                    ("B4 red reflectance","B3 green reflectance","Normalized red–green difference")):
                for s,_ in SEASONS:
                    rows = [r for r in matched if r["season"]==s]
                    ax.scatter([date.fromisoformat(r["acquired_utc"][:10]) for r in rows],
                               [r[key] for r in rows],label=s)
                ax.set_ylabel(title)
                ax.legend()
            fig.suptitle("Myntdu–Leshka | fixed interior-water footprint | descriptive only")
            fig.savefig(out/"dated_spectra.png",dpi=140)
            plt.close(fig)
        save_raster(out/"fixed_water_support.tif",np.stack([common,strict,wider,persistent]).astype("int16"),
                    affine,["common","strict_ndwi","wider_clearance","historical_occurrence"])
        first = data_by_id[matched[0]["id"]] if matched else None
        if first is not None:
            fig,ax = plt.subplots(figsize=(6,6),layout="constrained")
            rgb = np.stack(first[[2,1,0]],axis=-1)
            ax.imshow(np.clip(rgb.astype(float)/3000,0,1),extent=(xmin,xmax,ymin,ymax))
            if common.any():
                ax.contour(common.astype(float),levels=[.5],colors=["yellow"],
                           extent=(xmin,xmax,ymin,ymax),origin="upper")
            ax.set_title("Leshka station window | yellow: fixed common interior")
            ax.ticklabel_format(useOffset=False,style="plain")
            fig.savefig(out/"fixed_water_support.png",dpi=140)
            plt.close(fig)
        receipt = dict(station=SITE,coordinates=xy,reach_goid=goid,extent=anchor["extent"],
            corridor_pixels=int(corridor.sum()), source_collections=[RIVERS,WATER,RAIN,
            "COPERNICUS/S2_SR_HARMONIZED","COPERNICUS/S2_CLOUD_PROBABILITY"],
            rainfall_geometry="native CHIRPS station cell; preceding UTC dates exclude acquisition day",
            rainfall_daily={d.isoformat():v for d,v in rain.items()},
            matched_pairs=[[a.isoformat(),b.isoformat()] for a,b in pairs],
            available_interior_dates={k:dict(Counter(d.month for d in v)) for k,v in days.items()},
            leave_one_pair_out_pixels=leave_one_pair_out, common_pixels=support,strict_pixels=int(strict.sum()),wider_pixels=int(wider.sum()),
            historical_pixels=int(persistent.sum()),native_support=native_support,reportable=reportable,
            analysis_rules=dict(maximum_day_of_month_gap=15,minimum_common_pixels=25,minimum_matched_months=2))
        (out/"receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False),encoding="utf-8")
        out.rename(args.output)
    print(json.dumps({k:receipt[k] for k in ("matched_pairs","common_pixels","strict_pixels",
         "wider_pixels","historical_pixels","reportable")}),flush=True)


if __name__=="__main__":
    main()
