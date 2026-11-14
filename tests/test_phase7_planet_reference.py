import json

import numpy as np
import pytest
from rasterio.transform import from_origin

from config.settings import BEFORE
from scripts import phase7_planet_reference as planet


def test_scene_time_and_id(tmp_path):
    path = tmp_path / "item.json"
    item = dict(id=planet.IDS[0], properties=dict(acquired="2024-03-25T04:35:45.49Z"))
    path.write_text(json.dumps(item))
    assert planet.metadata(path, planet.IDS[0], BEFORE).startswith("2024-03-25")
    item["properties"]["acquired"] = "2024-03-26T04:35:45Z"
    path.write_text(json.dumps(item))
    with pytest.raises(ValueError, match="acquisition"):
        planet.metadata(path, planet.IDS[0], BEFORE)


def test_udm_flags_and_shifted_clear_overlap():
    sr = np.ones((8, 2, 3), dtype="uint16")
    udm = np.zeros_like(sr, dtype="uint8")
    udm[0] = 1
    udm[2, 0, 0] = 1
    udm[5, 0, 1] = 1
    udm[7, 0, 2] = 4
    clear, qa = planet.clear_pixels(sr, udm)
    assert qa["clear"] == 3 and qa["cloud_shadow"] == qa["cloud"] == 1
    scenes = [(sr, clear, from_origin(x, 6, 3, 3), {}) for x in (0, 3)]
    assert planet.common_clear(scenes, (3, 0, 9, 6)) == 2


def test_missing_assets(tmp_path):
    with pytest.raises(ValueError, match="Missing authorized Planet files"):
        planet.load_scene(tmp_path, planet.IDS[0], BEFORE, (0, 0, 10, 10))
