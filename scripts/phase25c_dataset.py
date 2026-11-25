"""Phase25C private pilot: offline crop-only packaging; no fitting or acquisition."""
import argparse
import csv
import json
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine

from scripts.phase25b_cached import (backup_gate,frozen,guarded,read_development,choose,
    digest,save,tif,PLAN,CONFIG,MANIFEST_SHA)
from scripts.phase25b1_recover import cached_json
from src.phase25.dataset import BANDS,COUNTS,LABELS,SCHEMA,windows,spatial_check,load_manifest,read_patch
from src.phase25.features import Grid

BASE='5b360daf2f42c6785eb65bfc92cc3c7fd5424725'
OLD=Path('outputs/phase25/experiments/25b-v1')
CONTEXT=Path('outputs/phase25/datasets/25b1-v1')
OUTPUT=Path('outputs/phase25/datasets/25c-v1')


def read_grid(path,grid,names):
    with rasterio.open(path) as ds:
        if ds.crs.to_string()!=grid.crs or ds.transform!=Affine(*grid.affine) or ds.shape!=grid.shape or list(ds.descriptions)!=names:
            raise ValueError('Source grid/schema mismatch')
        a=ds.read().astype(float)
        if ds.nodata is not None:a[a==ds.nodata]=np.nan
        return a


def schema(cfg):
    definitions=[]
    specs={x['name']:x for x in cfg['layers']}
    for name in BANDS:
        if name.startswith(('before_','after_')):
            short=name.split('_',1)[1]
            definitions.append(dict(name=name,units='dB' if short in ('VV','VH') else 'surface_reflectance' if short.startswith('B') and short!='BSI' else 'unitless_index',
                source='COPERNICUS/S1_GRD' if short in ('VV','VH') else 'COPERNICUS/S2_SR_HARMONIZED + S2_CLOUD_PROBABILITY',
                role='signal',native_support='S1 nominal 10m sampling; effective support and power-domain smoothing preserved' if short in ('VV','VH') else '10m optical; BSI also uses native 20m SWIR; legacy 30m composite sample',
                original_scene_identity='INCOMPLETE; current query corroboration is not original-source certification'))
        elif name.startswith('d'):
            definitions.append(dict(name=name,units='dB_difference' if name in ('dVV','dVH') else 'unitless_index_difference',role='signal',calculation='after minus before',native_support='inherited from paired seasonal features'))
        else:definitions.append(dict(specs[name]))
    return dict(schema=SCHEMA,version='25c-v1',bands=BANDS,definitions=definitions,
        grid=dict(crs='EPSG:32646',pixel_size_m=30,patch_shape=[32,32],patch_extent_m=[960,960],resampling='NONE: aligned integer-window crops only'),
        seasons=cfg['seasons'],label_semantics=LABELS,verified_reference_labels=0,
        no_data=-9999,missing='NoData plus false per-band validity; CSV empty field; never zero-imputed',
        diagnostics=COUNTS,follow_policy='follow count and pseudo states are retrospective evidence, not pre-event model input',
        inference_compatibility='29-band private context schema; NOT the registered 14-band model input; no automatic model adapter',
        validation_role='one debugging-only block; no calibration or independent accuracy',
        rights='private pilot only; source attribution and native support retained; release blocked')


