"""Bounded OFFLINE Phase25B replay. No acquisition, training or reference admission."""
import argparse
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine

from src.phase25.features import Grid, stack_layers, pseudo_states

CONFIG = Path('config/phase25b_v1.json')
X = Path('outputs/phase22x_landscape')
Y = Path('outputs/phase22y_persistence')
PLAN = Path('docs/reports/phase22x-preregistration.json')
MANIFEST_SHA = 'fac35b9b16303fdb2cb375af76f3dbba872e4c16c2b1cf30be5cda4b900de7c4'
FIELDS = ['B4', 'B3', 'B2', 'NDVI', 'BSI', 'NDWI']
BANDS = [f'{s}_{b}' for s in ('before','after') for b in FIELDS+['count','VV','VH','sar_count']] + ['slope']


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def backup_gate(backup):
    backup = Path(backup)
    if (json.loads((backup/'verification.json').read_bytes())['status'] != 'VERIFIED'
            or digest(backup/'files-sha256.csv') != MANIFEST_SHA):
        raise ValueError('Verified backup unavailable or altered')
    if shutil.disk_usage('.').free < 2*2**30 or shutil.disk_usage(backup).free < 10*2**30:
        raise ValueError('Storage safety gate failed')
    with (backup/'files-sha256.csv').open(encoding='utf-8', newline='') as f:
        return {r['path']:r['sha256'] for r in csv.DictReader(f)}


def frozen(path, hashes):
    path=Path(path)
    key='mining_monitor_phase1/'+path.as_posix()
    if key not in hashes or digest(path) != hashes[key]:
        raise ValueError('Unverified/changed historical input: '+str(path))
    return dict(path=path.as_posix(), sha256=hashes[key])


def choose(plan, selection):
    """Metadata-only ordering; no raster or label read here."""
    chosen=[]
    for split in ('train','validation'):
        keys=[k for k,v in plan['aois'].items() if v['split']==split]
        keys.sort(key=lambda k:hashlib.sha256(('42:25B:'+k).encode()).hexdigest())
        chosen += keys[:selection[split]]
    if len(chosen) != sum(selection[s] for s in ('train','validation')):
        raise ValueError('Insufficient development metadata; no substitutions')
    return chosen


def validate_config(cfg):
    r=cfg['rules']
    if cfg['schema'] != 'minechange-india-features/1' or cfg['version'] != '25b-v1':
        raise ValueError('Unknown versioned contract')
    if cfg['calibration'] != dict(status='UNCALIBRATED_EXPLORATORY',permitted_split='train',independent_evaluation=False):
        raise ValueError('No independent calibration/evaluation supplied')
    if cfg['seasons'] != dict(before=['2023-11-01','2024-04-01'],after=['2024-11-01','2025-04-01'],follow=['2025-11-01','2026-04-01']):
        raise ValueError('Frozen seasons changed')
    if any(not np.isfinite(float(v)) for v in r.values()) or r['min_observations'] < 2:
        raise ValueError('Invalid quality/rule values')
    if not -2 <= r['ndvi_drop'] < 0 or not 0 < r['bsi_increase'] <= 2:
        raise ValueError('Invalid signed change thresholds')
    if any(r[k]<0 for k in ('stable_ndvi_abs','stable_bsi_abs','stable_sar_abs_db')):
        raise ValueError('Invalid stability thresholds')
    if len(cfg['layers']) != 12 or any(s['role']!='context_only' for s in cfg['layers'][3:]):
        raise ValueError('Context/target leakage policy changed')


def guarded(key, row, area, protected):
    from scripts.phase22q_multi_aoi import guard
    if not re.fullmatch(r'\d+:\d+', key) or row['split'] not in ('train','validation'):
        raise ValueError('No TEST source access')
    g=guard(row['bounds'],area,protected)
    if not g['eligible'] or g['block']!=key or g['split']!=row['split']:
        raise ValueError('Frozen full-footprint guard failed')
    return g


