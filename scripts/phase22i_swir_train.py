"""Offline paired F1/F2 comparisons on identical Phase 22I cell support."""

import argparse
import json
from pathlib import Path
from statistics import mean, stdev
from time import process_time

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import torch
from torch import nn

from scripts.phase22b_maus import digest, train_normalization, write_json
from scripts.phase22f_maus import RF, Budget, StaticUNet, balanced_pixels, infer, select_threshold, tensors, update
from scripts.phase22h_maus_acquire import DEST as BASE
from scripts.phase22h_maus_train import WARNING, at_threshold, augment, batches, choose, training_data
from scripts.phase22i_swir_acquire import DEST, SHA, SPLIT_SHA, common_support, read_extra
from src.phase3.model import conv

BANDS = {"F1":["B3","B4","B8"],"F2":["B2","B3","B4","B8","B11","B12"]}


def inputs():
    observations,original,previous_norm,_=training_data()
    receipt=json.loads((DEST/"acquisition.json").read_bytes())
    if (receipt["manifest_sha256"]!=SHA or receipt["split_sha256"]!=SPLIT_SHA
            or receipt["test_sealed"] is not True or receipt["patches"]!=153):
        raise ValueError("Frozen acquisition receipt mismatch")
    paired={arm:{role:[] for role in observations} for arm in BANDS}
    changed=False
    for role,records in observations.items():
        for row,x,old,y in records:
            p=DEST/"bands"/f"{row['patch_id']}.tif"
            extra=json.loads(p.with_suffix(".json").read_bytes())
            if (extra["tiff_sha256"]!=digest(p.read_bytes()) or extra["source_ids"]!=row["source_ids"]
                    or extra["source_dates_ms"]!=row["source_dates_ms"]
                    or extra["parent_image_sha256"]!=row["image_sha256"]
                    or extra["parent_mask_sha256"]!=row["mask_sha256"]):
                raise ValueError("Extra bands fail frozen input hash/provenance check")
            z,valid=read_extra(p,row)
            common=common_support(old,valid,y)
            if int(common.sum())!=extra["common_valid_cells"]:
                raise ValueError("Common support changed after acquisition")
            changed |= not np.array_equal(old,common)
            paired["F1"][role].append((row,x,common,y))
            paired["F2"][role].append((row,np.concatenate((z[:1],x,z[1:])),common,y))
    norms={}
    for arm in BANDS:
        avg,std=train_normalization([("train",x,v) for _,x,v,_ in paired[arm]["train"]])
        norms[arm]=dict(mean=avg.tolist(),sd=std.tolist(),bands=BANDS[arm])
    if not changed:
        norms["F1"]=previous_norm
    ids={r[0]["patch_id"] for r in original["validation"]}
    return paired,norms,ids,changed


def flatten(records):
    a,b,c,d=[],[],[],[]
    for row,x,v,y in records:
        mask=v&(y!=255)
        a.append(x[:,mask].T)
        b.append(y[mask])
        c.append(np.full(mask.sum(),row["group_id"]))
        d.append(np.full(mask.sum(),bool(row["negative_stratum"])))
    return tuple(np.concatenate(x) for x in (a,b,c,d))


def subset(records,ids):
    values=[row for row in records if row[0]["patch_id"] in ids]
    if len(values)!=15:
        raise ValueError("Frozen original validation subset must have 15 records")
    return values


def verify_reused_checkpoint(name,baseline):
    extension=".joblib" if name.startswith("RF") else ".pt"
    p=BASE/"models"/(name+extension)
    if digest(p.read_bytes()) != baseline["checkpoint_sha256"]:
        raise ValueError("Frozen Phase 22H checkpoint checksum mismatch")
    return {k:baseline[k] for k in ("expanded","original","checkpoint_sha256")} | {"reused_phase22h":True}


def rf_run(paired,ids,changed,out):
    left=flatten(paired["F1"]["train"])
    right=flatten(paired["F2"]["train"])
    if any(not np.array_equal(a,b) for a,b in zip(left[1:],right[1:],strict=True)):
        raise ValueError("RF TRAIN support mismatch")
    selected=balanced_pixels(left[1])
    baseline=json.loads((BASE/"models"/"rf-results.json").read_bytes())["models"]["RF-A"]
    result={}
    budget=Budget(180)
    for arm,training in (("F1",left),("F2",right)):
        if arm=="F1" and not changed:
            result[arm]=verify_reused_checkpoint("RF-A",baseline)
            continue
        x,y,_,_=training
        model=RandomForestClassifier(**RF,warm_start=True)
        start=process_time()
        for n in range(10,101,10):
            budget.check()
            model.set_params(n_estimators=n).fit(x[selected],y[selected])
        val=paired[arm]["validation"]
        xx,yy,g,bg=flatten(val)
        p=model.predict_proba(xx)[:,1]
        t,candidates=select_threshold(yy,p)
        orig=subset(val,ids)
        ox,oy,og,obg=flatten(orig)
        path=out/f"rf-{arm}.joblib"
        joblib.dump(model,path,compress=3)
        result[arm]=dict(expanded=at_threshold(yy,p,g,bg,val,t),
            original=at_threshold(oy,model.predict_proba(ox)[:,1],og,obg,orig,t),
            cpu_seconds=process_time()-start,checkpoint_sha256=digest(path.read_bytes()),
            threshold_candidates=candidates,training_samples=int(len(selected)),
            sample_index_sha256=digest(selected.tobytes()),config=RF)
        print("RF",arm,result[arm]["expanded"]["pooled"],flush=True)
    return result


