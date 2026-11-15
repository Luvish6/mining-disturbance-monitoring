"""Bounded MineNetCD RGB validation experiments; no final test selection here."""
import argparse
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import pickle
import shutil
from time import monotonic

import numpy as np
import pyarrow.parquet as pq
import torch
from sklearn.ensemble import RandomForestClassifier

from scripts.minenetcd256_heldout import TestSource, evaluate, fingerprint, read, save
from scripts.minenetcd256_rf_pilot import DATASET, REVISION, RF_CONFIG, SHARDS, decode
from scripts.minenetcd256_rf_multi import sample_training
from scripts.minenetcd256_siamese_data import RGBPairs, digest
from src.phase3.evaluate import metrics
from src.phase3.model import SiameseUNet, masked_loss

BUDGET = 128*1024**2
THRESHOLDS = (.25, .35, .5, .65, .75, .9, .95)
EPOCHS = 3


def acquire(root, out, reuse=None):
    out.mkdir()
    original = read(root/"heldout_v1/split_manifest.json")
    records, transfers = [], {}
    for split in ("train", "val"):
        if split == "val" and reuse is not None:
            old = read(reuse/"manifest.json")
            for record in old["patches"]:
                if record["split"] != "val":
                    continue
                path = reuse/record["file"]
                if digest(path) != record["sha256"] or old["revision"] != REVISION or old["shards"][split] != SHARDS[split]:
                    raise ValueError("Invalid reusable validation cache")
                shutil.copyfile(path,out/path.name)
                records.append(record)
            transfers[split] = old["bytes"][split]
            continue
        previous = {r["site"] for r in original["development"]["patches"] if r["split"] == split}
        roster = original["official_roster"][split]
        url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{SHARDS[split]}"
        selected = defaultdict(list)
        with TestSource(url, BUDGET) as source:
            parquet = pq.ParquetFile(source)
            for group in range(min(parquet.num_row_groups, 16 if split=="train" else 3)):
                rows = parquet.read_row_group(group, columns=["domain","label"], use_threads=False)
                for index, row in enumerate(rows.to_pylist()):
                    site = row["domain"]
                    if site not in roster:
                        raise ValueError("Unofficial development site")
                    if site in previous or len(selected.get(site, [])) == 3:
                        continue
                    if site not in selected and len(selected) == 2:
                        continue
                    mask = decode(row["label"],"L",label=True)
                    if np.isin(mask,[0,255]).all() and (mask==255).sum() >= 64 and (mask==0).any():
                        selected[site].append((group,index))
                if len(selected)==2 and all(len(rows)==3 for rows in selected.values()):
                    break
            for group in sorted({g for rows in selected.values() for g,_ in rows}):
                table = parquet.read_row_group(group, use_threads=False)
                for site, rows in selected.items():
                    for g,index in rows:
                        if g!=group:
                            continue
                        row = table.slice(index,1).to_pylist()[0]
                        if row["domain"]!=site:
                            raise ValueError("Development row identity mismatch")
                        a,b = [decode(row[k],"RGB") for k in ("imageA","imageB")]
                        mask = decode(row["label"],"L",label=True)
                        file = f"{split}-{group}-{index}.npz"
                        np.savez_compressed(out/file,before=a,after=b,mask=mask)
                        records.append(dict(split=split,site=site,group=group,row=index,file=file,
                                            sha256=digest(out/file),changed=int((mask==255).sum()),
                                            source_sha256={k:sha256(row[k]["bytes"]).hexdigest()
                                                           for k in ("imageA","imageB","label")}))
            transfers[split]=BUDGET-source.budget
        print(split, dict(selected), transfers[split], flush=True)
    save(out/"manifest.json",dict(revision=REVISION,shards={s:SHARDS[s] for s in ("train","val")},
                                  patches=records,bytes=transfers))


def weighted_dice(logits, y, valid):
    bce = masked_loss(logits, y, valid, pos_weight=2.)
    p, t = logits[valid].sigmoid(), y[valid]
    dice = (2*(p*t).sum()+1)/(p.sum()+t.sum()+1)
    return .7*bce + .3*(1-dice)


def load_development(root, extra):
    original = root/"siamese_rgb_v1"
    official = read(root/"heldout_v1/split_manifest.json")
    batches, seen, ids = {"train":[], "val":[]}, {}, set()
    for split in batches:
        for cache in (original, extra):
            dataset = RGBPairs(cache, split)
            for i, rec in enumerate(dataset.records):
                key = (split,rec["group"],rec["row"])
                if key in ids or rec["site"] not in official["official_roster"][split]:
                    raise ValueError("Development roster or row identity mismatch")
                ids.add(key)
                a,b,y,valid = dataset[i]
                for image in (a,b):
                    if seen.setdefault(fingerprint(image.mul(255).round().byte().permute(1,2,0).numpy()),split) != split:
                        raise ValueError("Exact cross-split RGB match")
                if int(y.sum()) != rec["changed"]:
                    raise ValueError("Mask support differs from manifest")
                batches[split].append((rec,a,b,y,valid))
    return batches