def read_development(key, row, hashes, area, protected):
    """Guard the entire rectangle BEFORE hashing/opening any AOI payload."""
    g=guarded(key,row,area,protected)
    stem=key.replace(':','_'); p=X/(stem+'.npy'); m=X/(stem+'_meta.json')
    sources=[frozen(p,hashes),frozen(m,hashes)]
    meta=json.loads(m.read_bytes())
    if meta['bands'] != BANDS:
        raise ValueError('Unexpected cache band order')
    v=np.load(p,allow_pickle=False).astype(float)
    if v.shape != (21,64,64): raise ValueError('Unexpected cache dimensions')
    v[v==-9999]=np.nan
    values=dict(zip(BANDS,v))
    fp=Y/(stem+'.npy');fm=Y/(stem+'_meta.json')
    if fp.exists() and fm.exists():
        sources += [frozen(fp,hashes),frozen(fm,hashes)]
        follow=np.load(fp,allow_pickle=False).astype(float)
        if follow.shape != (7,64,64): raise ValueError('Follow-up grid mismatch')
        follow[follow==-9999]=np.nan
    else:
        follow=np.full((7,64,64),np.nan)
    grid=Grid('EPSG:32646',(30,0,g['bounds'][0],0,-30,g['bounds'][3]),(64,64))
    return values,follow,grid,sources,meta


def tif(path, values, grid, descriptions, *, dtype='float32', nodata=-9999):
    a=np.asarray(values)
    if a.ndim==2:a=a[None]
    with rasterio.open(path,'w',driver='GTiff',crs=grid.crs,transform=Affine(*grid.affine),
                       width=grid.shape[1],height=grid.shape[0],count=len(a),dtype=dtype,nodata=nodata,compress='deflate') as dst:
        dst.write(np.where(np.isfinite(a),a,nodata).astype(dtype));dst.descriptions=tuple(descriptions)


