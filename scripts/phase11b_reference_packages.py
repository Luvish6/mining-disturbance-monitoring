"""Build local acquisition packets from saved Meghalaya evidence."""
import argparse
import csv
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, mapping
from shapely import transform

from config.settings import AFTER, BEFORE
from src.phase3.spatial import block_for, partition

WINDOWS = (BEFORE, AFTER)
FORM = """# Independent interpretation worksheet

Neutral review ID:
Evidence sources and exact item IDs:
Actual before / after acquisition UTC:
Same-area coverage, clouds, haze, shadows and visibility:
Usage rights and documentation:
CRS, independent controls, positional error (m) and method:

## First reviewer
Identifier / date:
Before interpretation:
After interpretation:
Observed change or stability, attribution and alternative explanations:
Mapped conservative interior and confidence:
Decision (pending until completed):

## Independent second reviewer
Distinct identifier / date:
Independent before / after interpretation and confidence:
Agreement, disagreement or insufficient evidence:
Decision (pending until completed):

Record any adjudication in the annotation ledger. This form does not admit labels.
"""


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def candidate(point, claimed_block, claimed_split, geometry=None):
    project = Transformer.from_crs(4326, 32646, always_xy=True).transform
    reverse = Transformer.from_crs(32646, 4326, always_xy=True).transform
    x, y = project(*point)
    anchor = block_for((x - .01, y - .01, x + .01, y + .01))
    if anchor != claimed_block or partition(anchor) != claimed_split:
        raise ValueError("Candidate anchor disagrees with the frozen partition")
    if geometry is None:
        geometry = mapping(transform(Point(x, y).buffer(300), reverse, interleaved=False))
        kind = "300 m imagery search area"
    else:
        kind = "Published application polygon"
    return dict(anchor=point, block=anchor, split=claimed_split, geometry=geometry,
                geometry_kind=kind, status="UNKNOWN",
                windows=[dict(start=s.start, end_exclusive=s.end) for s in WINDOWS])


