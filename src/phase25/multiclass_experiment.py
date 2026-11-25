"""Retrospective three-class weak-label learning; offline TRAIN/VAL only."""
import json
from pathlib import Path
import numpy as np
from src.phase25.dataset import sha, within
from src.phase25.multiclass_data import load_dataset

ROOT=Path('outputs/phase25/datasets/minechange-india-multiclass-v2')
OUT=Path('outputs/phase25/experiments/25e4-multiclass-v1')
INTEGRITY='bd44f12ab2371f5930e287315c4e3ee86d5599f9a0da82b3bcff508445d98a78'
CLAIM='Retrospective agreement with algorithm-generated weak labels; NOT independently verified mining accuracy'
CLASSES={0:'stable',1:'persistent unattributed exposure',4:'other transient'}
CORE=[s+'_'+b for s in ['before','after'] for b in ['B2','B3','B4','VV','VH']]


def save(path,data):
    Path(path).write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def remap(y):
    y=np.asarray(y)
    if not np.isin(y,[0,1,2,3,4,255]).all():raise ValueError('Unknown taxonomy')
    out=np.full(y.shape,255,np.uint8)
    for internal,original in enumerate(CLASSES):out[y==original]=internal
    return out


def load():
    if sha(ROOT/'integrity.json')!=INTEGRITY:raise ValueError('Frozen V2 inventory changed')
    m=load_dataset(ROOT);bands=m['model_input_bands'];data=[]
    for row in m['patches']:
        with np.load(within(ROOT,row['output_folder']+'/model_ready.npz'),allow_pickle=False) as z:
            x=z['features'].copy();y=remap(z['weak_labels'])
            if x.shape!=(len(bands),32,32) or not np.array_equal(np.isfinite(x),z['validity']) or not np.array_equal(z['label_valid'],z['weak_labels']!=255):raise ValueError('Array alignment/validity')
        import rasterio
        from affine import Affine
        with rasterio.open(within(ROOT,row['output_folder']+'/observations.tif')) as ds:
            if ds.crs.to_string()!=row['crs'] or ds.shape!=(32,32) or ds.transform!=Affine(*row['affine']) or list(ds.descriptions)!=m['bands']:raise ValueError('Raster feature/grid alignment')
            source=ds.read([m['bands'].index(b)+1 for b in bands]);source=np.where(source==ds.nodata,np.nan,source)
            if not np.array_equal(source,x,equal_nan=True):raise ValueError('Array/source feature mismatch')
        with rasterio.open(within(ROOT,row['output_folder']+'/weak_classes.tif')) as ds:
            if ds.transform!=Affine(*row['affine']) or ds.crs.to_string()!=row['crs'] or not np.array_equal(remap(ds.read(1)),y):raise ValueError('Array/source label alignment')
        mask=(y!=255)&np.isfinite(x[[bands.index(b) for b in CORE]]).all(0)
        data.append(dict(row=row,x=x,y=y,mask=mask,input_valid=np.isfinite(x[[bands.index(b) for b in CORE]]).all(0)))
    if len(data)!=80 or sum(d['row']['split']=='train' for d in data)!=68:raise ValueError('Frozen roster mismatch')
    return m,data


def feature_families(bands,train):
    if any(d['row']['split']!='train' for d in train):raise ValueError('TRAIN-only feature selection')
    optical=[b for b in bands if b in [s+'_'+v for s in ['before','after'] for v in ['B2','B3','B4','NDVI','BSI','NDWI']]+['dNDVI','dBSI']]
    sar=[b for b in bands if b in [s+'_'+v for s in ['before','after'] for v in ['VV','VH']]+['dVV','dVH']]
    context=[b for b in bands if b in ['slope','elevation','land_cover','rainfall','surface_water'] or any(b==s+'_'+v for s in ['before','after'] for v in ['crops','built','water','bare'])]
    available=[b for b in context if any(np.isfinite(d['x'][bands.index(b)][d['mask']]).any() for d in train)]
    return dict(optical=optical,sar=sar,fused=optical+sar+available)


def frame(data):
    y=np.concatenate([d['y'].ravel() for d in data]);valid=np.concatenate([d['mask'].ravel() for d in data]);groups=np.repeat([d['row']['group_id'] for d in data],1024)
    ids=np.array([d['row']['patch_id']+':'+str(i) for d in data for i in range(1024)])
    return dict(labels=y,valid=valid,groups=groups,pixel_ids=ids)