def run(backup,run_id):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',run_id):raise ValueError('Invalid new run ID')
    out=Path('outputs/phase25/experiments')/run_id
    if out.exists():raise ValueError('Never overwrite an existing run')
    hashes=backup_gate(backup)
    cfg=json.loads(CONFIG.read_bytes());validate_config(cfg)
    plan_source=frozen(PLAN,hashes);plan=json.loads(PLAN.read_bytes())
    from scripts.phase22n_temporal import guards
    area,protected=guards()
    frozen(Path('outputs/phase6b_multitile/districts.json'),hashes)
    frozen(Path('outputs/phase6b_multitile/roster.json'),hashes)
    selected=choose(plan,cfg['selection'])
    # Entire selected roster is spatially checked before any array payload is opened.
    boxes=[]
    from shapely.geometry import box
    for key in selected:
        g=guarded(key,plan['aois'][key],area,protected);b=box(*g['bounds'])
        if any(b.intersects(x) for x in boxes):raise ValueError('Selected footprints overlap')
        boxes.append(b)
    product_source=frozen(X/'products.json',hashes)
    products=json.loads((X/'products.json').read_bytes())
    if products['bands'] != ['lossyear','treecover2000','datamask','driver_class','hard_commodities_p250']:
        raise ValueError('Context product schema changed')
    out.mkdir(parents=True,exist_ok=False)
    # Write selection/config receipts before processing; a failed run remains visibly partial.
    save(out/'selection.json',dict(aois=selected,config=cfg,config_sha256=digest(CONFIG),plan=plan_source,backup_manifest_sha256=MANIFEST_SHA))
    rows=[]
    for key in selected:
        row=plan['aois'][key];v,f,grid,sources,meta=read_development(key,row,hashes,area,protected)
        b=np.stack([v['before_'+k] for k in FIELDS]);a=np.stack([v['after_'+k] for k in FIELDS])
        states,evidence=pseudo_states(b,a,f[:6],v['before_count'],v['after_count'],f[6],
            v['before_VV'],v['after_VV'],v['before_VH'],v['after_VH'],v['before_sar_count'],v['after_sar_count'],v['slope'],cfg['rules'])
        layers={name:(x,np.isfinite(x),grid) for name,x in dict(vegetation_change=a[3]-b[3],bare_ground_change=a[4]-b[4],radar_change=v['after_VH']-v['before_VH'],slope=v['slope']).items()}
        stack,masks,status=stack_layers(layers,grid,cfg['layers'])
        folder=out/key.replace(':','_');folder.mkdir()
        names=[s['name'] for s in cfg['layers']]
        tif(folder/'features.tif',stack,grid,names)
        tif(folder/'feature_validity.tif',masks,grid,names,dtype='uint8',nodata=None)
        tif(folder/'pseudo_states.tif',states,grid,['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE'],dtype='uint8',nodata=255)
        tif(folder/'rule_evidence.tif',np.stack(list(evidence.values())),grid,list(evidence),dtype='uint8',nodata=None)
        context=np.asarray(products['grids'][key],float)
        if context.shape != (5,64,64):raise ValueError('Context grid mismatch')
        # No post-window forest-loss or driver probabilities enter pseudo-state rules or model inputs.
        tree=np.where((context[2]==1)&(context[1]>=0)&(context[1]<=100),context[1],np.nan)
        driver=np.where(np.isin(context[3],np.arange(1,8)),context[3],np.nan)
        context=np.stack([tree,driver])
        tif(folder/'context_only.tif',context,grid,['treecover2000_percent','coarse_driver_2001_2024'])
        days={s:len({int(t)//86400000 for t in meta['meta'][s]['s2_days']}) for s in ('before','after')}
        counts={str(k):int((states==k).sum()) for k in (0,1,255)}
        sensitivity={}
        for variant in cfg['sensitivity']:
            variant_rules={**cfg['rules'],**{k:variant[k] for k in ('ndvi_drop','bsi_increase')}}
            ps,_=pseudo_states(b,a,f[:6],v['before_count'],v['after_count'],f[6],v['before_VV'],v['after_VV'],v['before_VH'],v['after_VH'],v['before_sar_count'],v['after_sar_count'],v['slope'],variant_rules)
            sensitivity[variant['id']]={str(k):int((ps==k).sum()) for k in (0,1,255)}
        # Long-period, coarse cause categories are explicit hypotheses, never causal or dated labels.
        flags=np.stack([np.where(np.isfinite(context[1]),x,np.nan) for x in (np.isin(context[1],[1,3]),context[1]==4,context[1]==5,context[1]==6)]+[np.where(np.isfinite(v['slope']),evidence['steep_context'],np.nan)])
        tif(folder/'alternative_context_flags.tif',flags,grid,['possible_agriculture','possible_logging','possible_fire','possible_infrastructure','steep_context'],dtype='uint8',nodata=255)
        info=dict(aoi=key,split=row['split'],usage='development' if row['split']=='train' else 'debug_only_not_independent_evaluation',
            grid=dict(crs=grid.crs,affine=grid.affine,shape=grid.shape),grid_provenance='immutable plan and validated legacy exporter; NPY has no embedded CRS',
            config_sha256=digest(CONFIG),sources=sources+[product_source,plan_source],source_scene_metadata=meta['meta'],
            source_scene_ids_status='INCOMPLETE: exact S1/S2 item IDs and individual follow-up dates absent in these legacy receipts',
            seasons=cfg['seasons'],source_native_support=cfg['layers'],availability=status,optical_eligible_cells=int(evidence['eligible'].sum()),
            common_screening_support_cells=int((evidence['eligible']&evidence['sar_valid']&evidence['follow_valid']).sum()),
            context_sources=dict(treecover2000=dict(collection='UMD/hansen/global_forest_change_2025_v1_13',native_m=30,date='2000 baseline only; lossyear ignored',role='context_only'),
                driver=dict(collection='projects/landandcarbon/assets/wri_gdm_drivers_forest_loss_1km/v1_2_2001_2024',native_m=1000,date='2001-2024 aggregate; not dated site causation',role='context_only',sampling='legacy nearest-neighbor sample on frozen 30m grid')),
            independent_s2_days=days,pseudo_counts=counts,pseudo_hectares={k:n*.09 for k,n in counts.items()},
            explanations=dict(agriculture='possible seasonal/agricultural changes',construction='possible road/building clearance',forest_loss='possible forestry or natural vegetation change',
                fire='coarse historical driver context only; no in-window burn evidence',shadow='residual illumination/terrain artifacts unresolved',
                slope='context only; no steep-slope mining exclusion'),
            attribution='UNKNOWN',review_status='PENDING',independent_reference_labels=False,operational_alerts=0,
            sensitivity=sensitivity,calibration=cfg['calibration'],label_input_independence='SHARED SENSOR SOURCE: cannot validate accuracy against these pseudo states',
            temporal_scope='retrospective persistence uses 2025-26 follow-up; never an earlier prediction input or early-warning claim',
            release_status='BLOCKED: missing context, exact source identities and independent rights/review gates',
            outputs={p.name:digest(p) for p in folder.glob('*.tif')})
        save(folder/'receipt.json',info);rows.append({k:info[k] for k in ('aoi','split','availability','optical_eligible_cells','common_screening_support_cells','independent_s2_days','pseudo_counts','sensitivity')})
    result=dict(schema=cfg['schema'],version=cfg['version'],status='COMPLETED_EXPLORATORY_ONLY',aois=rows,
        config_sha256=digest(CONFIG),backup_manifest_sha256=MANIFEST_SHA,earth_engine_requests=0,data_downloads=0,training_runs=0,
        reference_labels=0,operational_alerts=0,attribution='UNKNOWN',output_bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()))
    save(out/'summary.json',result)
    print(json.dumps(result,allow_nan=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--backup',required=True);p.add_argument('--run-id',required=True)
    args=p.parse_args();run(args.backup,args.run_id)
