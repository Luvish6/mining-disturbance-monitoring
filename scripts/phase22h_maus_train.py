"""Fit and compare the preregistered Phase 22H weak-label baselines offline."""

import argparse
from collections import Counter
import json
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, ImageDraw
import torch

from scripts.phase22b_maus import ROOT, digest, stable, train_normalization, write_json
from scripts.phase22c_maus import SPLIT_SHA
from scripts.phase22e_maus_export import check_images
from scripts.phase22f_maus import (CACHE, Budget, StaticUNet, cached_inputs, detail, fit_rf, infer,
                                   ndvi_features, rf_arrays, tensors, update)
from scripts.phase22h_maus_acquire import DEST, MANIFEST, SHA, authenticated, data_paths

WARNING = "Agreement with unverified Maus v2 weak labels - NOT independently verified Indian accuracy."
GRID = tuple(i/100 for i in range(10,91,5))
BASELINE = Path("docs/reports/phase22f-weak-label-metrics.json")
PROTOCOL = Path("docs/preregistration-phase22h-v1.md")


def training_data():
    old, _, _, hashes = cached_inputs()
    dataset = json.loads((DEST/"dataset.json").read_bytes())
    inspection = json.loads((DEST/"visual-inspection.json").read_bytes())
    if (dataset["dataset_go"] is not True or dataset["approved_sha256"] != SHA
            or dataset["test_sealed"] is not True or hashes != dataset["original_manifest_hashes"]
            or inspection["contact_sha256"] != digest((DEST/"overlays"/"sample-contact.png").read_bytes())):
        raise ValueError("Dataset and visual QA gates must pass")
    manifest = authenticated(MANIFEST,SHA)
    proposed = {r["patch_id"]:r for r in manifest["patches"]}
    samples = {}
    for role in ("train","validation"):
        receipt = json.loads((DEST/f"{role}_manifest.json").read_bytes())
        if receipt["approved_sha256"] != SHA:
            raise ValueError("Approved acquisition hash mismatch")
        cache = {r[0]["patch_id"]:r for r in old[role]}
        records = []
        for row in receipt["patches"]:
            key = row["patch_id"]
            approved = proposed[key]
            if row["split"] != role or any(row[k] != approved[k] for k in (
                    "split","group_id","state","bounds","crs","affine","label_source_fids","negative_stratum")):
                raise ValueError("Changed or sealed patch identity")
            if key in cache:
                if row != cache[key][0]:
                    raise ValueError("Phase 22F cache receipt changed")
                records.append(cache[key])
                continue
            image,mask = data_paths(row)
            for file, field in ((image,"image_sha256"),(mask,"mask_sha256")):
                if digest(file.read_bytes()) != row[field]:
                    raise ValueError("New raster hash mismatch")
            original_receipt = json.loads((DEST/"patches"/f"{key}.json").read_bytes())
            fingerprint = original_receipt.pop("provenance_hash")
            if (digest(json.dumps(original_receipt,sort_keys=True).encode()) != fingerprint
                    or row != (original_receipt | dict(provenance_hash=fingerprint,cache="phase22h"))
                    or row["plan_sha256"] != SHA or row["state_of_patch"]!="QA_ACCEPTED_WEAK"):
                raise ValueError("New raster provenance mismatch")
            x,v,y = check_images(image,mask,row)
            if v.mean()<.70 or int((y==1).sum())!=row["positive_pixels"] or int((y==0).sum())!=row["background_pixels"]:
                raise ValueError("Weak-mask support changed")
            records.append((row,x,v,y))
        ids = [row[0]["patch_id"] for row in records]
        classes = Counter((r[0]["group_id"],bool(r[0]["negative_stratum"])) for r in records)
        if (not cache.keys() <= set(ids) or len(ids)!=len(set(ids))
                or any(classes[g,False]!=1 or classes[g,True]!=2 for g,_ in classes)):
            raise ValueError("Only complete frozen group triples may enter training")
        samples[role] = records
    means,sd = train_normalization(normalization_order(samples["train"],manifest))
    norm = dataset["normalization"]
    if not np.array_equal(means,norm["mean"]) or not np.array_equal(sd,norm["sd"]):
        raise ValueError("TRAIN-only normalization failed replay")
    if digest((ROOT/"split.json").read_bytes()) != SPLIT_SHA:
        raise ValueError("Frozen split changed")
    return samples,old,norm,dataset


def normalization_order(records,manifest):
    lookup={row[0]["patch_id"]:row for row in records}
    ordered=sorted((r for r in manifest["patches"][:39] if r["split"]=="train"),
                   key=lambda r:stable(r["patch_id"]))
    ordered+= [r for r in manifest["patches"][39:] if r["split"]=="train" and r["patch_id"] in lookup]
    return [("train",lookup[row["patch_id"]][1],lookup[row["patch_id"]][2]) for row in ordered]


