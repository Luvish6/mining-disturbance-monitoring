"""Compare Phase 10H with a deterministic per-patch robust RGB normalization."""
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import pickle

import numpy as np
import pyarrow.parquet as pq
from sklearn.metrics import average_precision_score

from scripts.minenetcd256_rf_multi import sample_training, RandomForestClassifier, metrics
from scripts.minenetcd256_rf_pilot import RangeSource, decode, patch_arrays
from scripts.minenetcd256_rf_positive import BUDGET, DATASET, REVISION, RF_CONFIG, SHARDS, TRAIN, VAL


def normalized_rgb(image):
    q25, median, q75 = np.percentile(image, [25, 50, 75], axis=(0, 1))
    return ((image - median) / np.maximum(q75 - q25, 1)).astype(np.float32)


def reconstruct(parquet, selection, cache):
    batches = {}
    for site, detail in selection["sites"].items():
        path = cache / f"{site}.npz"
        if sha256(path.read_bytes()).hexdigest() != detail["sha256"]:
            raise ValueError("Frozen feature cache hash mismatch")
        with np.load(path, allow_pickle=False) as arrays:
            batches[site] = (arrays["x"], arrays["y"], {})
    raw, features, labels = ({site: [] for site in batches} for _ in range(3))
    for group in sorted({g for detail in selection["sites"].values() for g, _ in detail["rows"]}):
        table = parquet.read_row_group(group, use_threads=False)
        for site, detail in selection["sites"].items():
            for g, index in detail["rows"]:
                if g != group:
                    continue
                row = table.slice(index, 1).to_pylist()[0]
                if row["domain"] != site:
                    raise ValueError("Frozen site identity mismatch")
                x, y, _ = patch_arrays(row)
                mask = decode(row["label"], "L", label=True)
                before = normalized_rgb(decode(row["imageA"], "RGB"))
                after = normalized_rgb(decode(row["imageB"], "RGB"))
                raw[site].append(x)
                labels[site].append(y)
                features[site].append((after - before)[(mask == 0) | (mask == 255)])
    for site, (x, y, _) in batches.items():
        if not np.array_equal(x, np.concatenate(raw[site])) or not np.array_equal(y, np.concatenate(labels[site])):
            raise ValueError("Source pixels differ from Phase 10H")
    return batches, {site: (np.concatenate(features[site]), batch[1], {}) for site, batch in batches.items()}


def diagnostics(y, score):
    result = metrics(y, score, .5)
    tn, fp = result["confusion_matrix"][0]
    return dict(**result, fpr=fp / (fp + tn), average_precision=float(average_precision_score(y, score)) if y.any() else None)


def frozen_inputs(cache, reference, reconstruct_split=reconstruct):
    splits, transfers = {}, {}
    with ExitStack() as stack:
        readers = {}
        for split, sites in (("train", TRAIN), ("val", VAL)):
            selection = reference["frozen_selections"][split]
            if (selection != json.loads((cache / f"{split}.json").read_text())
                    or selection["revision"] != REVISION or selection["shard"] != SHARDS[split]
                    or tuple(selection["sites"]) != sites):
                raise ValueError("Frozen source selection mismatch")
            url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{SHARDS[split]}"
            source = stack.enter_context(RangeSource(url, BUDGET))
            parquet = pq.ParquetFile(source)
            groups = {g for detail in selection["sites"].values() for g, _ in detail["rows"]}
            cost = sum(parquet.metadata.row_group(g).column(i).total_compressed_size
                       for g in groups for i in range(parquet.metadata.num_columns))
            if cost > source.budget:
                raise ValueError("Required source data exceeds existing transfer cap")
            readers[split] = source, parquet, selection
        for split, (source, parquet, selection) in readers.items():
            splits[split] = reconstruct_split(parquet, selection, cache)
            transfers[split] = BUDGET - source.budget
    return splits, transfers


def run(root):
    output = root / "rf_normalized_v1"
    if output.exists():
        raise ValueError("Choose a new run directory")
    cache = root / "rf_positive_cache_v1"
    reference = json.loads((root / "rf_positive_v1/metrics.json").read_text())
    prior = json.loads((root / "rf_validation_diagnostics_v1.json").read_text())
    contents = (root / "rf_positive_v1/rf.pkl").read_bytes()
    if sha256(contents).hexdigest() != prior["model_sha256"]:
        raise ValueError("Baseline model hash mismatch")
    baseline = pickle.loads(contents)
    splits, transfers = frozen_inputs(cache, reference)
    x, y, counts = sample_training(splits["train"][1])
    if counts != reference["training_counts"]:
        raise ValueError("Training allocation differs from baseline")
    normalized = RandomForestClassifier(**RF_CONFIG).fit(x, y)
    results = {}
    for name, model, index in (("baseline", baseline, 0), ("normalized", normalized, 1)):
        outcomes = {}
        ys, scores = [], []
        for site, (features, labels, _) in splits["val"][index].items():
            score = model.predict_proba(features)[:, 1]
            outcomes[site] = diagnostics(labels, score)
            ys.append(labels)
            scores.append(score)
        outcomes["pooled"] = diagnostics(np.concatenate(ys), np.concatenate(scores))
        results[name] = outcomes
    if results["baseline"]["pooled"]["confusion_matrix"] != reference["validation"]["confusion_matrix"]:
        raise ValueError("Baseline evaluation differs from Phase 10H")
    output.mkdir()
    with (output / "rf.pkl").open("xb") as handle:
        pickle.dump(normalized, handle)
    receipt = dict(normalization="Each patch/date/channel: subtract median, divide by max(IQR,1), then after minus before",
                   baseline_sha256=prior["model_sha256"], selections=reference["frozen_selections"],
                   parquet_bytes=transfers, training_counts=counts, results=results)
    (output / "metrics.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(transfers)
    for name, outcome in results.items():
        for site, r in outcome.items():
            print(name, site, r["confusion_matrix"], r["classes"][1], r["fpr"], r["average_precision"])


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1] / "outputs/external_minenetcd256")
