"""Compare Brahmani reaches on shared UTC dates using the Phase 12C fixed masks."""
import argparse
import csv
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from statistics import median

import numpy as np
import rasterio
from scipy.ndimage import label

from phase4b_leshka import match_dates, write_csv

REACHES = ("Talcher upstream SW3", "Talcher far downstream 2416")
SEASONS = ("before", "after")
WINDOWS = (("2023-11-01", "2024-04-01"), ("2024-11-01", "2025-04-01"))


def compare(observations, supports):
    indexed = {}
    for name in REACHES:
        rows = observations[name]["spectra"]
        indexed[name] = {}
        for side, (start, end) in zip(SEASONS, WINDOWS, strict=True):
            dated = {date.fromisoformat(row[side]): row for row in rows}
            if len(dated) != len(rows) or any(not start <= day.isoformat() < end for day in dated):
                raise ValueError("Duplicate or out-of-season spectral date")
            indexed[name][side] = dated
    shared = {side: indexed[REACHES[0]][side].keys() & indexed[REACHES[1]][side].keys()
              for side in SEASONS}
    pairs = [pair for month in (11, 12, 1, 2, 3)
             for pair in match_dates(*(sorted(d for d in shared[side] if d.month == month) for side in SEASONS))]
    months = len({a.month for a, _ in pairs})
    status = "DESCRIPTIVE ONLY" if min(supports) >= 25 and months >= 2 else "INSUFFICIENT DATA"
    summary = dict(row_type="summary", status=status, shared_before=len(shared["before"]),
                   shared_after=len(shared["after"]), matched_pairs=len(pairs), matched_months=months,
                   upstream_cells=supports[0], downstream_cells=supports[1], discharge="UNAVAILABLE")
    if status != "DESCRIPTIVE ONLY":
        return [summary]
    dates = []
    for number, pair in enumerate(pairs, 1):
        for side, day in zip(SEASONS, pair, strict=True):
            up, down = (indexed[name][side][day] for name in REACHES)
            u, d = (float(row[f"{side}_ndti"]) for row in (up, down))
            if not (-1 <= u <= 1 and -1 <= d <= 1):
                raise ValueError("Invalid NDTI value")
            dated = dict(row_type="date", status=status, pair=number, season=side, date=day.isoformat(),
                         upstream_ndti=u, downstream_ndti=d, downstream_minus_upstream=d-u)
            for reach, row in zip(("upstream", "downstream"), (up, down), strict=True):
                for days in (1, 3, 7):
                    dated[f"{reach}_rain_{days}d_mm"] = row.get(f"{side}_rain_{days}d_mm")
            dates.append(dated)
    for field in ("upstream_ndti", "downstream_ndti", "downstream_minus_upstream"):
        before, after = ([row[field] for row in dates if row["season"] == side] for side in SEASONS)
        for side, values in zip(SEASONS, (before, after), strict=True):
            summary[f"{side}_{field}_median"] = median(values)
            if field == "downstream_minus_upstream":
                summary[f"{side}_{field}_min"] = min(values)
                summary[f"{side}_{field}_max"] = max(values)
        summary[f"{field}_seasonal_change"] = median(after) - median(before)
    return [summary, *dates]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = args.source / "receipt.json"
    source = json.loads(path.read_bytes())
    table_path = args.source / "stations.csv"
    with table_path.open(newline="", encoding="utf-8") as stream:
        stations = {row["station"]: row for row in csv.DictReader(stream)}
    supports, hashes = [], {}
    for name in REACHES:
        station = stations[name]
        detail = source["observations"][name]
        if station["spectral_support"] != "PASSES" or station["linked_mainstem"] != "True":
            raise ValueError("Source reach has not passed Phase 12C screening")
        mask_path = args.source / detail["support_raster"]
        with rasterio.open(mask_path) as src:
            mask = src.read(1)
            if (str(src.crs) != source["crs"] or src.res != (10, 10)
                    or tuple(src.bounds) != tuple(detail["extent"])
                    or src.descriptions != ("common",)
                    or not np.isin(mask, [0, 1]).all()
                    or label(mask)[1] != 1 or int(mask.sum()) != int(station["common_cells"])):
                raise ValueError("Source footprint disagrees with Phase 12C")
        supports.append(int(mask.sum()))
        hashes[name] = sha256(mask_path.read_bytes()).hexdigest()
    rows = compare(source["observations"], supports)
    rows[0].update(source_receipt_sha256=sha256(path.read_bytes()).hexdigest(),
                   station_table_sha256=sha256(table_path.read_bytes()).hexdigest(),
                   source_collections="; ".join(source["source_collections"]),
                   upstream_mask_sha256=hashes[REACHES[0]], downstream_mask_sha256=hashes[REACHES[1]],
                   rainfall_geometry=source["rainfall"], mine_connectivity="UNKNOWN",
                   uncertainty="Fixed Phase 12C masks retained; date-pair variability is descriptive; discharge unavailable")
    write_csv(args.output, rows)
    print(rows[0])


if __name__ == "__main__":
    main()
