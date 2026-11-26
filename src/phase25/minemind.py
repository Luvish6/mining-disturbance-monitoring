"""MineMind: frozen masked-sensor encoder routing, not a new fitted model."""
import numpy as np
import torch

MODES={'both':(True,True),'sar':(True,False),'optical':(False,True)}


def availability(x,counts=None):
 x=np.asarray(x);v=np.isfinite(x)&(x!=-9999)
 result=np.stack([v[:,0:2].all(1),v[:,2:4].all(1)],1)
 if counts is not None:
  counts=np.asarray(counts)
  if counts.shape!=result.shape:raise ValueError('Two sensor observation counts required')
  known=np.isfinite(counts)&(counts!=-9999)
  if np.any(known&((counts<0)|(counts!=np.floor(counts)))):raise ValueError('Invalid observation count')
  result &= known&(counts>=2)
 return result


def embed(model,x,observed,center,spread):
 x=np.asarray(x);observed=np.asarray(observed,bool)&availability(x)
 if x.ndim!=2 or x.shape[1]!=4 or observed.shape!=(len(x),2):raise ValueError('Named VV,VH,NDVI,NDTI contract required')
 if np.shape(center)!=(4,) or np.shape(spread)!=(4,) or not np.isfinite(center).all() or not np.isfinite(spread).all() or np.any(np.asarray(spread)<=0):raise ValueError('Frozen TRAIN normalization required')
 result=np.full((len(x),8),np.nan,'float32')
 for pattern in [(True,True),(True,False),(False,True)]:
  ids=np.flatnonzero((observed==pattern).all(1))
  if not len(ids):continue
  z=(x[ids]-center)/spread;z=np.where(np.repeat(np.array(pattern),2)[None],z,0).astype('float32');z=torch.from_numpy(z)
  with torch.inference_mode():
   # view0was trained to hideSAR; view1to hideoptical. Missing values never reach an observed input.
   value=model.embed(z) if all(pattern) else model.view(z,1 if pattern[0] else 0)
  result[ids]=value.cpu().numpy()
 return result


def change(model,before,after,center,spread,mode,before_counts=None,after_counts=None):
 if mode not in MODES:raise ValueError('Unknown modality mode')
 common=availability(before,before_counts)&availability(after,after_counts)&np.array(MODES[mode])
 a=embed(model,before,common,center,spread);b=embed(model,after,common,center,spread)
 return np.linalg.norm(b-a,axis=1),common.any(1)


def physical(before,after,spread,mode):
 if mode not in MODES:raise ValueError('Unknown modality mode')
 z=np.abs(np.asarray(after)-before)/spread;s=z[:,:2].max(1);o=z[:,2:].max(1)
 return np.minimum(s,o) if mode=='both' else s if mode=='sar' else o


def cutoff(values,quota):
 values=np.asarray(values)
 if not np.isfinite(values).all() or not len(values) or not 0<=quota<=len(values):raise ValueError('Finite calibration-only scores/quota required')
 return float(np.sort(values)[-quota]) if quota else float(np.nextafter(float(values.max()),np.inf))


def tile_change(model,tile,center,spread,mode='both'):
    """Canonical14band input plus real counts; optional missing context is never imputed as evidence."""
    v=np.asarray(tile['values']);counts=np.asarray(tile['counts'])
    if v.ndim!=3 or v.shape[0]!=14 or counts.shape!=(4,*v.shape[1:]):raise ValueError('Canonical14bands/fourQAcounts required')
    a=v[:4].reshape(4,-1).T;b=v[4:8].reshape(4,-1).T
    before=counts[[0,2]].reshape(2,-1).T;after=counts[[1,3]].reshape(2,-1).T
    score,valid=change(model,a,b,center,spread,mode,before,after)
    return dict(score=score.reshape(v.shape[1:]),valid=valid.reshape(v.shape[1:]),sensor_observed=(availability(a,before)&availability(b,after)&np.array(MODES[mode])).T.reshape(2,*v.shape[1:]),context=v[12:].copy(),context_valid=np.isfinite(v[12:])&(v[12:]!=-9999),status='EXPLORATORY',operational_alerts=0)
