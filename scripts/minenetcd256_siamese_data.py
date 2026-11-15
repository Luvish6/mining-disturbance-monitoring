"""Prepare an immutable paired-RGB cache for the external Siamese experiment."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import torch
from torch.utils.data import Dataset

from scripts.minenetcd256_rf_normalized import frozen_inputs
from scripts.minenetcd256_rf_pilot import decode
from scripts.minenetcd256_rf_positive import REVISION, SHARDS, TRAIN, VAL
from src.phase3.model import SiameseUNet, masked_loss


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read_pairs(parquet, selection, cache, target, split):
    locations = {}
    for site, detail in selection["sites"].items():
        if len(detail["rows"]) != 5:
            raise ValueError("Expected five frozen patches per mine")
        for order, (group, row) in enumerate(detail["rows"]):
            if (group, row) in locations or not 0 <= group < parquet.num_row_groups:
                raise ValueError("Invalid or duplicate frozen row identity")
            locations[group, row] = (site, order)

    records = []
    for group in sorted({group for group, _ in locations}):
        table = parquet.read_row_group(group, use_threads=False)
        for (g, index), (site, order) in locations.items():
            if g != group:
                continue
            if not 0 <= index < len(table):
                raise ValueError("Frozen row outside its row group")
            row = table.slice(index, 1).to_pylist()[0]
            if row["domain"] != site:
                raise ValueError("Frozen patch belongs to a different mine")
            before, after = [decode(row[key], "RGB") for key in ("imageA", "imageB")]
            mask = decode(row["label"], "L", label=True)
            if not np.isin(mask, (0, 255)).all():
                raise ValueError("Expected a binary lossless PNG mask")
            name = f"{split}-{group}-{index}.npz"
            path = target / name
            np.savez_compressed(path, before=before, after=after, mask=mask)
            records.append(dict(split=split, site=site, group=group, row=index, order=order, file=name,
                                sha256=digest(path), changed=int(np.count_nonzero(mask)),
                                source_sha256={key: sha256(row[key]["bytes"]).hexdigest()
                                               for key in ("imageA", "imageB", "label")}))
    for site, detail in selection["sites"].items():
        original = cache / f"{site}.npz"
        if digest(original) != detail["sha256"] or detail["excluded"]:
            raise ValueError("Phase 10H cache hash or binary support mismatch")
        ordered = sorted((r for r in records if r["site"] == site), key=lambda r: r["order"])
        xs, ys = [], []
        for record in ordered:
            with np.load(target / record["file"], allow_pickle=False) as arrays:
                xs.append((arrays["after"].astype(np.int16) - arrays["before"]).reshape(-1, 3))
                ys.append((arrays["mask"] == 255).ravel())
        with np.load(original, allow_pickle=False) as arrays:
            if not np.array_equal(np.concatenate(xs), arrays["x"]) or not np.array_equal(np.concatenate(ys), arrays["y"]):
                raise ValueError("Original pair does not reproduce Phase 10H features and targets")
    return records


class RGBPairs(Dataset):
    def __init__(self, root, split):
        if split not in ("train", "val"):
            raise ValueError("Only frozen train and validation are available")
        self.root = Path(root)
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        if manifest["revision"] != REVISION or manifest["shards"] != {s: SHARDS[s] for s in ("train", "val")}:
            raise ValueError("Unexpected cache provenance")
        self.records = [r for r in manifest["patches"] if r["split"] == split]

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        record = self.records[index]
        path = self.root / record["file"]
        if digest(path) != record["sha256"]:
            raise ValueError("Cached pair hash mismatch")
        with np.load(path, allow_pickle=False) as arrays:
            a, b, mask = [arrays[key] for key in ("before", "after", "mask")]
        if (a.shape != (256, 256, 3) or b.shape != a.shape or mask.shape != (256, 256)
                or any(arr.dtype != np.uint8 for arr in (a, b, mask)) or not np.isin(mask, (0, 255)).all()):
            raise ValueError("Invalid cached pair geometry or labels")
        before, after = [torch.from_numpy(image.transpose(2, 0, 1)).float().div_(255) for image in (a, b)]
        target = torch.from_numpy((mask[None] == 255).astype(np.float32))
        return before, after, target, torch.ones_like(target, dtype=torch.bool)


def prepare(root):
    output = root / "siamese_rgb_v1"
    if output.exists():
        # A complete cache needs no source reads.
        for split, sites in (("train", TRAIN), ("val", VAL)):
            dataset = RGBPairs(output, split)
            if len(dataset) != 5 * len(sites) or {r["site"] for r in dataset.records} != set(sites):
                raise ValueError("Cached roster mismatch")
            for i in range(len(dataset)):
                dataset[i]
        return output, {"train": 0, "val": 0}
    reference = json.loads((root / "rf_positive_v1/metrics.json").read_text(encoding="utf-8"))
    if set(TRAIN) & set(VAL):
        raise ValueError("Mine leakage across frozen splits")
    with TemporaryDirectory(prefix=".siamese-", dir=root) as directory:
        stage = Path(directory) / "cache"
        stage.mkdir()

        def capture(parquet, selection, cache):
            split = next(s for s in ("train", "val") if SHARDS[s] == selection["shard"])
            return read_pairs(parquet, selection, cache, stage, split)

        records, transfers = frozen_inputs(root / "rf_positive_cache_v1", reference, capture)
        manifest = dict(revision=REVISION, shards={s: SHARDS[s] for s in records},
                        patches=[r for split in records.values() for r in split], parquet_bytes=transfers)
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        stage.rename(output)
    return output, transfers


def smoke(root):
    torch.manual_seed(42)
    torch.set_num_threads(2)
    a, b, label, valid = next(iter(torch.utils.data.DataLoader(RGBPairs(root, "train"), batch_size=1)))
    model = SiameseUNet(channels=3, width=16)
    logits = model(a, b)
    loss = masked_loss(logits, label, valid)
    loss.backward()
    if not torch.isfinite(loss) or not all(p.grad is not None and torch.isfinite(p.grad).all()
                                          for p in model.parameters()):
        raise ValueError("Nonfinite loss or missing gradients")
    print(dict(input=list(a.shape), logits=list(logits.shape), loss=loss.item(),
               valid=int(valid.sum()), positive=int(label.sum()), cuda=torch.cuda.is_available()))


if __name__ == "__main__":
    output, transfer = prepare(Path(__file__).resolve().parents[1] / "outputs/external_minenetcd256")
    print(transfer)
    smoke(output)
