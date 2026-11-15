import json

import numpy as np
import pytest

from scripts.minenetcd256_siamese_data import RGBPairs, REVISION, SHARDS, digest


def test_rgb_loader_returns_paired_chw_and_rejects_tampering(tmp_path):
    path = tmp_path / "pair.npz"
    rgb = np.full((256, 256, 3), 255, dtype=np.uint8)
    mask = np.zeros((256, 256), dtype=np.uint8)
    mask[0, 0] = 255
    np.savez(path, before=rgb, after=rgb, mask=mask)
    manifest = dict(revision=REVISION, shards={s: SHARDS[s] for s in ("train", "val")},
                    patches=[dict(split="train", file=path.name, sha256=digest(path))])
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    dataset = RGBPairs(tmp_path, "train")
    a, b, y, valid = dataset[0]
    assert a.shape == b.shape == (3, 256, 256)
    assert a.min() == 1
    assert y.shape == valid.shape == (1, 256, 256)
    assert y.sum() == 1 and valid.all()
    with pytest.raises(ValueError, match="train and validation"):
        RGBPairs(tmp_path, "test")
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash"):
        dataset[0]
