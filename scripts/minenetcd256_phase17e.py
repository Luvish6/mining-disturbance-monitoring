"""Diagnose and run the single prespecified Phase 17E U-Net recovery."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic, process_time

import numpy as np
import torch

from scripts import minenetcd256_phase17d as baseline
from src.phase3.model import SiameseUNet, masked_loss


def support(rows):
    return [{"patch_id": k["patch_id"], "mask_sha256": sha256(y.tobytes()).hexdigest()}
            for k, _, _, y in rows]


def weight(rows):
    positive = sum(int(y.sum()) for _, _, _, y in rows)
    negative = sum(y.size for _, _, _, y in rows) - positive
    if not positive or not negative:
        raise ValueError("Weight requires both TRAIN classes")
    return dict(positive=positive, negative=negative, pos_weight=min(10., negative / positive))


def setup():
    torch.manual_seed(42)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    model = SiameseUNet(channels=3, width=16)
    return model, torch.optim.Adam(model.parameters(), lr=.001)


def pass_loss(model, optimizer, rows, order, pos_weight, check):
    fitting = optimizer is not None
    model.train(fitting)
    total = 0.
    with torch.set_grad_enabled(fitting):
        for i in order:
            check()
            a, b, y, valid = baseline.tensors(rows[i])
            loss = masked_loss(model(a, b), y, valid, pos_weight=pos_weight)
            if fitting:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total += loss.item()
    return total / len(rows)


def smoke(train):
    # Use a real TRAIN foreground crop for shape/target, with a synthetic visible
    # change cue. No synthetic row enters the real experiment.
    for key, before, _, mask in train:
        hits = np.argwhere(mask)
        if hits.size:
            r, c = np.clip(hits[len(hits) // 2] - 16, 0, 224)
            target = mask[r:r+32, c:c+32].copy()
            if .05 <= target.mean() <= .95:
                break
    else:
        raise ValueError("No mixed TRAIN crop for smoke test")
    a = before[r:r+32, c:c+32].copy()
    b = a.copy()
    b[target] = 255 - a[target]
    row = (key, a, b, target)
    model, optimizer = setup()
    initial = pass_loss(model, None, [row], [0], 1., lambda: None)
    for _ in range(150):
        pass_loss(model, optimizer, [row], [0], 1., lambda: None)
    final = pass_loss(model, None, [row], [0], 1., lambda: None)
    with torch.inference_mode():
        pred = model(*baseline.tensors(row)[:2]).sigmoid().numpy().reshape(target.shape) >= .5
    recall = float(pred[target].mean())
    specificity = float((~pred[~target]).mean())
    if not (final < initial and recall >= .90 and specificity >= .90):
        raise ValueError("TRAIN-only synthetic overfit check failed")
    return dict(initial_loss=initial, final_loss=final, recall=recall, specificity=specificity,
                source_patch=key["patch_id"], crop_origin=[int(r), int(c)], steps=150)


def distribution(rows, predictions):
    y = np.concatenate([row[3].ravel() for row in rows])
    p = np.concatenate(predictions)
    if not np.isfinite(p).all() or not ((0 <= p) & (p <= 1)).all():
        raise ValueError("Invalid sigmoid output")
    bins = np.minimum((p * 10).astype(np.int32), 9)
    counts = np.bincount(bins, minlength=10)
    score_sum = np.bincount(bins, weights=p, minlength=10)
    foreground = np.bincount(bins, weights=y, minlength=10)
    n = len(y)
    calibration = [dict(lower=i/10, upper=(i+1)/10, count=int(k),
                        mean=float(score_sum[i]/k), observed=float(foreground[i]/k))
                   for i, k in enumerate(counts) if k]
    return dict(pixels=n, prevalence=float(y.mean()), mean_score=float(p.mean()),
                brier=float(np.square(p-y).mean()),
                ece=float(np.abs(score_sum-foreground).sum()/n), calibration=calibration,
                class_scores={name: dict(mean=float(p[mask].mean()),
                     quantiles=np.quantile(p[mask], [0, .05, .5, .95, 1]).tolist())
                     for name, mask in (("change", y), ("unchanged", ~y))},
                thresholds=[dict(threshold=t, positive_recall=float((p[y] >= t).mean()),
                                 negative_recall=float((p[~y] < t).mean()),
                                 predicted_positive=float((p >= t).mean())) for t in baseline.THRESHOLDS])


def predict(model, row):
    return model(*baseline.tensors(row)[:2]).sigmoid().numpy().ravel()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=("diagnose", "recover"))
    for name in ("selection", "cache", "roster", "baseline", "output"):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    start, cpu = monotonic(), process_time()

    def check():
        if monotonic() - start >= baseline.WALL:
            raise TimeoutError("Wall budget elapsed. Resume from completed recovery epochs.")

    files = [args.selection, args.cache / "manifest.json", args.roster,
             args.baseline / "run.json", args.baseline / "metrics.json", args.baseline / "rf.pkl"]
    hashes = dict(zip(("selection_file", "cache_manifest", "roster", "baseline_run", "baseline_metrics", "rf"),
                      map(baseline.file_hash, files), strict=True))
    data = baseline.load(args.selection, args.cache, args.roster)
    train, val = data["train"], data["val"]
    ref = json.loads(files[4].read_bytes())
    frozen = json.loads(files[3].read_bytes())
    checkpoint = args.baseline / f"epoch-{ref['best_epoch']}.pt"
    hashes["baseline_checkpoint"] = baseline.file_hash(checkpoint)
    if (hashes["baseline_checkpoint"] != ref["checkpoint_sha256"][checkpoint.name]
            or hashes["rf"] != ref["rf_fit"]["sha256"] or ref["rf"]["operating_threshold"] != .65
            or support(val) != ref["validation_support"]):
        raise ValueError("Baseline checkpoint, RF or validation support differs")
    identity = dict(inputs=hashes, weight=weight(train), baseline=frozen,
                    code=baseline.file_hash(Path(__file__)),
                    model_code=baseline.file_hash(Path("src/phase3/model.py")))
    model, optimizer = setup()
    out = args.output
    diagnosis = out / "diagnosis.json"
    if args.action == "diagnose":
        out.mkdir()
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if state["identity"] != frozen:
            raise ValueError("Baseline checkpoint run identity differs")
        model.load_state_dict(state["model"])
        model.eval()
        stats = {}
        with torch.inference_mode():
            for split, rows in data.items():
                predictions = [predict(model, row) for row in rows]
                stats[split] = distribution(rows, predictions)
                if split == "val":
                    by_id = dict(zip((row[0]["patch_id"] for row in rows), predictions, strict=True))
                    replay = baseline.evaluate(rows, lambda row: by_id[row[0]["patch_id"]], check)
                    if replay != ref["siamese"]:
                        raise ValueError("Phase 17D validation metrics did not reproduce")
        baseline.planner.write(diagnosis, dict(identity=identity, scores=stats, smoke=smoke(train)))
        print("Diagnosis passed and Phase 17D validation reproduced exactly", flush=True)
        return

    preflight = json.loads(diagnosis.read_bytes())
    if preflight["identity"] != identity or (out / "metrics.json").exists():
        raise ValueError("Diagnosis identity differs or recovery already completed")
    identity["diagnosis_sha256"] = baseline.file_hash(diagnosis)
    recovery = out / "run.json"
    if recovery.exists():
        if json.loads(recovery.read_bytes()) != identity:
            raise ValueError("Recovery configuration differs")
    else:
        baseline.planner.write(recovery, identity)
    history = []
    checkpoints = sorted(out.glob("epoch-*.pt"))
    if checkpoints:
        state = torch.load(checkpoints[-1], map_location="cpu", weights_only=True)
        if state["identity"] != identity:
            raise ValueError("Recovery checkpoint identity differs")
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        history = state["history"]
    pos_weight = identity["weight"]["pos_weight"]
    for epoch in range(len(history)+1, baseline.EPOCHS+1):
        elapsed = monotonic()
        order = torch.randperm(len(train), generator=torch.Generator().manual_seed(42+epoch)).tolist()
        fit = pass_loss(model, optimizer, train, order, pos_weight, check)
        val_loss = pass_loss(model, None, val, range(len(val)), pos_weight, check)
        history.append(dict(epoch=epoch, train=fit, val=val_loss, wall=monotonic()-elapsed))
        baseline.atomic(out / f"epoch-{epoch}.pt", dict(identity=identity, model=model.state_dict(),
                        optimizer=optimizer.state_dict(), history=history),
                        lambda path, item: torch.save(item, path))
        print(history[-1], flush=True)
    best = min(history, key=lambda h: h["val"])["epoch"]
    state = torch.load(out / f"epoch-{best}.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    model.eval()
    with torch.inference_mode():
        predictions = [predict(model, row) for row in val]
        by_id = dict(zip((row[0]["patch_id"] for row in val), predictions, strict=True))
        results = baseline.evaluate(val, lambda row: by_id[row[0]["patch_id"]], check)
    if baseline.file_hash(files[-1]) != hashes["rf"]:
        raise ValueError("Frozen RF changed during recovery")
    baseline.atomic(out / "metrics.json", dict(results=results, scores=distribution(val, predictions),
                    best_epoch=best, history=history, weight=identity["weight"],
                    checkpoint_sha256={p.name: baseline.file_hash(p) for p in sorted(out.glob("epoch-*.pt"))},
                    validation_support_sha256=ref["validation_support_sha256"],
                    wall=monotonic()-start, cpu=process_time()-cpu, memory_bytes=baseline.memory()),
                    baseline.planner.write)


if __name__ == "__main__":
    main()
