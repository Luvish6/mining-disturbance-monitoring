import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from scripts import phase7_real_change as change


def test_direction_quadrants_and_zero_exclusion():
    result = change.sign_agreement(np.array([1, 1, -1, -1, -1, 0]), np.array([1, 1, 1, -1, 0, 2]))
    assert [result[k] for k in ("positive_positive", "positive_negative", "negative_positive",
                                 "negative_negative")] == [2, 0, 1, 1]
    assert result["zero_excluded"] == 2 and result["sign_n"] == 4
    assert result["same_sign"] == .75 and result["expected_same_sign"] == .5
    assert result["excess_percentage_points"] == 25
    assert change.sign_agreement(np.zeros(2), np.ones(2))["same_sign"] is None


def test_distribution_and_within_tile_centring():
    values = np.array([-1., 0., 1., 3.])
    stats = change.statistics(values)
    assert stats["n"] == 4 and stats["median"] == .5 and stats["sd"] == pytest.approx(np.std(values, ddof=1))
    assert stats["p25"] == -.25 and stats["p75"] == 1.5
    ids = np.array([0, 0, 1, 1])
    x, y = np.array([0, 1, 10, 11]), np.array([1, 0, 11, 10])
    assert change.pearson(x, y) > .9
    assert change.pearson(change.centre(x, ids), change.centre(y, ids)) == pytest.approx(-1)
    assert change.pearson(x, np.ones(4)) is None
    assert change.statistics(np.array([]))["median"] is None


def test_read_only_mask_combines_explicit_nodata_and_nonfinite(tmp_path):
    path = tmp_path / "feature.tif"
    affine = Affine(30, 0, 300000, 0, -30, 2800000)
    values = np.ones((64,64), dtype="float32")
    values[0,:2] = [-9999, np.nan]
    with rasterio.open(path, "w", driver="GTiff", count=1, width=64, height=64,
                       dtype="float32", crs="EPSG:32646", transform=affine, nodata=-9999) as dst:
        dst.write(values, 1)
        dst.descriptions = ("dVV",)
        dst.write_mask(np.full((64,64), 255, dtype="uint8"))
    before = change.digest(path)
    array, valid = change.raster(path, ("dVV",), affine)
    assert int(valid.sum()) == 4094 and (array[0,0,:2] == -9999).all()
    assert change.digest(path) == before
    with pytest.raises(ValueError, match="grid or schema"):
        change.raster(path, ("dVH",), affine)
