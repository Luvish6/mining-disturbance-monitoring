import json

import numpy as np
import rasterio

from scripts.phase15c_screen import MAX_SLOPE, MIN_Z, MAX_Z, anomaly
from src.phase3.alerts import run
from src.phase3.regional_inference import NODATA
from test_phase14b_alerts import raster, entry


def test_scaling_and_cross_sensor_quality_masks():
    features = np.zeros((14, 8, 8))
    counts = np.full((4, 8, 8), 3)
    features[8:12, 1:3, 1:3] = np.array([4, 0, .08, 0])[:, None, None]
    features[8, 4, 4] = 5
    features[13, 1, 1] = MAX_SLOPE + 1
    counts[0, 1, 2] = 1
    features[0, 0, 0] = NODATA
    scores, valid, report = anomaly(features, counts, 2)
    assert np.count_nonzero(scores >= MIN_Z/MAX_Z) == 2
    assert scores[4, 4] == 0
    assert scores[1, 1] == scores[1, 2] == NODATA
    assert report["eligible_cells"] == valid.sum() == 61


def test_exploratory_alert_can_only_require_review(tmp_path):
    path = tmp_path/"observed.tif"
    raster(path, kind="exploratory")
    with rasterio.open(path, "r+") as dataset:
        dataset.descriptions = ("anomaly_score", "common_valid")
    spec = tmp_path/"input.json"
    spec.write_text(json.dumps(dict(observations=[entry("2025-03-31")])))
    report = run(spec, tmp_path/"result")
    [feature] = report["data"]["features"]
    properties = feature["properties"]
    assert properties["score_type"] == "anomaly_score"
    assert properties["status"] == "REVIEW_REQUIRED"
    assert properties["eligible_observation_count"] == 0
    assert properties["evidence_status"] == "UNKNOWN"