def at_threshold(y,p,groups,bg,records,threshold):
    by_state = {row[0]["group_id"]:row[0]["state"] for row in records}
    state = np.array([by_state[g] for g in groups])
    def partition(mask):
        fp = int(((p>=threshold)&bg&mask).sum())
        denom = int((bg&mask).sum())
        return detail(y[mask],p[mask],threshold) | dict(
            background_only=dict(fp=fp,pixels=denom,fpr=fp/denom if denom else None))
    return dict(threshold=threshold,pooled=partition(np.ones(y.shape,dtype=bool)),
        per_group={digest(str(g).encode())[:12]:partition(groups==g) for g in np.unique(groups)},
        per_state={s:partition(state==s) | dict(
            patches=sum(r[0]["state"]==s for r in records),
            groups=len({r[0]["group_id"] for r in records if r[0]["state"]==s}))
            for s in np.unique(state)})


def objective_rank(metric,threshold,epoch):
    iou,fpr = metric["iou"],metric["fpr"]
    return (iou-.25*fpr,-fpr,-abs(round(threshold*100)-50),-epoch,-threshold)


def choose(y,p,epoch):
    choices = [(objective_rank(detail(y,p,t),t,epoch),t) for t in GRID]
    return max(choices)


def batches(positives,backgrounds,rng):
    order=rng.permutation(positives)
    chosen=rng.permutation(backgrounds)[:3*len(order)]
    return [[p,*background] for p,background in zip(order,np.array_split(chosen,len(order)),strict=True)]


def augment(records,norm,rng):
    mean=torch.tensor(norm["mean"],dtype=torch.float32)[None,:,None,None]
    sd=torch.tensor(norm["sd"],dtype=torch.float32)[None,:,None,None]
    batch=[]
    for x,y,m,row,v in records:
        brightness=float(rng.uniform(.95,1.05))
        x=torch.where(v,(brightness*(x*sd+mean)-mean)/sd,0.)
        values=(x,y,m)
        for dimension in (-1,-2):
            if rng.integers(2):
                values=tuple(t.flip((dimension,)) for t in values)
        k=int(rng.integers(4))
        batch.append(tuple(t.rot90(k,(-2,-1)) for t in values)+(row,))
    return batch


def rf_scores(model,records,n,threshold):
    x,y,g,b,_=rf_arrays(records)
    return at_threshold(y,model.predict_proba(x[:,:n])[:,1],g,b,records,threshold)


def error_examples(model,n,records,threshold,out):
    choices=[]
    for row,x,v,y in records:
        clean,use=ndvi_features(x,v&(y!=255))
        if not use.any():
            continue
        p=model.predict_proba(clean[:,:n])[:,1]
        d=detail(y[use],p,threshold)
        pred=np.zeros(y.shape,dtype=bool)
        pred[use]=p>=threshold
        choices.append((row,x,y,pred,d))
    pos=sorted((r for r in choices if not r[0]["negative_stratum"]),
               key=lambda r:(r[4]["iou"],r[0]["patch_id"]))[:3]
    bg=sorted((r for r in choices if r[0]["negative_stratum"]),
              key=lambda r:(-r[4]["confusion"][0][1],r[0]["patch_id"]))[:2]
    sheet=Image.new("RGB",(3*128,150*len(pos+bg)),(20,20,20))
    draw=ImageDraw.Draw(sheet)
    result=[]
    for i,(row,x,y,pr,d) in enumerate(pos+bg):
        rgb=(np.clip(np.nan_to_num(x[[1,2,0]])/.30,0,1)*255).astype("uint8").transpose(1,2,0)
        weak=rgb.copy()
        weak[y==1]=(255,190,0)
        weak[y==0]=(70,140,200)
        errors=rgb.copy()
        errors[pr&(y==1)]=(0,220,125)
        errors[pr&(y==0)]=(255,70,80)
        errors[~pr&(y==1)]=(255,190,0)
        for col,arr in enumerate((rgb,weak,errors)):
            sheet.paste(Image.fromarray(arr),(128*col,150*i))
        draw.text((3,150*i+131),f"{i+1} {row['negative_stratum'] or 'positive'} | IoU {d['iou']} | FP {d['confusion'][0][1]}",fill="white")
        result.append(dict(index=i+1,group=digest(row["group_id"].encode())[:12],
                           patch_digest=digest(row["patch_id"].encode()), stratum=row["negative_stratum"],
                           metrics=d,visual_status="HUMAN REVIEW PENDING"))
    sheet.save(out/"rf-error-contact.png")
    return result


