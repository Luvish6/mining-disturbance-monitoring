"""Bounded Brahmani pilot at three official monitoring anchors."""
import argparse
from datetime import date
import json
from pathlib import Path
from statistics import median

import numpy as np
from shapely.geometry import Point, shape
from shapely import transform
from pyproj import Transformer

from phase12b_reaches import ee, confirms_link, initialize, RIVERS, screen_reach, save_raster, write_csv
from phase4b_leshka import rainfall, preceding

CRS = "EPSG:32645"
ANCHORS = {
    "Samal 1041": (85.142032, 21.074527),
    "Talcher upstream SW3": (85 + 15.313/60, 20 + 59.338/60),
    "Talcher upstream 1303": (85.216631, 20.949817),
    "Talcher downstream SW4": (85 + 14.306/60, 20 + 54.968/60),
    "Kamalanga 1042": (85.278472, 20.867785),
    "Talcher far downstream 2416": (85.316236, 20.825086),
}
SOURCES = [
    "https://ospcboard.odisha.gov.in/wp-content/uploads/2017/01/Action_plan_Implementation_Status_Angul_talcher-1.pdf",
    "https://cpcb.nic.in/wqm/WQMN_list.pdf",
]


def downstream_path(features, start, end):
    path = [start]
    while path[-1] != end:
        current = path[-1]
        target = features[current]["properties"].get("NDOID")
        if target in path or target not in features:
            return []
        if not confirms_link(current, "downstream", features[target]["properties"]):
            return []
        path.append(target)
    return path


def summarize(rows):
    before = median(row["before_ndti"] for row in rows)
    after = median(row["after_ndti"] for row in rows)
    differences = np.array([row["after_ndti"]-row["before_ndti"] for row in rows])
    return dict(before_ndti=before, after_ndti=after, ndti_change=after-before,
                paired_change_min=float(differences.min()), paired_change_max=float(differences.max()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    out = parser.parse_args().output
    out.mkdir()
    initialize()
    ee.data.setDeadline(90000)
    # One bounded hydrography lookup for station snapping and reciprocal path tracing.
    region = ee.Geometry.Rectangle([85.10, 20.79, 85.36, 21.11], None, False)
    result = ee.FeatureCollection(RIVERS).filterBounds(region).getInfo()
    features = {f["properties"]["NOID"]: f for f in result["features"]}
    project = Transformer.from_crs(4326, CRS, always_xy=True).transform
    mainstem = {noid: transform(shape(f["geometry"]), project, interleaved=False)
                for noid, f in features.items() if f["properties"]["DIS_AV_CMS"] >= 100}
    snaps, rejected = {}, {}
    for name, xy in ANCHORS.items():
        point = Point(*project(*xy))
        distance, noid = min((line.distance(point), noid) for noid, line in mainstem.items())
        if distance > 500 or noid in {item[0] for item in snaps.values()} or len(snaps) == 3:
            rejected[name] = dict(noid=noid, distance_m=round(distance, 1))
            continue
        snaps[name] = (noid, distance)
    print(dict(selected=snaps, rejected=rejected), flush=True)
    ordered = [item[0] for item in snaps.values()]
    paths = [downstream_path(features, a, b) for a, b in zip(ordered, ordered[1:])]
    connected = len(ordered) >= 2 and all(paths)
    receipt = dict(station_sources=SOURCES, topology_source=RIVERS, crs=CRS, paths=paths, rejected=rejected,
                   source_collections=["COPERNICUS/S2_SR_HARMONIZED", "COPERNICUS/S2_CLOUD_PROBABILITY",
                                       "UCSB-CHG/CHIRPS/DAILY"],
                   windows=[["2023-11-01", "2024-04-01"], ["2024-11-01", "2025-04-01"]],
                   rainfall="native CHIRPS station cell; complete preceding UTC days",
                   ndti="median of per-date fixed-footprint medians of (B4-B3)/(B4+B3)",
                   limits="Mixed pixels, atmospheric and hydrological effects remain; Bhubaneswari connectivity unknown",
                   observations={})
    rows = []
    rain_by_cell = {}
    for name, (noid, distance) in snaps.items():
        xy = ANCHORS[name]
        row = dict(station=name, noid=noid, anchor_lon=xy[0], anchor_lat=xy[1], snap_m=round(distance, 1),
                   linked_mainstem=connected, mine_connectivity="UNKNOWN")
        try:
            values, mask, affine, details = screen_reach(features[noid]["geometry"], CRS, anchor=xy)
            row.update(values)
        except (ee.EEException, RuntimeError, OSError, ValueError) as exc:
            row.update(spectral_support="UNSCREENED", error=type(exc).__name__)
            rows.append(row)
            print(row, flush=True)
            continue
        spectra = details.pop("spectra")
        if mask is not None:
            filename = f"{noid}_fixed_support.tif"
            save_raster(out / filename, mask[None].astype("int16"), affine, ["common"], CRS)
            details["support_raster"] = filename
        if spectra and connected:
            row.update(summarize(spectra))
        else:
            spectra = []
        # Existing Phase 4B rainfall method, with actual station-cell extraction.
        try:
            rain = rainfall(xy)
            rain_by_cell[name] = {day.isoformat(): value for day, value in rain.items()}
            for season, (start, end) in zip(("before", "after"), receipt["windows"], strict=True):
                span = (date.fromisoformat(end)-date.fromisoformat(start)).days
                totals = [v for d, v in rain.items() if start <= d.isoformat() < end and v is not None]
                row[f"{season}_rain_days"] = len(totals)
                row[f"{season}_rain_mm"] = sum(totals) if len(totals) == span else None
            for pair in spectra:
                for side in ("before", "after"):
                    for length in (1, 3, 7):
                        pair[f"{side}_rain_{length}d_mm"] = preceding(rain, date.fromisoformat(pair[side]), length)
        except (ee.EEException, RuntimeError, OSError, ValueError) as exc:
            row["rainfall_error"] = type(exc).__name__
        details["spectra"] = spectra
        receipt["observations"][name] = details
        rows.append(row)
        write_csv(out / f"{noid}.csv", [row])
        print(row, flush=True)
    write_csv(out / "stations.csv", rows)
    receipt["station_cell_daily_mm"] = rain_by_cell
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    main()
