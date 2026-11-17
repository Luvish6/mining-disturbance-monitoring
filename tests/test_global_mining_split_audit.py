from shapely.geometry import box
import pytest

from scripts.global_mining_split_audit import audit_tiles, decode_geometry


def test_source_reuse_is_distinct_from_spatial_overlap():
    rows = [(1, "train", "shared", box(0, 0, 1, 1)),
            (2, "val", "shared", box(1, 0, 2, 1)),
            (3, "test", "other", box(.5, .5, 1, 1))]
    audit = audit_tiles(rows)
    assert audit["positive_area_cross_split_overlaps"] == 1
    assert audit["cross_split_scene_ids"] == 1


def test_reject_duplicate_tile_id_and_bad_geopackage():
    with pytest.raises(ValueError, match="Duplicate"):
        audit_tiles([(1, "train", "a", box(0, 0, 1, 1)),
                     (1, "test", "b", box(2, 2, 3, 3))])
    with pytest.raises(ValueError, match="header"):
        decode_geometry(b"arbitrary")