def evaluate_dev(model, family, batch):
    groups = defaultdict(list)
    for rec,a,b,y,mask in batch:
        labels = y[mask].numpy()
        if family=="siamese":
            with torch.inference_mode():
                probability = model(a[None],b[None]).sigmoid()[0][mask].numpy()
        else:
            probability = model.predict_proba(rgb_delta(a,b))[:,1]
        groups[rec["site"]].append((labels,probability))
    paired = {site:tuple(np.concatenate(items) for items in zip(*patches)) for site,patches in groups.items()}
    paired["pooled"] = tuple(np.concatenate(items) for items in zip(*paired.values()))
    return {str(t):{site:metrics(y,p,t) for site,(y,p) in paired.items()} for t in THRESHOLDS}


def choose(configurations):
    trials = [(m["pooled"]["classes"][1]["f1"] or 0, float(threshold), name)
              for name,grid in configurations.items() for threshold,m in grid.items()]
    value, threshold, name = max(trials)
    original = configurations["original"]["0.5"]["pooled"]["classes"][1]["f1"] or 0
    return dict(model=name, threshold=threshold, validation_f1=value, original_f1=original,
                improved=value > original + .005)


def rgb_delta(a,b):
    return (torch.round(b*255)-torch.round(a*255)).permute(1,2,0).reshape(-1,3).numpy()


