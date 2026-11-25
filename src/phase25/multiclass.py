"""Versioned weak evidence; not verified class attribution."""
import numpy as np

def evidence(v,t):
    shape=v['before_NDVI'].shape
    def finite(*names):return np.isfinite(np.stack([v[n] for n in names])).all(0)
    common=finite(*[s+'_'+b for s in ['before','after'] for b in ['NDVI','BSI','NDWI','VV','VH']])
    for s in ['before','after']:common &= (v[s+'_optical_count']>=2)&(v[s+'_sar_count']>=2)&(v[s+'_NDWI']<0)
    dn=v['after_NDVI']-v['before_NDVI'];db=v['after_BSI']-v['before_BSI'];dv=v['after_VV']-v['before_VV'];dh=v['after_VH']-v['before_VH']
    follow=finite('follow_NDVI','follow_BSI','follow_NDWI','follow_count')&(v['follow_count']>=2)&(v['follow_NDWI']<0)
    loss=dn<=t['ndvi_drop'];bare=db>t['bsi_increase'];sar=(dv<=0)&(dh<=0)
    persistent=follow&(v['follow_NDVI']-v['before_NDVI']<=t['ndvi_drop'])&(v['follow_BSI']-v['before_BSI']>t['bsi_increase'])
    recovery=follow&(np.abs(v['follow_NDVI']-v['before_NDVI'])<=t['stable_ndvi'])&(np.abs(v['follow_BSI']-v['before_BSI'])<=t['stable_bsi'])
    dw=finite('before_crops','after_crops','before_built','after_built','before_dw_count','after_dw_count')&(v['before_dw_count']>=2)&(v['after_dw_count']>=2)
    crop=dw&(v['before_crops']>=t['context_probability'])&(v['after_crops']>=t['context_probability'])
    built=dw&(v['before_built']<=t['built_before_max'])&(v['after_built']>=t['context_probability']);specific=crop|built
    def score(parts,mask):return np.where(mask,np.mean(np.stack(parts).astype('float32'),0),np.nan)
    stable=[np.abs(dn)<=t['stable_ndvi'],np.abs(db)<=t['stable_bsi'],np.abs(dv)<=t['stable_sar_db'],np.abs(dh)<=t['stable_sar_db'],recovery]
    scores=np.stack([score(stable,common&follow),score([loss,bare,sar,persistent],common&follow&~specific),score([loss,bare,crop,recovery],common&follow&dw),score([loss,bare,built,persistent],common&follow&dw),score([loss,bare,~persistent,(np.abs(dv)>1)|(np.abs(dh)>1)],common&follow&~specific)])
    rank=np.where(np.isfinite(scores),scores,-np.inf);top=rank.max(0);second=np.sort(rank,axis=0)[-2]
    margin=np.full(shape,np.nan,dtype='float32');np.subtract(top,second,out=margin,where=np.isfinite(top)&np.isfinite(second))
    use=common&np.isfinite(top)&np.isfinite(margin)&(top>=t['minimum_winning_score'])&(margin>=t['minimum_margin'])
    fire=np.isfinite(v['burn_after'])&(v['burn_after']>0);use &= ~fire
    labels=np.full(shape,255,dtype='uint8');labels[use]=rank.argmax(0)[use]
    confidence=np.where(use,margin,np.nan).astype('float32');uncertainty=np.ones(shape,dtype='float32');uncertainty[use]=1-confidence[use]
    return dict(labels=labels,scores=scores,confidence=confidence,uncertainty=uncertainty,persistence=np.where(follow,persistent,np.nan).astype('float32'),common_valid=common)
