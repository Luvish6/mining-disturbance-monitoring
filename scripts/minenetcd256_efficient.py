"""Plan and acquire a bounded row-group-aware development sample."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from scripts import minenetcd256_planner as base


def choose(groups, sites, counts, targets, receipts, cap):
    """Maximize domain-prefix diversity, then minimize charged bytes."""
    keys = sorted(groups)
    shards = sorted({key[0] for key in keys})
    domains = [(split, site) for split in base.SOURCES for site in base.site_order(sites[split])]
    prefixes = sorted({site.rsplit("_", 1)[0] for site in sites["train"]})
    variables = keys + shards + domains + prefixes
    indexes = {key: i for i, key in enumerate(variables)}
    rules = []

    def rule(coefficients, low, high):
        rules.append((coefficients, low, high))

    cost = {key: sum(b - a for a, b in groups[key]["ranges"]) for key in keys}
    cost.update({s: receipts[s]["acquisition_header_footer_bytes"] for s in shards})
    rule(cost, 0, cap)
    for key in keys:
        rule({key: 1, key[0]: -1}, -np.inf, 0)
    for split, site in domains:
        support = {key: min(counts[split], groups[key]["domains"][site]) for key in keys
                   if site in groups[key]["domains"]}
        rule({**support, (split, site): -counts[split]}, 0, np.inf)
    for split, target in targets.items():
        rule({key: 1 for key in domains if key[0] == split}, target, target)
    for prefix in prefixes:
        support = {key: 1 for key in domains if key[0] == "train" and key[1].rsplit("_", 1)[0] == prefix}
        rule({**support, prefix: -1}, 0, np.inf)

    matrix = lil_matrix((len(rules), len(variables)))
    for i, (coefficients, _, _) in enumerate(rules):
        for key, value in coefficients.items():
            matrix[i, indexes[key]] = value
    # Integer byte costs dominate the seed-ordered fractional tie preference.
    objective = np.zeros(len(variables))
    for key, value in cost.items():
        objective[indexes[key]] = value
    for prefix in prefixes:
        objective[indexes[prefix]] = -(cap + 1)
    for i, key in enumerate(domains):
        objective[indexes[key]] = (i + 1) / (len(domains) + 1)**2
    result = milp(objective, integrality=np.ones(len(variables)), bounds=Bounds(0, 1),
                  constraints=LinearConstraint(matrix.tocsr(), [r[1] for r in rules], [r[2] for r in rules]),
                  options={"mip_rel_gap": 0.0})
    if result.status == 2:
        return None
    if not result.success:
        raise ValueError(f"Row-group optimization did not converge: {result.message}")
    picked = {key for key, value in zip(variables, result.x, strict=True) if value > .5}
    return [key for key in keys if key in picked], [key for key in domains if key in picked]


def plans(roster, scanner=base.scan, cap=base.CAP):
    if set(roster["train"]) & set(roster["val"]):
        raise ValueError("TRAIN and validation sites overlap")
    groups, receipts = {}, {}
    metadata = 0
    for split, shards in base.SOURCES.items():
        observed = Counter()
        for shard in shards:
            domains, chunks, receipt = scanner(shard, cap - metadata)
            metadata += receipt["metadata_bytes"]
            if metadata > cap:
                raise ValueError("Metadata exceeded transfer cap")
            receipts[shard] = receipt
            for index, (rows, fields) in enumerate(zip(domains, chunks, strict=True)):
                observed.update(rows)
                groups[(shard, index)] = dict(rows=rows, domains=Counter(rows), split=split,
                                             columns=fields, ranges=sorted(r for v in fields.values() for r in v))
        if observed != Counter(roster[split]):
            raise ValueError(f"{split} Parquet rows disagree with official roster")

    alternatives = {}
    for name, pair in (("primary", (12, 8)), ("fallback", (6, 4))):
        counts = dict(zip(base.SOURCES, pair, strict=True))
        # Preserve all validation mines first, then maximize the TRAIN site count up to 20.
        for val in range(10, 0, -1):
            for train in range(20, 0, -1):
                targets = dict(train=train, val=val)
                picked = choose(groups, roster, counts, targets, receipts, cap - metadata)
                if picked:
                    break
            if picked:
                break
        if not picked:
            continue
        keys, sites = picked
        selected = {s: defaultdict(list) for s in base.SOURCES}
        for shard, group in keys:
            info = groups[(shard, group)]
            for index, site in enumerate(info["rows"]):
                selected[info["split"]][site].append((shard, group, index))
        patches = {split: base.select(selected[split], [site for s, site in sites if s == split],
                                      counts[split]) for split in base.SOURCES}
        used = sorted({(r["shard"], r["group"]) for rows in patches.values() for r in rows})
        reads = [dict(shard=s, group=g, ranges=groups[(s, g)]["ranges"],
                      columns=groups[(s, g)]["columns"]) for s, g in used]
        transfer = sum(b - a for entry in reads for a, b in entry["ranges"])
        transfer += sum(receipts[s]["acquisition_header_footer_bytes"] for s in {s for s, _ in used})
        manifest = base.seal(dict(dataset=base.DATASET, revision=base.REVISION, seed=base.SEED,
                                  variant=f"17c-{name}", patches=patches, sources=receipts, reads=reads,
                                  metadata_bytes=metadata, acquisition_bytes=transfer,
                                  total_bytes=metadata + transfer, cap_bytes=cap, targets=targets,
                                  selection_rule="validation sites first, then training sites, TRAIN prefix diversity, bytes; equidistant within retained groups",
                                  prior_cache_credit_bytes=0))
        base.verify(manifest)
        alternatives[name] = manifest
    return alternatives


class RangeJournal:
    """Persist charged requests and verified byte ranges for same-budget resume."""

    def __init__(self, directory, manifest):
        self.directory = directory
        self.path = directory / "transfer.json"
        self.manifest = manifest
        if not self.path.exists():
            if any(directory.iterdir()):
                raise ValueError("Select a new directory or a matching resume journal")
            self.save(dict(selection_sha256=manifest["sha256"], charged=0, downloaded=0, ranges={}))
        self.state = json.loads(self.path.read_bytes())
        if self.state["selection_sha256"] != manifest["sha256"]:
            raise ValueError("Resume journal belongs to another selection")

    def save(self, state):
        temp = self.path.with_suffix(".tmp")
        base.write(temp, state)
        temp.replace(self.path)

    def source(self, url, budget):
        journal = self

        class JournalSource(base.GuardedSource):
            def _range(self, start, end):
                parts = []
                for lo in range(start, end + 1, 4 * 1024**2):
                    hi = min(end, lo + 4 * 1024**2 - 1)
                    size = hi - lo + 1
                    key = base.digest([url, lo, hi])
                    path = journal.directory / f"{key}.range"
                    state = journal.state
                    if key in state["ranges"]:
                        expected, length = state["ranges"][key]
                        data = path.read_bytes()
                        if len(data) != size or sha256(data).hexdigest() != expected:
                            raise ValueError("Corrupt cached source byte range")
                    else:
                        if state["charged"] + size + journal.manifest["metadata_bytes"] > base.CAP:
                            raise ValueError("Aggregate transfer cap exhausted")
                        state["charged"] += size
                        journal.save(state)
                        data, length = super()._range(lo, hi)
                        path.write_bytes(data)
                        state["downloaded"] += size
                        state["ranges"][key] = [sha256(data).hexdigest(), length]
                        journal.save(state)
                    parts.append(data)
                return b"".join(parts), length

        return JournalSource(url, budget)


def acquire(manifest, directory):
    base.verify(manifest)
    if (directory / "manifest.json").exists():
        raise ValueError("Acquisition already complete")
    directory.mkdir(exist_ok=True)
    journal = RangeJournal(directory, manifest)
    try:
        base.acquire(manifest, directory, source_factory=journal.source, resume=True)
    except Exception as error:
        base.write(directory / "blocker.json", dict(error=str(error), selection_sha256=manifest["sha256"]))
        raise


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=("plan", "acquire"))
    cli.add_argument("source", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    if args.action == "acquire":
        acquire(json.loads(args.source.read_bytes()), args.output)
    else:
        if args.output.exists():
            cli.error("Choose a new plan directory")
        result = plans(base.load_roster(args.source))
        args.output.mkdir()
        for name, manifest in result.items():
            base.write(args.output / f"{name}.json", manifest)
            print(name, manifest["targets"], manifest["total_bytes"], flush=True)
        if not result:
            print("No feasible development selection")


if __name__ == "__main__":
    main()
