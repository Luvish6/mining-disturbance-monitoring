"""Offline RF baselines and gated static U-Net experiments on frozen 2019 weak masks."""

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
from time import perf_counter, process_time

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
import torch
from torch import nn
from torch.nn import functional as F

from scripts.phase22b_maus import ROOT, digest, stable, train_normalization, write_json
from scripts.phase22c_maus import SPLIT_SHA, verify_split
from scripts.phase22e_maus_export import check_images, read_plan
from scripts.phase22e_r_maus import DEST as CACHE, ORIGINAL, PLAN_SHA
from src.phase3.evaluate import metrics
from src.phase3.model import conv, masked_loss

DEST = Path("outputs/phase22f_maus")
PROTO = Path("docs/preregistration-phase22f-v1.md")
THRESHOLDS = (.25, .50, .75)
RF = dict(n_estimators=100, max_depth=16, min_samples_leaf=2,
          max_features="sqrt", random_state=42, n_jobs=1)
CACHE_KEYS = ("split", "group_id", "affine", "bounds", "crs", "label_source_fids",
              "negative_stratum", "weak_label_type")


def cached_inputs(cache=CACHE):
    original = (ROOT / "split.json").read_bytes()
    verify_split(original, original)
    plan_raw = (cache / "plan.json").read_bytes()
    if digest(plan_raw) != PLAN_SHA or plan_raw != (ORIGINAL / "plan.json").read_bytes():
        raise ValueError("Frozen acquisition plan mismatch")
    plan, _ = read_plan(ROOT, cache)
    roster = {r["patch_id"]: r for r in plan["patches"]}
    seal = json.loads((ROOT / "sealed_test.json").read_bytes())
    expected_test = {key: row["ids"] for key, row in json.loads(original)["groups"].items()
                     if row["split"] == "test"}
    if (seal.get("sealed") is not True or seal.get("split_sha256") != SPLIT_SHA
            or seal.get("groups") != expected_test):
        raise ValueError("TEST seal mismatch")
    summary = json.loads((cache / "summary.json").read_bytes())
    if (summary["dataset_go"] is not True or summary["test_sealed"] is not True
            or summary["plan_sha256"] != PLAN_SHA
            or summary["split_sha_before"] != SPLIT_SHA or summary["split_sha_after"] != SPLIT_SHA):
        raise ValueError("Recovery receipt fails frozen dataset checks")

    expected = {"train": 24, "validation": 15}
    samples, input_hashes = {}, {}
    for role, count in expected.items():
        source = (cache / f"{role}_manifest.json").read_bytes()
        manifest = json.loads(source)
        rows = sorted(manifest["patches"], key=lambda r: stable(r["patch_id"]))
        ids = {r["patch_id"] for r in rows}
        if (len(rows) != count or manifest["plan_sha256"] != PLAN_SHA
                or ids != {key for key,row in roster.items() if row["split"] == role}):
            raise ValueError("Incomplete or changed development roster")
        input_hashes[role] = digest(source)
        records = []
        for row in rows:
            key = row["patch_id"]
            target = roster[key]
            if (row["split"] != role or row["state_of_patch"] != "QA_ACCEPTED_WEAK"
                    or row["plan_sha256"] != PLAN_SHA
                    or any(row[field] != target[field] for field in CACHE_KEYS)):
                raise ValueError("Changed patch provenance")
            fingerprint = row["provenance_hash"]
            if digest(json.dumps({k: v for k,v in row.items() if k != "provenance_hash"},
                                 sort_keys=True).encode()) != fingerprint:
                raise ValueError("Patch receipt checksum mismatch")
            assets = [cache / "patches" / f"{key}_{suffix}.tif" for suffix in ("image","weak_mask")]
            if any(digest(path.read_bytes()) != row[field] for path,field in zip(
                    assets, ("image_sha256","mask_sha256"), strict=True)):
                raise ValueError("Cached raster hash mismatch")
            x, valid, y = check_images(*assets, row)
            known = valid & (y != 255)
            if (valid.mean() < .70 or not np.isfinite(x[:,valid]).all()
                    or int(valid.sum()) != row["valid_pixels"]
                    or int((known & (y==1)).sum()) != row["positive_pixels"]
                    or int((known & (y==0)).sum()) != row["background_pixels"]
                    or (y[known] != (not bool(row["negative_stratum"]))).any()):
                raise ValueError("Weak label or valid-cell receipt mismatch")
            records.append((row, x, valid, y))
        samples[role] = records
    if {r[0]["group_id"] for r in samples["train"]} & {r[0]["group_id"] for r in samples["validation"]}:
        raise ValueError("TRAIN and validation group leakage")
    mean, sd = train_normalization([("train",x,v) for _,x,v,_ in samples["train"]])
    norm = summary["normalization"]
    if (norm["bands"] != ["B3","B4","B8"] or not np.array_equal(mean,norm["mean"])
            or not np.array_equal(sd,norm["sd"])):
        raise ValueError("TRAIN-only normalization did not reproduce")
    diagnostic = json.loads((cache / "debug.json").read_bytes())
    if diagnostic["plan_sha256"] != PLAN_SHA or diagnostic["test_sealed"] is not True:
        raise ValueError("Historical diagnostic receipt mismatch")
    keys = diagnostic["patches"]
    by_id = {r[0]["patch_id"]:r for r in samples["train"]}
    if len(keys) != 8 or len(set(keys)) != 8 or not set(keys) <= by_id.keys():
        raise ValueError("Unexpected diagnostic TRAIN roster")
    verify_split(original, (ROOT/"split.json").read_bytes())
    return samples, [by_id[k] for k in keys], norm, input_hashes