def train_rf(samples,old,out):
    fits=fit_rf(samples,out)
    scores={}
    for name,n in (("RF-A",3),("RF-B",4)):
        fit=fits[name]
        model=joblib.load(out/f"{name}.joblib")
        cutoff=fit["threshold"]
        scores[name]=dict(config=fit["config"],features=fit["features"],
            expanded=rf_scores(model,samples["validation"],n,cutoff),
            original=rf_scores(model,old["validation"],n,cutoff),
            candidates=fit["candidates"],train_samples=fit["train_samples"],
            ndvi_exclusions=[fit["train_ndvi_excluded"],fit["val_ndvi_excluded"]],
            cpu_seconds=fit["cpu_seconds"],wall_seconds=fit["wall_seconds"],
            checkpoint_sha256=fit["checkpoint_sha256"])
    chosen=min(scores,key=lambda k:(scores[k]["expanded"]["pooled"]["fpr"],-scores[k]["expanded"]["pooled"]["f1"],k))
    cv=scores[chosen]
    errors=error_examples(joblib.load(out/f"{chosen}.joblib"),len(cv["features"]),
                          samples["validation"],cv["expanded"]["threshold"],out)
    return dict(models=scores,provisional=chosen,error_examples=errors,warning=WARNING)


def train_unet(samples,old,norm,out):
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    train=[(*t,torch.from_numpy(v[None,None])) for t,(_,_,v,_) in
           zip(tensors(samples["train"],norm),samples["train"],strict=True)]
    val=tensors(samples["validation"],norm)
    original=tensors(old["validation"],norm)
    pos=[i for i,r in enumerate(train) if not r[3]["negative_stratum"]]
    bg=[i for i,r in enumerate(train) if r[3]["negative_stratum"]]
    overall=Budget(1200)
    results=[]
    for seed in (42,43,44):
        if max(overall.usage().values())>=1200:
            break
        local=Budget(1200)
        torch.manual_seed(seed)
        rng=np.random.default_rng(seed)
        model=StaticUNet()
        opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001)
        best=None
        best_epoch,cutoff=0,None
        epochs,exposure=[],Counter()
        failure=None
        path=out/f"unet-{seed}.pt"
        try:
            for epoch in range(1,41):
                for indices in batches(pos,bg,rng):
                    overall.check()
                    update(model,opt,augment([train[i] for i in indices],norm,rng),1.,True)
                    exposure.update("background" if train[i][3]["negative_stratum"] else "positive" for i in indices)
                overall.check()
                y,p,_,_,loss=infer(model,val)
                rank,selected=choose(y,p,epoch)
                epochs.append(dict(epoch=epoch,objective=rank[0],threshold=selected,masked_bce=loss))
                if best is None or rank>best:
                    best,best_epoch,cutoff=rank,epoch,selected
                    torch.save(model.state_dict(),path)
                if epoch-best_epoch>=5:
                    break
        except (TimeoutError,ValueError,RuntimeError) as exc:
            failure=str(exc)
        result=dict(seed=seed,features=["B3","B4","B8"],epochs=epochs,best_epoch=best_epoch,
            exposure=dict(exposure),failure=failure,
            config=dict(learning_rate=.0003,weight_decay=.0001,clip=1,loss="masked BCE + Dice")) | local.usage()
        if best_epoch:
            model.load_state_dict(torch.load(path,weights_only=True))
            for key,ts,records in (("expanded",val,samples["validation"]),("original",original,old["validation"])):
                y,p,g,b,_=infer(model,ts)
                result[key]=at_threshold(y,p,g,b,records,cutoff)
            result["checkpoint_sha256"]=digest(path.read_bytes())
        write_json(out/f"unet-{seed}.json",result)
        print("U-Net",seed,best_epoch,result.get("expanded",{}).get("pooled"),failure,flush=True)
        results.append(result)
        if failure:
            break
    return dict(runs=results,warning=WARNING) | overall.usage()


def run(action):
    samples,old,norm,dataset=training_data()
    out=DEST/"models"
    out.mkdir(exist_ok=True)
    target=out/f"{action}-results.json"
    if target.exists():
        raise ValueError("Completed Phase 22H training receipt already exists")
    result = train_rf(samples,old,out) if action=="rf" else train_unet(samples,old,norm,out)
    write_json(target,result | dict(approved_sha256=SHA,split_sha256=SPLIT_SHA,test_sealed=True,
                                 protocol_sha256=digest(PROTOCOL.read_bytes())))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action",choices=("rf","unet"))
    run(cli.parse_args().action)