def gather(outputs):
    discovery = outputs / "phase3e_candidate_discovery"
    readiness = {r["review_id"]: r for r in read(outputs / "phase6d_reference_readiness/candidate_readiness.json")}
    keys = {r["point_id"]: r["review_id"] for r in rows(discovery / "internal_review_key.csv")}
    queue = {r["review_id"]: r for r in rows(discovery / "internal_acquisition_queue.csv")}
    packets = {}
    for role in ("change", "background", "alternative_disturbance"):
        for r in rows(discovery / f"internal_{role}_leads.csv"):
            if r["partition"] != "train":
                continue
            key = keys[r["point_id"]]
            p = candidate([float(r["longitude"]), float(r["latitude"])], r["block"], "train")
            packets[key] = dict(**p, purpose=role, wayback_point_metadata=readiness[key]["wayback"],
                                landsat_qa_context={k: queue[key][k] for k in ("before_qa_pass_count", "after_qa_pass_count")},
                                source_ids_note="No site-specific Planet item verified. Wayback point hits require footprint, visibility and rights checks.")

    component, = [r for r in rows(outputs / "phase7_day2_spatial_patterns/examples.csv")
                  if r["tile"] == "east-94-559" and r["persistence"] == "persistent"]
    point = list(Transformer.from_crs(32646, 4326, always_xy=True).transform(
        float(component["centroid_easting_m"]), float(component["centroid_northing_m"])))
    tile = outputs / "phase6b_multitile/east-94-559"
    packets["east-94-559-c74"] = dict(
        **candidate(point, component["block"], "train"), purpose="change",
        source_receipt="phase6b_multitile/east-94-559/sources.json",
        context_preview="phase6b_multitile/east-94-559/exploratory.png",
        imagery_context=read(tile / "sources.json"),
        landsat_context=read(outputs / "phase6d_reference_readiness/landsat_east-94-559.json"),
        quality="Component touches the sampled tile edge. Inspect beyond that edge. Change features are coordinator-only.")

    phase3c = outputs / "phase3c_20261108_01"
    previews = read(phase3c / "preview_records.json")
    planet = read(outputs / "phase7_planet_third_before/inspection.json")
    for item in read(phase3c / "PHASE3C_VERIFIED_MINING_CANDIDATES.geojson")["features"]:
        props = item["properties"]
        key = props["candidate_id"]
        p = candidate(props["map_anchor"], props["anchor_block_id"], props["anchor_partition"], item["geometry"])
        records = [dict(r, file="phase3c_20261108_01/" + r["file"]) for r in previews
                   if r["candidate_id"] == key and (phase3c / r["file"]).is_file()]
        packet = dict(**p, purpose="existing mining-location lead", provenance=props,
                      contextual_images=records, quality="Application and pipeline imagery supply location and context. Activity attribution and independent review remain unresolved.")
        if key.startswith(("korpet", "sumon")):
            packet["resourcesat"] = dict(
                acquisitions=["2024-03-17", "2024-11-12"],
                ots_product_ids=["RAF17MAR2024037752011100054SSANSTUC00GTDA",
                                 "RAF12NOV2024041162011100054SSANSTUC00GTDA"],
                quality="Shared imagery context, possible March haze and November shadow, independent position unverified.",
                preview=f"phase3c_bhoonidhi_pair_review_17mar2024_12nov2024/{key}/detail_1_5km.png")
        if key.startswith("korpet"):
            packet["planet"] = dict(
                scenes=[{k: s[k] for k in ("id", "acquired", "clear", "roi_cells")} for s in planet["scenes"]],
                preview="phase7_korpet_detailed_review/rgb_comparison.png",
                quality="Inconclusive change. Confirm reviewer-use rights and independent positional control.")
        if key.startswith("lumshnong"):
            packet["ibm"] = "38MEG03016, inspections 2023-11-16/17 and 2025-01-22. Request comparable dated actual-work plans; Resourcesat pair lacks site signal."
        packets[key] = packet
    return packets


def make_packets(outputs, destination):
    packet_map = gather(outputs)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "reviewer-form.md").write_text(FORM, encoding="utf-8")
    checklist = ["# Coordinator checklist", "",
                 "Search Planet Explorer by longitude, latitude. Before: 2023-11-01 to 2024-03-31. After: 2024-11-01 to 2025-03-31.",
                 "Use single dated scenes that cover the same interior, check visibility, and record exact item IDs and timestamps. If licensed access permits, retain native SR, UDM2 and metadata locally.",
                 "Record usage rights and independent positional error ≤30 m. Give reviewers neutral IDs and admissible evidence only. Keep these coordinator packets, split IDs and change previews internal.", "",
                 "No saved Planet Explorer inspection receipt identifies the two priority training visits. The first two entries use the leading Phase 9D coordinates; confirm your inspected points before acquisition.", ""]
    priority = ["east-94-559-c74", "R007", next(key for key, p in packet_map.items()
                                             if p["purpose"] == "background" and p["block"] == "84:568")]
    for key in dict.fromkeys(priority + list(packet_map)):
        packet = packet_map[key]
        packet["missing_evidence"] = ["Independently interpretable same interior in both windows",
                                      "Documented usage rights and independent positional error ≤30 m",
                                      "Conservative interpreted polygon and two independent reviews"]
        (destination / f"{key}.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
        lon, lat = packet["anchor"]
        checklist.append(f"- {key} ({packet['purpose']}, {packet['split']}): {lon:.8f}, {lat:.8f}. See {key}.json for known imagery and gaps.")
    (destination / "manual-checklist.md").write_text("\n".join(checklist) + "\n", encoding="utf-8")
    return len(packet_map)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    outputs = Path("outputs")
    print(make_packets(outputs, outputs / "phase11b_reference_packages"))
