import json

import numpy as np
import pytest

from scripts import minenetcd256_rf_fit as fit


def test_prepared_subset_checks_site_leakage_and_binary_support(tmp_path, monkeypatch):
    monkeypatch.setattr(fit, "SPLITS", {"train": (1, 5), "val": (1, 5), "test": (1, 5)})
    manifest = dict(dataset=fit.DATASET, revision=fit.REVISION, rf=fit.RF_CONFIG,
                    features=[f"after_minus_before_{c}" for c in "RGB"], official_roster={}, splits={})
    for split, shard in fit.SHARDS.items():
        mine = f"site_{split}"
        manifest["official_roster"][split] = {mine: 5}
        manifest["splits"][split] = dict(
            patches=[dict(site=mine, shard=shard, row=i) for i in range(5)],
            unchanged=1, changed=1, excluded=5 * 256**2 - 2)
        np.savez(tmp_path / f"{split}.npz", features=np.zeros((2, 3), dtype=np.int16),
                 labels=np.array([0, 1], dtype=np.uint8))
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    assert fit.load_subset(tmp_path)["test"][2] == "site_test"
    manifest["official_roster"]["test"] = {"site_train": 5}
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="roster"):
        fit.load_subset(tmp_path)