def plot_example(path,key,grid,values,states):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap,BoundaryNorm
    a=Affine(*grid.affine);extent=[a.c,a.c+1920,a.f-1920,a.f]
    fig,axs=plt.subplots(1,4,figsize=(13,4))
    for ax,season in zip(axs[:2],['before','after']):
        rgb=np.stack([values[season+'_'+x] for x in ['B4','B3','B2']],axis=-1)
        ok=np.isfinite(rgb).all(-1);rgb=np.clip(np.nan_to_num(rgb)/.3,0,1)
        ax.imshow(np.dstack([rgb,ok.astype(float)]),extent=extent);ax.set_title(season+' RGB; fixed 0–0.30')
    im=axs[2].imshow(values['after_NDVI']-values['before_NDVI'],extent=extent,vmin=-1,vmax=1,cmap='RdBu')
    axs[2].set_title('NDVI after minus before');fig.colorbar(im,ax=axs[2],shrink=.6)
    z=np.where(states==255,2,states)
    im=axs[3].imshow(z,extent=extent,cmap=ListedColormap(['#557c61','#cf803a','#b6bac2']),norm=BoundaryNorm([-.5,.5,1.5,2.5],3))
    axs[3].set_title('Pseudo states; NOT reference truth')
    cb=fig.colorbar(im,ax=axs[3],ticks=[0,1,2],shrink=.6);cb.ax.set_yticklabels(['potential stable','potential disturbance','uncertain/ignore'])
    for ax in axs:ax.set_xlabel('Easting (m), EPSG:32646');ax.tick_params(axis='both',labelsize=6)
    fig.suptitle(key+' | BEFORE Nov2023–Mar2024 / AFTER Nov2024–Mar2025 | UNKNOWN; PRIVATE QA ONLY')
    fig.tight_layout();fig.savefig(path,dpi=120);plt.close(fig)


