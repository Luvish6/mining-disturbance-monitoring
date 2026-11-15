"""Build local screening context and independent annotation templates."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3

import numpy as np
from pyproj import CRS
import rasterio
from shapely.geometry import shape

from config.settings import BEFORE, AFTER
from scripts.phase11b_reference_packages import FORM
from src.phase3.admission import validate_references
from src.phase3.annotation import sha
from src.phase3.data import digest

SITES = ("gevra", "bhubaneswari")
LAYERS = ("potential_mining_change", "potential_unchanged_mine", "potential_non_mining")
MASKS = ("sar_before_valid", "sar_after_valid", "optical_before_valid", "optical_after_valid", "common_valid")


def schema(path):
    """Empty WGS84 polygon layers with typed fields recognized by QGIS/GDAL."""
    with sqlite3.connect(path) as db:
        db.executescript("""
            PRAGMA application_id = 1196444487;
            PRAGMA user_version = 10300;
            CREATE TABLE gpkg_spatial_ref_sys (
                srs_name TEXT NOT NULL, srs_id INTEGER PRIMARY KEY, organization TEXT NOT NULL,
                organization_coordsys_id INTEGER NOT NULL, definition TEXT NOT NULL, description TEXT);
            CREATE TABLE gpkg_contents (
                table_name TEXT PRIMARY KEY, data_type TEXT NOT NULL, identifier TEXT UNIQUE,
                description TEXT DEFAULT '', last_change DATETIME NOT NULL DEFAULT
                (strftime('%Y-%m-%dT%H:%M:%fZ','now')), min_x DOUBLE, min_y DOUBLE,
                max_x DOUBLE, max_y DOUBLE, srs_id INTEGER REFERENCES gpkg_spatial_ref_sys(srs_id));
            CREATE TABLE gpkg_geometry_columns (
                table_name TEXT NOT NULL PRIMARY KEY REFERENCES gpkg_contents(table_name),
                column_name TEXT NOT NULL, geometry_type_name TEXT NOT NULL,
                srs_id INTEGER NOT NULL REFERENCES gpkg_spatial_ref_sys(srs_id),
                z TINYINT NOT NULL, m TINYINT NOT NULL);
        """)
        db.executemany("INSERT INTO gpkg_spatial_ref_sys VALUES (?,?,?,?,?,?)", [
            ("Undefined Cartesian", -1, "NONE", -1, "undefined", ""),
            ("Undefined Geographic", 0, "NONE", 0, "undefined", ""),
            ("WGS 84", 4326, "EPSG", 4326, CRS.from_epsg(4326).to_wkt("WKT1_GDAL"), ""),
        ])
        for name in LAYERS:
            db.execute(f"""CREATE TABLE {name} (
                fid INTEGER PRIMARY KEY AUTOINCREMENT, geom POLYGON,
                review_id TEXT, evidence_id TEXT, notes TEXT,
                status TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(status = 'UNKNOWN'))""")
            db.execute("INSERT INTO gpkg_contents(table_name,data_type,identifier,srs_id) VALUES (?,?,?,4326)",
                       (name, "features", name))
            db.execute("INSERT INTO gpkg_geometry_columns VALUES (?, 'geom', 'POLYGON', 4326, 0, 0)", (name,))


def preflight(document, model_scene_ids):
    """Check review declarations. Only the authoritative ledger can admit labels."""
    issues = []
    try:
        polygon = shape(document["geometry"])
        if (document["crs"] != "EPSG:4326" or polygon.geom_type != "Polygon" or not polygon.is_valid
                or polygon.is_empty or not (-180 <= polygon.bounds[0] < polygon.bounds[2] <= 180
                                           and -90 <= polygon.bounds[1] < polygon.bounds[3] <= 90)):
            raise ValueError("Valid WGS84 polygon required")
        evidence = [document[key] for key in ("before", "after")]
        reviewers = document["reviews"]
        decision = document["decision"]
        review_hash = sha({key: document[key] for key in ("geometry", "before", "after", "decision", "reference_properties")})
        if (decision not in LAYERS or len(reviewers) != 2
                or len({review["reviewer"].strip().casefold() for review in reviewers}) != 2
                or any(not review["reviewer"].strip() or review["attests_independent"] is not True
                       or review["decision"] != decision or review.get("packet_sha256") != review_hash
                       for review in reviewers)):
            issues.append("Two distinct independent reviewers must agree on the same polygon/evidence hash")
        props = dict(document["reference_properties"])
        for item, season, side in zip(evidence, (BEFORE, AFTER), ("before", "after"), strict=True):
            observed = date.fromisoformat(item["date"]).isoformat()
            footprint = shape(item["valid_footprint"])
            if not season.start <= observed < season.end:
                issues.append(f"{side}: evidence outside frozen window")
            if (item["crs"] != "EPSG:4326" or not footprint.is_valid or not footprint.covers(polygon)
                    or item.get("coverage_verified") is not True):
                issues.append(f"{side}: independently verified valid coverage required")
            if item.get("reuse_permitted") is not True or not item.get("rights_reference"):
                issues.append(f"{side}: documented reviewer and research rights required")
            if (not item["id"].strip() or item["id"] in model_scene_ids
                    or item.get("independence_verified") is not True):
                issues.append(f"{side}: missing independent source or shared model-input scene")
            props[f"{side}_evidence_date"] = observed
        props.update(reviewer=reviewers[0]["reviewer"], second_reviewer=reviewers[1]["reviewer"])
        validate_references([props])
        if not props.get("evidence_group_id") or not props.get("positional_evidence_reference"):
            issues.append("Evidence group and independent positional-control source required")
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        issues.append(f"Incomplete or invalid evidence: {exc}")
    # Neither site has an admitted regional boundary, buffered block design, or split ledger.
    issues.append("Regional spatial-block separation and registration are not established")
    return dict(status="UNKNOWN", issues=issues)


def raster_context(source, destination, expected):
    with rasterio.open(source) as src:
        if (str(src.crs) != expected["grid_crs"] or tuple(src.bounds) != tuple(expected["bounds"])
                or src.res != (30, 30) or src.transform.e != -30 or src.transform.b or src.transform.d
                or src.nodata != -9999):
            raise ValueError("Cached raster does not match the documented grid")
        bands = src.descriptions
        profile = src.profile
        masks = src.read([bands.index(key)+1 for key in MASKS])
        if (not np.isin(masks, (0, 1)).all()
                or not np.array_equal(masks[-1] == 1, (masks[:4] == 1).all(0))
                or int(masks[-1].sum()) != expected["common"]):
            raise ValueError("Cached observation masks disagree")
        for season, valid in zip(("before", "after"), masks[2:4], strict=True):
            names = tuple(f"{band}_{season}" for band in ("B8", "B4", "B3"))
            rgb = src.read([bands.index(name)+1 for name in names])
            if np.any((valid == 1) & ~np.all(np.isfinite(rgb) & (rgb != src.nodata), axis=0)):
                raise ValueError("Nonfinite or missing screened optical pixels")
            rgb[:, valid != 1] = src.nodata
            with rasterio.open(destination / f"{season}_false_colour.tif", "w", **dict(profile, count=3)) as dst:
                dst.write(rgb)
                dst.descriptions = names
                dst.update_tags(role="Model-input composite: coordinator only")
        with rasterio.open(destination/"valid_masks.tif", "w", **dict(profile, count=len(MASKS))) as dst:
            dst.write(masks)
            dst.descriptions = MASKS
    return [int(layer.sum()) for layer in masks]


def build(inventory, output):
    items = {item["id"]: item for item in json.loads(inventory.read_bytes())}
    output.mkdir()
    for site in SITES:
        item = items[site]
        observed = item["screen"]
        root = output/site
        coordinator, independent = root/"coordinator", root/"independent_review"
        coordinator.mkdir(parents=True)
        independent.mkdir()
        tile = inventory.parent/site/"tile.tif"
        support = raster_context(tile, coordinator, observed)
        scenes = {}
        for season, record in zip(("before", "after"), observed["sources"], strict=True):
            scenes[season] = {
                sensor: [dict(id=key, acquired_utc=datetime.fromtimestamp(ms/1000, timezone.utc).isoformat())
                         for key, ms in zip(record[sensor+"_ids"], record[sensor+"_time_start_ms"], strict=True)]
                for sensor in ("s1", "s2")
            }
        metadata = dict(site=site, status="UNKNOWN", source=item["source"], anchor=item["anchor"],
                        crs=observed["grid_crs"], bounds=observed["bounds"],
                        windows=[[BEFORE.start, BEFORE.end], [AFTER.start, AFTER.end]],
                        scenes=scenes, mask_counts=dict(zip(MASKS, support, strict=True)),
                        grid_cells=observed["denominator"], processing=observed["config"],
                        cloud_note="Saved scene and cloud probability thresholds apply. No per-scene cloud percentages are recorded.",
                        inventory_sha256=digest(inventory), tile_sha256=digest(tile))
        (coordinator/"provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        schema(root/"candidate_templates.gpkg")
        for index in (1, 2):
            (independent/f"reviewer_{index}.md").write_text(
                FORM.split("## First reviewer")[0] +
                "Identifier / date:\nIndependent review attestation:\nMapped polygon ID:\n"
                "Observations, interpretation and confidence:\n"
                "Decision: MINING_CHANGE / UNCHANGED_MINE / NON_MINING / UNKNOWN / REJECT\n"
                "Decision recorded: PENDING\n",
                encoding="utf-8")
        (independent/"STATUS.md").write_text(
            "UNKNOWN. No eligible independent before/after imagery or survey pair supplied. "
            "Only add independently sourced evidence with documented reviewer rights. "
            "Keep coordinator imagery and candidate strata out of blinded interpretation.\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check-evidence", type=Path)
    parser.add_argument("--site", choices=SITES)
    args = parser.parse_args()
    if args.check_evidence:
        if not args.site:
            parser.error("--check-evidence requires --site")
        provenance = json.loads((args.output/args.site/"coordinator/provenance.json").read_bytes())
        ids = {item["id"] for season in provenance["scenes"].values() for source in season.values() for item in source}
        result = preflight(json.loads(args.check_evidence.read_bytes()), ids)
        print(json.dumps(result, indent=2))
        return
    build(args.inventory, args.output)


if __name__ == "__main__":
    main()
