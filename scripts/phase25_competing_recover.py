"""One new locked40request TRAIN-only supplement; existing ledgers/data immutable."""
import json,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import box
from scripts.phase25b_cached import backup_gate,digest,guarded
from scripts.phase25b1_recover import save_verified,cached_json
from scripts.phase25_multiclass_acquire import graph as context_graph,CONFIG as OLD_CONFIG,OUT as OLD
from src.phase25.acquisition import MeteredHttp
from src.phase25.competing_classes import reducer_limit

OUT=Path('outputs/phase25/datasets/competing-supplement-v1')
PARENT=Path('outputs/phase25/datasets/minechange-india-multiclass-v2')
INTEGRITY='bd44f12ab2371f5930e287315c4e3ee86d5599f9a0da82b3bcff508445d98a78'


def freeze():
    backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    if digest(PARENT/'integrity.json')!=INTEGRITY:raise ValueError('V2 integrity changed')
    old=cached_json(OLD/'supplement_plan.json');m=json.loads((PARENT/'manifest.json').read_bytes())
    from scripts.phase22n_temporal import guards
    area,protected=guards();occupied=[box(*r['bounds']) for r in m['patches']]
    windows=old['windows']
    for row in windows:
        if row['split']!='train':raise ValueError('TRAIN only')
        guarded(row['aoi'],row,area,protected);g=box(*row['bounds'])
        if any(g.distance(p)<120 for p in occupied):raise ValueError('Window overlap/buffer')
    plan=dict(schema='mci-competing-supplement/1',parent_inventory_sha256=INTEGRITY,old_ledger_sha256=digest(OLD/'http-ledger.jsonl'),old_config_sha256=digest(OLD_CONFIG),old_supplement_plan_sha256=digest(OLD/'supplement_plan.json'),windows=windows,budget=dict(max_requests=40,max_bytes=100000000,response_cap=2000000),selection='Existing hash-ordered TRAIN-only windows; select up to2crop-context maxima and1built-gain maximum, distinct frozen blocks; remaining slot by combined context count; no replacements or VAL-conditioned selection',maximum_new_patches=3,classes={'0':'potentially_stable','1':'persistent_unattributed_exposure','2':'agriculture_context_temporal_variability_NOT_verified_agriculture','3':'construction_context_transition_NOT_verified_construction','4':'other_transient_unattributed','255':'uncertain'},rules=dict(crop_probability=.6,built_before_max=.2,built_after_min=.6,within_season_ndvi_abs_min=.20,within_season_bsi_abs_min=.05,minimum_observations=2,construction_follow_built_min=.6,construction_corroboration='NDVI decline>=.10 OR BSI rise>.05',conflict='abstain; no class quotas'),annotation_only='follow-up and early/late diagnostic composites; no new model training',test_sealed=True)
    path=OUT/'frozen_plan.json'
    if path.exists():
        if cached_json(path)!=plan:raise ValueError('Frozen supplement plan changed')
    else:save_verified(path,plan)
    return plan


def choose(windows,screen):
    if any(r['split']!='train' for r in windows):raise ValueError('TRAIN-only selection')
    selected=[]
    for key,n in [('crop_context_cells',2),('built_gain_context_cells',1)]:
        candidates=sorted(windows,key=lambda r:(-float(screen[r['aoi']][key] or 0),r['aoi']))
        for row in candidates:
            if len([r for r in selected if r.get('selection_context')==key])>=n:break
            if float(screen[row['aoi']][key] or 0)>0 and not any(r['aoi']==row['aoi'] for r in selected):selected.append(dict(**row,selection_context=key))
    return selected[:3]


def run():
    cfg=freeze();meter=MeteredHttp(OUT/'gee-ledger.jsonl',**cfg['budget'])
    from scripts.phase22w_ablation import acquire_lock
    lock=acquire_lock(Path('outputs/phase25/receipts/.acquire.lock'))
    try:
        import ee
        from google.oauth2.credentials import Credentials
        from config.settings import project_id
        args=ee.oauth.get_credentials_arguments();ee.data.setMaxRetries(0);ee.Initialize(credentials=Credentials(None,**args),project=project_id(),http_transport=meter)
        oldcfg=cached_json(OLD_CONFIG) if OLD_CONFIG.with_suffix('.json.sha256').exists() else json.loads(OLD_CONFIG.read_bytes())
        path=OUT/'screen.json'
        if path.exists():screen=cached_json(path)
        else:
            stats={}
            for row in cfg['windows']:
                image,_=context_graph(ee,row,oldcfg);region=ee.Geometry.Rectangle(row['bounds'],'EPSG:32646',False)
                crop=image.select('before_crops').gte(.6).Or(image.select('after_crops').gte(.6)).rename('crop_context_cells')
                built=image.select('before_built').lte(.2).And(image.select('after_built').gte(.6)).rename('built_gain_context_cells')
                stats[row['aoi']]=ee.Image.cat([crop,built]).reduceRegion(ee.Reducer.sum(),region,crs='EPSG:32646',crsTransform=[30,0,row['bounds'][0],0,-30,row['bounds'][3]],maxPixels=reducer_limit((32,32),2))
            screen=ee.Dictionary(stats).getInfo();save_verified(path,screen)
        selected=choose(cfg['windows'],screen);save_verified(OUT/'selected.json',selected) if not (OUT/'selected.json').exists() else None
        print(json.dumps(dict(screen=screen,selected=selected,traffic=meter.summary())),flush=True)
        from scripts.phase25_competing_stack import acquire_and_build
        acquire_and_build(cfg,selected,meter,oldcfg)
    except BaseException as e:
        import re
        save_verified(OUT/'stop.json',dict(status='STOPPED',error=type(e).__name__,reason=re.sub(r'https?://\S+','[URL]',str(e))[:1000],traffic=meter.summary())) if not (OUT/'stop.json').exists() else None
        print(json.dumps(dict(error=type(e).__name__,reason=re.sub(r'https?://\S+','[URL]',str(e))[:1000],traffic=meter.summary())),flush=True)
    finally:
        if digest(OLD/'http-ledger.jsonl')!=cfg['old_ledger_sha256'] or digest(PARENT/'integrity.json')!=INTEGRITY:raise ValueError('Prior data/ledger changed')
        lock.unlink(missing_ok=True)

