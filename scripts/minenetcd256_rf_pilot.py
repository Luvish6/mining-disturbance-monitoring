"""Prepare a bounded RGB-only RF pilot from revision-pinned source Parquet."""

import io
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image
import pyarrow.parquet as pq

from scripts.minenetcd256_adapter import DATASET, REVISION, SPLITS, metadata, verify_roster

RF_CONFIG = dict(n_estimators=100, max_depth=16, min_samples_leaf=2,
                 class_weight="balanced", random_state=42, n_jobs=1)
SHARDS = {
    "train": "train-00000-of-00003-71b0c72c7a610c87.parquet",
    "val": "val-00000-of-00001-7df994b1ccb91e45.parquet",
    "test": "test-00000-of-00002-d36150432d358f48.parquet",
}


class RangeSource(io.RawIOBase):
    """Seekable reader with a hard per-shard transfer ceiling."""

    def __init__(self, url, budget=48 * 1024**2):
        super().__init__()
        self.url, self.budget, self.position = url, budget, 0
        data, self.size = self._range(0, 3)
        if data != b"PAR1":
            raise ValueError("Expected original Parquet header")

    def _range(self, start, end):
        size = end - start + 1
        if size > self.budget:
            raise ValueError("Parquet range budget exceeded")
        request = Request(f"{self.url}?range={start}-{end}",
                          headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"})
        with urlopen(request, timeout=45) as response:
            match = re.fullmatch(rf"bytes {start}-{end}/(\d+)", response.headers.get("Content-Range", ""))
            if response.status != 206 or not match:
                raise ValueError("Source did not honor the bounded byte range")
            total = int(match[1])
            if hasattr(self, "size") and total != self.size:
                raise ValueError("Shard length changed during read")
            data = response.read(size + 1)
        if len(data) != size:
            raise ValueError("Truncated Parquet range")
        self.budget -= size
        return data, total

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        target = {0: 0, 1: self.position, 2: self.size}[whence] + offset
        if target < 0:
            raise ValueError("Negative Parquet seek")
        self.position = target
        return target

    def read(self, size=-1):
        remaining = max(0, self.size - self.position)
        size = remaining if size < 0 else min(size, remaining)
        if not size:
            return b""
        data, _ = self._range(self.position, self.position + size - 1)
        self.position += size
        return data


def decode(asset, mode, label=False):
    with Image.open(io.BytesIO(asset["bytes"])) as image:
        if image.size != (256, 256) or image.mode != mode:
            raise ValueError("Unexpected MineNetCD patch geometry or channels")
        if label and image.format != "PNG":
            raise ValueError(f"Source label encoding {image.format} is not verified lossless")
        return np.array(image)


def patch_arrays(row):
    before = decode(row["imageA"], "RGB").astype(np.int16)
    after = decode(row["imageB"], "RGB").astype(np.int16)
    mask = decode(row["label"], "L", label=True)
    valid = (mask == 0) | (mask == 255)
    return (after - before)[valid], (mask[valid] == 255).astype(np.uint8), int((~valid).sum())


def prepare(output):
    if output.exists():
        raise ValueError("Choose a new external output directory")
    roster = verify_roster({split: metadata("statistics", split=split) for split in SPLITS})
    batches, report = {}, {}
    for split, shard in SHARDS.items():
        url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{shard}"
        with RangeSource(url) as source:
            parquet = pq.ParquetFile(source)
            if set(parquet.schema_arrow.names) != {"domain", "imageA", "imageB", "label"}:
                raise ValueError("Unexpected source Parquet schema")
            rows = parquet.read_row_group(0, use_threads=False).slice(0, 5).to_pylist()
        features, labels, excluded, patches = [], [], 0, []
        for index, row in enumerate(rows):
            site = row["domain"]
            if site not in roster[split]:
                raise ValueError("Patch site does not belong to its official split")
            x, y, unknown = patch_arrays(row)
            features.append(x)
            labels.append(y)
            excluded += unknown
            patches.append(dict(site=site, shard=shard, row=index))
        y = np.concatenate(labels)
        counts = np.bincount(y, minlength=2).tolist()
        if not all(counts):
            raise ValueError(f"{split} pilot subset lacks both mask classes")
        batches[split] = (np.concatenate(features), y)
        report[split] = dict(patches=patches, unchanged=counts[0], changed=counts[1], excluded=excluded)
    output.mkdir(parents=True)
    for split, (x, y) in batches.items():
        np.savez_compressed(output / f"{split}.npz", features=x, labels=y)
    manifest = dict(dataset=DATASET, revision=REVISION, official_roster=roster, splits=report,
                    features=["after_minus_before_R", "after_minus_before_G", "after_minus_before_B"],
                    rf=RF_CONFIG, scope="external ingestion pilot; one site per split may limit inference",
                    selection="fixed threshold 0.5; never select with test data")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(prepare(root / "outputs/external_minenetcd256/rf_pilot_v1"), indent=2))
