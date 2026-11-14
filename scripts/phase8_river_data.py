"""Build the ignored River Intelligence snapshot from existing local receipts."""

import csv
import hashlib
import json
import shutil
from pathlib import Path

import rasterio
from rasterio.warp import transform


FIELDS = {
    "unique_joined_dates": None,
    "valid_dates": "existing_valid",
    "water_dates": "water",
    "core_dates": "core_10m",
    "wider_core_dates": "core_20m",
}


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    river = Path("outputs/phase4a_river_feasibility")
    leshka = Path("outputs/phase4b_leshka_spectral_pilot")
    target = Path("frontend/public/local")
    a = json.loads((river / "receipt.json").read_text())
    b = json.loads((leshka / "receipt.json").read_text())
    observations = load_csv(leshka / "observations.csv")
    days = load_csv(leshka / "daily_availability.csv")
    previews = {}
    for key, station in a["stations"].items():
        with rasterio.open(river / key / "historical_water.tif") as grid:
            if (str(grid.crs) != a["projection"] or list(grid.bounds) != station["extent"]
                    or grid.res != (a["grid_m"], a["grid_m"]) or grid.transform.e >= 0):
                raise ValueError(f"Geometry mismatch for {key}")
            x, y = transform("EPSG:4326", grid.crs, [station["coordinates"][0]], [station["coordinates"][1]])
            if not (grid.bounds.left < x[0] < grid.bounds.right and grid.bounds.bottom < y[0] < grid.bounds.top):
                raise ValueError(f"Station lies outside its verified window: {key}")
            station["projected"] = [x[0], y[0]]
        for season, record in station["seasons"].items():
            for field, pixel_field in FIELDS.items():
                dates = {row["acquired_utc"][:10] for row in record["scenes"]
                         if pixel_field is None or row[pixel_field] > 0}
                if len(dates) != record[field]:
                    raise ValueError(f"Date count mismatch: {key}, {season}, {field}")
            image = river / key / f"{season}_example.png"
            if record["water_dates"] and image.is_file():
                previews[f"{key}-{season}.png"] = image
                record["preview"] = f"{key}-{season}.png"
    pilot = a["stations"][b["station"]]
    if (pilot["coordinates"] != b["coordinates"] or pilot["extent"] != b["extent"]
            or pilot["reach_properties"]["GOID"] != b["reach_goid"]):
        raise ValueError("Phase 4A and 4B use different station geometries")
    periods = {"before": ["2023-11-01", "2024-04-01"], "after": ["2024-11-01", "2025-04-01"]}
    for season, (start, end) in periods.items():
        if any(not start <= row["acquired_utc"][:10] < end
               for station in a["stations"].values() for row in station["seasons"][season]["scenes"]):
            raise ValueError("Saved observations extend outside the study window")
    for season, dates in zip(periods, zip(*b["matched_pairs"])):
        ledger = {row["date"] for row in days if row["season"] == season and row["matched"] == "True"}
        measured = {row["acquired_utc"][:10] for row in observations
                    if row["season"] == season and row["common_ratio"]
                    and int(row["fixed_pixels"]) == b["common_pixels"]}
        if ledger != set(dates) or measured != ledger:
            raise ValueError("Matched dates disagree across Phase 4B products")
    support = leshka / "fixed_water_support.png"
    if support.is_file():
        previews[support.name] = support
        b["preview"] = support.name
    target.mkdir(parents=True, exist_ok=True)
    for name, image in previews.items():
        shutil.copyfile(image, target / name)
    provenance = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (river/"receipt.json", leshka/"receipt.json",
                               leshka/"observations.csv", leshka/"daily_availability.csv")}
    payload = dict(periods=periods, river=a, pilot=b, observations=observations, days=days,
                   provenance=provenance)
    (target / "river.json").write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    main()