class SwirUNet(StaticUNet):
    def __init__(self):
        nn.Module.__init__(self)
        self.e1,self.e2,self.e3=conv(6,16),conv(16,32),conv(32,64)
        self.d2,self.d1,self.head=conv(96,32),conv(48,16),nn.Conv2d(16,1,1)


def unet_fit(arm,seed,data,norm,ids,out,cpu_start):
    train=[(*t,torch.from_numpy(v[None,None])) for t,(_,_,v,_) in
           zip(tensors(data["train"],norm),data["train"],strict=True)]
    va=data["validation"]
    orig=subset(va,ids)
    val=tensors(va,norm)
    pos=[i for i,r in enumerate(train) if not r[3]["negative_stratum"]]
    neg=[i for i,r in enumerate(train) if r[3]["negative_stratum"]]
    torch.manual_seed(seed)
    rng=np.random.default_rng(seed)
    model=StaticUNet() if arm=="F1" else SwirUNet()
    opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001)
    best=None
    cutoff,selected=0,0
    history=[]
    start=process_time()
    file=out/f"unet-{arm}-{seed}.pt"
    failure=None
    def budget_check():
        if process_time()-cpu_start>=1200:
            raise TimeoutError("Combined 1,200-second U-Net CPU cap")
    try:
        for epoch in range(1,41):
            for ix in batches(pos,neg,rng):
                budget_check()
                update(model,opt,augment([train[i] for i in ix],norm,rng),1.,True)
            budget_check()
            yy,p,_,_,loss=infer(model,val)
            rank,t=choose(yy,p,epoch)
            history.append(dict(epoch=epoch,threshold=t,objective=rank[0],masked_bce=loss))
            if best is None or rank>best:
                best,cutoff,selected=rank,t,epoch
                torch.save(model.state_dict(),file)
            if epoch-selected>=5:
                break
    except (TimeoutError,ValueError,RuntimeError) as exc:
        failure=str(exc)
    row=dict(arm=arm,seed=seed,bands=BANDS[arm],epochs=history,best_epoch=selected,
             failure=failure,cpu_seconds=process_time()-start)
    if selected:
        model.load_state_dict(torch.load(file,weights_only=True))
        for role,records in (("expanded",va),("original",orig)):
            y,p,g,b,_=infer(model,tensors(records,norm))
            row[role]=at_threshold(y,p,g,b,records,cutoff)
        row["checkpoint_sha256"]=digest(file.read_bytes())
    write_json(out/f"unet-{arm}-{seed}.json",row)
    print("U-Net",arm,seed,selected,row.get("expanded",{}).get("pooled"),failure,flush=True)
    return row


def unet_run(paired,norms,ids,changed,out):
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    baseline={r["seed"]:r for r in json.loads((BASE/"models"/"unet-results.json").read_bytes())["runs"]}
    cpu_start=process_time()
    results=[]
    for seed in (42,43,44):
        pair=dict(seed=seed)
        results.append(pair)
        for arm in BANDS:
            if process_time()-cpu_start>=1200:
                break
            if arm=="F1" and not changed:
                pair[arm]=verify_reused_checkpoint(f"unet-{seed}",baseline[seed])
            else:
                pair[arm]=unet_fit(arm,seed,paired[arm],norms[arm],ids,out,cpu_start)
                if pair[arm]["failure"]:
                    break
        if len(pair)!=3 or any(pair[k].get("failure") for k in BANDS if k in pair):
            break
    return dict(pairs=results,cpu_seconds=process_time()-cpu_start,summary=aggregate_pairs(results))


def aggregate_pairs(results):
    eligible=[r for r in results if all(k in r and not r[k].get("failure") and "expanded" in r[k]
                                      for k in BANDS)]
    table={}
    for arm in BANDS:
        table[arm]={}
        for role in ("expanded","original"):
            table[arm][role]={}
            for key in ("precision","recall","f1","iou","fpr"):
                values=[p[arm][role]["pooled"][key] for p in eligible]
                table[arm][role][key]=dict(mean=mean(values) if values else None,
                    sample_sd=stdev(values) if len(values)>1 else None)
    return dict(completed_seeds=[r["seed"] for r in eligible],arms=table)


