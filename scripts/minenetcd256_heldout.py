"""Train two external RGB models and freeze them before reading unseen test labels."""
import argparse
import json
from pathlib import Path
import pickle
from hashlib import sha256
from time import monotonic

import numpy as np
import pyarrow.parquet as pq
import torch
from sklearn.ensemble import RandomForestClassifier

from scripts.minenetcd256_adapter import SPLITS, metadata, verify_roster
from scripts.minenetcd256_rf_multi import sample_training
from scripts.minenetcd256_rf_pilot import DATASET, REVISION, RF_CONFIG, SHARDS, RangeSource, decode
from scripts.minenetcd256_siamese_data import RGBPairs, TRAIN, VAL, digest
from scripts.minenetcd256_siamese_fit import run as train_siamese, score, verify_rows
from src.phase3.model import SiameseUNet

BUDGET = 128 * 1024**2
TARGET_SITES = 3
PATCHES = 5


class TestSource(RangeSource):
    """Split large reads to avoid CDN resets; charge a failed range against the cap."""

    def _range(self, start, end):
        pieces = []
        for first in range(start, end+1, 4*1024**2):
            last = min(end, first+4*1024**2-1)
            try:
                data, size = super()._range(first, last)
            except (ConnectionError, TimeoutError):
                self.budget -= last-first+1
                data, size = super()._range(first, last)
            pieces.append(data)
        return b"".join(pieces), size


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def fingerprint(image):
    return sha256(image.tobytes()).hexdigest()


def test_rows(parquet, roster, excluded, target_sites=TARGET_SITES):
    """Select the first five rows of each of the first three new domains; use no masks."""
    selected = {}
    for group in range(parquet.num_row_groups):
        domains = parquet.read_row_group(group, columns=["domain"], use_threads=False)["domain"].to_pylist()
        for index, site in enumerate(domains):
            if site not in roster:
                raise ValueError("Shard contains an unofficial test site")
            if site in excluded or (site not in selected and len(selected) == target_sites):
                continue
            rows = selected.setdefault(site, [])
            if len(rows) < PATCHES:
                rows.append((group, index))
        if len(selected) == target_sites and all(len(rows) == PATCHES for rows in selected.values()):
            return selected
    raise ValueError("Insufficient unseen test domains in bounded shard")


def train(root, out, roster, resume=False):
    cache = root / "siamese_rgb_v1"
    reference = read(root/"rf_combined_v1/metrics.json")
    batches, seen = {}, {}
    for split, sites in (("train", TRAIN), ("val", VAL)):
        dataset = RGBPairs(cache, split)
        verify_rows(dataset.records, reference["selections"][split], sites)
        if set(sites) - roster[split].keys():
            raise ValueError("Unexpected official site assignment")
        for i, rec in enumerate(dataset.records):
            dataset[i]  # Validate the existing lossless-label receipt and cache bytes.
            with np.load(cache/rec["file"], allow_pickle=False) as pairs:
                a, b, mask = (pairs[k] for k in ("before", "after", "mask"))
            for image in (a, b):
                key = fingerprint(image)
                if seen.setdefault(key, split) != split:
                    raise ValueError("Identical RGB epoch across splits")
            if split == "train":
                batches.setdefault(rec["site"], []).append(((b.astype("int16")-a).reshape(-1,3),
                                                           (mask == 255).ravel()))
    if resume:
        result = read(out/"siamese/metrics.json")
        best = out/"siamese"/f'epoch-{result["best_epoch"]}.pt'
        fitting = read(out/"split_manifest.json")
        hashes = {"rf": digest(out/"rf.pkl"), "siamese": digest(best)}
        if fitting["artifact_hashes"] != hashes or fitting["development"] != read(cache/"manifest.json"):
            raise ValueError("Frozen model or development cache changed")
        with (out/"rf.pkl").open("rb") as handle:
            forest = pickle.load(handle)
        return best, forest, seen, {key: fitting[key] for key in ("training_pixels", "sampled_by_site", "artifact_hashes")}
    train_siamese(root, out/"siamese")
    result = read(out/"siamese/metrics.json")
    best = out/"siamese"/f'epoch-{result["best_epoch"]}.pt'
    x, y, counts = sample_training({s:(np.concatenate([a for a,_ in items]),
                                         np.concatenate([b for _,b in items]), {})
                                    for s, items in sorted(batches.items())})
    forest = RandomForestClassifier(**RF_CONFIG)
    forest.fit(x, y)
    rf_path = out/"rf.pkl"
    with rf_path.open("xb") as handle:
        pickle.dump(forest, handle)
    return best, forest, seen, dict(training_pixels=len(y), sampled_by_site=counts,
                                    artifact_hashes={"rf":digest(rf_path), "siamese":digest(best)})


