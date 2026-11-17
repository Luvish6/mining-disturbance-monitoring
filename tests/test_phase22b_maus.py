import json

import numpy as np
import pytest
from shapely.geometry import box

from scripts.phase22b_maus import BUFFER, groups, grid, partition, train_normalization, write_json
from scripts.phase22b_maus_qa import development_sites


def test_transitive_group_and_buffer_edges():
    items = {1: box(0, 0, 10, 10), 2: box(10, 0, 20, 10),
             3: box(20 + BUFFER, 0, 30 + BUFFER, 10),
             4: box(31 + 2 * BUFFER, 0, 42 + 2 * BUFFER, 10),
             5: box(2, 2, 8, 8)}
    assert list(groups(items)) == [[1, 2, 3, 5], [4]]
    assert list(groups(dict(reversed(list(items.items()))))) == list(groups(items))


def test_state_holdouts():
    assert partition({"Jh\u0101rkhand"}) == "test"
    assert partition({"Odisha"}) == "validation"
    assert partition({"Goa"}) == "train"
    assert partition({"Odisha", "Goa"}) == "excluded"


def test_normalization_rejects_non_train_and_ignores_nodata():
    x = np.array([[[1, 3, np.nan]], [[5, 5, 900]]])
    mask = np.array([[True, True, False]])
    means, scales = train_normalization([("train", x, mask)])
    np.testing.assert_equal(means, [2, 5])
    np.testing.assert_equal(scales, [1, 1])
    for role in ("validation", "test"):
        with pytest.raises(ValueError, match="TRAIN-only"):
            train_normalization([("train", x, mask), (role, x, mask)])
    with pytest.raises(ValueError, match="Nonfinite"):
        train_normalization([("train", x, np.ones_like(mask))])


def test_manifest_rejects_hash_mismatch_and_test_rows(tmp_path):
    groups_by_role = {r: {"split": r, "ids": [i]} for i, r in
                      enumerate(("train", "validation", "test"))}
    fingerprint = write_json(tmp_path / "split.json", dict(groups=groups_by_role))
    sites = [dict(split=role, group=role, fid=i) for i, role in
             enumerate(("train", "validation"))]
    write_json(tmp_path / "development.json", dict(split_sha256=fingerprint, sites=sites))
    assert list(development_sites(tmp_path)) == sites
    path = tmp_path / "development.json"
    path.write_text(json.dumps(dict(split_sha256="changed", sites=sites)))
    with pytest.raises(ValueError, match="hash mismatch"):
        development_sites(tmp_path)
    sites.append(dict(split="test", group="test", fid=2))
    path.write_text(json.dumps(dict(split_sha256=fingerprint, sites=sites)))
    with pytest.raises(ValueError, match="TEST"):
        development_sites(tmp_path)


def test_grid_is_north_up_and_snapped():
    crs, affine, bounds = grid(85.2, 20.9)
    assert crs == 32645
    assert affine[:2] == [30, 0] and affine[3:5] == [0, -30]
    assert affine[2] % 30 == affine[5] % 30 == 0
    assert bounds[2] - bounds[0] == bounds[3] - bounds[1] == 1920


def test_qa_raster_requires_matching_grid_and_band_order(tmp_path):
    from affine import Affine
    import rasterio

    from scripts.phase22b_maus import BANDS
    from scripts.phase22b_maus_qa import read_grid

    crs, affine, _ = grid(85.2, 20.9)
    site = {"crs": crs, "affine": affine}
    path = tmp_path / "diagnostics.tif"
    with rasterio.open(path, "w", driver="GTiff", count=7, width=64,
                       height=64, dtype="float32", crs=f"EPSG:{crs}",
                       transform=Affine(*affine), nodata=-9999) as out:
        values = np.ones((7, 64, 64), dtype="float32")
        values[-2:] = 2
        out.write(values)
        out.descriptions = BANDS
    assert read_grid(path, site)[1].sum() == 4096
    with pytest.raises(ValueError, match="grid"):
        read_grid(path, dict(site, crs=32644))
    with rasterio.open(path, "r+") as out:
        out.descriptions = BANDS[::-1]
    with pytest.raises(ValueError, match="band"):
        read_grid(path, site)
