"""Spatial quarantine for a metadata-only SmallMinesDS 2022 footprint index."""

import hashlib
import math

from shapely.geometry import box
from shapely.strtree import STRtree

BUFFER_METRES = 1280


def buffered_split(footprints, train_ids, test_ids):
    """Assign whole connected groups, keeping all publisher TEST IDs sealed.

    Input bounds must be verified on the EPSG:32630 metre grid upstream.
    """
    train_ids, test_ids = set(train_ids), set(test_ids)
    if not train_ids or not test_ids or train_ids & test_ids:
        raise ValueError("Expected disjoint nonempty publisher rosters")
    if set(footprints) != train_ids | test_ids:
        raise ValueError("Complete publisher TRAIN and TEST footprint coverage required")

    ids = sorted(footprints)
    shapes = []
    for patch_id in ids:
        west, south, east, north = footprints[patch_id]
        if not all(map(math.isfinite, (west, south, east, north))):
            raise ValueError("Nonfinite footprint")
        if east - west != 1280 or north - south != 1280:
            raise ValueError("Expected verified 1280 m patch extents")
        shapes.append(box(west, south, east, north))

    tree = STRtree(shapes)
    pending = set(range(len(ids)))
    result = {}
    for index in range(len(ids)):
        if index not in pending:
            continue
        pending.remove(index)
        group = [index]
        for member in group:
            geom = shapes[member]
            west, south, east, north = geom.bounds
            radius = BUFFER_METRES
            candidates = tree.query(box(west - radius, south - radius,
                                        east + radius, north + radius))
            for other in sorted(pending.intersection(candidates)):
                if geom.distance(shapes[other]) <= radius:
                    pending.remove(other)
                    group.append(other)
        members = sorted(ids[item] for item in group)
        group_id = hashlib.sha256("\n".join(members).encode()).hexdigest()
        rank = hashlib.sha256(f"42:{group_id}".encode()).digest()
        if test_ids.intersection(members):
            dev_split = "quarantine"
        else:
            dev_split = "validation" if rank[0] < 51 else "train"
        for patch_id in members:
            result[patch_id] = {
                "group": group_id,
                "split": "test" if patch_id in test_ids else dev_split,
            }
    if not {"train", "validation", "test"} <= {row["split"] for row in result.values()}:
        raise ValueError("Buffer and quarantine leave an empty experiment partition")
    return result


def radar_conversion(values, verified_unit):
    """Convert explicitly verified linear power to dB or accept verified dB."""
    import numpy as np

    if verified_unit not in {"linear_power", "dB"}:
        raise ValueError("Verified delivered radar units are required")
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Mask invalid radar cells before conversion")
    if verified_unit == "dB":
        return values
    if np.any(values <= 0):
        raise ValueError("Linear radar power must be positive")
    return 10 * np.log10(values)


def probe_headers(patch_ids):
    """Read only bounded ZIP prefixes and return image grid metadata."""
    import re
    import struct
    import zipfile
    import zlib

    from rasterio.io import MemoryFile

    from scripts.minenetcd256_rf_pilot import RangeSource

    ids = sorted(set(patch_ids))
    if not 1 <= len(ids) <= 32 or any(not re.fullmatch(r"\d{4}", i) for i in ids):
        raise ValueError("Provide 1 to 32 distinct four-digit patch IDs")
    cap = 2 * 1024**2

    class ZipSource(RangeSource):
        def __init__(self):
            self.url = (
                "https://huggingface.co/datasets/ellaampy/SmallMinesDS/resolve/"
                "0cb168b807206d9d34c0d1bd3c81097e69bb889b/SmallMinesDS.zip"
            )
            self.position, self.size, self.budget = 0, 1650426488, cap

    footprints = {}
    with ZipSource() as stream, zipfile.ZipFile(stream) as archive:
        for patch_id in ids:
            name = f"SmallMinesDS/2022/IMAGE/IMG_GH_{patch_id}_2022.tif"
            member = archive.getinfo(name)
            if member.compress_type != zipfile.ZIP_DEFLATED or member.compress_size <= 4096:
                raise ValueError("Expected a deflated image member larger than the prefix")
            stream.seek(member.header_offset)
            header = stream.read(30)
            if header[:4] != b"PK\x03\x04":
                raise ValueError("Invalid local ZIP header")
            name_size, extra_size = struct.unpack_from("<HH", header, 26)
            if name_size != len(name) or stream.read(name_size) != name.encode():
                raise ValueError("ZIP directory and local member identity disagree")
            stream.seek(extra_size, 1)
            prefix = zlib.decompressobj(-15).decompress(stream.read(4096), 4096)
            with MemoryFile(prefix) as memory, memory.open() as raster:
                a, b, _, d, e, _ = tuple(raster.transform)[:6]
                if (raster.shape != (128, 128) or raster.count != 13
                        or raster.crs is None or raster.crs.to_epsg() != 32630
                        or (a, b, d, e) != (10, 0, 0, -10)):
                    raise ValueError("Unexpected SmallMinesDS image grid")
                footprints[patch_id] = tuple(raster.bounds)
        return footprints, cap - stream.budget


if __name__ == "__main__":
    import json
    import sys

    bounds, transferred = probe_headers(sys.argv[1:])
    print(json.dumps({"footprints": bounds, "zip_body_bytes": transferred}, sort_keys=True))