def ndvi_features(x, known):
    g,r,n = x
    den = n+r
    ndvi = np.divide(n-r, den, out=np.full_like(den,np.nan), where=den!=0)
    common = known & np.isfinite(ndvi)
    return np.stack((g[common],r[common],n[common],ndvi[common]),axis=1), common


def rf_arrays(records):
    xs, ys, groups, bg = [], [], [], []
    excluded = 0
    for row,x,v,y in records:
        known = v & (y != 255)
        feat, use = ndvi_features(x,known)
        excluded += int(known.sum()-use.sum())
        xs.append(feat)
        ys.append(y[use])
        groups.append(np.full(use.sum(),row["group_id"]))
        bg.append(np.full(use.sum(),bool(row["negative_stratum"])))
    return tuple(np.concatenate(seq) for seq in (xs,ys,groups,bg)) + (excluded,)


def balanced_pixels(y):
    parts = [np.flatnonzero(y == c) for c in (0,1)]
    count = min(50000, *(len(part) for part in parts))
    if not count:
        raise ValueError("Both TRAIN classes are required")
    rng = np.random.default_rng(42)
    return np.sort(np.concatenate([rng.choice(part,count,replace=False) for part in parts]))


def detail(y, p, threshold):
    m = metrics(y,p,threshold)
    (tn,fp),_ = m["confusion_matrix"]
    return m["classes"][1] | dict(confusion=m["confusion_matrix"],
                                  fpr=fp/(tn+fp) if tn+fp else None)


def select_threshold(y, p):
    results = {str(t):detail(y,p,t) for t in THRESHOLDS}
    def key(t):
        f1 = results[str(t)]["f1"]
        return (-1 if f1 is None else f1,t)
    return max(THRESHOLDS,key=key),results


def evaluate(y, p, groups, bg):
    t, candidates = select_threshold(y,p)
    false = int(((p >= t) & bg).sum())
    return dict(threshold=t, candidates=candidates, pooled=detail(y,p,t),
                per_group={digest(k.encode())[:12]:detail(y[groups==k],p[groups==k],t)
                           for k in np.unique(groups)},
                background_only=dict(false_positives=false, pixels=int(bg.sum()),
                                     fpr=false/int(bg.sum()) if bg.any() else None))


class Budget:
    def __init__(self, seconds):
        self.limit = seconds
        self.t0 = process_time()
        self.w0 = perf_counter()

    def usage(self):
        return dict(cpu_seconds=process_time()-self.t0,wall_seconds=perf_counter()-self.w0)

    def check(self):
        if max(self.usage().values()) >= self.limit:
            raise TimeoutError(f"Combined {self.limit}-second resource cap")