def evaluate(out, roster, excluded, seen, best, forest, thresholds=None, target_sites=TARGET_SITES, require_both=True):
    thresholds = {"rf": .5, "siamese": .5} if thresholds is None else thresholds
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{SHARDS['test']}"
    if "siamese" in thresholds:
        model = SiameseUNet(channels=3,width=16).eval()
        model.load_state_dict(torch.load(best, weights_only=True, map_location="cpu")["model"])
    targets, rf, unet, records = [], [], [], []
    with TestSource(url, BUDGET) as source:
        parquet = pq.ParquetFile(source)
        selection = test_rows(parquet, roster, excluded, target_sites)
        selection_path = out/"test_selection.json"
        if selection_path.is_file() and json.loads(json.dumps(selection)) != read(selection_path):
            raise ValueError("Frozen test selection changed")
        save(selection_path, selection)
        for group in sorted({g for rows in selection.values() for g,_ in rows}):
            table = parquet.read_row_group(group, use_threads=False)
            for site, rows in selection.items():
                for g, index in rows:
                    if g != group:
                        continue
                    row = table.slice(index, 1).to_pylist()[0]
                    if row["domain"] != site:
                        raise ValueError("Test row identity mismatch")
                    a, b = [decode(row[k], "RGB") for k in ("imageA", "imageB")]
                    for image in (a,b):
                        if seen.setdefault(fingerprint(image), "test") != "test":
                            raise ValueError("Identical RGB epoch overlaps development data")
                    mask = decode(row["label"], "L", label=True)
                    valid = np.isin(mask, [0,255])
                    y = mask[valid] == 255
                    targets.append(y)
                    if "rf" in thresholds:
                        rf.append(forest.predict_proba((b.astype("int16")-a)[valid])[:,1])
                    if "siamese" in thresholds:
                        with torch.inference_mode():
                            tensors = [torch.from_numpy(image.transpose(2,0,1)).float().div_(255)[None] for image in (a,b)]
                            unet.append(model(*tensors).sigmoid()[0,0].numpy()[valid])
                    name = f"test-{group}-{index}.npz"
                    np.savez_compressed(out/name, before=a, after=b, mask=mask)
                    records.append(dict(site=site, row_group=group, row=index, file=name, sha256=digest(out/name),
                                        changed=int(y.sum()), unchanged=int(len(y)-y.sum()), excluded=int((~valid).sum()),
                                        source_sha256={k:sha256(row[k]["bytes"]).hexdigest()
                                                       for k in ("imageA","imageB","label")}))
        transferred = BUDGET - source.budget
    pooled = np.concatenate(targets)
    if require_both and len(np.unique(pooled)) != 2:
        raise ValueError("Frozen test sample lacks both classes")
    results = {}
    for name, probabilities in (("rf",rf),("siamese",unet)):
        if name not in thresholds:
            continue
        results[name] = {"pooled":score(pooled,np.concatenate(probabilities),thresholds[name])}
        for site in selection:
            chosen = [i for i, rec in enumerate(records) if rec["site"] == site]
            results[name][site] = score(np.concatenate([targets[i] for i in chosen]),
                                        np.concatenate([probabilities[i] for i in chosen]),thresholds[name])
    return records, results, transferred


def run(root, out, resume=False):
    start = monotonic()
    roster = verify_roster({split:metadata("statistics",split=split) for split in SPLITS})
    prior = read(root/"rf_pilot_v1/manifest.json")
    viewer = read(root/"phase10c.json")
    if any(d["revision"] != REVISION or d["official_roster"] != roster for d in (prior, viewer)):
        raise ValueError("Official roster changed")
    excluded = set(viewer["split_summary"]["test"]["sites"])
    excluded.update(p["site"] for p in prior["splits"]["test"]["patches"])
    if resume:
        frozen = read(out/"split_manifest.json")
        if (out/"metrics.json").exists() or frozen["official_roster"] != roster or set(frozen["previous_test_sites_excluded"]) != excluded:
            raise ValueError("Cannot resume this frozen evaluation")
    else:
        out.mkdir()
    best, forest, seen, fitting = train(root, out, roster, resume=resume)
    save(out/"split_manifest.json", dict(dataset=DATASET, revision=REVISION, license="CC BY 4.0 (RODARE 3251)",
         test_shard=SHARDS["test"], development=read(root/"siamese_rgb_v1/manifest.json"),
         previous_test_sites_excluded=sorted(excluded), official_roster=roster, threshold=.5, **fitting))
    records, results, transfer = evaluate(out, roster["test"], excluded, seen, best, forest)
    save(out/"test_manifest.json", records)
    save(out/"metrics.json", dict(results=results, parquet_bytes=transfer, seconds=monotonic()-start,
                                 fit=fitting, test_patches=len(records), test_sites=sorted({r["site"] for r in records})))
    print(results, flush=True)


def domain_probe(cache, indian_cache):
    """Compare R/G signed-difference marginals, without applying either RGB model."""
    import rasterio
    from scipy.stats import wasserstein_distance

    training = RGBPairs(cache, "train")
    source = []
    for record in training.records:
        path = cache / record["file"]
        if digest(path) != record["sha256"]:
            raise ValueError("Training RGB hash mismatch")
        with np.load(path, allow_pickle=False) as data:
            source.append(((data["after"].astype(float) - data["before"])/255)[:, :, :2].reshape(-1, 2))
    source = np.concatenate(source)

    def standardize(values):
        center = np.median(values, axis=0)
        scale = 1.4826*np.median(np.abs(values-center), axis=0)
        if np.any(scale <= 0):
            raise ValueError("Degenerate radiometric scale")
        return (values-center)/scale

    result = {}
    for site in ("gevra", "bhubaneswari"):
        path = indian_cache / site / "tile.tif"
        with rasterio.open(path) as raster:
            bands = ("B4_before", "B3_before", "B4_after", "B3_after", "common_valid")
            data = raster.read([raster.descriptions.index(b)+1 for b in bands], masked=True)
            valid = ~np.ma.getmaskarray(data).any(0) & (data[4].filled(0) == 1)
            target = (data[2:4, valid]-data[:2, valid]).T.data.astype(float)
        result[site] = dict(target_pixels=len(target), sha256=digest(path),
                            raw_rg=[float(wasserstein_distance(a,b)) for a,b in zip(source.T,target.T,strict=True)],
                            standardized_rg=[float(wasserstein_distance(a,b)) for a,b in
                                             zip(standardize(source).T,standardize(target).T,strict=True)])
    return dict(source_train_pixels=len(source), comparison=result,
                interpretation="Unlabeled marginal shift only: RGB intensity and Sentinel reflectance are different; no transfer or accuracy inferred.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--resume", action="store_true")
    run(**vars(parser.parse_args()))
