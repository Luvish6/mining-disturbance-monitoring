"""Fit the fixed external MineNetCD256 pilot from the prepared local subset."""

from hashlib import sha256
import json
from pathlib import Path
import pickle
from time import perf_counter

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier

from scripts.minenetcd256_adapter import DATASET, REVISION, SPLITS
from scripts.minenetcd256_rf_pilot import RF_CONFIG, SHARDS
from src.phase3.evaluate import metrics


def load_subset(source):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if (manifest["dataset"], manifest["revision"], manifest["rf"], manifest["features"]) != (
        DATASET, REVISION, RF_CONFIG, [f"after_minus_before_{c}" for c in "RGB"]
    ):
        raise ValueError("Unexpected external dataset or RF configuration")
    roster = manifest["official_roster"]
    seen, batches = set(), {}
    for split, (num_sites, num_rows) in SPLITS.items():
        sites = set(roster[split])
        if seen & sites or len(sites) != num_sites or sum(roster[split].values()) != num_rows:
            raise ValueError("Official site roster mismatch")
        seen.update(sites)
        entry = manifest["splits"][split]
        patches = entry["patches"]
        mines = {patch["site"] for patch in patches}
        if (len(mines) != 1 or not mines <= sites or len(patches) != 5
                or [p["row"] for p in patches] != list(range(5))
                or any(p["shard"] != SHARDS[split] for p in patches)):
            raise ValueError("Unexpected bounded site or patch assignments")
        with np.load(source / f"{split}.npz", allow_pickle=False) as arrays:
            x, y = arrays["features"], arrays["labels"]
        if (x.shape != (len(y), 3) or y.ndim != 1 or x.dtype != np.int16
                or y.dtype != np.uint8 or not np.isin(y, (0, 1)).all()
                or np.any((x < -255) | (x > 255))
                or not entry["unchanged"] or not entry["changed"]
                or np.bincount(y, minlength=2).tolist() != [entry["unchanged"], entry["changed"]]
                or entry["excluded"] < 0 or len(y) + entry["excluded"] != 5 * 256**2):
            raise ValueError("Prepared feature or label counts are inconsistent")
        batches[split] = (x, y, mines.pop())
    return batches


def run(source, output):
    start = perf_counter()
    if output.exists():
        raise ValueError("Choose a new external run directory")
    batches = load_subset(source)
    train_x, train_y, _ = batches["train"]
    rng = np.random.default_rng(RF_CONFIG["random_state"])
    selected = np.sort(rng.choice(len(train_y), min(len(train_y), 100_000), replace=False))
    if len(np.unique(train_y[selected])) != 2:
        raise ValueError("Training sample lost class support")
    model = RandomForestClassifier(**RF_CONFIG)
    before_fit = perf_counter()
    model.fit(train_x[selected], train_y[selected])
    fit_seconds = perf_counter() - before_fit
    splits = {}
    for split, (x, y, mine) in batches.items():
        scores = metrics(y, model.predict_proba(x)[:, 1], threshold=.5)
        splits[split] = dict(mine=mine, evaluated_pixels=len(y), **scores)
    receipt = dict(dataset=DATASET, revision=REVISION, rf=RF_CONFIG,
                   sklearn=sklearn.__version__, scope="external RGB pilot; one mine per split",
                   fitted_pixels=len(selected),
                   fitted_class_counts=np.bincount(train_y[selected], minlength=2).tolist(),
                   fitted_index_sha256=sha256(selected.astype("<i8").tobytes()).hexdigest(),
                   input_sha256={name: sha256((source / name).read_bytes()).hexdigest()
                                 for name in ("manifest.json", "train.npz", "val.npz", "test.npz")},
                   fit_seconds=fit_seconds, elapsed_seconds=perf_counter() - start, splits=splits)
    output.mkdir(parents=True)
    with (output / "rf.pkl").open("xb") as handle:
        pickle.dump(model, handle)
    (output / "metrics.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "outputs/external_minenetcd256"
    print(json.dumps(run(root / "rf_pilot_v1", root / "rf_fit_v1"), indent=2))