def fit_rf(samples, out):
    xt, yt, _, _, excluded_train = rf_arrays(samples["train"])
    xv, yv, group, bg, excluded_val = rf_arrays(samples["validation"])
    ix = balanced_pixels(yt)
    overall = Budget(180)
    runs = {}
    for name,n in (("RF-A",3),("RF-B",4)):
        local = Budget(180)
        model = RandomForestClassifier(**RF, warm_start=True)
        for trees in range(10,101,10):
            overall.check()
            model.set_params(n_estimators=trees).fit(xt[ix,:n],yt[ix])
        overall.check()
        prob = model.predict_proba(xv[:,:n])[:,1]
        path = out / f"{name}.joblib"
        joblib.dump(model,path,compress=3)
        result = evaluate(yv,prob,group,bg)
        runs[name] = result | local.usage() | dict(
            features=["B3","B4","B8","NDVI"][:n], config=RF, train_samples=int(ix.size),
            train_positive=int(yt[ix].sum()), sample_index_sha256=digest(ix.tobytes()),
            train_ndvi_excluded=excluded_train, val_ndvi_excluded=excluded_val,
            checkpoint_sha256=digest(path.read_bytes()))
        write_json(out / f"{name}.json",runs[name])
        print(name,runs[name]["pooled"],local.usage(),flush=True)
    return runs


class StaticUNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.e1,self.e2,self.e3 = conv(3,16),conv(16,32),conv(32,64)
        self.d2,self.d1,self.head = conv(96,32),conv(48,16),nn.Conv2d(16,1,1)

    def forward(self,x):
        a = self.e1(x)
        b = self.e2(F.max_pool2d(a,2))
        c = self.e3(F.max_pool2d(b,2))
        d = self.d2(torch.cat([F.interpolate(c,size=b.shape[-2:],mode="bilinear",
                                             align_corners=False),b],1))
        return self.head(self.d1(torch.cat([F.interpolate(d,size=a.shape[-2:],mode="bilinear",
                                                          align_corners=False),a],1)))


def tensors(records,norm):
    means, scales = (np.asarray(norm[k])[:,None,None] for k in ("mean","sd"))
    return [(
        torch.from_numpy(np.where(v,(x-means)/scales,0).astype("float32")[None]),
        torch.from_numpy((y==1)[None,None]).float(),
        torch.from_numpy((v & (y!=255))[None,None]),
        row,
    ) for row,x,v,y in records]


def update(model,opt,batch,clip,dice=False):
    x,y,m = (torch.cat([row[k] for row in batch]) for k in range(3))
    opt.zero_grad(set_to_none=True)
    logits = model(x)
    loss = masked_loss(logits,y,m)
    if dice:
        p,t = logits[m].sigmoid(),y[m]
        loss = loss + 1 - (2*(p*t).sum()+1)/(p.sum()+t.sum()+1)
    if not torch.isfinite(loss):
        raise ValueError("Nonfinite masked loss")
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(),clip if clip else float("inf"),
                                          error_if_nonfinite=True)
    opt.step()
    if any(not torch.isfinite(p).all() for p in model.parameters()):
        raise ValueError("Nonfinite weights after update")
    return float(norm)


def infer(model,samples):
    ys, ps, groups, bg, losses = [], [], [], [], []
    model.eval()
    with torch.no_grad():
        for x,y,m,row in samples:
            logits = model(x)
            losses.append(float(masked_loss(logits,y,m)))
            ys.append(y[m].numpy().astype("uint8"))
            ps.append(logits[m].sigmoid().numpy())
            groups.append(np.full(int(m.sum()),row["group_id"]))
            bg.append(np.full(int(m.sum()),bool(row["negative_stratum"])))
    model.train()
    return tuple(np.concatenate(k) for k in (ys,ps,groups,bg)) + (float(np.mean(losses)),)


def stability_pass(track):
    final = [v for v in track if 900 <= v["step"] <= 1000]
    return ([v["step"] for v in final] == [900,925,950,975,1000]
            and all(v["iou"] is not None and v["iou"] >= .90 for v in final)
            and final[-1]["loss"] < .15)


