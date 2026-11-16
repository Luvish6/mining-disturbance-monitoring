"""Preregister a quarantined RF holdout, then evaluate only in a separate invocation."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import pickle

import numpy as np
import pyarrow.parquet as pq

from scripts import minenetcd256_planner as base
from scripts import minenetcd256_phase17d as fit
from scripts.minenetcd256_efficient import RangeJournal

TEST = (base.SHARDS["test"], "test-00001-of-00002-cd778c8ae2b173af.parquet")
RF = "937c5c8c7165c0e0bc19425a48136a10dbe4ae009067249669c785e443bcf5bc"
CUTOFF = .65
PER_SITE = 4
METRICS = ["confusion_matrix", "precision", "recall", "f1", "iou", "fpr", "worst_mine_fpr"]


def read(path):
    return json.loads(path.read_bytes())


def model_contract(root):
    run = root / "phase17d_run"
    metrics = read(run / "metrics.json")
    settings = read(run / "run.json")
    if (fit.file_hash(run / "rf.pkl") != RF or metrics["rf_fit"]["sha256"] != RF
            or metrics["rf"]["operating_threshold"] != CUTOFF or settings["rf"] != fit.RF_CONFIG
            or settings["selection"] != fit.FROZEN or settings["manifest"] != fit.RECEIPT):
        raise ValueError("Frozen RF checkpoint or training contract differs")
    return dict(sha256=RF, threshold=CUTOFF, settings=settings["rf"],
                features=["after_R-before_R", "after_G-before_G", "after_B-before_B"],
                calibration="none", run_sha256=fit.file_hash(run / "run.json"),
                metrics_sha256=fit.file_hash(run / "metrics.json"))


def audit(root):
    """Require all known test receipts and inventory remaining local experiment JSON."""
    viewer = read(root / "phase10c.json")
    if viewer["revision"] != base.REVISION:
        raise ValueError("Official roster revision differs")
    base.load_roster(root / "phase10c.json")
    roster = viewer["official_roster"]["test"]
    accesses = [
        dict(site=r["site_id"], viewer_row=r["row_index"], source_sha256=r["assets"])
        for r in viewer["patches"] if r["split"] == "test"
    ]
    known = {"phase10c.json", "rf_pilot_v1/manifest.json", "heldout_v1/split_manifest.json",
             "heldout_v1/test_selection.json", "heldout_v1/test_manifest.json",
             "improve_holdout_v1/test_selection.json", "improve_holdout_v1/manifest.json",
             "improve_holdout_v1/frozen.json"}
    if read(root / "heldout_v1/split_manifest.json")["test_shard"] != TEST[0]:
        raise ValueError("Prior holdout shard provenance differs")
    for r in read(root / "rf_pilot_v1/manifest.json")["splits"]["test"]["patches"]:
        if r["shard"] != TEST[0]:
            raise ValueError("Unexpected previous test source")
        accesses.append(dict(site=r["site"], shard=r["shard"], group=0, row=r["row"]))
    for directory, filename in (("heldout_v1", "test_manifest.json"), ("improve_holdout_v1", "manifest.json")):
        selection = read(root / directory / "test_selection.json")
        records = read(root / directory / filename)
        expected = {(s, g, r) for s, items in selection.items() for g, r in items}
        actual = {(r["site"], r["row_group"], r["row"]) for r in records}
        if expected != actual or len(records) != len(expected):
            raise ValueError("Prior TEST selection and provenance disagree")
        accesses.extend(dict(site=r["site"], shard=TEST[0], group=r["row_group"], row=r["row"],
                             source_sha256=r["source_sha256"]) for r in records)
    frozen = {r["site"] for r in accesses}
    if frozen != {"America_02", "Brazil_02", "Brazil_03", "Brunei_01", "Canada_01", "Canada_02"}:
        raise ValueError("Historical direct exposure records differ")
    inventory = {}
    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(root).as_posix()
        # Future phase directories are excluded from this immutable historical inventory.
        if rel.startswith(("phase17f_", "phase17g_")):
            continue
        payload = read(path)
        inventory[rel] = fit.file_hash(path)
        pending = [payload]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                site = item.get("site", item.get("site_id"))
                if isinstance(site, str) and site in roster and site not in frozen:
                    raise ValueError(f"Unaccounted prior TEST site in {rel}: {site}")
                source = item.get("shard", item.get("test_shard"))
                if isinstance(source, str) and source.startswith("test-") and source != TEST[0]:
                    raise ValueError(f"Unaccounted prior TEST shard in {rel}")
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
    if not known <= inventory.keys():
        raise ValueError("Missing prior exposure record")
    return roster, accesses, inventory


def pick(groups, eligible, limit, overhead):
    """Exact bounded group search: site coverage, prefix diversity, then bytes."""
    if len(groups) > 20:
        raise ValueError("Unexpected TEST row-group count")
    best = None
    for n in range(1, len(groups) + 1):
        for indices in combinations(range(len(groups)), n):
            cost = overhead + sum(groups[g]["cost"] for g in indices)
            if cost > limit:
                continue
            counts = Counter(s for g in indices for s in groups[g]["domains"] if s in eligible)
            sites = {s for s, count in counts.items() if count >= PER_SITE}
            if not sites:
                continue
            score = (-len(sites), -len({s.rsplit("_", 1)[0] for s in sites}), cost,
                     base.digest([42, indices]))
            if best is None or score < best[0]:
                best = score, indices, sites
    if best is None:
        raise ValueError("No eligible bounded TEST selection")
    return best[1:]


def prior_bytes(root):
    b = read(root / "phase17b_plan/primary.json")
    c = read(root / "phase17c_plan/primary.json")
    journal = read(root / "phase17c_acquired/transfer.json")
    base.verify(c)
    if (base.seal({k: v for k, v in b.items() if k != "sha256"}) != b
            or c["sha256"] != fit.FROZEN or journal["selection_sha256"] != fit.FROZEN
            or journal["charged"] < journal["downloaded"] or journal["downloaded"] != c["acquisition_bytes"]):
        raise ValueError("Development transfer receipts disagree")
    return b["metadata_bytes"] + c["metadata_bytes"] + journal["charged"]


def plan(root, scanner=base.scan):
    roster, exposed, inventory = audit(root)
    model = model_contract(root)
    consumed = prior_bytes(root)
    traffic = 0
    scans = {}
    for shard in TEST:
        scans[shard] = scanner(shard, base.CAP - consumed - traffic)
        traffic += scans[shard][2]["metadata_bytes"]
    first, second = (scans[s][0] for s in TEST)
    if Counter(s for groups in (first, second) for group in groups for s in group) != Counter(roster):
        raise ValueError("Pinned TEST metadata does not match the official roster")
    for item in exposed:
        if "group" in item and first[item["group"]][item["row"]] != item["site"]:
            raise ValueError("Historical TEST row identity does not match pinned domains")
    quarantined = {s for group in first for s in group} | {r["site"] for r in exposed}
    eligible = set(roster) - quarantined
    fields, source = scans[TEST[1]][1:]
    groups = []
    for domains, columns in zip(second, fields, strict=True):
        ranges = sorted(r for field in columns.values() for r in field)
        groups.append(dict(domains=domains, ranges=ranges, cost=sum(b-a for a, b in ranges)))
    selected_groups, sites = pick(groups, eligible, base.CAP-consumed-traffic,
                                  source["acquisition_header_footer_bytes"])
    rows = defaultdict(list)
    for g in selected_groups:
        for index, site in enumerate(groups[g]["domains"]):
            if site in sites:
                rows[site].append((TEST[1], g, index))
    patches = base.select(rows, base.site_order(sites), PER_SITE)
    used = sorted({r["group"] for r in patches})
    reads = [dict(group=g, ranges=groups[g]["ranges"]) for g in used]
    estimate = source["acquisition_header_footer_bytes"] + sum(groups[g]["cost"] for g in used)
    return base.seal(dict(dataset=base.DATASET, revision=base.REVISION, seed=42, model=model,
                          cap_bytes=base.CAP, prior_bytes=consumed, planning_bytes=traffic,
                          metadata_bytes=consumed+traffic, acquisition_bytes=estimate,
                          sources={s: scans[s][2] for s in TEST}, eligible=sorted(eligible),
                          quarantined=sorted(quarantined), prior_access=exposed, audit_sha256=inventory,
                          patches=patches, reads=reads, metrics=METRICS, per_site=PER_SITE,
                          strata=["mine", "change_present", "zero_change"], undefined_recall=None,
                          rule="maximize eligible site count then prefix diversity, minimize bytes, seed hash tie; equidistant rows",
                          feature_limits="No crop coordinates, no replicated-geometry independence claim; archive group selection bias",
                          test_tuning=False))


def verify(root, receipt, expected):
    body = {k: v for k, v in receipt.items() if k != "sha256"}
    roster, exposure, inventory = audit(root)
    sites = Counter(r["site"] for r in receipt["patches"])
    if (base.seal(body) != receipt or receipt["sha256"] != expected
            or receipt["dataset"] != base.DATASET or receipt["revision"] != base.REVISION
            or receipt["model"] != model_contract(root) or receipt["audit_sha256"] != inventory
            or receipt["prior_access"] != exposure or receipt["prior_bytes"] != prior_bytes(root)
            or receipt["metadata_bytes"] != receipt["prior_bytes"] + receipt["planning_bytes"]
            or not 0 < receipt["acquisition_bytes"] <= base.CAP-receipt["metadata_bytes"]
            or set(sites.values()) != {PER_SITE} or not sites.keys() <= set(receipt["eligible"]) <= roster.keys()
            or sites.keys() & (set(receipt["quarantined"]) | {r["site"] for r in exposure})
            or len({r["patch_id"] for r in receipt["patches"]}) != len(receipt["patches"])
            or any(r["shard"] != TEST[1] for r in receipt["patches"])
            or receipt["metrics"] != METRICS or receipt["test_tuning"] is not False):
        raise ValueError("Holdout freeze, checkpoint, quarantine or budget check failed")


def evaluate(root, receipt, expected, out):
    verify(root, receipt, expected)
    data = fit.load(root / "phase17c_plan/primary.json", root / "phase17c_acquired", root / "phase10c.json")
    seen = {sha256(frame.tobytes()).hexdigest() for rows in data.values() for _, a, b, _ in rows for frame in (a, b)}
    model = pickle.loads((root / "phase17d_run/rf.pkl").read_bytes())
    if model.get_params() != {**model.get_params(), **fit.RF_CONFIG} or list(model.classes_) != [0, 1]:
        raise ValueError("Loaded model differs from the RF contract")
    out.mkdir()
    journal = RangeJournal(out, receipt)
    shard = TEST[1]
    url = f"https://huggingface.co/datasets/{base.DATASET}/resolve/{base.REVISION}/data/{shard}"
    totals = defaultdict(lambda: np.zeros(4, dtype=np.int64))
    records, pairs = [], set()
    with journal.source(url, receipt["acquisition_bytes"]) as source:
        md, start, digest = base.footer(source)
        frozen = receipt["sources"][shard]
        if (source.size, digest) != (frozen["size"], frozen["footer_sha256"]):
            raise ValueError("TEST source identity changed")
        chunks = base.chunks(md, start)
        parquet = pq.ParquetFile(source, metadata=md, pre_buffer=False)
        for entry in receipt["reads"]:
            group = entry["group"]
            source.allowed = sorted(r for field in chunks[group].values() for r in field)
            if entry["ranges"] != [list(r) for r in source.allowed]:
                raise ValueError("TEST range differs from freeze")
            table = parquet.read_row_group(group, use_threads=False)
            for key in (r for r in receipt["patches"] if r["group"] == group):
                row = table.slice(key["row"], 1).to_pylist()[0]
                if row["domain"] != key["site"]:
                    raise ValueError("TEST row domain differs from freeze")
                a, b = [base.decode(row[k], "RGB") for k in base.ASSETS[:2]]
                mask = base.decode(row["label"], "L", label=True)
                pair = tuple(sha256(x.tobytes()).hexdigest() for x in (a, b))
                if set(pair) & seen or pair in pairs or not np.isin(mask, [0, 255]).all():
                    raise ValueError("Duplicate RGB or nonbinary TEST mask")
                pairs.add(pair)
                y = mask.ravel() == 255
                pred = model.predict_proba(fit.delta(a, b))[:, 1] >= CUTOFF
                cm = np.bincount(2*y+pred, minlength=4)
                for name in ("pooled", "mine:"+key["site"], "change_present" if y.any() else "zero_change"):
                    totals[name] += cm
                records.append(dict(key, source_sha256={k: sha256(row[k]["bytes"]).hexdigest()
                                                      for k in base.ASSETS}))
    if len(records) != len(receipt["patches"]) or journal.state["downloaded"] != receipt["acquisition_bytes"]:
        raise ValueError("Incomplete TEST support or differing transfer")
    metrics = {key: fit.describe(cm) for key, cm in totals.items()}
    fprs = [r["fpr"] for key, r in metrics.items() if key.startswith("mine:") and r["fpr"] is not None]
    base.write(out / "metrics.json", dict(freeze=expected, metrics=metrics, records=records,
                                          worst_mine_fpr=max(fprs) if fprs else None,
                                          bytes=journal.state["downloaded"]))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="action", required=True)
    setup = commands.add_parser("plan")
    setup.add_argument("root", type=Path)
    setup.add_argument("receipt", type=Path)
    run = commands.add_parser("evaluate")
    run.add_argument("root", type=Path)
    run.add_argument("receipt", type=Path)
    run.add_argument("sha256")
    run.add_argument("output", type=Path)
    args = cli.parse_args()
    if args.action == "plan":
        if args.receipt.exists():
            cli.error("Choose a new preregistration receipt")
        receipt = plan(args.root)
        base.write(args.receipt, receipt)
        print(receipt["sha256"])
    else:
        evaluate(args.root, read(args.receipt), args.sha256, args.output)


if __name__ == "__main__":
    main()
