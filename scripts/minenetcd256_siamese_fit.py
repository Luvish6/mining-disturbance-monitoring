"""CPU-only, resumable external MineNetCD256 RGB training pilot."""
import json
from pathlib import Path
from time import monotonic

import numpy as np
import torch
from sklearn.metrics import average_precision_score

from scripts.minenetcd256_siamese_data import RGBPairs, TRAIN, VAL, digest
from src.phase3.evaluate import metrics
from src.phase3.model import SiameseUNet, masked_loss

EPOCHS = 5
SECONDS = 600


def verify_rows(records, selection, sites):
    expected = {(site, g, r) for site in sites for g, r in selection["sites"][site]["rows"]}
    actual = {(r["site"], r["group"], r["row"]) for r in records}
    if actual != expected or len(records) != 5 * len(sites) or len(actual) != len(records):
        raise ValueError("Frozen rows disagree")


def score(y, p):
    result = metrics(y, p, .5)
    tn, fp = result["confusion_matrix"][0]
    result.update(fpr=fp / (tn + fp) if tn + fp else None,
                  average_precision=float(average_precision_score(y, p)) if np.any(y) else None)
    return result


def run(root):
    began = monotonic()
    deadline = began + SECONDS
    torch.manual_seed(42)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(2)
    cache = root / "siamese_rgb_v1"
    rf = json.loads((root / "rf_combined_v1/metrics.json").read_text())
    datasets = {s: RGBPairs(cache, s) for s in ("train", "val")}
    for split, sites in (("train", TRAIN), ("val", VAL)):
        verify_rows(datasets[split].records, rf["selections"][split], sites)
    output = root / "siamese_fit_v1"
    output.mkdir(exist_ok=True)
    identity = {"manifest": digest(cache / "manifest.json"), "seed": 42, "batch": 1,
                "epochs": EPOCHS, "lr": .001, "width": 16, "precision": "float32", "pos_weight": 1.,
                "limit_seconds_per_invocation": SECONDS, "torch": str(torch.__version__)}
    model = SiameseUNet(channels=3, width=16)
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    history = []
    latest = output / "latest.pt"
    if latest.exists():
        state = torch.load(latest, map_location="cpu", weights_only=True)
        if state["identity"] != identity:
            raise ValueError("Checkpoint configuration or source changed")
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        history = state["history"]

    def epoch_pass(split, epoch):
        train = split == "train"
        model.train(train)
        loader = torch.utils.data.DataLoader(datasets[split], batch_size=1, shuffle=train,
                                             generator=torch.Generator().manual_seed(42 + epoch))
        total = count = 0
        for a, b, y, mask in loader:
            if monotonic() >= deadline:
                raise TimeoutError("Runtime limit reached")
            with torch.set_grad_enabled(train):
                loss = masked_loss(model(a, b), y, mask)
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite loss")
                if train:
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
            n = int(mask.sum())
            total += loss.item() * n
            count += n
        return total / count

    for epoch in range(len(history) + 1, EPOCHS + 1):
        start = monotonic()
        try:
            train_loss = epoch_pass("train", epoch)
            val_loss = epoch_pass("val", epoch)
        except TimeoutError:
            print("Time limit reached. Resume from the last completed epoch.")
            return
        history.append(dict(epoch=epoch, train=train_loss, val=val_loss, seconds=monotonic() - start))
        checkpoint = output / f"epoch-{epoch}.pt"
        temp = output / "checkpoint.tmp"
        torch.save(dict(identity=identity, model=model.state_dict(), optimizer=optimizer.state_dict(),
                        history=history), temp)
        temp.replace(checkpoint)
        # A single atomically replaced checkpoint pointer is enough to resume.
        temp.write_bytes(checkpoint.read_bytes())
        temp.replace(latest)
        print(history[-1], flush=True)
    best = min(history, key=lambda item: item["val"])["epoch"]
    state = torch.load(output / f"epoch-{best}.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    model.eval()
    targets, probabilities = {}, {}
    with torch.inference_mode():
        for index, record in enumerate(datasets["val"].records):
            if monotonic() >= deadline:
                print("Time limit reached before final scoring. Resume with the saved checkpoint.")
                return
            a, b, y, mask = datasets["val"][index]
            site = record["site"]
            targets.setdefault(site, []).append(y[mask].numpy())
            probabilities.setdefault(site, []).append(model(a[None], b[None]).sigmoid()[0][mask].numpy())
    ys = {s: np.concatenate(v) for s, v in targets.items()}
    ps = {s: np.concatenate(v) for s, v in probabilities.items()}
    results = {s: score(ys[s], ps[s]) for s in ys}
    results["pooled"] = score(np.concatenate(list(ys.values())), np.concatenate(list(ps.values())))
    for site, row in results.items():
        for baseline in rf["results"].values():
            if [r["support"] for r in row["classes"]] != [r["support"] for r in baseline[site]["classes"]]:
                raise ValueError("RF and U-Net label support disagree")
    saved = dict(identity=identity, history=history, best_epoch=best, results=results,
                 rf=rf["results"], seconds=monotonic() - began, cuda=torch.cuda.is_available())
    (output / "metrics.json").write_text(json.dumps(saved, indent=2, allow_nan=False))
    print(best, saved["seconds"], results, flush=True)


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1] / "outputs/external_minenetcd256")
