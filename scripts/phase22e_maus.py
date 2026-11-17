"""Plan and materialize the preregistered Phase 22E optical weak-label patches."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3

from affine import Affine
import ee
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.features import rasterize
from shapely import from_wkb, transform
from shapely.geometry import Point, box, mapping, shape
from shapely.strtree import STRtree

from config.phase2_settings import Phase2Config
from scripts.phase22b_maus import ADM, BUFFER, MAUS, MAUS_SHA, ROOT, TO_METRES, digest, fetch
from scripts.phase22b_maus import source_geometries, stable, write_json
from scripts.phase22c_maus import NODATA, OPTICAL, check_geographic_buffer, check_seal, optical_graph, verify_split
from src.gee_setup import initialize

DEST = Path("outputs/phase22e_maus")
SIZE = 128
BANDS = OPTICAL + ("optical_count",)
STRATA = ("bare_soil", "sand_riverbed", "built_up", "exposed_rock")
MAX_TIFF = 2 * 1024**2
PROTO = Path("docs/preregistration-phase22e-v1.md")
DIRECTIONS = np.arange(8) * np.pi / 4


def reproject(geom, start, end):
    return transform(geom, Transformer.from_crs(start, end, always_xy=True).transform,
                     interleaved=False)


def bounds_row(point, crs):
    position = reproject(point, 4326, crs)
    left = round(position.x / 10) * 10 - 640
    top = round(position.y / 10) * 10 + 640
    return [left, top-1280, left+1280, top], [10, 0, left, 0, -10, top]


def label_mask(geometries, affine, valid, background=False):
    mask = np.full(valid.shape, 255, dtype="uint8")
    if background:
        mask[valid] = 0
    elif geometries:
        present = rasterize([(g, 1) for g in geometries], out_shape=valid.shape,
                            transform=Affine(*affine), all_touched=False)
        mask[valid & (present == 1)] = 1
    return mask


def score(values, stratum):
    g, r, n = values
    if not np.isfinite(values).all() or n+r == 0:
        return None
    ndvi = (n-r)/(n+r)
    return {"bare_soil": r-abs(ndvi), "sand_riverbed": (g+r)/2-n,
            "built_up": r+g-n, "exposed_rock": (g+r+n)/3-abs(g-r)-abs(ndvi)}[stratum]


def exclusion_sources():
    base = Path("outputs")
    inputs = [base / "phase11c_india_discovery/inventory.json"]
    inputs += sorted((base / "phase11b_reference_packages").glob("*.json"))
    inputs += [base / f"phase15c_{key}/candidates/alerts.geojson" for key in ("gevra", "bhubaneswari")]
    inputs += [base / f"phase15b_annotation/{key}/candidate_templates.gpkg" for key in ("gevra", "bhubaneswari")]
    if len(inputs) <= 5:
        raise ValueError("Missing project candidate exclusion sources")
    geometries, receipts = [], {}
    for path in inputs:
        payload = path.read_bytes()
        receipts[path.name if path.suffix == ".json" else str(path.relative_to(base))] = digest(payload)
        if path.suffix == ".gpkg":
            with sqlite3.connect(":memory:") as db:
                db.deserialize(payload)
                for table, field, crs in db.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns"):
                    if table not in {"potential_mining_change", "potential_unchanged_mine"}:
                        continue
                    if crs != 4326:
                        raise ValueError("Unexpected candidate geometry CRS")
                    for (blob,) in db.execute(f'SELECT "{field}" FROM "{table}"'):
                        if blob:
                            envelope = (blob[3] >> 1) & 7
                            geometries.append(from_wkb(blob[8 + 8 * (0, 4, 6, 6, 8)[envelope]:]))
        else:
            data = json.loads(payload)
            rows = data if isinstance(data, list) else data.get("features", [data])
            for row in rows:
                if row.get("published_bounds"):
                    geometries.append(box(*row["published_bounds"]))
                geom = row.get("geometry") or row.get("polygon")
                if geom:
                    geometries.append(shape(geom))
    if any(g.is_empty or not g.is_valid for g in geometries):
        raise ValueError("Malformed project candidate exclusion")
    return [transform(g, TO_METRES, interleaved=False) for g in geometries], receipts


def source_context(root):
    original = (root / "split.json").read_bytes()
    verify_split(original, original)
    split = json.loads(original)
    sites = json.loads((root / "development.json").read_bytes())
    if sites["split_sha256"] != digest(original):
        raise ValueError("Development roster hash mismatch")
    check_seal(split["groups"], json.loads((root / "sealed_test.json").read_bytes()), sites["sites"])
    maus = source_geometries(fetch(MAUS, 26 * 1024**2))
    admin = fetch(ADM, 8 * 1024**2)
    if digest(admin) != split["boundary_sha256"]:
        raise ValueError("Frozen boundary source hash mismatch")
    states = {f["properties"]["shapeName"]: transform(shape(f["geometry"]), TO_METRES, interleaved=False)
              for f in json.loads(admin)["features"]}
    geometry = {k: transform(g, TO_METRES, interleaved=False) for k, g in maus.items()}
    check_geographic_buffer(geometry, split["groups"])
    return original, split, sites["sites"], maus, geometry, states


def safe_window(window, state, opposing, exclusions, occupied, background):
    return (state.covers(window.buffer(BUFFER))
            and not len(opposing.query(window, predicate="dwithin", distance=BUFFER))
            and not any(window.intersects(other) for other in occupied)
            and (not background or not len(exclusions.query(window, predicate="intersects"))))


def hard_scores(candidates, crs, stratum):
    points = [ee.Feature(ee.Geometry.Point(row["center"], "EPSG:4326"), {"index": i})
              for i, row in enumerate(candidates)]
    fc = ee.FeatureCollection(points)
    graph, count, _ = optical_graph(fc.geometry().bounds(1), Phase2Config(analysis_crs=f"EPSG:{crs}"))
    values = graph.addBands(count).reduceRegions(collection=fc, reducer=ee.Reducer.first(),
                                                scale=10, crs=f"EPSG:{crs}").getInfo()
    ranked = []
    for feature in values["features"]:
        props = feature["properties"]
        if all(props.get(band) is not None for band in OPTICAL):
            value = score([props[b] for b in OPTICAL], stratum)
            if value is not None:
                row = candidates[int(props["index"])]
                ranked.append((-value, stable(row["patch_id"]), row))
    return sorted(ranked, key=lambda item: item[:2])


def plan(root=ROOT, dest=DEST):
    original, split, sites, maus, geometry, states = source_context(root)
    project, excluded_sources = exclusion_sources()
    exclusions = STRtree(list(geometry.values()) + project)
    roles = {fid: row["split"] for row in split["groups"].values() for fid in row["ids"]}
    opposing = {role: STRtree([g for fid, g in geometry.items() if roles[fid] != role])
                for role in ("train", "validation")}
    chosen, occupied, missing = [], [], []
    initialize()
    for role, cap in (("train", 10), ("validation", 5)):
        anchors = [s for s in sites if s["split"] == role][:cap]
        for index, site in enumerate(anchors):
            crs = site["crs"]
            group = split["groups"][site["group"]]
            anchor = Point(site["longitude"], site["latitude"])
            origin = reproject(anchor, 4326, crs)
            state = states[site["state"]]

            def make(point, suffix):
                bounds, affine = bounds_row(point, crs)
                window = reproject(box(*bounds), crs, 7755)
                return dict(patch_id=f"{site['group']}-{suffix}", center=[point.x, point.y],
                            bounds=bounds, affine=affine, crs=crs, group_id=site["group"],
                            state=site["state"], split=role, geometry=mapping(reproject(box(*bounds), crs, 4326))), window

            positive, window = make(anchor, "pos")
            if not safe_window(window, state, opposing[role], exclusions, occupied, False):
                missing.append(dict(group=site["group"], split=role, slot="positive", reason="geometry"))
                continue
            positive.update(weak_label_type="WEAK_UNVERIFIED_POSITIVE", negative_stratum=None,
                            label_source_fids=[fid for fid in group["ids"] if window.intersects(geometry[fid])])
            chosen.append(positive)
            occupied.append(window)

            ring = []
            for radius in (3000, 4500, 6000):
                for bearing, angle in enumerate(DIRECTIONS):
                    center = Point(origin.x + radius*np.cos(angle), origin.y + radius*np.sin(angle))
                    row, window = make(reproject(center, crs, 4326), f"{radius}-{bearing}")
                    if safe_window(window, state, opposing[role], exclusions, occupied, True):
                        ring.append((row, window))
            ring.sort(key=lambda item: stable(item[0]["patch_id"]))
            ranked = []
            if ring:
                random, window = ring[0]
                random.update(weak_label_type="WEAK_UNVERIFIED_BACKGROUND", negative_stratum="random",
                              label_source_fids=[])
                chosen.append(random)
                occupied.append(window)
                pool = [row for row, g in ring[1:] if not g.intersects(window)]
                if pool:
                    ranked = hard_scores(pool, crs, STRATA[index % len(STRATA)])
            if not ring:
                missing.append(dict(group=site["group"], split=role, slot="random", reason="geometry"))
            if not ranked:
                missing.append(dict(group=site["group"], split=role, slot="hard", reason="geometry_or_proxy"))
                continue
            hard = ranked[0][2]
            hard.update(weak_label_type="WEAK_UNVERIFIED_BACKGROUND", negative_stratum=STRATA[index % len(STRATA)],
                        optical_proxy_score=-ranked[0][0], label_source_fids=[])
            chosen.append(hard)
            occupied.append(reproject(box(*hard["bounds"]), crs, 7755))
    estimate = len(chosen) * MAX_TIFF
    if len(chosen) > 45 or estimate > 500_000_000:
        raise ValueError("Export exceeds preregistered sample or transfer ceiling")
    if any(safe_window(g, states[r["state"]], opposing[r["split"]], exclusions,
                       occupied[:i]+occupied[i+1:], not r["label_source_fids"]) is False
           for i, (r, g) in enumerate(zip(chosen, occupied, strict=True))):
        raise ValueError("Frozen plan contains overlapping or unsafe windows")
    verify_split(original, (root / "split.json").read_bytes())
    dest.mkdir(parents=True, exist_ok=True)
    context = dict(split_sha_before=digest(original), split_sha_after=digest((root/"split.json").read_bytes()),
                   maus_sha256=MAUS_SHA, protocol_sha256=digest(PROTO.read_bytes()),
                   adm_sha256=split["boundary_sha256"], project_exclusions=excluded_sources,
                   test_sealed=True, max_download_bytes=estimate, planned_work_units=len(chosen),
                   patch_counts_by_split=dict(Counter(r["split"] for r in chosen)),
                   patch_counts_by_split_and_state=dict(Counter(f"{r['split']}:{r['state']}" for r in chosen)),
                   patch_counts_by_group=dict(Counter(r["group_id"] for r in chosen)),
                   missing_slots=missing, patches=chosen)
    print("Export plan", json.dumps({k: v for k, v in context.items() if k.startswith(("patch_counts", "max_download"))}), flush=True)
    write_json(dest / "plan.json", context)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=("plan", "export", "debug"))
    args = cli.parse_args()
    if args.action == "plan":
        plan()
    else:
        from scripts.phase22e_maus_export import debug, export_all
        (export_all if args.action == "export" else debug)(ROOT, DEST)