def diagnose(samples, norm, out):
    samples = tensors(samples,norm)
    overall = Budget(720)

    def attempt(name,seed,batch,clip):
        local = Budget(720)
        torch.manual_seed(seed)
        model = StaticUNet()
        opt = torch.optim.Adam(model.parameters(),lr=.0003)
        trajectory, norms, done, failure = [], [], 0, None
        try:
            for step in range(1001):
                overall.check()
                if step:
                    idx = (step-1)*batch
                    norms.append(update(model,opt,[samples[(idx+i)%8] for i in range(batch)],clip))
                    done = step
                if step % 25 == 0:
                    y,p,_,_,loss = infer(model,samples)
                    trajectory.append(dict(step=step,loss=loss,iou=detail(y,p,.5)["iou"],
                                           max_unclipped_grad=max(norms,default=None)))
                    norms.clear()
                    overall.check()
        except (TimeoutError,ValueError,RuntimeError) as exc:
            failure = str(exc)
        passed = failure is None and stability_pass(trajectory)
        result = dict(name=name,seed=seed,batch=batch,clip=clip,lr=.0003,
                      steps=done,trajectory=trajectory,failure=failure,passed=passed) | local.usage()
        write_json(out / f"diagnostic-{name}-{seed}.json",result)
        print("Stability",name,seed,done,passed,failure,trajectory[-1:] ,flush=True)
        return result

    attempts = []
    selected = None
    for name,batch,clip in (("lower_lr",1,None),("clip",1,1.),("batch4",4,1.)):
        run = attempt(name,42,batch,clip)
        attempts.append(run)
        if run["passed"]:
            selected = (name,batch,clip)
            break
        if isinstance(run["failure"],str) and "resource cap" in run["failure"]:
            break
    gate = False
    if selected:
        name,batch,clip = selected
        for seed in (43,44):
            run = attempt(name,seed,batch,clip)
            attempts.append(run)
            if not run["passed"]:
                break
        gate = sum(r["passed"] for r in attempts) == 3
    return dict(gate_pass=gate,selected=selected,attempts=attempts) | overall.usage()


def fit_unet(samples,norm,selected,out):
    train,val = (tensors(samples[k],norm) for k in ("train","validation"))
    _,batch,clip = selected
    overall = Budget(900)
    results = {}
    for seed in (42,43):
        local = Budget(900)
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        model = StaticUNet()
        optimizer = torch.optim.Adam(model.parameters(),lr=.0003)
        path = out / f"unet-{seed}.pt"
        scores,best,best_epoch,failure = [],-1.,0,None
        try:
            for epoch in range(1,31):
                order = rng.permutation(len(train))
                for start in range(0,len(order),batch):
                    overall.check()
                    update(model,optimizer,[train[i] for i in order[start:start+batch]],clip,True)
                overall.check()
                y,p,_,_,loss = infer(model,val)
                score = detail(y,p,.5)["iou"]
                scores.append(dict(epoch=epoch,val_weak_iou=score,val_masked_bce=loss))
                if score > best:
                    best,best_epoch = score,epoch
                    torch.save(model.state_dict(),path)
                if epoch-best_epoch >= 5:
                    break
        except (TimeoutError,ValueError,RuntimeError) as exc:
            failure = str(exc)
        result = dict(seed=seed,features=["B3","B4","B8"], lr=.0003,batch=batch,
                      clip=clip,loss="masked BCE + Dice", epochs=scores,best_epoch=best_epoch,
                      failure=failure) | local.usage()
        if best_epoch:
            model.load_state_dict(torch.load(path,weights_only=True))
            y,p,g,b,_ = infer(model,val)
            result |= evaluate(y,p,g,b) | dict(checkpoint_sha256=digest(path.read_bytes()))
        write_json(out/f"unet-{seed}.json",result)
        results[str(seed)] = result
        if failure:
            break
    return results


def run(action,out=DEST):
    samples,diagnostic,norm,hashes = cached_inputs()
    out.mkdir(parents=True,exist_ok=True)
    receipt = dict(plan_sha256=PLAN_SHA,split_sha256=SPLIT_SHA,test_sealed=True,
        normalization=norm,manifest_hashes=hashes,protocol_sha256=digest(PROTO.read_bytes()),
        python=platform.python_version(), numpy=np.__version__, sklearn=sklearn.__version__,
        torch=str(torch.__version__), support={k:dict(patches=len(v),groups=len({r[0]["group_id"] for r in v}),
          known_pixels=sum(int((r[2] & (r[3]!=255)).sum()) for r in v)) for k,v in samples.items()})
    if not (out/"preflight.json").exists():
        write_json(out/"preflight.json",receipt)
    elif json.loads((out/"preflight.json").read_bytes()) != receipt:
        raise ValueError("Local Phase 22F preflight differs from the previous invocation")
    if action == "rf":
        fit_rf(samples,out)
    elif action == "unet":
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        state = diagnose(diagnostic,norm,out)
        write_json(out/"stability.json",state)
        if state["gate_pass"]:
            write_json(out/"unet.json",fit_unet(samples,norm,state["selected"],out))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action",choices=("preflight","rf","unet"))
    run(cli.parse_args().action)