def run(backup):
    start=time.perf_counter();cpu=time.process_time()
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='phase25-minechange-india':raise ValueError('Wrong branch')
    subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],check=True)
    if subprocess.check_output(['git','rev-parse','pre-minechange-india^{commit}'],text=True).strip()!='08604dea4fe39641ea32ebda8a37532669b52933':raise ValueError('Stable tag mismatch')
    if OUTPUT.exists():raise ValueError('Existing run: never overwrite')
    if Path('outputs/phase25/receipts/.acquire.lock').exists():raise ValueError('Active acquisition lock: stop')
    hashes=backup_gate(backup);backup=Path(backup)
    for p in [PLAN,CONFIG,Path('docs/reports/phase25b1-preregistration.json')]:
        committed=subprocess.check_output(['git','show',BASE+':'+p.as_posix()])
        # Git stores LF while this Windows checkout may contain CRLF. Raw file
        # identities are separately bound to the backup and acquisition receipts.
        if committed.replace(b'\r\n',b'\n')!=p.read_bytes().replace(b'\r\n',b'\n'):raise ValueError('Changed frozen input contract')
    session=json.loads((CONTEXT/'session.json').read_bytes())
    if digest('docs/reports/phase25b1-preregistration.json')!=session['plan_sha256']:raise ValueError('Acquisition plan raw hash changed')
    cfg=json.loads(CONFIG.read_bytes());plan=json.loads(PLAN.read_bytes());selection=json.loads((OLD/'selection.json').read_bytes())
    keys=choose(plan,cfg['selection'])
    if keys!=selection['aois'] or cfg!=selection['config']:raise ValueError('Original roster/config changed')
    from scripts.phase22n_temporal import guards
    area,protected=guards()
    for p in [PLAN,Path('outputs/phase6b_multitile/districts.json'),Path('outputs/phase6b_multitile/roster.json')]:frozen(p,hashes)
    # All parent guards pass before any AOI imagery/pseudo-state payload read.
    for key in keys:guarded(key,plan['aois'][key],area,protected)
    patches=[];parents=[];source_hashes={};backup_checks={}
    prereg=json.loads(Path('docs/reports/phase25b1-preregistration.json').read_bytes())
    specs=[x['name'] for x in cfg['layers']]
    for key in keys:
        row=plan['aois'][key];values,follow,grid,sources,meta=read_development(key,row,hashes,area,protected)
        for s in sources:
            p=backup/'project_parent'/'mining_monitor_phase1'/s['path']
            if digest(p)!=s['sha256']:raise ValueError('Essential backup payload mismatch')
            backup_checks[s['path']]=s['sha256'];source_hashes[s['path']]=s['sha256']
        old=OLD/key.replace(':','_');receipt=json.loads((old/'receipt.json').read_bytes())
        if receipt['config_sha256']!=digest(CONFIG) or receipt['split']!=row['split']:raise ValueError('Historical receipt mismatch')
        for name,h in receipt['outputs'].items():
            if digest(old/name)!=h:raise ValueError('Historical output altered')
            source_hashes[(old/name).as_posix()]=h
        if digest(old/'pseudo_states.tif')!=prereg['preserved_pseudo_outputs'][key]:raise ValueError('Frozen pseudo state changed')
        states=read_grid(old/'pseudo_states.tif',grid,['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE'])[0]
        # Raster NoData255 is deliberately restored as the uncertain state, never background.
        states=np.where(np.isfinite(states),states,255).astype('uint8')
        if not np.isin(states,[0,1,255]).all():raise ValueError('Invalid pseudo semantics')
        expected={str(k):int((states==k).sum()) for k in [0,1,255]}
        if expected!=receipt['pseudo_counts']:raise ValueError('Pseudo counts changed')
        context_path=CONTEXT/key.replace(':','_')/'integrated/receipt.json'
        context_receipt=None
        if row['split']=='train':
            context_receipt=cached_json(context_path)
            for name,h in context_receipt['output_hashes'].items():
                if digest(context_path.parent/name)!=h:raise ValueError('Context output altered')
                source_hashes[(context_path.parent/name).as_posix()]=h
            source_hashes[context_path.as_posix()]=digest(context_path)
            context=read_grid(context_path.parent/'features.tif',grid,specs)
        else:context=read_grid(old/'features.tif',grid,specs)
        layers={}
        for season in ('before','after'):
            for b in ['VV','VH']+['B2','B3','B4','NDVI','BSI','NDWI']:
                x=values[season+'_'+b].copy();counts=values[season+('_sar_count' if b in ('VV','VH') else '_count')]
                layers[season+'_'+b]=np.where(counts>=cfg['rules']['min_observations'],x,np.nan)
        for b in ['VV','VH','NDVI','BSI']:layers['d'+b]=layers['after_'+b]-layers['before_'+b]
        for name in BANDS:
            if name not in layers:layers[name]=context[specs.index(name)]
        features=np.stack([layers[n] for n in BANDS]).astype('float32');valid=np.isfinite(features)
        counts=np.stack([values['before_count'],values['after_count'],values['before_sar_count'],values['after_sar_count'],follow[6]])
        if np.any((states!=255)&~np.all(valid[:20],axis=0)):raise ValueError('Pseudo state without valid seasonal signals')
        # Crop aligned parents; no selection based on pseudo states or feature values.
        for r,c,h,w in windows():
            a=Affine(*grid.affine)*Affine.translation(c,r);pid='mci25c_'+key.replace(':','_')+f'_r{r:02d}_c{c:02d}'
            patches.append(dict(patch_id=pid,group_id=key,split=row['split'],row_offset=r,col_offset=c,
                crs=grid.crs,affine=list(a)[:6],shape=[h,w],bounds=[a.c,a.f-h*30,a.c+w*30,a.f],parent_bounds=row['bounds']))
        parents.append(dict(key=key,grid=grid,values=values,features=features,valid=valid,counts=counts,states=states,
            receipt=receipt,context=context_receipt,sources=sources,meta=meta))
    spatial_check(patches)
    OUTPUT.mkdir(parents=True,exist_ok=False);(OUTPUT/'patches').mkdir();(OUTPUT/'provenance').mkdir();(OUTPUT/'examples').mkdir()
    save(OUTPUT/'schema.json',schema(cfg))
    for parent in parents:
        key=parent['key'];save(OUTPUT/'provenance'/(key.replace(':','_')+'.json'),dict(original=parent['receipt'],context=parent['context'],historical_inputs=parent['sources'],
            original_scene_status='INCOMPLETE',follow_up='INCOMPLETE original item IDs/dates; count is retrospective QA only',
            no_reference_admission=True,context_absence='VAL has no acquired B1 context; never copied from TRAIN'))
        plot_example(OUTPUT/'examples'/(key.replace(':','_')+'.png'),key,parent['grid'],parent['values'],parent['states'])
        for row in [r for r in patches if r['group_id']==key]:
            folder=OUTPUT/'patches'/row['patch_id'];folder.mkdir();r,c=row['row_offset'],row['col_offset'];sl=np.s_[:,r:r+32,c:c+32]
            x=parent['features'][sl];v=parent['valid'][sl];count=parent['counts'][sl];y=parent['states'][r:r+32,c:c+32]
            grid=Grid(row['crs'],tuple(row['affine']),(32,32))
            tif(folder/'features.tif',x,grid,BANDS);tif(folder/'validity.tif',v,grid,BANDS,dtype='uint8',nodata=None)
            tif(folder/'counts.tif',count,grid,COUNTS)
            tif(folder/'pseudo_states.tif',y,grid,['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE'],dtype='uint8',nodata=255)
            tif(folder/'pseudo_masks.tif',np.stack([y==k for k in [0,1,255]]),grid,list(LABELS.values()),dtype='uint8',nodata=None)
            with (folder/'features.csv').open('x',newline='',encoding='utf-8') as f:
                writer=csv.writer(f);writer.writerow(['pixel_id','patch_id','group_id','split','easting_m','northing_m','pseudo_state','validity_bits']+BANDS)
                a=Affine(*grid.affine)
                for i in range(32):
                    for j in range(32):
                        writer.writerow([key+f':r{r+i}:c{c+j}',row['patch_id'],key,row['split'],*(a*(j+.5,i+.5)),int(y[i,j]),sum(int(v[k,i,j])<<k for k in range(len(BANDS)))]+[float(z) if np.isfinite(z) else '' for z in x[:,i,j]])
            row['files']={name:(folder/(name+'.tif')).relative_to(OUTPUT).as_posix() for name in ['features','validity','counts','pseudo_states','pseudo_masks']}
            row['feature_table']=(folder/'features.csv').relative_to(OUTPUT).as_posix()
            row['provenance']='provenance/'+key.replace(':','_')+'.json'
            row['pseudo_counts']={str(k):int((y==k).sum()) for k in [0,1,255]}
            row['valid_cells']={n:int(v[i].sum()) for i,n in enumerate(BANDS)}
            save(folder/'receipt.json',dict(**row,verified_labels=0,attribution='UNKNOWN',rule_config_sha256=digest(CONFIG),
                outputs={p.name:digest(p) for p in folder.iterdir() if p.is_file()}))
    summary=dict(schema=SCHEMA,status='PRIVATE_PILOT_ENGINEERING_GO_NOT_REFERENCE_DATA',patches=len(patches),pixels=len(patches)*1024,
        bands=len(BANDS),by_split={s:dict(patches=sum(r['split']==s for r in patches),groups=len({r['group_id'] for r in patches if r['split']==s}),
          pseudo_counts={str(k):sum(r['pseudo_counts'][str(k)] for r in patches if r['split']==s) for k in [0,1,255]}) for s in ['train','validation']},
        source_hashes=source_hashes,backup_sources_verified=len(backup_checks),backup_manifest_sha256=MANIFEST_SHA,
        operational_alerts=0,verified_reference_labels=0,requests=0,downloads=0,training_runs=0,
        test='SEALED; only protected geometry metadata used',release='NO-GO',runtime_wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,
        output_bytes_before_manifest=sum(p.stat().st_size for p in OUTPUT.rglob('*') if p.is_file()))
    save(OUTPUT/'summary.json',summary)
    artifacts={p.relative_to(OUTPUT).as_posix():digest(p) for p in OUTPUT.rglob('*') if p.is_file()}
    manifest=dict(schema=SCHEMA,version='25c-v1',bands=BANDS,label_semantics=LABELS,verified_reference_labels=0,
        patches=patches,artifacts=artifacts,source_hashes=source_hashes,rule_config_sha256=digest(CONFIG),original_plan_sha256=digest(PLAN),
        follow_policy='retrospective annotation evidence, excluded from model features',release='NO-GO',normalization='NONE FITTED; native units preserved')
    save(OUTPUT/'manifest.json',manifest);(OUTPUT/'manifest.sha256').write_text(digest(OUTPUT/'manifest.json')+'\n',encoding='utf-8')
    load_manifest(OUTPUT)
    for row in patches:read_patch(OUTPUT,row['patch_id'],allow_pseudo=True)
    for path,h in source_hashes.items():
        if digest(path)!=h:raise ValueError('Source changed during packaging')
    print(json.dumps({k:v for k,v in summary.items() if k!='source_hashes'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--backup',required=True);a=p.parse_args();run(a.backup)
