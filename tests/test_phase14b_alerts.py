import csv
import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.phase3.alerts import Rules, run
from src.phase3.data import digest


def raster(path, *, kind="synthetic", anomalous=False, low_coverage=False):
    probability = np.full((6, 6), .1, dtype="float32")
    probability[1:3, 2:4] = .9
    probability[5, 5] = .99
    mask = np.ones_like(probability)
    if low_coverage:
        mask[:1] = 0
        mask[-2:] = 0
    if anomalous:
        probability[0, 0] = np.nan
    with rasterio.open(path, "w", driver="GTiff", width=6, height=6, count=2, dtype="float32",
                       crs="EPSG:32646", transform=from_origin(400000, 2800000, 30, 30)) as dst:
        dst.write(np.stack([probability, mask]))
        dst.descriptions = ("disturbance_probability", "common_valid")
        dst.update_tags(data_kind=kind, model_sha256="fixture", experiment="fused")


def execute(root, entries):
    path = root / "input.json"
    path.write_text(json.dumps(dict(observations=entries)), encoding="utf-8")
    return run(path, root / "result")


def entry(after):
    return dict(raster="observed.tif", region_id="fixture", before_date="2024-01-01",
                after_date=after, model_validation="VALIDATED")


def test_synthetic_area_repeat_dedup_and_never_eligible(tmp_path):
    raster(tmp_path/"observed.tif", anomalous=True)
    report = execute(tmp_path, [entry(d) for d in ("2025-03-08", "2025-03-01", "2025-03-01")])
    assert len(report["data"]["features"]) == 1
    feature = report["data"]["features"][0]
    p = feature["properties"]
    assert p["area_m2"] == 3600 and p["cells"] == 4
    assert p["mean_score"] == pytest.approx(.9)
    assert p["status"] == "NOT_VALIDATED" and p["eligible_observation_count"] == 0
    assert p["screening_priority"] == "HIGH" and p["observation_count"] == 2
    assert p["invalid_claimed_cells"] == 1
    assert 91 < p["longitude"] < 93 and 25 < p["latitude"] < 26
    with (tmp_path/"result"/"alerts.csv").open(newline="") as stream:
        assert next(csv.DictReader(stream))["status"] == p["status"]


def test_policy_requires_matching_receipts_and_suppresses_missing_indicators(tmp_path):
    path = tmp_path/"observed.tif"
    raster(path, kind="real", low_coverage=True)
    model = dict(data_kind="real", selected_experiment="fused", manifest_sha256="fixture",
                 selection_partition="validation", test_used_for_selection=False,
                 experiments={"fused": {"sha256": "fixture"}})
    evaluation = dict(data_kind="real", partition="test", selection_partition="validation",
                      selected_experiment="fused", manifest_sha256="fixture",
                      test_class_counts=[100, 100], independent_test_blocks=2)
    for name, document in (("model.json", model), ("evaluation.json", evaluation)):
        (tmp_path/name).write_text(json.dumps(document))
    approved = dict(entry("2025-03-01"), raster_sha256=digest(path), model_sha256="fixture",
                    run_receipt="model.json", run_sha256=digest(tmp_path/"model.json"),
                    evaluation="evaluation.json", evaluation_sha256=digest(tmp_path/"evaluation.json"),
                    validated_region_id="fixture")
    report = execute(tmp_path, [approved, dict(approved, after_date="2025-03-02", raster_sha256="wrong")])
    earlier, later = report["observations"]
    assert earlier["status"] == "REVIEW_REQUIRED" and earlier["coverage"] == .5
    assert later["status"] == "NOT_VALIDATED"
    assert report["data"]["features"][0]["properties"]["status"] == "NOT_VALIDATED"


def test_config_rejects_invalid_threshold_and_area():
    with pytest.raises(ValueError):
        Rules(threshold=.95, high_score=.85)
    with pytest.raises(ValueError):
        Rules(min_area_m2=float("nan"))
