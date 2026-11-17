"""Freeze the separate Phase 22B spatial pilot and prepare blinded review sheets."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata
from urllib.request import urlopen

import numpy as np
from pyproj import Transformer
from shapely import from_wkb, transform
from shapely.geometry import box, mapping, shape
from shapely.strtree import STRtree

ROOT = Path("outputs/phase22b_maus_frozen")
MAUS = "https://download.pangaea.de/dataset/942325/files/global_mining_polygons_v2.gpkg"
ADM = ("https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/"
       "gbOpen/IND/ADM1/geoBoundaries-IND-ADM1_simplified.geojson")
MAUS_SHA = "6936e2743a21ba952b4de3e4b6f77099a0aa4479f7e2639d9d1b0787876a3ea1"
TO_METRES = Transformer.from_crs(4326, 7755, always_xy=True).transform
BUFFER = 2050
SIZE = 64
BANDS = ("B3", "B4", "B8", "VV", "VH", "optical_count", "sar_count")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stable(value):
    return digest(f"42:{value}".encode())


def fetch(url, cap):
    with urlopen(url, timeout=60) as response:
        payload = response.read(cap + 1)
    if len(payload) > cap:
        raise ValueError("Download exceeded the Phase 22B byte cap")
    return payload


def groups(geometries, distance=BUFFER):
    """Single-linkage geographic clusters, including touches and overlaps."""
    ids = sorted(geometries)
    geoms = [geometries[key] for key in ids]
    tree = STRtree(geoms)
    pending = set(range(len(ids)))
    for i in range(len(ids)):
        if i not in pending:
            continue
        pending.remove(i)
        component = [i]
        for current in component:
            geometry = geoms[current]
            w, s, e, n = geometry.bounds
            neighbors = tree.query(box(w-distance, s-distance, e+distance, n+distance))
            for j in sorted(pending.intersection(neighbors)):
                if geometry.distance(geoms[j]) <= distance:
                    pending.remove(j)
                    component.append(j)
        yield sorted(ids[j] for j in component)


def partition(state_set):
    if len(state_set) != 1:
        return "excluded"
    state = unicodedata.normalize("NFKD", next(iter(state_set))).encode("ascii", "ignore").decode()
    return {"Odisha": "validation", "Jharkhand": "test"}.get(state, "train")


def grid(lon, lat):
    crs = 32601 + int((lon + 180) // 6)
    project = Transformer.from_crs(4326, crs, always_xy=True)
    x, y = project.transform(lon, lat)
    left, top = round(x / 30) * 30 - 960, round(y / 30) * 30 + 960
    return crs, [30, 0, left, 0, -30, top], [left, top-1920, left+1920, top]


def clear_window(bounds, crs, own_group, owners, geometry):
    local_to_metres = Transformer.from_crs(crs, 7755, always_xy=True).transform
    window = transform(box(*bounds), local_to_metres, interleaved=False)
    return all(window.distance(poly) > BUFFER for key, poly in geometry.items()
               if owners[key] != own_group)


def train_normalization(samples):
    """Fit from role-tagged, common-valid TRAIN cells; reject other roles."""
    values = []
    for split, features, valid in samples:
        features, valid = np.asarray(features), np.asarray(valid)
        if (split != "train" or valid.dtype != np.bool_
                or features.ndim != 3 or features.shape[1:] != valid.shape):
            raise ValueError("Expected aligned TRAIN-only features and boolean masks")
        cells = features[:, valid]
        if not np.isfinite(cells).all():
            raise ValueError("Nonfinite values on common-valid TRAIN support")
        values.append(cells)
    if not values or not any(value.size for value in values):
        raise ValueError("No valid TRAIN cells")
    cells = np.concatenate(values, axis=1).astype("float64")
    scale = cells.std(axis=1)
    return cells.mean(axis=1), np.where(scale == 0, 1, scale)


def write_json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return digest(path.read_bytes())


def source_geometries(data):
    if digest(data) != MAUS_SHA:
        raise ValueError("Maus v2 source hash mismatch")
    with sqlite3.connect(":memory:") as db:
        db.deserialize(data)
        schema = db.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns")
        if schema.fetchall() != [("mining_polygons", "geom", 4326)]:
            raise ValueError("Unexpected GeoPackage geometry schema")
        rows = db.execute("SELECT FID,geom FROM mining_polygons WHERE ISO3_CODE='IND'")
        result = {}
        for fid, blob in rows:
            envelope = (blob[3] >> 1) & 7
            geom = from_wkb(blob[8 + 8 * (0, 4, 6, 6, 8)[envelope]:])
            if not geom.is_valid or geom.is_empty or geom.geom_type not in {"Polygon", "MultiPolygon"}:
                raise ValueError("Invalid Maus candidate geometry")
            result[fid] = geom
    if len(result) != 1204:
        raise ValueError("Unexpected India candidate count")
    return result


def freeze(root, data, boundary):
    candidates = source_geometries(data)
    regions = [(f["properties"]["shapeName"], shape(f["geometry"]))
               for f in json.loads(boundary)["features"]]
    geometry = {key: transform(poly, TO_METRES, interleaved=False) for key, poly in candidates.items()}
    roster, owners = {}, {}
    for members in groups(geometry):
        states = {state for state, region in regions
                  if any(region.intersects(candidates[key]) for key in members)}
        group_id = stable(",".join(map(str, members)))[:16]
        roster[group_id] = dict(split=partition(states), states=sorted(states), ids=members)
        owners.update(dict.fromkeys(members, group_id))

    if not {"train", "validation", "test"} <= {row["split"] for row in roster.values()}:
        raise ValueError("Geographic roster lacks a required partition")

    development = []
    for split, target in (("train", 16), ("validation", 8)):
        by_state = {}
        for group_id, record in sorted(roster.items(), key=lambda item: stable(item[0])):
            if record["split"] != split:
                continue
            for fid in sorted(record["ids"], key=stable):
                point = candidates[fid].representative_point()
                crs, affine, bounds = grid(point.x, point.y)
                if clear_window(bounds, crs, group_id, owners, geometry):
                    site = dict(split=split, group=group_id, fid=fid, longitude=point.x,
                                latitude=point.y, crs=crs, affine=affine, bounds=bounds)
                    by_state.setdefault(record["states"][0], []).append(site)
                    break
        for i in range(max(map(len, by_state.values()), default=0)):
            for state in sorted(by_state, key=stable):
                if target and i < len(by_state[state]):
                    development.append(dict(by_state[state][i], state=state))
                    target -= 1

    root.mkdir(parents=True, exist_ok=False)
    split_sha = write_json(root / "split.json", dict(maus_sha256=MAUS_SHA,
                          boundary_sha256=digest(boundary), metric_crs=7755,
                          buffer_metres=BUFFER, groups=roster))
    write_json(root / "sealed_test.json", dict(split_sha256=split_sha, sealed=True,
               groups={key: item["ids"] for key, item in roster.items() if item["split"] == "test"}))
    write_json(root / "development.json", dict(split_sha256=split_sha, sites=development))
    overlays = [dict(type="Feature", geometry=mapping(candidates[item["fid"]]),
                     properties=dict(fid=item["fid"], group=item["group"],
                                     status="UNREVIEWED_LOCATOR")) for item in development]
    write_json(root / "development_overlay.geojson", dict(type="FeatureCollection", features=overlays))
    with (root / "review.csv").open("x", newline="", encoding="utf-8") as stream:
        fields = ["fid", "longitude", "latitude", "polygon_overlay", "review_scope",
                  "independent_image_id", "capture_date", "position_error_m", "rights",
                  "reviewer_one", "reviewer_two", "adjudication"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for site in development:
            for scope in ("mining interior", "boundary", "hard-negative search"):
                writer.writerow({key: site[key] for key in fields[:3]} |
                                dict(polygon_overlay="development_overlay.geojson", review_scope=scope))
    from collections import Counter
    print(dict(groups=Counter(row["split"] for row in roster.values()),
               polygons=Counter(roster[key]["split"] for key in owners.values()),
               review=Counter(row["split"] for row in development), split_sha256=split_sha))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "qa"))
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(ROOT, fetch(MAUS, 26 * 1024**2), fetch(ADM, 8 * 1024**2))
    else:
        from scripts.phase22b_maus_qa import run
        run(ROOT)
