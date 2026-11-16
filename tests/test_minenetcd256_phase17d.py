from hashlib import sha256
import io

import numpy as np
import pytest

from scripts import minenetcd256_phase17d as run


def test_mask_binary_and_hash():
    rgb = np.zeros((256, 256, 3), np.uint8)
    label = np.zeros((256, 256), np.uint8)
    label[0, 0] = 255
    blob = io.BytesIO()
    np.savez(blob, before=rgb, after=rgb, mask=label)
    raw = blob.getvalue()
    assert run.verify_arrays(raw, dict(sha256=sha256(raw).hexdigest(), changed=1))[2].sum() == 1
    with pytest.raises(ValueError, match="hash mismatch"):
        run.verify_arrays(raw, dict(sha256="incorrect", changed=1))
    label[0, 0] = 254
    blob = io.BytesIO()
    np.savez(blob, before=rgb, after=rgb, mask=label)
    raw = blob.getvalue()
    with pytest.raises(ValueError, match="binary mask"):
        run.verify_arrays(raw, dict(sha256=sha256(raw).hexdigest(), changed=1))


def test_threshold_floor_and_zero_change():
    rows = [({"site": "a"}, None, None, np.array([True, False])),
            ({"site": "b"}, None, None, np.array([False, False]))]
    estimates = {"a": np.array([.6, .3]), "b": np.array([.4, .2])}
    result = run.evaluate(rows, lambda row: estimates[row[0]["site"]], lambda: None)
    assert result["operating_threshold"] == .50
    row = next(r for r in result["thresholds"] if r["threshold"] == .50)
    assert row["metrics"]["pooled"]["confusion_matrix"] == [[3, 0], [0, 1]]
    assert row["metrics"]["zero_change"]["recall"] is None
    assert row["metrics"]["mine:b"]["recall"] is None
    assert run.evaluate(rows, lambda row: np.zeros(2), lambda: None)["operating_threshold"] is None


def test_rf_signed_features_and_class_caps():
    a = np.full((100, 100, 3), 255, dtype=np.uint8)
    b = np.zeros_like(a)
    y = np.indices((100, 100))[0] < 50
    rows = [({"site": str(i)}, a, b, y) for i in range(20)]
    x, labels, counts = run.rf_training(rows)
    assert len(labels) == 100_000 and (x == -255).all()
    assert set(map(tuple, counts.values())) == {(2500, 2500)}
