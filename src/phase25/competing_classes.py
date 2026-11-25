"""Supplement-only competing-class rules; never change the V2 parent labels."""
import numpy as np
from src.phase25.multiclass import evidence


def reducer_limit(shape,bands):
    if len(shape)!=2 or min(shape)<=0 or bands<=0:raise ValueError('Invalid reducer grid')
    return int(np.prod(shape)*bands*2)


def competing_evidence(v,thresholds):
    r=evidence(v,thresholds);base=r['labels'].copy()
    # Only the new versioned class-specific rules may populate IDs2/3 in the supplement.
    base[np.isin(base,[2,3])]=255
    finite=lambda names:np.isfinite(np.stack([v[n] for n in names])).all(0)
    common=r['common_valid'];dw=finite([s+'_'+n for s in ['before','after'] for n in ['crops','built','dw_count']])
    dw &= (v['before_dw_count']>=2)&(v['after_dw_count']>=2)
    crop=dw&(((v['before_crops']>=.6)|(v['after_crops']>=.6))|(np.isfinite(v['land_cover'])&(v['land_cover']==40)))&(v['before_built']<.2)&(v['after_built']<.2)
    # Agricultural temporal variability is allowed in either direction; no mining-style SAR/NDVI-drop gate.
    cycles=[]
    for s in ['before','after']:
        names=[s+'_'+p+'_'+n for p in ['early','late'] for n in ['NDVI','BSI','count']]
        valid=finite(names)&(v[s+'_early_count']>=2)&(v[s+'_late_count']>=2)
        nd=v[s+'_late_NDVI']-v[s+'_early_NDVI'];bs=v[s+'_late_BSI']-v[s+'_early_BSI']
        cycles.append(valid&(np.abs(nd)>=.20)&(np.abs(bs)>=.05)&(nd*bs<0))
    agriculture=common&crop&(cycles[0]|cycles[1])
    follow=finite(['follow_built','follow_dw_count'])&(v['follow_dw_count']>=2)
    built=dw&(v['before_built']<=.2)&(v['after_built']>=.6)&follow&(v['follow_built']>=.6)
    corroborated=((v['after_NDVI']-v['before_NDVI'])<=-.10)|((v['after_BSI']-v['before_BSI'])>.05)
    construction=common&built&corroborated&~crop
    # A context probability does not itself establish a true class. Conflicting explanations abstain.
    conflict=agriculture&construction
    labels=base.copy();labels[agriculture&~construction]=2;labels[construction&~agriculture]=3;labels[conflict]=255
    labels[np.isfinite(v['burn_after'])&(v['burn_after']>0)]=255
    return dict(labels=labels,agriculture=agriculture,construction=construction,conflict=conflict,base_labels=base,confidence_kind='unvalidated rule support, not calibrated probability')


def thematic_gate(metadata):
    """Numeric legend required; WMS visualization and product scale are not class IDs/resolution."""
    required=['source_url','reference_dates','crs','pixel_size_m','numeric_legend','legend_sha256','research_permission_evidence']
    if any(not metadata.get(k) for k in required) or metadata.get('representation')!='numeric_class_ids':raise ValueError('Unverified thematic data/legend/rights')
    if metadata.get('rendered_rgb',False):raise ValueError('Rendered map colors cannot become class IDs')
    from rasterio.crs import CRS
    CRS.from_user_input(metadata['crs'])
    if metadata['pixel_size_m']<=0:raise ValueError('Map scale is not pixel resolution')
    return dict(role='context_only',independent_reference=False,redistribution=metadata.get('redistribution_permission_evidence','UNKNOWN_NO_PUBLIC_RELEASE'))
