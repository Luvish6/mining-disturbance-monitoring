"""Summarize bounded, receipt-backed river observations for the frozen seasons."""
import argparse
import csv
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from shutil import copyfile
from statistics import median
from tempfile import TemporaryDirectory

import rasterio

if __package__:
    from .phase4b_leshka import BEFORE, AFTER, write_csv
else:
    from phase4b_leshka import BEFORE, AFTER, write_csv

WINDOWS = {"before": BEFORE, "after": AFTER}


def spectral_summary(receipt, observations):
    """Use the Phase 4B fixed footprint and an equal number of dates per month."""
    pairs = receipt["matched_pairs"]
    dates = [date.fromisoformat(value) for pair in pairs for value in pair]
    if len(set(dates)) != len(dates) or any(
        a.month != b.month or abs(a.day - b.day) > 15
        or not (BEFORE.start <= a.isoformat() < BEFORE.end)
        or not (AFTER.start <= b.isoformat() < AFTER.end)
        for a, b in zip(dates[::2], dates[1::2], strict=True)
    ):
        raise ValueError("Invalid matched dates")
    months = len({day.month for day in dates})
    support = receipt["common_pixels"]
    eligible = support >= 25 and months >= 2
    if receipt["reportable"] != eligible:
        raise ValueError("Fixed-footprint admission disagrees with source receipt")
    result = dict(common_10m_pixels=support, matched_pairs=len(pairs), matched_months=months)
    if not eligible:
        return result
    selected = {}
    target_dates = {day.isoformat() for day in dates}
    for row in observations:
        day = row["acquired_utc"][:10]
        if day not in target_dates or row["status"] != "matched, fixed-footprint screen passed":
            continue
        value = float(row["common_ratio"])
        if day in selected or int(row["fixed_pixels"]) != support or not -1 <= value <= 1:
            raise ValueError("Invalid fixed-footprint spectral observation")
        selected[day] = value
    if selected.keys() != target_dates:
        raise ValueError("Missing eligible spectral observations")
    before, after = (median(selected[d.isoformat()] for d in dates[offset::2]) for offset in (0, 1))
    return dict(result, before_ndti=before, after_ndti=after, ndti_change=after-before)


def build(phase4a, pilots, output):
    baseline = phase4a / "receipt.json"
    source = json.loads(baseline.read_text(encoding="utf-8"))
    inputs = {"station_screen": sha256(baseline.read_bytes()).hexdigest()}
    rows, coverage, features = [], [], []
    products = {}
    stations = source["stations"]
    if not pilots.keys() <= stations.keys():
        raise ValueError("Pilot configured for an unknown station")
    for station, anchor in stations.items():
        row = dict(station=station, status="INSUFFICIENT DATA",
                   reason="No verified matched fixed footprint", corridor_pixels=anchor.get("corridor_pixels"),
                   flow_position="UNVERIFIED")
        if "coordinates" in anchor:
            features.append(dict(type="Feature", geometry=dict(type="Point", coordinates=anchor["coordinates"]),
                                 properties={"station": station, "role": "station search anchor"}))
        for season, window in WINDOWS.items():
            details = anchor.get("seasons", {}).get(season)
            if details is None:
                continue
            dates = {}
            for scene in details["scenes"]:
                day = scene["acquired_utc"][:10]
                if not window.start <= day < window.end:
                    raise ValueError("Source observation outside frozen season")
                daily = dates.setdefault(day, [0, 0, 0, 0])
                daily[0] += 1
                for i, field in enumerate(("existing_valid", "water", "core_10m"), 1):
                    daily[i] = max(daily[i], scene[field])
            for day, (granules, valid, water, interior) in sorted(dates.items()):
                coverage.append(dict(station=station, season=season, date=day, granules=granules,
                                     max_valid_pixels=valid, max_water_pixels=water, max_interior_pixels=interior,
                                     corridor_pixels=row["corridor_pixels"]))
            for i, field in enumerate(("valid", "water", "interior"), 1):
                row[f"{season}_{field}_dates"] = sum(counts[i] > 0 for counts in dates.values())
            row[f"{season}_rain_days"] = details["rainfall"]["days"]
            row[f"{season}_station_cell_mm"] = details["rainfall"]["total_mm"]
        if station in pilots:
            folder = pilots[station]
            path = folder / "receipt.json"
            observations = folder / "observations.csv"
            mask = folder / "fixed_water_support.tif"
            pilot = json.loads(path.read_text(encoding="utf-8"))
            if (pilot["station"] != station or pilot["coordinates"] != anchor["coordinates"]
                    or pilot["extent"] != anchor["extent"] or pilot["corridor_pixels"] != anchor["corridor_pixels"]
                    or pilot["reach_goid"] != anchor["reach_properties"]["GOID"]):
                raise ValueError("Pilot geometry disagrees with station receipt")
            with rasterio.open(mask) as src:
                pixels = src.read(1)
                if (tuple(src.bounds) != tuple(anchor["extent"]) or str(src.crs) != source["projection"]
                        or tuple(src.res) != (10, 10) or src.descriptions[0] != "common"
                        or not ((pixels == 1) | (pixels == 0)).all()
                        or int(pixels.sum()) != pilot["common_pixels"]):
                    raise ValueError("Invalid source footprint raster")
            with observations.open(newline="", encoding="utf-8") as stream:
                row.update(spectral_summary(pilot, csv.DictReader(stream)))
            row["reason"] = "Matched footprint below spatial or temporal support floor"
            if "ndti_change" in row:
                row.update(status="DESCRIPTIVE ONLY", reason="Fixed-footprint spectral comparison")
            products[station] = mask
            inputs[station] = {asset.name: sha256(asset.read_bytes()).hexdigest() for asset in (path, observations, mask)}
        elif row.get("before_interior_dates") == 0 or row.get("after_interior_dates") == 0:
            row["reason"] = "No screened interior observations in at least one season"
        rows.append(row)
    with TemporaryDirectory(dir=output.parent) as temp:
        target = Path(temp) / "analysis"
        target.mkdir()
        write_csv(target / "stations.csv", rows)
        if coverage:
            write_csv(target / "daily_coverage.csv", coverage)
        (target / "stations.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=features)), encoding="utf-8")
        for station, mask in products.items():
            name = sha256(station.encode()).hexdigest()[:16] + "_fixed_support.tif"
            copyfile(mask, target / name)
            inputs[station]["output_mask"] = name
        receipt = dict(source_sha256=inputs, collections=source["sources"],
                       seasons={key: [v.start, v.end] for key, v in WINDOWS.items()},
                       minimum_common_pixels=25, minimum_matched_months=2,
                       ndti="median across matched dates of per-date median (B4-B3)/(B4+B3)",
                       rainfall="CHIRPS coarse station-cell totals, mm",
                       limitations=["No verified drainage ordering", "Water-screen proxy subject to mixed pixels",
                                    "No calibrated water quality or causal attribution"])
        (target / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False), encoding="utf-8")
        target.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", required=True, type=Path)
    parser.add_argument("--pilot", action="append", nargs=2, metavar=("STATION", "DIR"), default=[])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output directory")
    build(args.screen, {station: Path(folder) for station, folder in args.pilot}, args.output)


if __name__ == "__main__":
    main()
