"""Interpretable weak evidence, never a calibrated mining probability."""
import numpy as np
NAMES=['vegetation','soil','sar','persistence','terrain','geology','environment']
PHYSICAL=np.array([.25,.25,.20,.15,.025,.05,.075])


def fit_scales(rows):
 if any(r['split']!='train' for r,v in rows):raise ValueError('TRAIN only')
 def q(field,floor):
  a=np.concatenate([np.abs(v[field]).ravel() for _,v in rows]);a=a[np.isfinite(a)]
  return max(float(np.quantile(a,.9)),floor) if len(a) else floor
 return dict(ndvi=max(q('dNDVI',.3),.3),soil=max(q('dBSI',.1),.1),sar=q('dVV',1.),rain=q('rainfall',100.))


def components(v,scales,geology=None,retrospective=False):
 shape=next(iter(v.values())).shape
 get=lambda k:np.asarray(v.get(k,np.full(shape,np.nan)),float)
 dn=get('after_NDVI')-get('before_NDVI');db=get('after_BSI')-get('before_BSI')
 veg=np.clip((-dn-.05)/max(scales['ndvi']-.05,.01),0,1);soil=np.clip((db-.02)/max(scales['soil']-.02,.01),0,1)
 sar=np.clip(np.maximum(np.abs(get('after_VV')-get('before_VV')),np.abs(get('after_VH')-get('before_VH')))/scales['sar'],0,1)
 persistence=np.full(shape,np.nan)
 if retrospective:
  valid=(get('follow_count')>=2)&np.isfinite(get('follow_NDVI'))&np.isfinite(get('follow_BSI'))
  persistence=np.where(valid,np.minimum(np.clip((get('before_NDVI')-get('follow_NDVI'))/scales['ndvi'],0,1),np.clip((get('follow_BSI')-get('before_BSI'))/scales['soil'],0,1)),np.nan)
 # Terrain contributes neutral support only: high slopes are not ruled out as mining.
 terrain=np.where(np.isfinite(get('slope')),.5,np.nan)
 geo=np.full(shape,np.nan) if geology is None else geology
 env=[]
 for field in ['surface_water','burn_after','rainfall']:
  x=get(field)
  env.append(1-np.clip(x/100,0,1) if field=='surface_water' else np.where(np.isfinite(x),1-np.clip(x,0,1),np.nan) if field=='burn_after' else np.where(np.isfinite(x),.5,np.nan))
 a=np.stack(env);n=np.isfinite(a).sum(0);environment=np.divide(np.nansum(a,0),n,out=np.full(shape,np.nan),where=n>0)
 core=np.isfinite(np.stack([get(s+'_'+b) for s in ['before','after'] for b in ['NDVI','BSI','VV','VH']])).all(0)
 for s in ['before','after']:core &= (get(s+'_optical_count')>=2)&(get(s+'_sar_count')>=2)&(get(s+'_NDWI')<0)
 crop=np.fmax(get('before_crops'),get('after_crops'));crop=np.where(np.isfinite(crop),crop,np.where(get('land_cover')==40,.6,np.nan))
 agriculture=crop*np.clip(np.abs(dn)/scales['ndvi'],0,1)
 built=np.clip((get('after_built')-get('before_built'))/.4,0,1);built=np.where((get('before_dw_count')>=2)&(get('after_dw_count')>=2),built,np.nan)
 construction=built*(veg+soil)/2
 other=np.fmax(.5*np.clip(get('slope')/30,0,1)*veg*soil,np.where(np.isfinite(get('burn_after')),get('burn_after')*veg,np.nan))
 return dict(values=np.stack([veg,soil,sar,persistence,terrain,geo,environment]),valid=core,competitors=np.stack([agriculture,construction,other]))


def adaptive_weights(parts):
 a=np.concatenate([p['values'].reshape(7,-1) for p in parts],1);coverage=np.isfinite(a).mean(1);redundancy=np.zeros(7)
 for i in range(7):
  correlations=[]
  for j in range(7):
   valid=np.isfinite(a[i])&np.isfinite(a[j])
   if i!=j and valid.sum()>=25 and a[i,valid].std()>1e-8 and a[j,valid].std()>1e-8:correlations.append(abs(float(np.corrcoef(a[i,valid],a[j,valid])[0,1])))
  redundancy[i]=np.mean(correlations) if correlations else 0
 w=PHYSICAL*coverage/(1+redundancy)
 return (w/w.sum()).tolist() if w.sum() else [0.]*7


def combine(parts,weights,threshold=60):
 w=np.asarray(weights,float)
 if w.shape!=(7,) or not np.isfinite(w).all() or (w<0).any() or w.sum()<=0 or not 0<=threshold<=100:raise ValueError('Invalid evidence controls')
 w=w/w.sum();a=parts['values'];available=np.isfinite(a);coverage=(available*w[:,None,None]).sum(0)
 contributions=np.divide(np.nan_to_num(a)*w[:,None,None]*100,coverage[None],out=np.zeros_like(a),where=coverage[None]>0)
 score=contributions.sum(0);score[~parts['valid']|(coverage<.6)]=np.nan
 alternative=np.max(np.where(np.isfinite(parts['competitors']),parts['competitors']*100,0),0)
 # Require spectral change support, adequate coverage and a competing-evidence margin.
 candidate=np.isfinite(score)&(score>=threshold)&(a[0]>=.25)&(a[1]>=.25)&((score-alternative)>=10)
 uncertainty=1-coverage+.25*np.nan_to_num(np.std(np.where(available,a,0),0));uncertainty=np.clip(uncertainty,0,1)
 return dict(score=score,coverage=coverage,contributions=contributions,uncertainty=uncertainty,candidate=candidate,alternative=alternative)
