"""Audit frozen MineNetCD RGB models on a bounded label-blind validation sample."""
import argparse
from hashlib import sha256
from pathlib import Path
import pickle
from time import monotonic

import numpy as np
import pyarrow.parquet as pq
import torch

from scripts.minenetcd256_heldout import TestSource, fingerprint, read, save
from scripts.minenetcd256_rf_multi import roster_for
from scripts.minenetcd256_rf_pilot import DATASET, REVISION, SHARDS, decode
from scripts.minenetcd256_siamese_data import digest
from scripts.minenetcd256_siamese_fit import score
from src.phase3.model import SiameseUNet

BUDGET = 160 * 1024**2
PATCHES = 4
THRESHOLDS = (.25, .35, .5, .65, .75, .9, .95)


def select(parquet, roster):
    """Inspect domains only, keeping the first four rows per publisher site."""
    selected = {site: [] for site in sorted(roster)}
    counts = dict.fromkeys(selected, 0)
    for group in range(parquet.num_row_groups):
        rows = parquet.read_row_group(group, columns=["domain"], use_threads=False)["domain"].to_pylist()
        for index, site in enumerate(rows):
            if site not in selected:
                raise ValueError("Unknown validation site")
            counts[site] += 1
            if len(selected[site]) < PATCHES:
                selected[site].append((group,index))
    if counts != roster or any(len(rows) != min(roster[site],PATCHES) for site,rows in selected.items()):
        raise ValueError("Validation shard roster differs from the official inventory")
    return selected


def calibration(y, p):
    bins = np.minimum((p*10).astype(int),9)
    rows, ece = [], 0.
    for index in range(10):
        mask = bins == index
        n = int(mask.sum())
        if n:
            probability, prevalence = float(p[mask].mean()), float(y[mask].mean())
            ece += n*abs(probability-prevalence)/len(y)
            rows.append(dict(bin=index,count=n,mean_score=probability,positive_fraction=prevalence))
    return dict(brier=float(np.mean((p-y.astype(float))**2)), ece=ece, bins=rows)


def summarize(y, p, threshold):
    result = score(y,p,threshold)
    result["predicted_positive_pixels"] = int((p>=threshold).sum())
    if not y.any():
        result["positive_metrics_policy"] = "No positive reference support; use FPR and predicted-positive pixels"
        for key in ("recall","f1","iou"):
            result["classes"][1][key] = None
    return result