def sample_indices(data,cap=100000,seed=42):
    if any(d['row']['split']!='train' for d in data):raise ValueError('No validation in sampling')
    f=frame(data);rng=np.random.default_rng(seed);selected=[]
    # Equal group budgets; balanced within available classes, without replacement.
    groups=sorted(set(f['groups']));per=cap//len(groups)
    for group in groups:
        pools=[np.flatnonzero(f['valid']&(f['groups']==group)&(f['labels']==c)) for c in range(3)]
        active=[p for p in pools if len(p)];budget=min(per,sum(map(len,active)))
        take=[min(len(p),budget//len(active)) for p in active]
        while sum(take)<budget:
            eligible=[i for i,p in enumerate(active) if take[i]<len(p)]
            if not eligible:break
            for i in eligible:
                if sum(take)>=budget:break
                take[i]+=1
        selected.extend(np.concatenate([rng.permutation(p)[:n] for p,n in zip(active,take)]).tolist())
    result=np.array(sorted(selected),np.int64)
    if len(result)!=len(np.unique(result)):raise ValueError('Duplicate sampled pixel')
    return result


def metrics(y,p,valid):
    y=np.asarray(y)[valid];p=np.asarray(p)[valid]
    if not np.isin(y,[0,1,2]).all() or not np.isin(p,[0,1,2]).all():raise ValueError('Invalid class')
    cm=np.bincount(3*y.astype(int)+p.astype(int),minlength=9).reshape(3,3);classes={}
    div=lambda a,b:float(a/b) if b else None
    for c,original in enumerate(CLASSES):
        tp=int(cm[c,c]);fn=int(cm[c].sum()-tp);fp=int(cm[:,c].sum()-tp);tn=int(cm.sum()-tp-fn-fp)
        support=tp+fn
        classes[str(original)]=dict(precision=div(tp,tp+fp),recall=div(tp,support),f1=div(2*tp,2*tp+fp+fn) if support else None,iou=div(tp,tp+fp+fn) if support else None,fpr=div(fp,fp+tn),support=support,predicted=tp+fp)
    f1=[v['f1'] for v in classes.values() if v['f1'] is not None]
    return dict(confusion_matrix=cm.tolist(),class_order=[0,1,4],classes=classes,macro_f1=float(np.mean(f1)) if f1 else None,support=int(cm.sum()),predicted_counts=cm.sum(0).tolist())


def score(f,p,data):
    result=dict(pooled=metrics(f['labels'],p,f['valid']),per_group={g:metrics(f['labels'],p,f['valid']&(f['groups']==g)) for g in sorted(set(f['groups']))})
    result['patches']={d['row']['patch_id']:metrics(f['labels'][i*1024:(i+1)*1024],p[i*1024:(i+1)*1024],d['mask'].ravel()) for i,d in enumerate(data)}
    return result


def fit_preprocessing(x,indices):
    values=x[indices];median=np.array([np.median(v[np.isfinite(v)]) if np.isfinite(v).any() else np.nan for v in values.T])
    if not np.isfinite(median).all():raise ValueError('All-missing TRAIN feature')
    return median


def impute(x,median):return np.where(np.isfinite(x),x,median)


def matrix(data,bands,names):
    idx=[bands.index(b) for b in names]
    return np.concatenate([d['x'][idx].reshape(len(idx),-1).T for d in data])


def write_predictions(data,prob,dest,model_hash):
    import rasterio
    from affine import Affine
    dest.mkdir()
    for i,d in enumerate(data):
        block=prob[i*1024:(i+1)*1024].reshape(32,32,3);r=d['row'];valid=d['input_valid']&np.isfinite(block).all(2)
        original=np.array([0,1,4])[block.argmax(2)];a=np.concatenate([block.transpose(2,0,1),original[None]],0).astype('float32');a[:,~valid]=-9999
        with rasterio.open(dest/(r['patch_id']+'.tif'),'w',driver='GTiff',width=32,height=32,count=4,dtype='float32',crs=r['crs'],transform=Affine(*r['affine']),nodata=-9999) as ds:
            ds.write(a)
            for j,name in enumerate(['p_stable','p_persistent_unattributed','p_other_transient','original_taxonomy_class'],1):ds.set_band_description(j,name)
            ds.update_tags(model_validation_status='NOT_VALIDATED',label_semantics='WEAK_ALGORITHMIC_HYPOTHESES_NOT_REFERENCE',operational_alerts='0',checkpoint_sha256=model_hash,decision='argmax; no threshold tuning',analysis='retrospective')


def save_result(name,prob,data,checkpoint_hash,extra):
    dest=OUT/name;dest.mkdir(exist_ok=True);f=frame(data);pred=prob.argmax(1)
    s=score(f,pred,data);save(dest/'metrics.json',dict(validation=s,checkpoint_sha256=checkpoint_hash,**extra))
    np.savez_compressed(dest/'validation_predictions.npz',probabilities=prob,**f)
    write_predictions(data,prob,dest/'georeferenced_predictions',checkpoint_hash)
    return dict(id=name,validation=s,checkpoint_sha256=checkpoint_hash,**extra)


def masked_ce(logits,target,weight):
    import torch
    from torch.nn import functional as F
    if logits.shape[0]!=target.shape[0] or logits.shape[1]!=3 or logits.shape[2:]!=target.shape[1:]:raise ValueError('Multiclass alignment')
    valid=target!=255
    if not valid.any() or not torch.isfinite(logits).all() or not torch.isin(target[valid],target.new_tensor([0,1,2])).all():raise ValueError('Invalid masked targets/logits')
    labels=target[valid].long();logp=F.log_softmax(logits,dim=1).permute(0,2,3,1)[valid];w=weight[labels]
    return (-logp.gather(1,labels[:,None]).squeeze(1)*w).sum()/w.sum()


def load_unet(checkpoint,expected_sha,normalization,device='cpu'):
    """Explicit private checkpoint loader; no endpoint and no unrestricted pickle."""
    import torch
    from src.phase3.model import SiameseUNet
    if sha(checkpoint)!=expected_sha:raise ValueError('Checkpoint integrity')
    value=torch.load(checkpoint,map_location=device,weights_only=True);meta=value['metadata']
    if meta['schema']!='mci-multiclass-model/1' or meta['class_order']!=[0,1,4] or meta['bands']!=CORE or meta['dataset_inventory_sha256']!=INTEGRITY or meta['status']!='NOT_VALIDATED' or sha(normalization)!=meta['normalization_sha256']:raise ValueError('Multiclass model/normalization contract')
    model=SiameseUNet(channels=5,width=16);model.head=torch.nn.Conv2d(16,3,1);model.load_state_dict(value['state_dict'],strict=True);return model.to(device).eval(),meta
