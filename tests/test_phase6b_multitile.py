"""Offline checks for the Phase 6B exploratory acquisition contract."""
import numpy as np
import pytest
from shapely.geometry import box

from scripts import phase6b_multitile as pilot


def test_selection_is_deterministic_and_buffered():
    east, west = pilot.DISTRICTS
    districts = {east: box(300000, 2700000, 340000, 2740000),
                 west: box(340000, 2700000, 380000, 2740000)}
    shortlist, rejected = pilot.candidates(districts)
    assert len(shortlist) == 18
    assert rejected and pilot.snap(15) == 0 and pilot.snap(-15) == -30
    metrics = {row["id"]: dict(sar_scenes=[4, 4], slope=1, ndvi=.6, paired_count=5)
               for row in shortlist}
    selected, excluded, missing = pilot.select(shortlist, metrics)
    assert not missing and len(selected) == 6 and len(excluded) == 12
    assert pilot.select(shortlist[::-1], metrics)[0] == selected
    for row in selected:
        assert districts[row["district"]].covers(box(*row["bounds"]))
        assert pilot.block_for(row["bounds"]) == row["block"]
        assert all(c % 30 == 0 for c in row["bounds"])
    for row in shortlist:
        if row["district"] == east and row["split"] == "train":
            metrics[row["id"]]["sar_scenes"] = [4, 0]
    assert len(pilot.select(shortlist, metrics)[2]) == 1


def arrays():
    data = np.ones((23, pilot.SIZE, pilot.SIZE), dtype=np.float32)
    data[4:8] = 2
    data[14:18] = 2
    data[[0, 1, 8, 9], 0, 0] = pilot.NODATA
    data[14, 0, 0] = 1
    data[[18, 22], 0, 0] = 0
    return data


def test_support_and_raster_roundtrip(tmp_path):
    data = arrays()
    quality = pilot.validate_pixels(data, [4] * 4)
    assert quality["valid_cells"]["common_valid"] == pilot.SIZE**2 - 1
    pilot.write_raster(tmp_path / "features.tif", data[:14], pilot.BANDS,
                       pilot.Affine(30, 0, 300000, 0, -30, 2700000))


@pytest.mark.parametrize(("band", "value", "message"), [
    (14, 5, "Observation counts"), (18, 0, "Seasonal mask"),
    (8, 7, "After-minus-before"), (22, 0, "Common footprint"),
    (13, 95, "terrain support"),
])
def test_rejects_bad_measurements(band, value, message):
    data = arrays()
    data[band, 1, 1] = value
    with pytest.raises(ValueError, match=message):
        pilot.validate_pixels(data, [4] * 4)


def test_alignment_screen_distinguishes_shifted_texture():
    data = arrays()
    texture = np.random.default_rng(42).normal(0, 4, data.shape[1:])
    data[0] = data[4] = texture
    assert pilot.alignment(data)["status"] == "pass"
    data[4] = np.roll(texture, 1, axis=0)
    assert pilot.alignment(data)["status"] == "inconclusive"
