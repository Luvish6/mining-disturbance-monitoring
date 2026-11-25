"""Offline pseudo-label U-Net experiment. No admitted mining labels or TEST support."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import hashlib
import json
import random
import time
from pathlib import Path
import numpy as np
import rasterio
import torch
from src.phase3.model import SiameseUNet
from src.phase25.dataset import load_manifest,BANDS,sha
from src.phase25.learning import adapt_patch,masked_bce_dice,metric_counts,CONTRACT,CONTRACT_SHA,load_evaluation_frame

MANIFEST_SHA='3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa'
CLAIM='Agreement with algorithm-generated pseudo-labels; NOT verified mining detection accuracy'


def load_data(root):
    root=Path(root)
    if sha(root/'manifest.json')!=MANIFEST_SHA:raise ValueError('Frozen dataset changed')
    m=load_manifest(root);data=[]
    if len(m['patches'])!=80:raise ValueError('Exactly frozen80patches required')
    for row in m['patches']:
        record={}
        for name,names in [('features',BANDS),('validity',BANDS),('pseudo_states',['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE'])]:
            path=root/row['files'][name]
            with rasterio.open(path) as ds:
                if ds.crs.to_string()!=row['crs'] or list(ds.transform)[:6]!=row['affine'] or list(ds.shape)!=[32,32] or list(ds.descriptions)!=names:raise ValueError('Input raster contract mismatch')
                a=ds.read()
                if name=='features':a=np.where(a==ds.nodata,np.nan,a)
                if name=='validity' and not np.isin(a,[0,1]).all():raise ValueError('Binary validity required')
                record[name]=a[0] if name=='pseudo_states' else a.astype(bool) if name=='validity' else a
            if sha(path)!=m['artifacts'][row['files'][name]]:raise ValueError('Cache changed during loading')
        d=adapt_patch(record);data.append(dict(row=row,raw=record,adapted=d))
    if sum(r['row']['split']=='train' for r in data)!=68:raise ValueError('Frozen TRAIN/VAL counts changed')
    return m,data


def payload_metadata(seed):
    return dict(architecture='SiameseUNet',channels=5,width=16,contract_sha256=CONTRACT_SHA,input_contract=CONTRACT,dataset_sha256=MANIFEST_SHA,seed=seed,label_kind='ALGORITHM_PSEUDO_LABEL_NOT_REFERENCE',model_validation_status='NOT_VALIDATED',operational_alerts=0,threshold=.5,claim=CLAIM)


def load_model(path,device='cpu'):
    """Read-only hook for a later dashboard adapter; never operational inference admission."""
    p=Path(path);receipt=json.loads(p.with_suffix('.json').read_bytes())
    if sha(p)!=receipt['sha256']:raise ValueError('Checkpoint checksum mismatch')
    ck=torch.load(p,map_location='cpu',weights_only=True);meta=ck['metadata']
    if meta!=payload_metadata(meta['seed']):raise ValueError('Checkpoint contract mismatch')
    model=SiameseUNet(channels=5,width=16);model.load_state_dict(ck['state_dict'],strict=True)
    return model.to(device).eval(),meta


def evaluate(model,data,device,pos_weight):
    probs=[];labels=[];valid=[];ids=[];groups=[];losses=[];images={}
    model.eval()
    with torch.no_grad():
        for record in data:
            d=record['adapted'];row=record['row'];mask=d['mask'].to(device)
            logits=model(d['before'].to(device),d['after'].to(device));p=logits.sigmoid().cpu().numpy()[0,0]
            if not np.isfinite(p).all():raise ValueError('Nonfinite predictions')
            if mask.any():losses.append(float(masked_bce_dice(logits,d['target'].to(device),mask,pos_weight)))
            images[row['patch_id']]=p
            probs.extend(p.ravel().tolist());labels.extend(record['raw']['pseudo_states'].ravel().tolist());valid.extend(d['mask'].numpy().ravel().tolist())
            ids.extend(row['group_id']+f":r{row['row_offset']+r}:c{row['col_offset']+c}" for r in range(32) for c in range(32))
            groups.extend([row['group_id']]*1024)
    return dict(probabilities=probs,labels=labels,valid=valid,pixel_ids=ids,group_ids=groups,loss=float(np.mean(losses)) if losses else None,images=images)


def metrics(frame):
    y=np.array(frame['labels']);p=np.array(frame['probabilities']);mask=np.array(frame['valid'],bool);groups=np.array(frame['group_ids'])
    return dict(pooled=metric_counts(y,p,mask,.5),per_group={g:metric_counts(y[groups==g],p[groups==g],mask[groups==g],.5) for g in sorted(set(groups))})


def fit(seed,train,val,out,device,pos_weight,remaining):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if device=='cuda':torch.cuda.manual_seed_all(seed);torch.cuda.reset_peak_memory_stats()
    torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    model=SiameseUNet(channels=5,width=16).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001)
    rng=np.random.default_rng(seed);history=[];best=None;stale=0;start=time.monotonic();stop='MAX_EPOCHS'
    usable=[r for r in train if r['adapted']['mask'].any()]
    for epoch in range(1,6):
        order=rng.permutation(len(usable));model.train();losses=[];interrupted=False
        for offset in range(0,len(order),4):
            if time.monotonic()-start>=min(300,remaining):interrupted=True;stop='TIME_CAP';break
            batch=order[offset:offset+4];optimizer.zero_grad(set_to_none=True)
            for index in batch:
                d=usable[index]['adapted'];logits=model(d['before'].to(device),d['after'].to(device))
                loss=masked_bce_dice(logits,d['target'].to(device),d['mask'].to(device),pos_weight)
                if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                (loss/len(batch)).backward();losses.append(float(loss.detach()))
            torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step()
        if interrupted:break
        ev=evaluate(model,val,device,pos_weight);value=ev['loss']
        if value is None:raise ValueError('No validation supervision')
        history.append(dict(epoch=epoch,train_loss=float(np.mean(losses)),validation_loss=value,elapsed_seconds=time.monotonic()-start))
        state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        path=out/f'epoch_{epoch}.pt';torch.save(dict(state_dict=state,metadata=payload_metadata(seed),epoch=epoch,optimizer_state=optimizer.state_dict()),path)
        if best is None or value<best[0]:best=(value,epoch,path);stale=0
        else:stale+=1
        print(json.dumps(dict(seed=seed,**history[-1])),flush=True)
        if stale>=2:stop='EARLY_STOP_PATIENCE_2';break
    elapsed=time.monotonic()-start
    if best is None:raise RuntimeError('No completed epoch within cap; retained progress directory')
    best_path=out/'best.pt';best_path.write_bytes(best[2].read_bytes())
    best_path.with_suffix('.json').write_text(json.dumps(dict(sha256=sha(best_path),metadata=payload_metadata(seed),best_epoch=best[1]),indent=2))
    selected,meta=load_model(best_path,device);final=evaluate(selected,val,device,pos_weight)
    result=dict(seed=seed,completed_epochs=len(history),best_epoch=best[1],training_wall_seconds=elapsed,stop=stop,history=history,validation=metrics(final),checkpoint_sha256=sha(best_path),cuda_peak_allocated=torch.cuda.max_memory_allocated() if device=='cuda' else None,cuda_peak_reserved=torch.cuda.max_memory_reserved() if device=='cuda' else None,claim=CLAIM)
    (out/'metrics.json').write_text(json.dumps(result,indent=2,allow_nan=False));return result,final
