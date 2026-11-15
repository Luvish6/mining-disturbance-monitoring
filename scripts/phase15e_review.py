"""Prepare blinded review windows from existing Gevra screening results."""
import argparse
import json
from pathlib import Path

from pyproj import Transformer
from shapely import transform
from shapely.geometry import box, mapping, shape

from scripts.phase11b_reference_packages import FORM
from src.phase3.annotation import collection
from src.phase3.data import digest


def windows(features):
    to_grid = Transformer.from_crs(4326, 32644, always_xy=True).transform
    to_wgs = Transformer.from_crs(32644, 4326, always_xy=True).transform
    review, key = [], {}
    for i, feature in enumerate(sorted(features, key=lambda f: f["id"]), 1):
        p = feature["properties"]
        if (p["region_id"], p["status"], p["evidence_status"], p["data_kind"],
            p["eligible_observation_count"]) != ("gevra", "REVIEW_REQUIRED", "UNKNOWN", "exploratory", 0):
            raise ValueError("Expected a review-only Gevra lead")
        area = transform(shape(feature["geometry"]), to_grid, interleaved=False)
        if area.geom_type != "Polygon" or area.is_empty or not area.is_valid:
            raise ValueError("Invalid candidate polygon")
        locator = box(*area.bounds).buffer(150, cap_style="square", join_style="mitre").envelope
        review_id = f"G{i:02d}"
        review.append(dict(type="Feature", geometry=mapping(transform(locator, to_wgs, interleaved=False)),
                           properties=dict(review_id=review_id)))
        key[review_id] = feature["id"]
    return collection(review), key


def build(source, output):
    data = json.loads(source.read_bytes())
    review, key = windows(data["features"])
    output.mkdir()
    for index in (1, 2):
        folder = output / f"reviewer_{index}"
        folder.mkdir()
        (folder/"search_windows.geojson").write_text(json.dumps(review), encoding="utf-8")
        (folder/"worksheet.md").write_text(
            FORM.split("## First reviewer")[0]
            + "Reviewer identifier / date:\nObserved change or stability and alternative explanations:\n"
              "Decision: MINING_CHANGE / UNCHANGED_MINE / NON_MINING / UNKNOWN / REJECT\n"
              "Decision recorded: PENDING\n",
            encoding="utf-8")
        (folder/"README.md").write_text(
            "Open the WGS84 search windows in QGIS with independently dated and licensed evidence only. "
            "Inspect each entire window. Map conservative interpreted interiors in a separate layer. "
            "Use 2023-11-01 through 2024-03-31 and 2024-11-01 through 2025-03-31. "
            "Leave decisions UNKNOWN if coverage, quality or attribution is insufficient. "
            "Independent imagery or actual-work maps are still pending.\n", encoding="utf-8")
    (output/"coordinator_key.json").write_text(
        json.dumps(dict(review_to_phase15c_id=key, source_sha256=digest(source),
                        status="REVIEW_REQUIRED", evidence_status="UNKNOWN"), indent=2), encoding="utf-8")
    return len(key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    print(build(**vars(parser.parse_args())))
