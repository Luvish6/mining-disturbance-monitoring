"""Check Landsat context availability at Phase 3E leads; no imagery export."""
import argparse
import csv
import json
from pathlib import Path
import sys

import ee

sys.path.insert(0, str(Path.cwd()))
from config.settings import BEFORE, AFTER
from src.gee_setup import initialize

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=Path("outputs/phase3e_candidate_discovery"))
dest = parser.parse_args().output
with (dest / "review_locations.csv").open(newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))

initialize()
ee.data.setDeadline(120000)
points = ee.FeatureCollection([
    ee.Feature(ee.Geometry.Point([float(r["longitude"]), float(r["latitude"])]),
               {"review_id": r["review_id"]}) for r in rows])
region = points.geometry().bounds(30)
collections = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").merge(
    ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")).filterBounds(region)

def usable(image):
    qa = image.select("QA_PIXEL").bitwiseAnd(63).eq(0)
    unsaturated = image.select("QA_RADSAT").eq(0)
    return image.select("SR_B4").multiply(0).add(1).rename("observation").updateMask(
        qa.And(unsaturated))

counts = ee.Image.cat([
    collections.filterDate(season.start, season.end).map(usable).count().unmask(0).rename(name)
    for season, name in ((BEFORE, "before"), (AFTER, "after"))])
result = counts.sampleRegions(collection=points, projection="EPSG:32646",
                              scale=30, tileScale=4).getInfo()
by_id = {p["review_id"]: p for p in (f["properties"] for f in result["features"])}
assert set(by_id) == {r["review_id"] for r in rows}
output = []
for row in rows:
    p = by_id[row["review_id"]]
    output.append(dict(row, before_qa_pass_count=p["before"], after_qa_pass_count=p["after"],
                       context_priority="Two-window Landsat context available" if min(p["before"], p["after"]) > 0
                       else "Search alternative context",
                       high_resolution_availability="Unknown; external archive search required"))
output.sort(key=lambda r: (-min(r["before_qa_pass_count"], r["after_qa_pass_count"]), r["review_id"]))
with (dest / "internal_acquisition_queue.csv").open("x", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=output[0].keys())
    writer.writeheader()
    writer.writerows(output)
print(json.dumps(dict(points=len(output), both=sum(min(r["before_qa_pass_count"],
      r["after_qa_pass_count"]) > 0 for r in output))))
