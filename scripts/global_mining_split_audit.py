"""Audit publisher tile identities and split geography without opening label tables."""
from collections import Counter, defaultdict
import sqlite3

from shapely import STRtree, from_wkb

SPLITS = {"train", "val", "test"}
ENVELOPES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


def decode_geometry(blob):
    if len(blob) < 9 or blob[:2] != b"GP" or blob[2] != 0:
        raise ValueError("Invalid GeoPackage geometry header")
    size = ENVELOPES.get((blob[3] >> 1) & 7)
    if size is None:
        raise ValueError("Invalid GeoPackage envelope code")
    order = "little" if blob[3] & 1 else "big"
    if int.from_bytes(blob[4:8], order, signed=True) != 4326:
        raise ValueError("Expected WGS84 geometry")
    return from_wkb(blob[8 + size:])


def audit_tiles(rows):
    selected = [row for row in rows if row[1] in SPLITS]
    if len({row[0] for row in selected}) != len(selected):
        raise ValueError("Duplicate assigned tile ID")
    scenes = defaultdict(set)
    for _, split, scene, footprint in selected:
        if not scene or not footprint.is_valid or footprint.is_empty:
            raise ValueError("Incomplete assigned tile provenance")
        scenes[scene].add(split)
    footprints = [row[3] for row in selected]
    overlap = Counter()
    for i, j in zip(*STRtree(footprints).query(footprints, predicate="intersects")):
        if (i < j and selected[i][1] != selected[j][1]
                and footprints[i].intersection(footprints[j]).area > 0):
            overlap[tuple(sorted((selected[i][1], selected[j][1])))] += 1
    return dict(split_counts=dict(Counter(row[1] for row in rows)),
                positive_area_cross_split_overlaps=sum(overlap.values()),
                cross_split_scene_ids=sum(len(s) > 1 for s in scenes.values()))


def audit_file(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as database:
        records = database.execute("SELECT tile_id, split, s2_tile_id, geom FROM tiles")
        return audit_tiles([(tile, split, scene, decode_geometry(blob))
                            for tile, split, scene, blob in records])
