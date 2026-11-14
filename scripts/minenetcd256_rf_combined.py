"""Compare raw, normalized and combined RGB RFs on frozen external patches."""
from hashlib import sha256
import json
from pathlib import Path
import pickle

import numpy as np

from scripts.minenetcd256_rf_normalized import (
    RF_CONFIG, RandomForestClassifier, diagnostics, frozen_inputs, sample_training,
)


def combine(raw, normalized):
    if raw.keys() != normalized.keys():
        raise ValueError("Mine identities disagree")
    result = {}
    for site, (x, y, detail) in raw.items():
        z, labels, _ = normalized[site]
        if x.shape != z.shape or not np.array_equal(y, labels):
            raise ValueError("Frozen pixel support disagrees")
        result[site] = (np.concatenate((x, z), axis=1), y, detail)
    return result


def score_split(model, mines):
    results, targets, scores = {}, [], []
    for site, (features, labels, _) in mines.items():
        score = model.predict_proba(features)[:, 1]
        results[site] = diagnostics(labels, score)
        targets.append(labels)
        scores.append(score)
    results["pooled"] = diagnostics(np.concatenate(targets), np.concatenate(scores))
    return results


def run(root):
    output = root / "rf_combined_v1"
    if output.exists():
        raise ValueError("Choose a new run directory")
    reference = json.loads((root / "rf_positive_v1/metrics.json").read_text())
    prior = json.loads((root / "rf_normalized_v1/metrics.json").read_text())
    if prior["selections"] != reference["frozen_selections"]:
        raise ValueError("Baseline selections disagree")
    baselines, hashes = {}, {}
    for key, directory in (("raw", "rf_positive_v1"), ("normalized", "rf_normalized_v1")):
        data = (root / directory / "rf.pkl").read_bytes()
        hashes[key] = sha256(data).hexdigest()
        baselines[key] = pickle.loads(data)
        if (baselines[key].n_features_in_ != 3 or baselines[key].classes_.tolist() != [0, 1]
                or not RF_CONFIG.items() <= baselines[key].get_params().items()):
            raise ValueError("Baseline model configuration mismatch")
    if hashes["raw"] != prior["baseline_sha256"]:
        raise ValueError("Raw model hash mismatch")
    splits, transfers = frozen_inputs(root / "rf_positive_cache_v1", reference)
    validation = splits["val"]
    results = {key: score_split(baselines[key], batch)
               for key, batch in zip(baselines, validation, strict=True)}
    for key, prior_key in (("raw", "baseline"), ("normalized", "normalized")):
        if results[key] != prior["results"][prior_key]:
            raise ValueError("Baseline predictions differ from Phase 10L metrics")
    x, y, counts = sample_training(combine(*splits["train"]))
    if counts != reference["training_counts"] or counts != prior["training_counts"]:
        raise ValueError("Frozen sampling allocation differs")
    model = RandomForestClassifier(**RF_CONFIG).fit(x, y)
    results["combined"] = score_split(model, combine(*validation))
    output.mkdir()
    with (output / "rf.pkl").open("xb") as handle:
        pickle.dump(model, handle)
    receipt = dict(results=results, baseline_sha256=hashes, rf=RF_CONFIG, parquet_bytes=transfers,
                   features=["raw_dR", "raw_dG", "raw_dB", "normalized_dR", "normalized_dG", "normalized_dB"],
                   selections=prior["selections"], training_counts=counts, threshold=.5)
    (output / "metrics.json").write_text(json.dumps(receipt, indent=2, allow_nan=False), encoding="utf-8")
    print(transfers)
    for name, outcome in results.items():
        for site, r in outcome.items():
            print(name, site, r["confusion_matrix"], r["classes"][1], r["fpr"], r["average_precision"])


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1] / "outputs/external_minenetcd256")