def worldcover_fallback():
    cfg=freeze();amendment=dict(parent_plan_sha256=digest(OUT/'frozen_plan.json'),reason='Original17window DW-only context screen measured zero; WorldCover2021cropland exists in development caches. Historical context can guide sampling, never prove current agriculture.',unchanged_windows=cfg['windows'],additional_source='ESA/WorldCover/v200/2021 Map==40; CC-BY4.0;10m native; nearest30m context only',selection='Up to2highest combined WorldCover cropland/DW crop-context windows, plus1DW built-gain window; no window relocation; distinct frozen TRAIN blocks',label_change='New supplement agricultural context permits historicalWorldCover40 OR DW crop>=.6, still requires paired valid SAR/optical and independently observed early/late vegetation/exposure variation. Not verified agriculture or mining.',budget='SAME new40request/100MB ledger; no reset')
    path=OUT/'worldcover_amendment.json'
    if not path.exists():save_verified(path,amendment)
    elif cached_json(path)!=amendment:raise ValueError('Amendment changed')
    meter=MeteredHttp(OUT/'gee-ledger.jsonl',**cfg['budget'])
    from scripts.phase22w_ablation import acquire_lock
    lock=acquire_lock(Path('outputs/phase25/receipts/.acquire.lock'))
    try:
        import ee
        from google.oauth2.credentials import Credentials
        from config.settings import project_id
        ee.data.setMaxRetries(0);ee.Initialize(credentials=Credentials(None,**ee.oauth.get_credentials_arguments()),project=project_id(),http_transport=meter)
        oldcfg=json.loads(OLD_CONFIG.read_bytes());base=cached_json(OUT/'screen.json');path=OUT/'worldcover_screen.json'
        if path.exists():screen=cached_json(path)
        else:
            stats={}
            for row in cfg['windows']:
                region=ee.Geometry.Rectangle(row['bounds'],'EPSG:32646',False);crop=ee.Image('ESA/WorldCover/v200/2021').select('Map').eq(40).rename('worldcover2021_cropland_cells')
                stats[row['aoi']]=crop.reduceRegion(ee.Reducer.sum(),region,crs='EPSG:32646',crsTransform=[30,0,row['bounds'][0],0,-30,row['bounds'][3]],maxPixels=reducer_limit((32,32),1))
            measured=ee.Dictionary(stats).getInfo();screen={k:dict(base[k],crop_context_cells=float(base[k]['crop_context_cells'] or 0)+float(v.get('worldcover2021_cropland_cells') or 0),worldcover2021_cropland_cells=v.get('worldcover2021_cropland_cells')) for k,v in measured.items()};save_verified(path,screen)
        selected=choose(cfg['windows'],screen)
        if not (OUT/'selected_worldcover.json').exists():save_verified(OUT/'selected_worldcover.json',selected)
        elif cached_json(OUT/'selected_worldcover.json')!=selected:raise ValueError('Selection changed')
        print(json.dumps(dict(screen=screen,selected=selected,traffic=meter.summary())),flush=True)
        from scripts.phase25_competing_stack import acquire_and_build
        acquire_and_build(cfg,selected,meter,oldcfg)
    except BaseException as e:
        import re
        path=OUT/'worldcover_stop.json'
        if not path.exists():save_verified(path,dict(error=type(e).__name__,reason=re.sub(r'https?://\S+','[URL]',str(e))[:1000],traffic=meter.summary()))
        print(json.dumps(dict(error=type(e).__name__,reason=re.sub(r'https?://\S+','[URL]',str(e))[:1000],traffic=meter.summary())),flush=True)
    finally:
        if digest(OLD/'http-ledger.jsonl')!=cfg['old_ledger_sha256'] or digest(PARENT/'integrity.json')!=INTEGRITY:raise ValueError('Prior data/ledger changed')
        lock.unlink(missing_ok=True)

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--worldcover-fallback']:worldcover_fallback()
    elif not sys.argv[1:]:run()
    else:raise ValueError('Unknown arguments')
