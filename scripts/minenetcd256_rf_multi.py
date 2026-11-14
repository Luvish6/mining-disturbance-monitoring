"""Bounded site-balanced MineNetCD256 RGB experiment using train and val only."""
import json
from pathlib import Path
import pickle
from time import perf_counter

import numpy as np
import pyarrow.parquet as pq
from sklearn.ensemble import RandomForestClassifier

from scripts.minenetcd256_adapter import DATASET, REVISION, SPLITS, metadata
from scripts.minenetcd256_rf_pilot import RF_CONFIG, SHARDS, RangeSource, patch_arrays
from src.phase3.evaluate import metrics

LIMITS = {"train": 8, "val": 4}
BUDGET = 48 * 1024**2


def roster_for(split):
    record = metadata("statistics", split=split)
    domain, = [c["column_statistics"] for c in record["statistics"] if c["column_name"] == "domain"]
    counts = domain["frequencies"]
    sites, rows = SPLITS[split]
    if (record["partial"] or record["num_examples"] != rows or len(counts) != sites
            or sum(counts.values()) != rows or domain["nan_count"] or domain["no_label_count"]):
        raise ValueError("Incomplete official site metadata")
    return counts


def load_mines(split, roster):
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{SHARDS[split]}"
    mines = {}
    with RangeSource(url, BUDGET) as source:
        parquet = pq.ParquetFile(source)
        for group in range(parquet.num_row_groups):
            domains = parquet.read_row_group(group, columns=["domain"], use_threads=False)["domain"].to_pylist()
            if set(domains) - roster.keys():
                raise ValueError("Shard contains sites outside its official split")
            selected = list(dict.fromkeys(site for site in domains if site not in mines))
            selected = selected[:LIMITS[split] - len(mines)]
            if not selected:
                continue
            info = parquet.metadata.row_group(group)
            if sum(info.column(i).total_compressed_size for i in range(info.num_columns)) > source.budget:
                break
            table = parquet.read_row_group(group, use_threads=False)
            for site in selected:
                indices = [i for i, value in enumerate(domains) if value == site][:5]
                patches = [patch_arrays(row) for row in table.take(indices).to_pylist()]
                mines[site] = (np.concatenate([p[0] for p in patches]), np.concatenate([p[1] for p in patches]),
                               dict(group=group, rows=indices, excluded=sum(p[2] for p in patches)))
            if len(mines) == LIMITS[split]:
                break
        return mines, BUDGET - source.budget


def sample_training(mines, cap=100_000):
    rng = np.random.default_rng(42)
    quota = cap // len(mines)
    xs, ys, counts = [], [], {}
    for site, (x, y, _) in mines.items():
        selected = []
        for label in (0, 1):
            available = np.flatnonzero(y == label)
            selected.extend(rng.choice(available, min(quota // 2, len(available)), replace=False))
        xs.append(x[selected])
        ys.append(y[selected])
        counts[site] = np.bincount(y[selected], minlength=2).tolist()
    return np.concatenate(xs), np.concatenate(ys), counts


def run(output):
    if output.exists():
        raise ValueError("Choose a new local run directory")
    rosters = {split: roster_for(split) for split in LIMITS}
    if rosters["train"].keys() & rosters["val"].keys():
        raise ValueError("Official site overlap")
    start = perf_counter()
    batches = {split: load_mines(split, roster) for split, roster in rosters.items()}
    if any(not mines for mines, _ in batches.values()):
        raise ValueError("No usable mines within transfer budget")
    x, y, sampled = sample_training(batches["train"][0])
    if len(np.unique(y)) != 2:
        raise ValueError("Training requires both classes")
    model = RandomForestClassifier(**RF_CONFIG)
    model.fit(x, y)
    results = {}
    for split, (mines, transferred) in batches.items():
        per_mine, targets, probabilities = {}, [], []
        for site, (features, labels, detail) in mines.items():
            probability = model.predict_proba(features)[:, 1]
            per_mine[site] = dict(**detail, **metrics(labels, probability, .5))
            targets.append(labels)
            probabilities.append(probability)
        results[split] = dict(parquet_bytes=transferred, per_mine=per_mine,
                              pooled=metrics(np.concatenate(targets), np.concatenate(probabilities), .5))
    receipt = dict(revision=REVISION, rf=RF_CONFIG, fitted_pixels=len(y), sampled=sampled,
                   sampling="First mines in pinned shard order, first up to five rows in the discovery group, equal per-mine and per-class ceilings, no redistribution, seed 42",
                   elapsed_seconds=perf_counter() - start, splits=results)
    output.mkdir(parents=True)
    with (output / "rf.pkl").open("xb") as handle:
        pickle.dump(model, handle)
    (output / "metrics.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    for split, result in results.items():
        print(split, len(result["per_mine"]), result["parquet_bytes"], result["pooled"])


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1] / "outputs/external_minenetcd256/rf_multi_v1")
