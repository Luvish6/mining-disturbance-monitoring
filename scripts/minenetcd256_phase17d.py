"""Offline Phase 17D training on the frozen Phase 17C development cache."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import io
import json
import pickle
from pathlib import Path
import re
from statistics import median
from time import monotonic, process_time

import numpy as np
import torch
from sklearn.ensemble import RandomForestClassifier

from scripts import minenetcd256_planner as planner
from scripts.minenetcd256_rf_multi import sample_training
from scripts.minenetcd256_rf_pilot import RF_CONFIG
from src.phase3.model import SiameseUNet, masked_loss

FROZEN = "7ad4f2aca7055029c0f5ac99bee7cda61fbb04fe3403c3557620ec652ed99209"
RECEIPT = "d47a84e1b7a2c0fd640fded1fb467c92e306ae8e05a5b827d29ec8ca55f79467"
THRESHOLDS = (.25, .35, .50, .65, .75, .90, .95)
RECALL_FLOOR = .20
EPOCHS = 5
WALL = 1800


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def verify_arrays(raw, record):
    if sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError("Cached patch hash mismatch")
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        a, b, mask = (data[k] for k in ("before", "after", "mask"))
    if (a.shape != (256, 256, 3) or b.shape != a.shape or mask.shape != a.shape[:2]
            or any(x.dtype != np.uint8 for x in (a, b, mask)) or not np.isin(mask, [0, 255]).all()
            or np.count_nonzero(mask) != record["changed"]):
        raise ValueError("RGB or binary mask validation failed")
    return a, b, mask != 0


def load(selection, cache, roster_path):
    plan = json.loads(selection.read_bytes())
    planner.verify(plan)
    receipt = (cache / "manifest.json").read_bytes()
    if sha256(receipt).hexdigest() != RECEIPT:
        raise ValueError("Frozen acquisition receipt hash mismatch")
    manifest = json.loads(receipt)
    roster = planner.load_roster(roster_path)
    if (plan["sha256"] != FROZEN or manifest["selection_sha256"] != FROZEN
            or manifest["bytes"] != plan["acquisition_bytes"]):
        raise ValueError("Wrong frozen Phase 17C primary selection")
    records = {r["patch_id"]: r for r in manifest["patches"]}
    if len(records) != len(manifest["patches"]) or len(records) != 320:
        raise ValueError("Missing or duplicate cached rows")
    datasets, site_sets, epochs, pairs = {}, {}, {}, set()
    for split, n_sites, per_site in (("train", 20, 12), ("val", 10, 8)):
        data = []
        counts = Counter(k["site"] for k in plan["patches"][split])
        if len(counts) != n_sites or set(counts.values()) != {per_site} or counts.keys() - roster[split].keys():
            raise ValueError("Official split or frozen site counts disagree")
        site_sets[split] = set(counts)
        for key in plan["patches"][split]:
            record = records.pop(key["patch_id"])
            name = planner.digest(key["patch_id"]) + ".npz"
            hashes = record["source_sha256"]
            if (record["file"] != name or record["split"] != split
                    or any(record[k] != v for k, v in key.items())
                    or set(hashes) != set(planner.ASSETS)
                    or any(not re.fullmatch(r"[a-f0-9]{64}", h) for h in hashes.values())):
                raise ValueError("Patch provenance mismatch")
            a, b, label = verify_arrays((cache / name).read_bytes(), record)
            frames = tuple(sha256(x.tobytes()).hexdigest() for x in (a, b))
            if frames in pairs or any(epochs.setdefault(h, split) != split for h in frames):
                raise ValueError("Duplicate pair or cross-split RGB observation")
            pairs.add(frames)
            data.append((key, a, b, label))
        if len({k["site"] for k, _, _, y in data if y.any()}) < 3 or not any((~y).any() for _, _, _, y in data):
            raise ValueError("Insufficient class support")
        datasets[split] = data
    if records or site_sets["train"] & site_sets["val"]:
        raise ValueError("Extra rows or split leakage")
    return datasets


def tensors(row):
    _, a, b, label = row
    x1, x2 = (torch.from_numpy(x).permute(2, 0, 1)[None].float() / 255 for x in (a, b))
    y = torch.from_numpy(label)[None, None].float()
    return x1, x2, y, torch.ones_like(y, dtype=torch.bool)


def delta(a, b):
    return (b.astype(np.int16) - a).reshape(-1, 3)


def rf_training(rows):
    per_mine = defaultdict(list)
    for key, a, b, mask in rows:
        per_mine[key["site"]].append((delta(a, b), mask.ravel().astype(np.uint8)))
    mines = {site: (np.concatenate([x for x, _ in items]),
                    np.concatenate([y for _, y in items]), None)
             for site, items in sorted(per_mine.items())}
    return sample_training(mines)


def describe(cm):
    tn, fp, fn, tp = (int(v) for v in cm)
    def fraction(a, b):
        return a / b if b else None
    return dict(confusion_matrix=[[tn, fp], [fn, tp]], precision=fraction(tp, tp + fp),
                recall=fraction(tp, tp + fn), f1=fraction(2 * tp, 2 * tp + fp + fn),
                iou=fraction(tp, tp + fp + fn), fpr=fraction(fp, tn + fp), positives=tp + fn)


def operating(entries):
    valid = [row for row in entries if row["median_site_recall"] is not None
             and row["median_site_recall"] >= RECALL_FLOOR]
    return min(valid, key=lambda row: (row["worst_site_fpr"], -row["median_site_recall"],
                                      -row["threshold"]))["threshold"] if valid else None


def evaluate(rows, predict, check):
    totals = {t: defaultdict(lambda: np.zeros(4, dtype=np.int64)) for t in THRESHOLDS}
    for row in rows:
        check()
        key, _, _, y = row
        y = y.ravel()
        probability = np.asarray(predict(row)).ravel()
        if probability.shape != y.shape or not np.isfinite(probability).all() or not ((0 <= probability) & (probability <= 1)).all():
            raise ValueError("Invalid validation probabilities")
        for t, groups in totals.items():
            cm = np.bincount(2 * y + (probability >= t), minlength=4)
            for name in ("pooled", f"mine:{key['site']}", "change_present" if y.any() else "zero_change"):
                groups[name] += cm
    report = []
    for t, groups in totals.items():
        results = {name: describe(cm) for name, cm in sorted(groups.items())}
        mines = [item for name, item in results.items() if name.startswith("mine:")]
        recalls = [m["recall"] for m in mines if m["recall"] is not None]
        fprs = [m["fpr"] for m in mines if m["fpr"] is not None]
        report.append(dict(threshold=t, metrics=results,
                           median_site_recall=median(recalls) if recalls else None,
                           worst_site_fpr=max(fprs) if fprs else None))
    return dict(operating_threshold=operating(report), thresholds=report)


def memory():
    try:
        import psutil
        info = psutil.Process().memory_info()
        return getattr(info, "peak_wset", info.rss)
    except ImportError:
        return None


def atomic(path, value, writer):
    temp = path.with_suffix(".tmp")
    writer(temp, value)
    temp.replace(path)


def fit_siamese(train, val, identity, out, check):
    torch.manual_seed(42)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    model = SiameseUNet(channels=3, width=16)
    optim = torch.optim.Adam(model.parameters(), lr=.001)
    history = []
    checkpoints = sorted(out.glob("epoch-*.pt"))
    if checkpoints:
        state = torch.load(checkpoints[-1], map_location="cpu", weights_only=True)
        if state["identity"] != identity:
            raise ValueError("Checkpoint run identity differs")
        model.load_state_dict(state["model"])
        optim.load_state_dict(state["optimizer"])
        history = state["history"]

    def epoch_pass(rows, order, training):
        model.train(training)
        loss_sum = 0.
        with torch.set_grad_enabled(training):
            for i in order:
                check()
                a, b, y, valid = tensors(rows[i])
                loss = masked_loss(model(a, b), y, valid)
                if training:
                    optim.zero_grad()
                    loss.backward()
                    optim.step()
                loss_sum += loss.item()
        return loss_sum / len(rows)

    for epoch in range(len(history) + 1, EPOCHS + 1):
        start, cpu = monotonic(), process_time()
        order = torch.randperm(len(train), generator=torch.Generator().manual_seed(42 + epoch)).tolist()
        train_loss = epoch_pass(train, order, True)
        val_loss = epoch_pass(val, range(len(val)), False)
        history.append(dict(epoch=epoch, train=train_loss, val=val_loss,
                            wall=monotonic()-start, cpu=process_time()-cpu, memory_bytes=memory()))
        atomic(out / f"epoch-{epoch}.pt", dict(identity=identity, model=model.state_dict(),
                                              optimizer=optim.state_dict(), history=history),
               lambda path, item: torch.save(item, path))
        print(history[-1], flush=True)
    best = min(history, key=lambda item: item["val"])["epoch"]
    state = torch.load(out / f"epoch-{best}.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    model.eval()
    return model, history, best


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("selection", "cache", "roster", "output"):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    start, cpu = monotonic(), process_time()

    def check():
        if monotonic() - start >= WALL:
            raise TimeoutError("Wall budget elapsed. Resume from completed artifacts.")

    data = load(args.selection, args.cache, args.roster)
    print("Verified 240 TRAIN and 80 validation patches", flush=True)
    train, val = data["train"], data["val"]
    identity = dict(selection=FROZEN, manifest=file_hash(args.cache / "manifest.json"),
                    roster=file_hash(args.roster), code=file_hash(Path(__file__)),
                    epochs=EPOCHS, seed=42, wall_seconds=WALL, threads=2, batch=1, precision="FP32",
                    width=16, channels=3, optimizer="Adam", lr=.001, positive_weight=1.,
                    normalization="fixed divide by 255", thresholds=list(THRESHOLDS),
                    recall_floor=RECALL_FLOOR, rf=RF_CONFIG, rf_cap=100000, torch=str(torch.__version__))
    out = args.output
    out.mkdir(exist_ok=True)
    run = out / "run.json"
    if run.exists():
        if json.loads(run.read_bytes()) != identity or (out / "metrics.json").exists():
            raise ValueError("Run differs or is already complete")
    else:
        if any(out.iterdir()):
            raise ValueError("Expected an unused output directory")
        planner.write(run, identity)

    model, history, best = fit_siamese(train, val, identity, out, check)
    check()
    rf_path, rf_meta = out / "rf.pkl", out / "rf.json"
    if rf_meta.exists():
        rf_info = json.loads(rf_meta.read_bytes())
        if rf_info["sha256"] != file_hash(rf_path):
            raise ValueError("RF checkpoint hash mismatch")
        rf = pickle.loads(rf_path.read_bytes())
    else:
        x, y, sampled = rf_training(train)
        check()
        rf_start, rf_cpu = monotonic(), process_time()
        rf = RandomForestClassifier(**RF_CONFIG).fit(x, y)
        atomic(rf_path, rf, lambda path, item: path.write_bytes(pickle.dumps(item)))
        rf_info = dict(pixels=len(y), counts=sampled, wall=monotonic()-rf_start,
                       cpu=process_time()-rf_cpu, sha256=file_hash(rf_path))
        atomic(rf_meta, rf_info, planner.write)
        print("RF fitted", len(y), "pixels", flush=True)

    with torch.inference_mode():
        siamese = evaluate(val, lambda row: model(*tensors(row)[:2]).sigmoid().numpy(), check)
    forest = evaluate(val, lambda row: rf.predict_proba(delta(row[1], row[2]))[:, 1], check)
    support = [{"patch_id": k["patch_id"], "mask_sha256": sha256(y.tobytes()).hexdigest()}
               for k, _, _, y in val]
    atomic(out / "metrics.json", dict(history=history, best_epoch=best, rf_fit=rf_info,
           siamese=siamese, rf=forest, validation_support=support,
           validation_support_sha256=planner.digest(support),
           checkpoint_sha256={p.name: file_hash(p) for p in sorted(out.glob("epoch-*.pt"))},
           wall=monotonic()-start, cpu=process_time()-cpu, peak_memory_bytes=memory()), planner.write)


if __name__ == "__main__":
    main()