def run(root,out):
    start = monotonic()
    torch.set_num_threads(2)
    original = root/"heldout_v1"
    original_receipt = read(original/"split_manifest.json")
    rf_receipt = read(root/"improve_holdout_v1/frozen.json")
    fit = root/"improve_fit_v1"
    rf_selection = rf_receipt["selection"]["rf"]
    if (rf_selection != read(fit/"metrics.json")["selected"]["rf"]
            or digest(fit/"metrics.json") != rf_receipt["validation_sha256"]):
        raise ValueError("Frozen RF validation selection mismatch")
    epoch = read(original/"siamese/metrics.json")["best_epoch"]
    unet_path = original/"siamese"/f"epoch-{epoch}.pt"
    rf_path = fit/f'{rf_selection["model"]}.pkl'
    if digest(unet_path)!=original_receipt["artifact_hashes"]["siamese"] or digest(rf_path)!=rf_receipt["artifacts"]["rf"]:
        raise ValueError("Frozen checkpoint hash mismatch")
    train, val = (original_receipt["official_roster"][key] for key in ("train","val"))
    if original_receipt["revision"] != REVISION or set(train)&set(val) or roster_for("val") != val:
        raise ValueError("Official validation inventory changed")
    if set(val)&set(original_receipt["official_roster"]["test"]):
        raise ValueError("Validation/test site overlap")
    models = {}
    models["siamese"] = SiameseUNet(channels=3,width=16).eval()
    models["siamese"].load_state_dict(torch.load(unet_path,weights_only=True,map_location="cpu")["model"])
    with rf_path.open("rb") as stream:
        models["rf"] = pickle.load(stream)  # Trusted local artifact, verified above.
    thresholds = {"siamese":.5,"rf":rf_selection["threshold"]}
    cached, train_hashes = {}, set()
    for folder in (root/"siamese_rgb_v1",root/"improve_cache_v2"):
        manifest = read(folder/"manifest.json")
        if manifest["revision"] != REVISION or manifest["shards"] != {s:SHARDS[s] for s in ("train","val")}:
            raise ValueError("Invalid development cache provenance")
        for row in manifest["patches"]:
            split = row["split"]
            if split not in ("train","val") or row["site"] not in (train if split=="train" else val):
                raise ValueError("Cached split identity mismatch")
            path = folder/row["file"]
            if digest(path)!=row["sha256"]:
                raise ValueError("Cached image changed")
            if split=="train":
                with np.load(path,allow_pickle=False) as data:
                    train_hashes.update(fingerprint(data[key]) for key in ("before","after"))
            else:
                cached[(row["group"],row["row"])] = (path,row)
    out.mkdir()
    records, grouped, seen = [], {}, set()
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{SHARDS['val']}"
    with TestSource(url,BUDGET) as source:
        parquet = pq.ParquetFile(source)
        selected = select(parquet,val)
        save(out/"selection.json",dict(revision=REVISION,shard=SHARDS["val"],
            roster=val, rows=selected, sampling="First four row identities per site, domains only",
            thresholds=thresholds, artifact_hashes={"siamese":digest(unet_path),"rf":digest(rf_path)}))
        for group in sorted({g for entries in selected.values() for g,_ in entries}):
            missing = [(site,index) for site,entries in selected.items() for g,index in entries
                       if g==group and (g,index) not in cached]
            table = parquet.read_row_group(group,use_threads=False) if missing else None
            for site,entries in selected.items():
                for g,index in entries:
                    if g!=group:
                        continue
                    if (g,index) in cached:
                        path,record = cached[(g,index)]
                        if record["site"]!=site:
                            raise ValueError("Cached row belongs to a different site")
                        with np.load(path,allow_pickle=False) as data:
                            a,b,mask = [data[k] for k in ("before","after","mask")]
                        sources = record["source_sha256"]
                    else:
                        row = table.slice(index,1).to_pylist()[0]
                        if row["domain"]!=site:
                            raise ValueError("Validation row belongs to a different site")
                        a,b = [decode(row[key],"RGB") for key in ("imageA","imageB")]
                        mask = decode(row["label"],"L",label=True)
                        sources = {k:sha256(row[k]["bytes"]).hexdigest() for k in ("imageA","imageB","label")}
                    if train_hashes.intersection(fingerprint(frame) for frame in (a,b)):
                        raise ValueError("Identical epoch image overlaps training")
                    pair = (fingerprint(a),fingerprint(b))
                    if pair in seen:
                        raise ValueError("Duplicate sampled image pair")
                    seen.add(pair)
                    valid = np.isin(mask,(0,255))
                    y = mask[valid]==255
                    with torch.inference_mode():
                        frames = [torch.from_numpy(frame.transpose(2,0,1)).float().div_(255)[None] for frame in (a,b)]
                        unet = models["siamese"](*frames).sigmoid()[0,0].numpy()[valid]
                    rf = models["rf"].predict_proba((b.astype("int16")-a)[valid])[:,1]
                    grouped.setdefault(site,[]).append((y,unet,rf))
                    path = out/f"val-{g}-{index}.npz"
                    np.savez_compressed(path,before=a,after=b,mask=mask)
                    records.append(dict(site=site,group=g,row=index,file=path.name,sha256=digest(path),
                                        sources=sources,changed=int(y.sum()),n=len(y),excluded=int((~valid).sum()),
                                        cached=(g,index) in cached))
            print("Scored row group",group,"range bytes",BUDGET-source.budget,flush=True)
        transferred = BUDGET-source.budget
    grouped["pooled"] = [item for rows in grouped.values() for item in rows]
    models_report = {}
    for column,name in enumerate(("siamese","rf"),1):
        pairs = {site:(np.concatenate([row[0] for row in rows]),np.concatenate([row[column] for row in rows]))
                 for site,rows in grouped.items()}
        yp,pp = pairs["pooled"]
        models_report[name] = dict(operating_point={site:summarize(y,p,thresholds[name]) for site,(y,p) in pairs.items()},
                                   calibration={site:calibration(y,p) for site,(y,p) in pairs.items()},
                                   sensitivity={str(t):summarize(yp,pp,t) for t in THRESHOLDS})
    save(out/"manifest.json",records)
    save(out/"metrics.json",dict(models=models_report,patches=len(records),bytes=transferred,seconds=monotonic()-start))
    print({n:r["operating_point"]["pooled"] for n,r in models_report.items()},flush=True)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root",type=Path)
    parser.add_argument("out",type=Path)
    run(**vars(parser.parse_args()))
