"""25E.1 interpretable evidence diagnostics; not a mining classifier or new labels."""
import numpy as np
from src.phase25.dataset import BANDS,COUNTS
from src.phase3.spatial import partition


def build_graph_bundle(ee,key,row,area,protected):
    # Caller supplies initialized EE; this function never initializes, evaluates or exports.
    from scripts.phase25b_cached import guarded
    from scripts.phase25b1_recover import graphs
    from scripts.phase22l_temporal import seasonal_graph
    from config.phase2_settings import Phase2Config
    from config.settings import BEFORE,AFTER
    from src import sar_preprocessing as sar
    if row['split']!='train' or partition(key)!='train':raise ValueError('New graph pilot TRAIN only; TEST/VAL sealed')
    guarded(key,row,area,protected)
    cfg=Phase2Config(relative_orbit=77)
    region=ee.Geometry.Rectangle(row['bounds'],'EPSG:32646',False)
    context,metadata=graphs(ee,key,row)
    out={'context':context,'slope':ee.Terrain.slope(context.select('elevation'))}
    for name,season in [('before',BEFORE),('after',AFTER)]:
        optical,count,_,_=seasonal_graph(region,season,cfg)
        radar,radar_count=sar.seasonal(sar.collection(region,season,cfg),77,region,cfg)
        out[name]=dict(optical=optical,optical_count=count,sar=radar,sar_count=radar_count)
    return out,metadata


def score_cached(record,rules):
    x=record['features'];counts=record['counts']
    if x.shape!=(len(BANDS),32,32) or counts.shape!=(len(COUNTS),32,32):raise ValueError('Frozen feature/count schema required')
    if not np.array_equal(record['validity'],np.isfinite(x)):raise ValueError('Explicit finite-data masks required')
    def band(n):return x[BANDS.index(n)]
    n=rules['min_observations']
    # Preserve the original finite land/count screen, including raw optical completeness.
    optical=np.ones((32,32),bool)
    for season in ['before','after']:
        for name in ['B4','B3','B2','NDVI','BSI','NDWI']:optical &= np.isfinite(band(season+'_'+name))
        optical &= band(season+'_NDWI')<0
        c=counts[COUNTS.index(season+'_optical_count')];optical &= np.isfinite(c)&(c>=n)
    optical &= np.isfinite(band('slope'))
    sar=np.ones((32,32),bool)
    for season in ['before','after']:
        sar &= np.isfinite(band(season+'_VV'))&np.isfinite(band(season+'_VH'))
        c=counts[COUNTS.index(season+'_sar_count')];sar &= np.isfinite(c)&(c>=n)
    common=optical&sar
    flags=np.stack([band('dNDVI')<=rules['ndvi_drop'],band('dBSI')>rules['bsi_increase'],(band('dVV')<=rules['sar_drop_max'])&(band('dVH')<=rules['sar_drop_max'])])
    common &= np.isfinite(np.stack([band(k) for k in ['dNDVI','dBSI','dVV','dVH']])).all(0)
    score=np.where(common,flags.sum(0),np.nan).astype('float32')
    components=np.where(common[None],flags.astype('float32'),np.nan)
    contexts={}
    for name in ['slope','elevation','land_cover','rainfall','surface_water','fire_history','roads','geology','mining_context']:
        v=band(name);ok=np.isfinite(v)
        contexts[name]=dict(valid_cells=int(ok.sum()),status='AVAILABLE_CONTEXT_ONLY' if ok.any() else 'MISSING',minimum=float(v[ok].min()) if ok.any() else None,maximum=float(v[ok].max()) if ok.any() else None)
    # Alternative explanations are context flags only: no cause labels, weights or exclusions.
    alternatives=dict(agriculture_context_cells=int((common&(band('land_cover')==40)).sum()),built_up_context_cells=int((common&(band('land_cover')==50)).sum()),steep_terrain_context_cells=int((common&(band('slope')>=rules['steep_context_degrees'])).sum()),roads_status=contexts['roads']['status'],interpretation='Historical land-cover/terrain flags suggest review questions only; agriculture, forestry, road works, construction, landslides, erosion and artifacts remain alternatives.')
    return dict(score=score,components=components,valid=common,contexts=contexts,alternatives=alternatives,component_names=['NDVI_DROP_SUPPORT','BSI_INCREASE_SUPPORT','BOTH_SAR_CHANNELS_NONINCREASE_SUPPORT'],score_semantics='0..3 count of frozen optical/SAR conditions, not probability, risk, mining attribution or a new pseudo-label; persistence remains separate')
