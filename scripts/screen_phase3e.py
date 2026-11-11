"""Sample existing seasonal features at bounded planning points for discovery only."""
import argparse
import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

import ee
from pyproj import Transformer
from shapely.geometry import Point, box, shape
from shapely.ops import transform

sys.path.insert(0, str(Path.cwd()))
from config.phase2_settings import Phase2Config
from config.settings import BEFORE, AFTER
from phase2 import build
from src.gee_setup import initialize
from src.phase3.spatial import block_for, partition

BANDS = ("dVV", "dVH", "dNDVI", "dNDTI")
COUNTS = ("sar_before_count", "sar_after_count", "optical_before_count", "optical_after_count")
REQUIREMENTS = "Dated independent coverage of both seasons, local visibility, documented <=30 m error, provenance and second review"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def planning_points(cores, boundary):
    project = Transformer.from_crs(4326, 32646, always_xy=True).transform
    geographic = Transformer.from_crs(32646, 4326, always_xy=True).transform
    district = transform(project, boundary)
    groups = {}
    centers = {}
    for feature in cores:
        p = feature["properties"]
        block = p["block"]
        bx, by = map(int, block.split(":"))
        split = partition(block)
        if (p["split"], p["block_m"], p["buffer_m"], p["seed"]) != (split, 5000, 120, 42):
            raise ValueError(f"Inconsistent frozen core {block}")
        points = []
        for dx in (650, 1850, 3150, 4350):
            for dy in (650, 1850, 3150, 4350):
                x, y = bx * 5000 + dx, by * 5000 + dy
                footprint = box(x - 150, y - 150, x + 150, y + 150)
                if district.covers(footprint) and block_for(footprint.bounds) == block:
                    lon, lat = geographic(x, y)
                    points.append(dict(point_id=f"{block}-{dx}-{dy}", block=block,
                                       partition=split, longitude=lon, latitude=lat))
        if len(points) >= 8:
            groups[block] = points
            centers[block] = Point(bx, by)
    picked = []
    for split in ("train", "validation", "test"):
        available = sorted(b for b in groups if partition(b) == split)
        if len(available) < 3:
            raise ValueError(f"Fewer than three eligible planning cores in {split}")
        chosen = [available.pop(len(available) // 2)]
        for _ in range(2):
            block = max(available, key=lambda b: min(centers[b].distance(centers[c]) for c in chosen))
            available.remove(block)
            chosen.append(block)
        picked.extend(point for block in chosen for point in groups[block])
    return picked


def select(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row["block"], []).append(row)
    selected = []
    for block, group in sorted(groups.items()):
        supported = [r for r in group if all(r.get(b) is not None and math.isfinite(r[b]) for b in BANDS)
                     and all((r.get(c) or 0) >= 2 for c in COUNTS)]
        if len(supported) < 3:
            continue
        def optical(r):
            return max(abs(r["dNDVI"]), abs(r["dNDTI"]))
        def radar(r):
            return max(abs(r["dVV"]), abs(r["dVH"]))
        optical_order = sorted(supported, key=lambda r: (optical(r), r["point_id"]))
        radar_order = sorted(supported, key=lambda r: (radar(r), r["point_id"]))
        o = {r["point_id"]: i for i, r in enumerate(optical_order)}
        s = {r["point_id"]: i for i, r in enumerate(radar_order)}
        def ranks(row):
            key = row["point_id"]
            return o[key], s[key]
        change = max(supported, key=lambda r: (min(ranks(r)), sum(ranks(r)), r["point_id"]))
        remainder = [r for r in supported if r != change]
        background = min(remainder, key=lambda r: (sum(ranks(r)), r["point_id"]))
        contrast = max((r for r in remainder if r != background),
                       key=lambda r: (ranks(r)[0] - ranks(r)[1], r["point_id"]))
        for role, row, rationale in (
            ("change", change, "Jointly high optical and SAR change magnitude within sampled block"),
            ("background", background, "Low combined change ranks; seek stable background corroboration"),
            ("alternative_disturbance", contrast, "Largest optical-minus-SAR rank among remaining points; investigate non-mining explanations"),
        ):
            selected.append(dict(row, role=role, rationale=rationale, status="UNKNOWN",
                                 evidence_status="External independent evidence needed",
                                 independent_imagery="Unknown in both seasons",
                                 uncertainty="Point sample; cause, extent, visibility and positional error unverified",
                                 requirements=REQUIREMENTS))
    return selected


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf-8") as stream:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output directory")
    boundary = read(Path("data/reference_annotation/v20261108_01/boundary_original.geojson"))
    if boundary["type"] == "FeatureCollection":
        from shapely.ops import unary_union
        district = unary_union([shape(f["geometry"]) for f in boundary["features"]])
    else:
        district = shape(boundary.get("geometry", boundary))
    points = planning_points(read(Path("data/planning/labeling_cores.geojson"))["features"], district)
    initialize()
    ee.data.setDeadline(120000)
    cfg = Phase2Config(relative_orbit=77)
    geometries = [ee.Geometry.Point([p["longitude"], p["latitude"]]) for p in points]
    collection = ee.FeatureCollection([ee.Feature(g, {"point_id": p["point_id"]})
                                       for p, g in zip(points, geometries)])
    region = collection.geometry().bounds(30).buffer(500)
    stack, diagnostics, meta = build(region, cfg)
    image = stack.select(list(BANDS)).unmask(-9999).addBands(diagnostics.select(list(COUNTS)).unmask(0))
    result = image.sampleRegions(collection=collection, projection=cfg.analysis_crs,
                                 scale=cfg.analysis_scale_m, tileScale=4).getInfo()
    values = {f["properties"]["point_id"]: f["properties"] for f in result["features"]}
    if len(values) != len(points):
        raise ValueError("Earth Engine did not return one record per planning point")
    rows = []
    for p in points:
        row = values[p["point_id"]]
        rows.append(dict(p, **{k: None if row[k] == -9999 else row[k] for k in BANDS + COUNTS}))
    leads = select(rows)
    args.output.mkdir(parents=True, exist_ok=False)
    write_csv(args.output / "internal_screening_samples.csv", rows)
    for role in ("change", "background", "alternative_disturbance"):
        selected = [r for r in leads if r["role"] == role]
        if selected:
            write_csv(args.output / f"internal_{role}_leads.csv", selected)
    ordered = sorted(leads, key=lambda r: r["point_id"])
    if ordered:
        write_csv(args.output / "review_locations.csv", [
            dict(review_id=f"R{i:03d}", longitude=r["longitude"], latitude=r["latitude"])
            for i, r in enumerate(ordered, 1)])
        write_csv(args.output / "internal_review_key.csv", [
            dict(review_id=f"R{i:03d}", point_id=r["point_id"])
            for i, r in enumerate(ordered, 1)])
    receipt = dict(seasons=[asdict(BEFORE), asdict(AFTER)], phase2_config=asdict(cfg),
                   earth_engine=meta, points=len(points), blocks=sorted({p["block"] for p in points}),
                   leads_by_partition={split: sum(r["partition"] == split for r in leads)
                                       for split in ("train", "validation", "test")})
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
