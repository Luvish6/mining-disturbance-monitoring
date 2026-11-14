"""Run the frozen six-mine RGB training and three-mine validation experiment."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import pickle
from time import perf_counter

import numpy as np
import pyarrow.parquet as pq

from scripts.minenetcd256_rf_multi import roster_for, sample_training, RandomForestClassifier, metrics
from scripts.minenetcd256_rf_pilot import DATASET, REVISION, SHARDS, RangeSource, RF_CONFIG, decode, patch_arrays

TRAIN = ("America_01", "America_03", "America_05", "America_06", "America_07", "Australia_01")
VAL = ("Chile_01", "Germany_05", "Congo_01")
BUDGET = 256 * 1024**2
GROUPS = {"train": 6, "val": 2}
PATCHES = 5


def select_rows(split, candidates):
    rng = np.random.default_rng(42)
    selected = {}
    for site, rows in candidates.items():
        eligible = [item for item, mixed in rows if mixed or split == "val"]
        if len(eligible) < PATCHES:
            raise ValueError(f"Insufficient eligible patches for {site}")
        indices = sorted(rng.choice(len(eligible), PATCHES, replace=False))
        selected[site] = [eligible[i] for i in indices]
    return selected


def acquire(split, sites, roster, cache):
    shard = SHARDS[split]
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{shard}"
    selected_cache = cache / f"{split}.json"
    if selected_cache.is_file():
        records = json.loads(selected_cache.read_text())
        if (records["revision"] != REVISION or records["shard"] != shard
                or set(records["sites"]) != set(sites) or not set(sites) <= roster.keys()):
            raise ValueError("Cached selection disagrees with official source")
        for site, entry in records["sites"].items():
            if sha256((cache / f"{site}.npz").read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError("Cached feature hash mismatch")
        return records, 0

    candidates = {site: [] for site in sites}
    payloads = {site: [] for site in sites}
    with RangeSource(url, BUDGET) as source:
        parquet = pq.ParquetFile(source)
        for group in range(min(GROUPS[split], parquet.num_row_groups)):
            rows = parquet.read_row_group(group, columns=["domain", "label"], use_threads=False)
            for i, row in enumerate(rows.to_pylist()):
                site = row["domain"]
                if site not in roster:
                    raise ValueError("Parquet site absent from its official split")
                if site in candidates:
                    mask = decode(row["label"], "L", label=True)
                    candidates[site].append(((group, i), bool((mask == 255).any() and (mask == 0).any())))
        selected = select_rows(split, candidates)
        for group in sorted({g for rows in selected.values() for g, _ in rows}):
            table = parquet.read_row_group(group, use_threads=False)
            for site, rows in selected.items():
                for g, i in rows:
                    if g != group:
                        continue
                    row = table.slice(i, 1).to_pylist()[0]
                    if row["domain"] != site:
                        raise ValueError("Selected patch site mismatch")
                    payloads[site].append(patch_arrays(row))
        transferred = BUDGET - source.budget

    records = dict(revision=REVISION, shard=shard, parquet_bytes=transferred, sites={})
    for site, patches in payloads.items():
        path = cache / f"{site}.npz"
        with path.open("wb") as handle:
            np.savez_compressed(handle, x=np.concatenate([p[0] for p in patches]),
                                y=np.concatenate([p[1] for p in patches]))
        records["sites"][site] = dict(rows=selected[site], excluded=sum(p[2] for p in patches),
                                     sha256=sha256(path.read_bytes()).hexdigest())
    with selected_cache.open("x") as handle:
        json.dump(records, handle, indent=2)
    return records, transferred


def run(root):
    start = perf_counter()
    output = root / "rf_positive_v1"
    if output.exists():
        raise ValueError("Existing positive-mine run is immutable")
    rosters = {split: roster_for(split) for split in ("train", "val")}
    if rosters["train"].keys() & rosters["val"].keys():
        raise ValueError("Official split overlap")
    cache = root / "rf_positive_cache_v1"
    cache.mkdir(parents=True, exist_ok=True)
    sites_by_split = {"train": TRAIN, "val": VAL}
    if any(not set(sites) <= rosters[split].keys() for split, sites in sites_by_split.items()):
        raise ValueError("Requested mine absent from official split")
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {split: pool.submit(acquire, split, sites, rosters[split], cache)
                for split, sites in sites_by_split.items()}
        acquired = {split: job.result() for split, job in jobs.items()}
    batches = {}
    for split, sites in sites_by_split.items():
        batches[split] = {}
        for site in sites:
            with np.load(cache / f"{site}.npz", allow_pickle=False) as item:
                batches[split][site] = (item["x"], item["y"], {})
    x, y, counts = sample_training(batches["train"])
    if not all(all(c) for c in counts.values()):
        raise ValueError("Every training mine must supply both classes")
    model = RandomForestClassifier(**RF_CONFIG)
    fit_at = perf_counter()
    model.fit(x, y)
    fit_seconds = perf_counter() - fit_at
    per_mine, targets, probabilities = {}, [], []
    for site, (features, labels, _) in batches["val"].items():
        score = model.predict_proba(features)[:, 1]
        per_mine[site] = metrics(labels, score, .5)
        targets.append(labels)
        probabilities.append(score)
    result = dict(revision=REVISION, rf=RF_CONFIG, training_counts=counts,
                  scope="External RGB only. Seed-42 patch sampling across the Phase 10G scanned row groups. Train uses mixed-mask patches; validation samples without label-based filtering.",
                  fitted_pixels=len(y), fit_seconds=fit_seconds, elapsed_seconds=perf_counter()-start,
                  parquet_bytes={split: item[1] for split, item in acquired.items()},
                  frozen_selections={split: item[0] for split, item in acquired.items()},
                  validation=metrics(np.concatenate(targets), np.concatenate(probabilities), .5),
                  per_mine=per_mine)
    output.mkdir()
    with (output / "rf.pkl").open("xb") as handle:
        pickle.dump(model, handle)
    (output / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "frozen_selections"}, indent=2))


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1] / "outputs/external_minenetcd256")
