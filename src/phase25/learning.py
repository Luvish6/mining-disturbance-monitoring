"""Phase25D.1 shared-input/mask contracts. No pretrained loader or training runner."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from src.phase25.dataset import BANDS
from src.phase3.model import masked_loss

RAW_BANDS=('B2','B3','B4','VV','VH')
# Pinned TerraTorch v1 facts, cached in Phase25A; S2 SR*10000, S1 GRD dB.
MEAN=np.array([1503.317,1718.197,1853.910,-12.599,-20.293],dtype='float32')
STD=np.array([2141.107,2038.973,2134.138,5.195,5.890],dtype='float32')
SCALE=np.array([10000.,10000.,10000.,1.,1.],dtype='float32')
CONTRACT=dict(version='25d1-shared-raw/1',bands=list(RAW_BANDS),mean=MEAN.tolist(),std=STD.tolist(),scale=SCALE.tolist(),
    grid='32x32 at30m; no spatial resampling or invented spectral channels',token_size=16,
    mask='all five raw channels valid in both dates; exclude incomplete16x16 tokens for BOTH systems; labels0/1 only',
    target='retrospective pseudo-label agreement; not independently verified mining',normalization='fixed publisher constants once; no TRAIN/VAL fitting',
    models=['existing SiameseUNet(channels=5,width=16)','frozen TerraMind1.0-tiny with S2L2A BLUE/GREEN/RED and S1GRD VV/VH'],
    temporal='paired shared encoder; absolute feature difference, temporally symmetric',
    checkpoint='NOT_LOADED',operational_alerts=0)
CONTRACT_SHA=hashlib.sha256(json.dumps(CONTRACT,sort_keys=True).encode()).hexdigest()


def token_support(valid,token=16):
    valid=np.asarray(valid,bool)
    if valid.ndim!=2 or valid.shape[0]%token or valid.shape[1]%token:raise ValueError('Whole native embedding tokens required; no resize')
    h,w=valid.shape
    full=valid.reshape(h//token,token,w//token,token).all((1,3))
    return full.repeat(token,0).repeat(token,1)


def adapt_patch(record,*,bands=RAW_BANDS):
    if tuple(bands)!=RAW_BANDS:raise ValueError('Unavailable/unapproved raw channels; no NIR/SWIR synthesis')
    x=np.asarray(record['features']);valid=np.asarray(record['validity'],bool);y=record.get('pseudo_states')
    if x.shape!=(len(BANDS),32,32) or valid.shape!=x.shape or y is None or np.asarray(y).shape!=(32,32):raise ValueError('Explicit pseudo opt-in and fixed grid required')
    y=np.asarray(y)
    if not np.isin(y,[0,1,255]).all():raise ValueError('Pseudo states must be0/1/255')
    if not np.array_equal(valid,np.isfinite(x)):raise ValueError('Per-band finite validity mismatch')
    inputs=[];masks=[]
    for s in ['before','after']:
        indices=[BANDS.index(s+'_'+b) for b in RAW_BANDS];a=x[indices].astype('float32');m=valid[indices]
        # Zero is a normalized computational fill, never an observed value or label.
        z=np.where(m,(a*SCALE[:,None,None]-MEAN[:,None,None])/STD[:,None,None],0.)
        inputs.append(torch.from_numpy(z[None].copy()));masks.append(m)
    pixel=masks[0].all(0)&masks[1].all(0);support=token_support(pixel)
    use=support&np.isin(y,[0,1])
    before,after=inputs
    return dict(before=before,after=after,
        terramind_before={'S2L2A':before[:,:3], 'S1GRD':before[:,3:]},
        terramind_after={'S2L2A':after[:,:3], 'S1GRD':after[:,3:]},
        target=torch.from_numpy(y.astype('float32')[None,None].copy()),mask=torch.from_numpy(use[None,None].copy()),
        pixel_common_valid=pixel,token_common_valid=support,uncertain=(y==255),
        contract_sha256=CONTRACT_SHA,normalization_applied=True,verified_labels=False)


def masked_bce_dice(logits,target,mask,pos_weight=1.):
    """Same masked objective for both trainable systems; no optimizer is included."""
    if mask.dtype!=torch.bool:raise ValueError('Explicit boolean valid mask required')
    if not 0<pos_weight<=10:raise ValueError('Prespecified TRAIN-only positive-weight cap10')
    bce=masked_loss(logits,target,mask,pos_weight=pos_weight)
    t=target[mask.bool()];p=logits[mask.bool()].sigmoid()
    # Foreground Dice is undefined without positives; BCE still penalizes false positives.
    if t.sum()==0:return bce
    dice=1-(2*(p*t).sum()+1e-6)/(p.sum()+t.sum()+1e-6)
    return .5*bce+.5*dice


class FrozenEncoder(nn.Module):
    """Generic injected-encoder guard, not a TerraMind implementation/checkpoint loader."""
    def __init__(self,encoder):
        super().__init__();self.encoder=encoder.requires_grad_(False).eval()
    def train(self,mode=True):
        super().train(mode);self.encoder.eval();return self
    def forward(self,x):
        self.encoder.eval()
        with torch.no_grad():return self.encoder(x)


def load_evaluation_frame(path,expected_sha256):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('Frozen evaluation-frame hash mismatch')
    frame=json.loads(raw)
    if frame['contract_sha256']!=CONTRACT_SHA or frame['split']!='validation':raise ValueError('Wrong evaluation-frame contract')
    if frame['dataset_sha256']!='3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa':raise ValueError('Wrong evaluation dataset')
    if not all(type(v) is bool for v in frame['valid']):raise ValueError('Explicit boolean frame masks required')
    return frame


def compare_contract(a,b,expected):
    """Expected frame must be the separately hash-frozen dataset-derived VAL receipt."""
    from src.phase3.spatial import partition
    for r in [a,b,expected]:
        if r['contract_sha256']!=CONTRACT_SHA or r['split']!='validation':raise ValueError('Development VAL only; no TEST support')
        if r['dataset_sha256']!='3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa':raise ValueError('Frozen dataset mismatch')
    for key in ['pixel_ids','group_ids','labels','valid']:
        if not np.array_equal(a[key],b[key]) or not np.array_equal(a[key],expected[key]):raise ValueError('Evaluation IDs/order/labels/masks differ')
    ids=np.asarray(expected['pixel_ids']);n=len(ids)
    if len(set(ids.tolist()))!=n:raise ValueError('Duplicate evaluation pixels')
    if any(np.asarray(expected[k]).shape!=(n,) for k in ['group_ids','labels','valid']):raise ValueError('Evaluation vector shape mismatch')
    if any(partition(str(g),42)!='validation' for g in set(expected['group_ids'])):raise ValueError('Frozen group split mismatch')
    if np.asarray(expected['valid']).dtype!=bool:raise ValueError('Boolean common mask required')
    for r in [a,b]:
        if np.asarray(r['probabilities']).shape!=(n,):raise ValueError('Prediction length mismatch')
        metric_counts(r['labels'],r['probabilities'],r['valid'])


def metric_counts(labels,probabilities,valid,threshold=.5):
    y=np.asarray(labels);p=np.asarray(probabilities);m=np.asarray(valid,bool)
    if y.shape!=p.shape or p.shape!=m.shape or not 0<threshold<1:raise ValueError('Metric shape/threshold mismatch')
    y,p=y[m],p[m]
    if not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Only binary valid pseudo targets and finite probabilities')
    q=p>=threshold;tn=int(((y==0)&~q).sum());fp=int(((y==0)&q).sum());fn=int(((y==1)&~q).sum());tp=int(((y==1)&q).sum())
    positive=tp+fn;negative=tn+fp
    ratio=lambda a,b:a/b if b else None
    return dict(confusion_matrix=[[tn,fp],[fn,tp]],positive_support=positive,negative_support=negative,
        precision=ratio(tp,tp+fp),recall=ratio(tp,positive),dice_f1=ratio(2*tp,2*tp+fp+fn) if positive else None,
        iou=ratio(tp,tp+fp+fn) if positive else None,fpr=ratio(fp,negative),predicted_positive_pixels=tp+fp,
        prevalence=ratio(positive,len(y)),excluded_pixels=int((~m).sum()),
        claim='PSEUDO_LABEL_AGREEMENT_NOT_VERIFIED_MINING_ACCURACY')
