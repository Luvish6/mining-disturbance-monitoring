"""Bounded Phase 4A station-neighbourhood screen. No hydrological attribution."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import ee
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.features import geometry_mask
from rasterio.io import MemoryFile
import requests
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Point, box, mapping, shape
from shapely import transform

sys.path.insert(0, str(Path.cwd()))
from config.phase2_settings import Phase2Config
from config.settings import BEFORE, AFTER
from src.gee_setup import initialize
from src import optical_preprocessing as optical
from src.study_area import get_study_area, verify_boundary

STATIONS = {
    "Lukha-Khaddum-4315": (92.422355, 25.224359),
    "Lukha-Sunapur-3376": (92.361445, 25.108633),
    "Myntdu-Mihmyntdu-4316": (92.204576, 25.434337),
    "Myntdu-Leshka-3379": (92.19829, 25.268735),
}
RIVERS = "WWF/HydroSHEDS/v1/FreeFlowingRivers"
WATER = "JRC/GSW1_4/GlobalSurfaceWater"
RAIN = "UCSB-CHG/CHIRPS/DAILY"
SIZE = 72
STEP = 10
CRS = "EPSG:32646"
NODATA = -9999
BANDS = ("B2", "B3", "B4", "B8", "scl", "cloud", "existing_valid")


def fetch(image, affine):
    url = image.toInt16().unmask(NODATA, sameFootprint=False).getDownloadURL(
        dict(format="GEO_TIFF", crs=CRS, crs_transform=list(affine)[:6], dimensions=[SIZE, SIZE]))
    with requests.get(url, timeout=(15, 180)) as response:
        if response.status_code != 200:
            raise RuntimeError(f"Earth Engine download returned HTTP {response.status_code}")
        content = response.content
    with MemoryFile(content) as mem, mem.open() as src:
        if (src.crs.to_string(), src.transform, src.shape) != (CRS, affine, (SIZE, SIZE)):
            raise ValueError("Unexpected raster grid")
        return src.read()


def save_raster(path, data, affine, names):
    with rasterio.open(path, "w", driver="GTiff", crs=CRS, transform=affine,
                       width=SIZE, height=SIZE, count=len(data), dtype=data.dtype,
                       nodata=NODATA, compress="deflate") as dst:
        dst.write(data)
        dst.descriptions = tuple(names)
    with rasterio.open(path) as src:
        if src.transform != affine or tuple(src.descriptions) != tuple(names) or not np.array_equal(src.read(), data):
            raise ValueError("GeoTIFF verification failed")


def scene_bands(img, cfg):
    valid = ee.Image(optical.prepare(img, cfg)).select("NDVI").mask().rename("existing_valid")
    cloud = ee.Image(img.get("clouds")).select("probability").rename("cloud")
    return img.select(["B2", "B3", "B4", "B8", "SCL"]).rename(list(BANDS[:5])).addBands(cloud).addBands(valid)


def screen(array, corridor):
    blue, green, red, nir, scl, cloud, existing = array
    available = (cloud != NODATA) & (scl != NODATA)
    denominator = green.astype(float) + nir
    ndwi = np.divide(green.astype(float) - nir, denominator,
                     out=np.zeros(green.shape), where=denominator > 0)
    valid = (existing == 1) & (green >= 0) & (nir >= 0) & (red >= 0)
    water = valid & (scl == 6) & (ndwi > 0)
    strict = valid & (scl == 6) & (ndwi > .1)
    distance = distance_transform_edt(np.pad(water, 1))[1:-1, 1:-1] * STEP
    strict_distance = distance_transform_edt(np.pad(strict, 1))[1:-1, 1:-1] * STEP
    core = corridor & (distance >= 20)
    strict_core = corridor & (strict_distance >= 20)
    def count(mask):
        return int((mask & corridor).sum())
    metrics = dict(available=count(available), cloud=count(available & ((cloud >= 40) | np.isin(scl, [8,9,10]))),
                   shadow=count(np.isin(scl, [2,3])), existing_valid=count(valid),
                   scl_water=count(valid & (scl == 6)), water=count(water),
                   strict_water=count(strict), core_10m=count(core),
                   core_20m=count(distance >= 30), strict_core_10m=count(strict_core),
                   clearance_m=float(distance[corridor].max()))
    return metrics, water, core


def render(path, array, water, core, reach, affine, name, date):
    rgb = np.stack((array[2],array[1],array[0]), axis=-1)
    rgb = np.clip(rgb.astype(float) / 3000, 0, 1)
    extent = (affine.c, affine.c + SIZE*STEP, affine.f-SIZE*STEP, affine.f)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.5), layout="constrained")
    axes[0].imshow(rgb, extent=extent, interpolation="nearest")
    axes[1].imshow(rgb, extent=extent, interpolation="nearest")
    overlay = np.zeros((SIZE,SIZE,4))
    overlay[water] = [0,.65,1,.55]
    overlay[core] = [1,.75,0,.9]
    axes[1].imshow(overlay, extent=extent, interpolation="nearest")
    if reach.geom_type == "LineString":
        axes[1].plot(*reach.xy, color="white", linewidth=.8)
    for ax in axes:
        ax.set_xlim(extent[:2])
        ax.set_ylim(extent[2:])
        ax.ticklabel_format(useOffset=False, style="plain")
        ax.tick_params(labelsize=7)
    axes[0].set_title("Sentinel-2 B4/B3/B2")
    axes[1].set_title("Blue: screened water · gold: interior proxy")
    fig.suptitle(f"{name} | {date} UTC | white: mapped reach")
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output directory")
    cfg = Phase2Config()
    project = Transformer.from_crs(4326, CRS, always_xy=True).transform
    initialize()
    ee.data.setDeadline(180000)
    district = verify_boundary(get_study_area())
    result = {}
    with TemporaryDirectory(dir=args.output.parent) as temp:
        output = Path(temp) / "river"
        output.mkdir()
        for station, xy in STATIONS.items():
            print(f"Checking {station}", flush=True)
            folder = output / station
            folder.mkdir()
            center = Point(*project(*xy))
            left, top = round(center.x/STEP)*STEP-SIZE*STEP/2, round(center.y/STEP)*STEP+SIZE*STEP/2
            affine = rasterio.Affine(STEP,0,left,0,-STEP,top)
            extent = [left, top-SIZE*STEP, left+SIZE*STEP, top]
            region = ee.Geometry.Rectangle(extent, CRS, False)
            if not district.intersects(region, 1).getInfo():
                raise ValueError(f"{station} window does not intersect study districts")
            inside = district.contains(region, 1).getInfo()
            features = ee.FeatureCollection(RIVERS).filterBounds(region).getInfo()["features"]
            reaches = [(transform(shape(f["geometry"]), project, interleaved=False).intersection(box(*extent)), f)
                       for f in features]
            reaches = [(g,f) for g,f in reaches if g.length > 0]
            if not reaches:
                result[station] = dict(coordinates=xy, extent=extent, inside_district=inside,
                                       reason="No intersecting mapped river reach")
                continue
            reach, feature = min(reaches,key=lambda gf: gf[0].distance(center))
            corridor_geom = reach.buffer(80).intersection(center.buffer(260)).intersection(box(*extent))
            corridor = geometry_mask([mapping(corridor_geom)],out_shape=(SIZE,SIZE),transform=affine,invert=True)
            if not corridor.any():
                raise ValueError(f"No pixels in reach corridor for {station}")
            occurrence, = fetch(ee.Image(WATER).select("occurrence").clip(region),affine)
            save_raster(folder/"historical_water.tif",occurrence[None],affine,["JRC_occurrence_percent"])
            rain = ee.ImageCollection(RAIN)
            rows = dict(coordinates=xy, extent=extent, inside_district=inside,
                        reach_properties=feature["properties"], intersecting_reaches=len(reaches),
                        station_to_reach_m=round(reach.distance(center),2),
                        corridor_pixels=int(corridor.sum()), jrc_positive=int(((occurrence>0)&corridor).sum()),
                        jrc_at_least_50=int(((occurrence>=50)&corridor).sum()),
                        jrc_grid_note="30 m source sampled on 10 m display grid; counts are not independent",
                        seasons={})
            for label, season in (("before",BEFORE),("after",AFTER)):
                raw,joined = optical.collections(region,season,cfg)
                joined = joined.sort("system:index")
                info = ee.Dictionary(dict(ids=joined.aggregate_array("system:index"),
                     times=joined.aggregate_array("system:time_start"), raw=raw.size())).getInfo()
                ids = info["ids"]
                if not ids or len(ids)>160:
                    raise ValueError(f"Unexpected scene count at {station}/{label}: {len(ids)}")
                prepared = joined.map(lambda img: scene_bands(img,cfg).clip(region))
                all_bands = fetch(prepared.toBands(),affine)
                if len(all_bands) != len(ids)*len(BANDS):
                    raise ValueError("Scene band count mismatch")
                dates, best = [], None
                for index,(image_id,time) in enumerate(zip(ids,info["times"],strict=True)):
                    data = all_bands[index*len(BANDS):(index+1)*len(BANDS)]
                    metrics,water,core = screen(data,corridor)
                    date = datetime.fromtimestamp(time/1000,timezone.utc).isoformat()
                    dates.append(dict(id=image_id,acquired_utc=date,**metrics))
                    score = (metrics["core_10m"], metrics["water"], metrics["existing_valid"])
                    if best is None or score>best[0]:
                        best = score,data,water,core,date
                _,data,water,core,date = best
                if water[corridor].any():
                    save_raster(folder/f"{label}_example.tif",data,affine,BANDS)
                    render(folder/f"{label}_example.png",data,water,core,reach,affine,station,date[:10])
                def unique(field, threshold):
                    return len({row["acquired_utc"][:10] for row in dates if row[field]>=threshold})
                daily = rain.filterDate(season.start,season.end)
                rainfall = ee.Dictionary(dict(days=daily.size(), total_mm=daily.sum().reduceRegion(
                    ee.Reducer.first(),ee.Geometry.Point(xy),scale=5566,maxPixels=10).get("precipitation"))).getInfo()
                rows["seasons"][label] = dict(raw_scene_count=info["raw"],joined_scene_count=len(ids),
                    unique_joined_dates=unique("available",0), valid_dates=unique("existing_valid",1),
                    water_dates=unique("water",1), core_dates=unique("core_10m",1),
                    strict_core_dates=unique("strict_core_10m",1), wider_core_dates=unique("core_20m",1),
                    core_month_counts=dict(Counter(sorted({r["acquired_utc"][:10] for r in dates
                                               if r["core_10m"]>0})[i][:7] for i in range(unique("core_10m",1)))),
                    max_clearance_m=max(r["clearance_m"] for r in dates), rainfall=rainfall,
                    example_date=date,scenes=dates)
                print(station,label,{k:v for k,v in rows["seasons"][label].items() if k!="scenes"},flush=True)
            result[station]=rows
        (output/"receipt.json").write_text(json.dumps(dict(sources=[RIVERS,WATER,RAIN,
            "COPERNICUS/S2_SR_HARMONIZED","COPERNICUS/S2_CLOUD_PROBABILITY"],
            projection=CRS, grid_m=STEP, stations=result),indent=2),encoding="utf-8")
        output.rename(args.output)


if __name__ == "__main__":
    main()
