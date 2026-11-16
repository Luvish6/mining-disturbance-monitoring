"""Freeze label-blind development rows from the pinned MineNetCD256 release."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import struct

import numpy as np
import pyarrow.parquet as pq

from scripts.minenetcd256_adapter import SPLITS
from scripts.minenetcd256_rf_pilot import DATASET, REVISION, SHARDS, RangeSource, decode

CAP = 512 * 1024**2
SEED = 42
SOURCES = {
    "train": (SHARDS["train"], "train-00001-of-00003-35e4fc5a06f6d361.parquet",
              "train-00002-of-00003-aa08409b2f32c17e.parquet"),
    "val": (SHARDS["val"],),
}
ASSETS = ("imageA", "imageB", "label")


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class GuardedSource(RangeSource):
    """Require each PyArrow read to fit in one authorized column chunk."""

    def read(self, size=-1):
        if size == 0:
            return b""
        if size < 0 or not any(start <= self.position and self.position + size <= end
                               for start, end in self.allowed):
            raise ValueError("Unplanned Parquet byte range")
        return super().read(size)


def footer(source):
    # PyArrow's default footer read can include image bytes. Fetch exactly the footer.
    tail, _ = source._range(source.size - 8, source.size - 1)
    length, magic = struct.unpack("<I4s", tail)
    start = source.size - 8 - length
    if magic != b"PAR1" or start < 4 or not length or length > 16 * 1024**2:
        raise ValueError("Invalid Parquet footer")
    body, _ = source._range(start, source.size - 9)
    metadata = pq.read_metadata(io.BytesIO(b"PAR1" + body + tail))
    return metadata, start, sha256(body + tail).hexdigest()


def chunks(metadata, footer_start):
    groups = []
    for index in range(metadata.num_row_groups):
        group = metadata.row_group(index)
        fields = defaultdict(list)
        for column in range(group.num_columns):
            c = group.column(column)
            start = min(c.dictionary_page_offset or c.data_page_offset, c.data_page_offset)
            end = start + c.total_compressed_size
            if c.file_path or not 4 <= start < end <= footer_start:
                raise ValueError("Unexpected Parquet column chunk bounds")
            fields[c.path_in_schema.split(".")[0]].append((start, end))
        if set(fields) != {*ASSETS, "domain"} or len(fields["domain"]) != 1:
            raise ValueError("Unexpected development shard schema")
        groups.append(dict(fields))
    ranges = sorted(r for group in groups for field in group.values() for r in field)
    if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
        raise ValueError("Overlapping Parquet chunks")
    return groups


def scan(shard, budget, source_type=GuardedSource):
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{shard}"
    with source_type(url, budget) as source:
        metadata, start, footer_hash = footer(source)
        ranges = chunks(metadata, start)
        parquet = pq.ParquetFile(source, metadata=metadata, pre_buffer=False)
        groups = []
        for index, fields in enumerate(ranges):
            source.allowed = fields["domain"]
            domains = parquet.read_row_group(index, columns=["domain"], use_threads=False)["domain"].to_pylist()
            if len(domains) != metadata.row_group(index).num_rows:
                raise ValueError("Parquet domain row count mismatch")
            groups.append(domains)
        receipt = dict(size=source.size, footer_sha256=footer_hash,
                       metadata_bytes=budget - source.budget,
                       acquisition_header_footer_bytes=source.size - start + 4)
    return groups, ranges, receipt


def load_roster(path):
    saved = json.loads(path.read_bytes())
    if saved["dataset"] != DATASET or saved["revision"] != REVISION:
        raise ValueError("Roster revision mismatch")
    roster = saved["official_roster"]
    seen = set()
    for split, (sites, count) in SPLITS.items():
        values = roster[split]
        if (len(values) != sites or sum(values.values()) != count or seen.intersection(values)
                or any(not re.fullmatch(r"[A-Za-z]+_[0-9]+", k) or type(v) is not int or v < 1
                       for k, v in values.items())):
            raise ValueError("Invalid official site roster")
        seen.update(values)
    return {s: roster[s] for s in SOURCES}


def site_order(sites):
    # Published domain names supply the geographic prefix (e.g. Australia_01).
    # Keep the publisher's names, including America, without inferring countries.
    groups = defaultdict(list)
    for site in sites:
        groups[site.rpartition("_")[0] or "UNKNOWN"].append(site)
    rank = lambda name: (digest([SEED, name]), name)
    ordered = [sorted(groups[key], key=rank) for key in sorted(groups, key=rank)]
    return [group[i] for i in range(max(map(len, ordered))) for group in ordered if i < len(group)]


def select(rows, sites, count):
    selected = []
    for site in sites:
        population = rows[site]
        if len(population) < count:
            raise ValueError("Insufficient rows for selected site")
        for i in range(count):
            shard, group, row = population[i * (len(population) - 1) // (count - 1)]
            selected.append(dict(site=site, shard=shard, group=group, row=row,
                                 patch_id=f"{REVISION}:{shard}:{group}:{row}"))
    return selected


def build(roster, scanner=scan, cap=CAP):
    receipts, ranges, selected_sites, rows = {}, {}, {}, {}
    for split, shards in SOURCES.items():
        split_rows = defaultdict(list)
        for shard in shards:
            remaining = cap - sum(item["metadata_bytes"] for item in receipts.values())
            groups, ranges[shard], receipts[shard] = scanner(shard, remaining)
            if receipts[shard]["metadata_bytes"] > remaining:
                raise ValueError("Metadata exceeded transfer cap")
            for group, domains in enumerate(groups):
                for row, site in enumerate(domains):
                    split_rows[site].append((shard, group, row))
        if Counter({site: len(items) for site, items in split_rows.items()}) != Counter(roster[split]):
            raise ValueError(f"{split} Parquet rows disagree with official roster")
        rows[split] = split_rows
        selected_sites[split] = site_order(split_rows)[:20 if split == "train" else 10]
    metadata_bytes = sum(item["metadata_bytes"] for item in receipts.values())
    plans = {}
    for variant, counts in (("primary", (12, 8)), ("fallback", (6, 4))):
        patches = {s: select(rows[s], selected_sites[s], n) for s, n in zip(SOURCES, counts, strict=True)}
        used = sorted({(r["shard"], r["group"]) for split in patches.values() for r in split})
        # Acquisition uses the same guarded reader with prebuffering disabled.
        # Charge each physical chunk once, including domain verification and nested image fields.
        reads = [{"shard": shard, "group": group, "ranges": sorted(
            r for column in ranges[shard][group].values() for r in column)}
            for shard, group in used]
        transfer = sum(end - start for group in reads for start, end in group["ranges"])
        transfer += sum(receipts[s]["acquisition_header_footer_bytes"] for s in {s for s, _ in used})
        manifest = dict(dataset=DATASET, revision=REVISION, seed=SEED, variant=variant, patches=patches,
                        sources=receipts, reads=reads, metadata_bytes=metadata_bytes,
                        acquisition_bytes=transfer, total_bytes=metadata_bytes + transfer, cap_bytes=cap)
        plans[variant] = seal(manifest)
    decision = next((key for key, plan in plans.items() if plan["total_bytes"] <= cap), "blocked")
    return plans, decision


def seal(manifest):
    return {**manifest, "sha256": digest(manifest)}


def verify(manifest):
    body = {k: v for k, v in manifest.items() if k != "sha256"}
    if (seal(body) != manifest or manifest["dataset"] != DATASET or manifest["revision"] != REVISION
            or not 0 < manifest["total_bytes"] <= manifest["cap_bytes"] <= CAP
            or manifest["total_bytes"] != manifest["metadata_bytes"] + manifest["acquisition_bytes"]
            or set(manifest["patches"]) != set(SOURCES)
            or any(row["shard"] not in SOURCES[split]
                   for split, rows in manifest["patches"].items() for row in rows)
            or set(manifest["sources"]) != {s for split in SOURCES.values() for s in split}):
        raise ValueError("Invalid, over-cap or altered acquisition manifest")


def acquire(manifest, out, *, source_factory=GuardedSource, resume=False):
    verify(manifest)
    out.mkdir(exist_ok=resume)
    remaining = manifest["acquisition_bytes"]
    records, fingerprints = [], {}
    for split, shards in SOURCES.items():
        for shard in shards:
            rows = [r for r in manifest["patches"][split] if r["shard"] == shard]
            if not rows:
                continue
            url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{shard}"
            with source_factory(url, remaining) as source:
                metadata, start, footer_hash = footer(source)
                receipt = manifest["sources"][shard]
                if (source.size, footer_hash) != (receipt["size"], receipt["footer_sha256"]):
                    raise ValueError("Parquet source changed since preflight")
                ranges = chunks(metadata, start)
                parquet = pq.ParquetFile(source, metadata=metadata, pre_buffer=False)
                for group in sorted({r["group"] for r in rows}):
                    source.allowed = sorted(r for values in ranges[group].values() for r in values)
                    expected = [item["ranges"] for item in manifest["reads"]
                                if item["shard"] == shard and item["group"] == group]
                    if expected != [[list(r) for r in source.allowed]]:
                        raise ValueError("Acquisition ranges disagree with preflight")
                    table = parquet.read_row_group(group, use_threads=False)
                    for key in (r for r in rows if r["group"] == group):
                        item = table.slice(key["row"], 1).to_pylist()[0]
                        if item["domain"] != key["site"]:
                            raise ValueError("Frozen site identity mismatch")
                        a, b = (decode(item[k], "RGB") for k in ASSETS[:2])
                        label = decode(item["label"], "L", label=True)
                        if not np.isin(label, [0, 255]).all():
                            raise ValueError("Source mask is not binary")
                        for asset in (a, b):
                            fingerprint = sha256(asset.tobytes()).hexdigest()
                            if fingerprints.setdefault(fingerprint, split) != split:
                                raise ValueError("Identical RGB observation across splits")
                        target = out / f"{digest(key['patch_id'])}.npz"
                        np.savez_compressed(target, before=a, after=b, mask=label)
                        records.append(dict(key, split=split, file=target.name,
                                            sha256=sha256(target.read_bytes()).hexdigest(),
                                            changed=int((label == 255).sum()),
                                            source_sha256={k: sha256(item[k]["bytes"]).hexdigest() for k in ASSETS}))
                remaining = source.budget
    write(out / "manifest.json", dict(selection_sha256=manifest["sha256"],
                                     bytes=manifest["acquisition_bytes"] - remaining, patches=records))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "acquire"))
    parser.add_argument("input", type=Path, help="Saved Phase 10C roster or frozen selection manifest")
    parser.add_argument("output", type=Path, help="New local output directory")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new local output directory")
    if args.action == "acquire":
        acquire(json.loads(args.input.read_bytes()), args.output)
        return
    plans, decision = build(load_roster(args.input))
    args.output.mkdir()
    for key, plan in plans.items():
        write(args.output / f"{key}.json", plan)
    write(args.output / "transfer.json", dict(decision=decision,
          estimates={key: {k: plan[k] for k in ("metadata_bytes", "acquisition_bytes", "total_bytes", "cap_bytes")}
                     for key, plan in plans.items()}))
    summary = "\n".join([f"Cap decision: {decision} (limit {CAP:,} bytes)",
                         *(f"{key}: {plan['total_bytes']:,} bytes including "
                           f"{plan['metadata_bytes']:,} metadata bytes" for key, plan in plans.items())])
    (args.output / "summary.txt").write_text(summary + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