def fit(root, extra, out, resume=False):
    start = monotonic()
    torch.manual_seed(42)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    batches = load_development(root,extra)
    out.mkdir(exist_ok=resume)
    if (out/"metrics.json").exists():
        raise ValueError("Completed validation runs are immutable")
    val = batches["val"]
    previous = root/"heldout_v1"
    validation = {}
    base = SiameseUNet(channels=3,width=16).eval()
    original_epoch = read(previous/"siamese/metrics.json")["best_epoch"]
    base.load_state_dict(torch.load(previous/"siamese"/f"epoch-{original_epoch}.pt",
                                   weights_only=True,map_location="cpu")["model"])
    validation["siamese"] = {"original":evaluate_dev(base,"siamese",val)}
    with (previous/"rf.pkl").open("rb") as handle:
        forest = pickle.load(handle)
    validation["rf"] = {"original":evaluate_dev(forest,"rf",val)}
    model = SiameseUNet(channels=3,width=16)
    optimizer = torch.optim.Adam(model.parameters(),lr=.001)
    history = []
    for epoch in range(1,EPOCHS+1):
        name = f"dice-{epoch}"
        checkpoint = out/f"{name}.pt"
        if resume and checkpoint.is_file():
            model.load_state_dict(torch.load(checkpoint,weights_only=True,map_location="cpu")["model"])
            model.eval()
            validation["siamese"][name] = evaluate_dev(model,"siamese",val)
            history.append(dict(epoch=epoch,loss=None,reused=True))
            continue
        if resume:
            raise ValueError("Resume requires all completed development checkpoints")
        model.train()
        loss_values = []
        for i in np.random.default_rng(42+epoch).permutation(len(batches["train"])):
            if monotonic()-start > 360:
                raise TimeoutError("Bounded training runtime exceeded")
            _,a,b,y,mask = batches["train"][i]
            optimizer.zero_grad()
            loss = weighted_dice(model(a[None],b[None]),y[None],mask[None])
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite weighted BCE/Dice")
            loss.backward()
            optimizer.step()
            loss_values.append(float(loss.detach()))
        model.eval()
        torch.save(dict(model=model.state_dict()),checkpoint)
        validation["siamese"][name] = evaluate_dev(model,"siamese",val)
        history.append(dict(epoch=epoch,loss=float(np.mean(loss_values))))
        print(name, flush=True)
    grouped = defaultdict(list)
    for rec,a,b,y,mask in batches["train"]:
        grouped[rec["site"]].append((rgb_delta(a,b),y.numpy().ravel().astype("uint8")))
    mines = {s:(np.concatenate([x for x,_ in items]),np.concatenate([y for _,y in items]),{})
             for s,items in sorted(grouped.items())}
    sampling = {}
    for balanced in (False,True):
        config = dict(RF_CONFIG)
        name = "expanded-balanced" if balanced else "expanded-uniform"
        if balanced:
            x,y,counts = sample_training(mines)
        else:
            config["class_weight"] = None
            rng = np.random.default_rng(42)
            data = [(s,*mine[:2]) for s,mine in mines.items()]
            selections = [rng.choice(len(y),min(len(y),100000//len(data)),replace=False) for _,_,y in data]
            x = np.concatenate([a[i] for (_,a,_),i in zip(data,selections,strict=True)])
            y = np.concatenate([b[i] for (_,_,b),i in zip(data,selections,strict=True)])
            counts = {s:np.bincount(b[i].astype(int),minlength=2).tolist()
                      for (s,_,b),i in zip(data,selections,strict=True)}
        classifier = RandomForestClassifier(**config).fit(x,y)
        with (out/f"{name}.pkl").open("wb") as handle:
            pickle.dump(classifier,handle)
        validation["rf"][name] = evaluate_dev(classifier,"rf",val)
        sampling[name] = dict(pixels=len(y),counts=counts,config=config)
    selection = {family:choose(attempts) for family,attempts in validation.items()}
    support = {}
    for split,batch in batches.items():
        sites = defaultdict(lambda:[0,0,0])
        for row,*_ in batch:
            counts = sites[row["site"]]
            counts[0]+=1
            counts[1]+=row["changed"]
            counts[2]+=65536-row["changed"]
        support[split] = dict(sites)
    save(out/"metrics.json",dict(validation=validation,selected=selection,support=support,
         training_history=history,sampling=sampling,seconds=monotonic()-start,
         source_hashes={str(p.name):digest(p/"manifest.json") for p in (root/"siamese_rgb_v1",extra)},
         selection_rule="Maximum pooled validation positive F1; ties favor higher threshold then name. Require >0.005 absolute gain over original at 0.50."))
    print(selection, flush=True)


def holdout(root, extra, fit_dir, out):
    report = read(fit_dir/"metrics.json")
    selected = {family:entry for family,entry in report["selected"].items() if entry["improved"]}
    if not selected:
        print("Validation gain did not meet the prespecified margin. Test untouched.")
        return
    previous = root/"heldout_v1"
    manifest = read(previous/"split_manifest.json")
    excluded = set(manifest["previous_test_sites_excluded"]) | set(read(previous/"test_selection.json"))
    batches = load_development(root,extra)
    hashes = {}
    for name in (root/"siamese_rgb_v1",extra):
        if digest(name/"manifest.json") != report["source_hashes"][name.name]:
            raise ValueError("Development manifest changed after selection")
    seen = {fingerprint(image.mul(255).round().byte().permute(1,2,0).numpy()): split
            for split,batch in batches.items() for _,a,b,_,_ in batch for image in (a,b)}
    best = forest = None
    if "siamese" in selected:
        name = selected["siamese"]["model"]
        best = (previous/"siamese"/f'epoch-{read(previous/"siamese/metrics.json")["best_epoch"]}.pt'
                if name=="original" else fit_dir/f"{name}.pt")
        hashes["siamese"] = digest(best)
    if "rf" in selected:
        name = selected["rf"]["model"]
        path = previous/"rf.pkl" if name=="original" else fit_dir/f"{name}.pkl"
        hashes["rf"] = digest(path)
        with path.open("rb") as handle:
            forest = pickle.load(handle)
    out.mkdir()
    save(out/"frozen.json",dict(selection=selected, artifacts=hashes, excluded=sorted(excluded),
                                 validation_sha256=digest(fit_dir/"metrics.json"), revision=REVISION))
    torch.set_num_threads(2)
    records, results, transferred = evaluate(out,manifest["official_roster"]["test"],excluded,seen,best,forest,
                                              thresholds={k:v["threshold"] for k,v in selected.items()},target_sites=2,require_both=False)
    save(out/"manifest.json",records)
    save(out/"metrics.json",dict(results=results,bytes=transferred,patches=len(records)))
    print({name:m["pooled"] for name,m in results.items()},flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("acquire","fit","holdout"))
    parser.add_argument("root",type=Path)
    parser.add_argument("out",type=Path)
    parser.add_argument("--extra",type=Path)
    parser.add_argument("--fit-dir",type=Path)
    parser.add_argument("--resume",action="store_true")
    args=parser.parse_args()
    if args.action=="acquire":
        acquire(args.root,args.out,args.extra)
    else:
        if args.extra is None:
            parser.error("fit requires --extra")
        if args.action=="fit":
            fit(args.root,args.extra,args.out,args.resume)
        elif args.fit_dir is None:
            parser.error("holdout requires --fit-dir")
        else:
            holdout(args.root,args.extra,args.fit_dir,args.out)