def support_receipt(paired):
    return {role:dict(
        mask_sha256=digest(b"".join(np.packbits(v).tobytes() for _,_,v,_ in rows)),
        known_cells=sum(int((v&(y!=255)).sum()) for _,_,v,y in rows))
        for role,rows in paired["F1"].items()}


def recover_results(action,paired,ids,changed,out):
    if action=="rf":
        x,y,_,_=flatten(paired["F1"]["train"])
        selected=balanced_pixels(y)
        scored={}
        for arm in BANDS:
            if arm=="F1" and not changed:
                baseline=json.loads((BASE/"models"/"rf-results.json").read_bytes())["models"]["RF-A"]
                scored[arm]=verify_reused_checkpoint("RF-A",baseline)
                continue
            path=out/f"rf-{arm}.joblib"
            model=joblib.load(path)
            if (model.n_features_in_!=len(BANDS[arm]) or len(model.estimators_)!=100
                    or any(model.get_params()[k]!=v for k,v in RF.items())):
                raise ValueError("Recovered RF checkpoint has a different feature/config contract")
            val=paired[arm]["validation"]
            xx,yy,g,bg=flatten(val)
            p=model.predict_proba(xx)[:,1]
            t,candidates=select_threshold(yy,p)
            orig=subset(val,ids)
            ox,oy,og,obg=flatten(orig)
            scored[arm]=dict(expanded=at_threshold(yy,p,g,bg,val,t),
                original=at_threshold(oy,model.predict_proba(ox)[:,1],og,obg,orig,t),
                threshold_candidates=candidates,training_samples=int(len(selected)),config=RF,
                sample_index_sha256=digest(selected.tobytes()),
                checkpoint_sha256=digest(path.read_bytes()),recovered_without_refit=True)
        return scored
    baseline={r["seed"]:r for r in json.loads((BASE/"models"/"unet-results.json").read_bytes())["runs"]}
    pairs=[]
    for seed in (42,43,44):
        row=dict(seed=seed)
        for arm in BANDS:
            receipt=out/f"unet-{arm}-{seed}.json"
            if arm=="F1" and not changed:
                row[arm]=verify_reused_checkpoint(f"unet-{seed}",baseline[seed])
            elif receipt.exists():
                r=json.loads(receipt.read_bytes())
                if r["seed"]!=seed or r["bands"]!=BANDS[arm] or r["arm"]!=arm:
                    raise ValueError("Recovered U-Net arm/seed metadata mismatch")
                if r["best_epoch"] and r["checkpoint_sha256"] != digest(
                        (out/f"unet-{arm}-{seed}.pt").read_bytes()):
                    raise ValueError("Recovered U-Net checkpoint hash mismatch")
                row[arm]=r
        if len(row)>1:
            pairs.append(row)
    partial = []
    for seed in (42,43,44):
        for arm in BANDS:
            checkpoint = out / f"unet-{arm}-{seed}.pt"
            receipt = out / f"unet-{arm}-{seed}.json"
            if checkpoint.exists() and not receipt.exists():
                partial.append(dict(seed=seed,arm=arm,status="PARTIAL_CHECKPOINT_WITHOUT_RECEIPT",
                                    checkpoint_sha256=digest(checkpoint.read_bytes())))
    return dict(pairs=pairs,summary=aggregate_pairs(pairs),recovered_without_refit=True,
        partial_artifacts=partial,cpu_accounting_verified=False,
        cpu_accounting_limitation="Per-arm receipts omit interrupted and duplicate-fit CPU usage; remaining budget is unverified",
        sum_arm_cpu_seconds=sum(r[k].get("cpu_seconds",0) for r in pairs for k in BANDS if k in r))


def run(action):
    paired,norms,ids,changed=inputs()
    out=DEST/"models"
    out.mkdir(exist_ok=True)
    recover=action.endswith("-recover")
    model=action.removesuffix("-recover")
    target=out/f"{model}-results.json"
    if target.exists():
        raise ValueError("Phase 22I result already exists")
    if not recover:
        pattern = "rf-*.joblib" if model == "rf" else "unet-*"
        if any(out.glob(pattern)):
            raise ValueError("Existing completed or partial fit artifacts; use recovery without refitting")
    if recover:
        data=recover_results(model,paired,ids,changed,out)
    elif model=="rf":
        data=rf_run(paired,ids,changed,out)
    elif model=="unet":
        data=unet_run(paired,norms,ids,changed,out)
    else:
        raise ValueError("Unknown Phase 22I action")
    write_json(target,dict(warning=WARNING,test_sealed=True,common_support_changed=changed,
        split_sha256=SPLIT_SHA,manifest_sha256=SHA,bands=BANDS,train_normalization=norms,
        support=support_receipt(paired),results=data))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("rf","unet","rf-recover","unet-recover"))
    run(parser.parse_args().action)
