"""Screen adjacent mapped river reaches using the Phase 4 interior-water rules."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path

import ee
import numpy as np
from pyproj import Transformer
from rasterio import Affine
from shapely import transform
from shapely.geometry import Point, mapping, shape

from phase4a_river import (
    AFTER, BEFORE, BANDS, CRS, RIVERS, SIZE, STEP, Phase2Config,
    fetch, geometry_mask, initialize, optical, save_raster, scene_bands, screen,
)
from phase4b_leshka import largest_component, match_dates, write_csv

ANCHORS = ("Lukha-Sunapur-3376", "Myntdu-Leshka-3379")


def upstream(properties):
    return {int(value) for value in (properties.get("NUOID") or "").split("_") if int(value or 0) > 0}


def leads(stations):
    for station, limit in zip(ANCHORS, (3, 2), strict=True):
        reach = stations[station]["reach_properties"]
        for noid in [reach["NDOID"], *sorted(upstream(reach))][:limit]:
            if noid > 0:
                yield station, reach["NOID"], noid, "downstream" if noid == reach["NDOID"] else "upstream"


def confirms_link(anchor, direction, candidate):
    return (anchor in upstream(candidate) if direction == "downstream"
            else candidate.get("NDOID") == anchor)


def fixed_support(seasons):
    pairs = []
    for month in (11, 12, 1, 2, 3):
        pairs.extend(match_dates(*(sorted(day for day in season if day.month == month) for season in seasons)))
    masks = [season[day][2] for pair in pairs for season, day in zip(seasons, pair, strict=True)]
    return pairs, largest_component(np.logical_and.reduce(masks)) if masks else None


def screen_reach(geometry, crs=CRS, anchor=None):
    project = Transformer.from_crs(4326, crs, always_xy=True)
    line = transform(shape(geometry), project.transform, interleaved=False)
    point = (line.interpolate(0.5, normalized=True) if anchor is None
             else line.interpolate(line.project(Point(*project.transform(*anchor)))))
    left = round(point.x/STEP)*STEP-SIZE*STEP/2
    top = round(point.y/STEP)*STEP+SIZE*STEP/2
    affine = Affine(STEP, 0, left, 0, -STEP, top)
    extent = [left, top-SIZE*STEP, left+SIZE*STEP, top]
    region = ee.Geometry.Rectangle(extent, crs, False)
    corridor = geometry_mask([mapping(line.buffer(80).intersection(point.buffer(260)))],
                             out_shape=(SIZE, SIZE), transform=affine, invert=True)
    cfg = Phase2Config()
    seasons, counts, inventory = [], {}, {}
    for name, window in (("before", BEFORE), ("after", AFTER)):
        _, joined = optical.collections(region, window, cfg)
        joined = joined.sort("system:index")
        info = ee.Dictionary(dict(ids=joined.aggregate_array("system:index"),
                             times=joined.aggregate_array("system:time_start"))).getInfo()
        ids = info["ids"]
        if len(ids) > 160:
            raise ValueError("Scene count exceeds bounded station limit")
        dated, water_dates, valid_dates = {}, set(), set()
        inventory[name] = []
        if ids:
            bands = fetch(joined.map(lambda img: scene_bands(img, cfg).clip(region)).toBands(), affine, crs)
            if len(bands) != len(ids)*len(BANDS):
                raise ValueError("Scene band count mismatch")
            for index, (scene, millis) in enumerate(zip(ids, info["times"], strict=True)):
                instant = datetime.fromtimestamp(millis/1000, timezone.utc)
                day = instant.date()
                data = bands[index*len(BANDS):(index+1)*len(BANDS)]
                metrics, _, core = screen(data, corridor)
                eligible = core & (data[1].astype(float)+data[2] > 0)
                inventory[name].append(dict(id=scene, utc=instant.isoformat(), **metrics))
                if metrics["existing_valid"]:
                    valid_dates.add(day)
                if metrics["water"]:
                    water_dates.add(day)
                if eligible.any():
                    score = (metrics["core_10m"], scene)
                    if day not in dated or score > dated[day][:2]:
                        dated[day] = (*score, eligible, data[2].copy(), data[1].copy())
        seasons.append(dated)
        counts.update({name+"_valid_dates": len(valid_dates), name+"_water_dates": len(water_dates),
                       name+"_interior_dates": len(dated)})
    pairs, mask = fixed_support(seasons)
    count = int(mask.sum()) if mask is not None else 0
    months = len({a.month for a, _ in pairs})
    spectra = []
    if count >= 25 and months >= 2:
        for before, after in pairs:
            values = []
            for season, day in zip(seasons, (before, after), strict=True):
                red, green = (band[mask].astype(float) for band in season[day][3:])
                values.append(float(np.median((red-green)/(red+green))))
            spectra.append(dict(before=before.isoformat(), after=after.isoformat(),
                                before_ndti=values[0], after_ndti=values[1]))
    lon, lat = Transformer.from_crs(crs, 4326, always_xy=True).transform(point.x, point.y)
    return dict(longitude=lon, latitude=lat, corridor_cells=int(corridor.sum()), **counts,
                matched_pairs=len(pairs), matched_months=months, common_cells=count,
                spectral_support="PASSES" if count >= 25 and months >= 2 else "INSUFFICIENT DATA"), mask, affine, dict(
                    extent=extent, scenes=inventory, spectra=spectra,
                    matched=[[a.isoformat(), b.isoformat()] for a,b in pairs])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.screen.read_text(encoding="utf-8"))
    wanted = list(leads(source["stations"]))
    if len(wanted) > 5:
        raise ValueError("Maximum five adjacent reaches")
    args.output.mkdir()
    rows, details = [], {}
    try:
        initialize()
        ee.data.setDeadline(90000)
        features = ee.FeatureCollection(RIVERS).filter(ee.Filter.inList("NOID", [item[2] for item in wanted]))
        indexed = {f["properties"]["NOID"]: f for f in features.getInfo()["features"]}
        error = None
    except (ee.EEException, RuntimeError, OSError) as exc:
        indexed, error = {}, type(exc).__name__
    for station, anchor, noid, direction in wanted:
        row = dict(station=station, anchor_noid=anchor, candidate_noid=noid,
                   mapped_direction=direction, reciprocal_link="UNKNOWN", mining_flow_relationship="UNKNOWN",
                   spectral_support="UNSCREENED")
        feature = indexed.get(noid)
        if feature is not None:
            row["reciprocal_link"] = "CONFIRMED" if confirms_link(anchor, direction, feature["properties"]) else "UNKNOWN"
            try:
                result, mask, affine, details[noid] = screen_reach(feature["geometry"])
                row.update(result)
                if mask is not None:
                    save_raster(args.output/f"{noid}_fixed_support.tif", mask[None].astype("int16"), affine, ["common"])
            except (ee.EEException, RuntimeError, OSError, ValueError) as exc:
                row["error"] = type(exc).__name__
        elif error:
            row["error"] = error
        rows.append(row)
        write_csv(args.output/f"{noid}.csv", [row])
        print(row, flush=True)
    write_csv(args.output/"reaches.csv", rows)
    (args.output/"observations.json").write_text(json.dumps(details, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
