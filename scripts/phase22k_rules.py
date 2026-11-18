"""TRAIN-selected static index rules on frozen Phase 22H optical weak masks."""

from itertools import product
import json
from pathlib import Path

import numpy as np

from scripts.phase22b_maus import digest, write_json
from scripts.phase22h_maus_train import WARNING, at_threshold, training_data
from scripts.phase22h_maus_acquire import SHA
from scripts.phase22c_maus import SPLIT_SHA

GRIDS = (np.arange(-2,9)/10, np.arange(1,16)/50, np.arange(-6,5)/10)
OUT = Path("outputs/phase22k_maus")


def indices(features):
    g,r,n = np.asarray(features,dtype="float64")
    if not np.isfinite(features).all() or np.any(n+r==0) or np.any(g+n==0):
        raise ValueError("Finite optical input and nonzero index denominators required")
    return np.stack(((n-r)/(n+r), (g+r+n)/3, (g-n)/(g+n)),axis=1)


def rule(values,thresholds):
    predicted=values[:,0]<thresholds[0]
    if len(thresholds)>=2:
        predicted &= values[:,1]>thresholds[1]
    if len(thresholds)==3:
        predicted &= values[:,2]<thresholds[2]
    return predicted


def select_train(values,y):
    if values.shape!=(len(y),3) or not np.isin(y,[0,1]).all() or not len(y):
        raise ValueError("Expected nonempty binary TRAIN support")
    # Encode strict comparisons exactly, including observations on grid boundaries.
    bins=np.stack([np.searchsorted(grid,values[:,k],side="right" if k!=1 else "left")
                   for k,grid in enumerate(GRIDS)],axis=1)
    shape=tuple(len(g)+1 for g in GRIDS)
    encoded=np.ravel_multi_index(bins.T,shape)
    hist=[np.bincount(encoded[y==c],minlength=int(np.prod(shape))).reshape(shape) for c in (0,1)]
    total=int(y.sum())
    selected={}
    for length,name in ((1,"A"),(2,"B"),(3,"C")):
        best=-1
        for combo in product(*(range(len(g)) for g in GRIDS[:length])):
            a=combo[0]
            b=slice(combo[1]+1,None) if length>=2 else slice(None)
            c=slice(None,combo[2]+1) if length==3 else slice(None)
            fp,tp=(int(h[:a+1,b,c].sum()) for h in hist)
            f1=2*tp/(total+tp+fp) if total+tp+fp else 0.
            if f1>best:
                best=f1
                selected[name]=[float(GRIDS[k][v]) for k,v in enumerate(combo)]
    return selected


def flatten(records):
    values,labels,groups,background=[],[],[],[]
    for row,x,valid,y in records:
        known=valid&(y!=255)
        values.append(indices(x[:,known]))
        labels.append(y[known])
        groups.append(np.full(known.sum(),row["group_id"]))
        background.append(np.full(known.sum(),bool(row["negative_stratum"])))
    return tuple(np.concatenate(k) for k in (values,labels,groups,background))


def run():
    samples,_,_,_=training_data()
    train=flatten(samples["train"])
    thresholds=select_train(train[0],train[1])
    OUT.mkdir(parents=True,exist_ok=True)
    write_json(OUT/"frozen-thresholds.json",dict(selected_on="TRAIN",thresholds=thresholds,
        protocol_sha256=digest(Path("docs/preregistration-phase22k-v1.md").read_bytes())))
    # Thresholds are persisted before validation features or labels are evaluated.
    val=flatten(samples["validation"])
    scores={}
    for name,cutoffs in thresholds.items():
        scores[name]=dict(thresholds=cutoffs)
        for role,arrays in (("train",train),("validation",val)):
            x,y,g,bg=arrays
            scores[name][role]=at_threshold(y,rule(x,cutoffs).astype(float),g,bg,samples[role],.5)
    result=dict(warning=WARNING,selected_on="TRAIN",test_sealed=True,
                split_sha256=SPLIT_SHA,manifest_sha256=SHA,
                grids=[g.tolist() for g in GRIDS],rules=scores,
                support=dict(train=len(train[1]),validation=len(val[1])))
    write_json(OUT/"metrics.json",result)
    print(json.dumps({name:dict(thresholds=row["thresholds"],
        train=row["train"]["pooled"],validation=row["validation"]["pooled"]) for name,row in scores.items()}))


if __name__=="__main__":
    run()
