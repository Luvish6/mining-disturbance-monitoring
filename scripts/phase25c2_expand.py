"""Phase25C.2: frozen offline QA, ONE metered context session, separate private expansion."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.io import MemoryFile

from scripts.phase25b_cached import (backup_gate,frozen,guarded,read_development,digest,save,tif,PLAN,CONFIG,FIELDS)
from scripts.phase25b1_recover import cached_json,save_verified
from scripts.phase25c_dataset import package,read_grid
from src.phase25.dataset import BANDS,COUNTS,spatial_check,load_manifest
from src.phase25.features import Grid,pseudo_states

P=Path('outputs/phase25/datasets/25c1-plan-v1')
Q=Path('outputs/phase25/qa/25c2-offline-v1')
R=Path('outputs/phase25/datasets/25c2-acquisition-v1')
D=Path('outputs/phase25/datasets/25c2-v1')
OLD=Path('outputs/phase25/experiments/25b-v1')
PLAN_SHA='e2fa7d831421bae8bd338060193f6104b66ec25524dec5417fd8abfc0e363d84'
CONTRACT_SHA='b10e1f803bf38f5471c796a906e5e3947e820a297a3d434e0efdae7376c8a98f'
RULE_SHA='f59a7d08541103f33fb28d8da7815ed13c1e3d1ee41dd3a4b9a9a9a58ac89186'
NAMES=['elevation','land_cover','rain_before_mm','rain_after_mm','rain_before_count','rain_after_count','water_occurrence']


def checked(path,h):
    if digest(path)!=h:raise ValueError('Frozen SHA256 mismatch: '+Path(path).name)
    return json.loads(Path(path).read_bytes())


def verify(backup):
    p=checked(P/'plan.json',PLAN_SHA);contract=checked(P/'acquisition-contract.json',CONTRACT_SHA)
    if contract['plan_sha256']!=PLAN_SHA or digest(contract['reference_contract']['path'])!=contract['reference_contract']['sha256']:
        raise ValueError('Referenced frozen contract changed')
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='phase25-minechange-india':raise ValueError('Wrong branch')
    subprocess.run(['git','merge-base','--is-ancestor','ea25bb7','HEAD'],check=True)
    if subprocess.check_output(['git','rev-parse','pre-minechange-india^{commit}'],text=True).strip()!='08604dea4fe39641ea32ebda8a37532669b52933':raise ValueError('Stable tag changed')
    hashes=backup_gate(backup);frozen(PLAN,hashes);original=checked(PLAN,p['original_plan_sha256']);cfg=checked(CONFIG,RULE_SHA)
    from scripts.phase22n_temporal import guards
    area,protected=guards()
    for path in ['outputs/phase6b_multitile/districts.json','outputs/phase6b_multitile/roster.json']:frozen(path,hashes)
    keys=[a['aoi'] for a in p['aois']]
    if len(keys)!=20 or set(keys)!=set(original['aois']) or len(set(keys))!=20:raise ValueError('Frozen roster changed')
    for row in p['aois']:
        key=row['aoi'];base=original['aois'][key]
        if row['bounds']!=base['bounds'] or row['split']!=base['split']:raise ValueError('Source geometry/split mismatch')
        guarded(key,base,area,protected)
    spatial_check(p['proposed_patches'])
    for path,h in p['metadata_hashes'].items():checked(path,h)
    # Previous private dataset is integrity-checked only after all parent TEST guards.
    checked('outputs/phase25/datasets/25c-v1/manifest.json','540b2479e062877ac41090dfa7ed04d4deb90e7422f3a8b3583b333766461e08')
    old_m=load_manifest('outputs/phase25/datasets/25c-v1')
    preserved={'outputs/phase25/datasets/25c-v1/manifest.json':'540b2479e062877ac41090dfa7ed04d4deb90e7422f3a8b3583b333766461e08'}
    for name,h in old_m['artifacts'].items():preserved['outputs/phase25/datasets/25c-v1/'+name]=h
    old_b1=json.loads(Path('docs/reports/phase25b1-preregistration.json').read_bytes())
    for key,h in old_b1['preserved_pseudo_outputs'].items():preserved[str(OLD/key.replace(':','_')/'pseudo_states.tif')]=h
    reviews=json.loads(Path('outputs/phase25/receipts/25c1-review-import-v1/receipt.json').read_bytes())
    for role in ['A','B']:
        item=reviews['original_sheets'][role];preserved['outputs/phase23i_review/'+item['filename']]=item['sha256']
    preserved['outputs/phase23i_review/crosswalk.json']=p['review']['source_crosswalk_sha256']
    for path,h in preserved.items():
        if digest(path)!=h:raise ValueError('Preserved artifact changed')
    return p,contract,cfg,hashes,original,area,protected,preserved


def signals(v):
    layers={}
    for s in ['before','after']:
        for b in ['VV','VH','B2','B3','B4','NDVI','BSI','NDWI']:
            count=v[s+('_sar_count' if b in ('VV','VH') else '_count')]
            layers[s+'_'+b]=np.where(count>=2,v[s+'_'+b],np.nan)
    for b in ['VV','VH','NDVI','BSI']:layers['d'+b]=layers['after_'+b]-layers['before_'+b]
    return layers


def qa(backup):
    p,c,cfg,hashes,original,area,protected,preserved=verify(backup)
    if Q.exists():raise ValueError('Existing QA run; no overwrite')
    results=[];payload_hashes={};states_by_key={};backup_checks={}
    for row in p['aois']:
        key=row['aoi'];v,f,g,sources,m=read_development(key,original['aois'][key],hashes,area,protected)
        for src in sources:
            path=Path(backup)/'project_parent'/'mining_monitor_phase1'/src['path']
            if digest(path)!=src['sha256']:raise ValueError('Backup development payload mismatch')
            payload_hashes[src['path']]=src['sha256'];backup_checks[src['path']]=src['sha256']
        if any(np.isinf(x).any() for x in list(v.values())+[f]):raise ValueError('Nonfinite infinite source data')
        y,e=pseudo_states(np.stack([v['before_'+b] for b in FIELDS]),np.stack([v['after_'+b] for b in FIELDS]),f[:6],v['before_count'],v['after_count'],f[6],
            v['before_VV'],v['after_VV'],v['before_VH'],v['after_VH'],v['before_sar_count'],v['after_sar_count'],v['slope'],cfg['rules'])
        a=np.stack(list(signals(v).values()))
        if np.any((y!=255)&~np.isfinite(a).all(0)):raise ValueError('Pseudo-state/signal validity mismatch')
        prior=OLD/key.replace(':','_')/'pseudo_states.tif'
        if prior.exists():
            py=read_grid(prior,g,['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE'])[0];py=np.where(np.isfinite(py),py,255).astype('uint8')
            if not np.array_equal(y,py):raise ValueError('Historical pseudo-state replay mismatch')
        results.append(dict(aoi=key,split=row['split'],grid=dict(crs=g.crs,affine=g.affine,shape=g.shape),
            pseudo_counts={str(k):int((y==k).sum()) for k in [0,1,255]},eligible_optical_cells=int(e['eligible'].sum()),
            common_screening_support=int((e['eligible']&e['sar_valid']&e['follow_valid']).sum()),
            signal_valid_cells={n:int(np.isfinite(x).sum()) for n,x in signals(v).items()},
            acquisition_days={s:len({int(t)//86400000 for t in m['meta'][s]['s2_days']}) for s in ['before','after']}))
        states_by_key[key]=(y,g)
    Q.mkdir(parents=True,exist_ok=False)
    for key,(y,g) in states_by_key.items():tif(Q/(key.replace(':','_')+'_pseudo.tif'),y,g,['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE'],dtype='uint8',nodata=255)
    result=dict(status='PASS_ALL_20_NO_RESELECTION',plan_sha256=PLAN_SHA,contract_sha256=CONTRACT_SHA,rules_sha256=RULE_SHA,aois=results,
        source_hashes=payload_hashes,backup_verified_files=len(backup_checks),preserved=preserved,
        pseudo_hashes={k:digest(Q/(k.replace(':','_')+'_pseudo.tif')) for k in states_by_key},
        duplicate_image_payloads=len([h for path,h in payload_hashes.items() if path.endswith('.npy')])-len({h for path,h in payload_hashes.items() if path.endswith('.npy')}),
        requests=0,verified_labels=0)
    save_verified(Q/'receipt.json',result)
    print(json.dumps(dict(status=result['status'],aois=len(results),by_split={s:{str(k):sum(r['pseudo_counts'][str(k)] for r in results if r['split']==s) for k in [0,1,255]} for s in ['train','validation']})))


def checked_qa():
    q=cached_json(Q/'receipt.json')
    if q['plan_sha256']!=PLAN_SHA or q['contract_sha256']!=CONTRACT_SHA or q['rules_sha256']!=RULE_SHA:raise ValueError('QA contract changed')
    for path,h in {**q['source_hashes'],**q['preserved']}.items():
        if digest(path)!=h:raise ValueError('QA source or preserved artifact changed')
    for key,h in q['pseudo_hashes'].items():
        if digest(Q/(key.replace(':','_')+'_pseudo.tif'))!=h:raise ValueError('QA pseudo raster changed')
    return q


def graph(ee,row,contract,*,metadata=True):
    region=ee.Geometry.Rectangle(row['bounds'],'EPSG:32646',False)
    sources=contract['sources'];dem=ee.Image(sources['elevation']).select('elevation');cover=ee.Image(sources['land_cover']).select('Map');water=ee.Image(sources['surface_water']).select('occurrence')
    rain=[];counts=[];info={}
    from config.phase2_settings import Phase2Config
    from config.settings import Season
    from src.optical_preprocessing import collections
    from src.sar_preprocessing import collection
    cfg=Phase2Config(relative_orbit=77)
    for s in ['before','after']:
        dates=contract['seasons'][s];n=152 if s=='before' else 151
        c=ee.ImageCollection(sources['rain']).filterDate(*dates);count=c.select('precipitation').count().unmask(0)
        rain.append(c.select('precipitation').sum().updateMask(count.eq(n)));counts.append(count)
        if metadata:
            _,s2=collections(region,Season(s,*dates),cfg);s1=collection(region,Season(s,*dates),cfg).filter(ee.Filter.eq('relativeOrbitNumber_start',77))
            info[s]=dict(s1_ids=s1.aggregate_array('system:index'),s1_dates_ms=s1.aggregate_array('system:time_start'),s2_ids=s2.aggregate_array('system:index'),s2_dates_ms=s2.aggregate_array('system:time_start'),
                rain_ids=c.aggregate_array('system:index'),rain_count=c.size())
    if metadata:
        _,follow=collections(region,Season('follow',*contract['seasons']['follow']),cfg)
        info['follow']=dict(s2_ids=follow.aggregate_array('system:index'),s2_dates_ms=follow.aggregate_array('system:time_start'))
        info['native']={n:dict(crs=i.projection().crs(),transform=i.projection().transform(),nominal_metres=i.projection().nominalScale()) for n,i in [('elevation',dem),('land_cover',cover),('water',water),('rain',ee.Image(c.first()).select('precipitation'))]}
    return ee.Image.cat([dem,cover,rain[0],rain[1],counts[0],counts[1],water]).rename(NAMES),info


def validate_raw(raw,row):
    a=Affine(30,0,row['bounds'][0],0,-30,row['bounds'][3])
    with MemoryFile(raw) as m,m.open() as d:
        if d.shape!=(64,64) or d.count!=7 or d.crs.to_string()!='EPSG:32646' or d.transform!=a:raise ValueError('Context grid/shape mismatch')
        if any(d.descriptions) and list(d.descriptions)!=NAMES:raise ValueError('Context band-order mismatch')
        v=d.read().astype(float);v[v==-9999]=np.nan
    if np.isinf(v).any():raise ValueError('Infinite context values')
    for i in [4,5]:
        finite=v[i][np.isfinite(v[i])]
        if np.any(finite<0) or np.any(finite!=np.floor(finite)):raise ValueError('Invalid context counts')
    return v


def validate_metadata(data,keys):
    if set(data)!=set(keys):raise ValueError('Incomplete current metadata chunk')
    for info in data.values():
        for s in ['before','after','follow']:
            for sensor in (['s1','s2'] if s!='follow' else ['s2']):
                ids=info[s][sensor+'_ids'];dates=info[s][sensor+'_dates_ms']
                if not ids or len(ids)!=len(dates) or len(ids)!=len(set(ids)) or any(not isinstance(i,str) or not i for i in ids):raise ValueError('Invalid current source identity metadata')
        for s,n in [('before',152),('after',151)]:
            if info[s]['rain_count']!=n or len(info[s]['rain_ids'])!=n:raise ValueError('Incomplete rainfall source season')
        if set(info['native'])!={'elevation','land_cover','water','rain'}:raise ValueError('Missing native-grid metadata')


def acquire(backup):
    p,c,cfg,hashes,original,area,protected,preserved=verify(backup);q=checked_qa()
    from scripts.phase22w_ablation import acquire_lock
    from src.phase25.acquisition import MeteredHttp
    lock=acquire_lock(Path('outputs/phase25/receipts/.acquire.lock'));meter=None
    try:
        R.mkdir(parents=True,exist_ok=True)
        software={str(x):digest(x) for x in [Path(__file__),Path('src/phase25/acquisition.py')]}
        session=dict(plan_sha256=PLAN_SHA,contract_sha256=CONTRACT_SHA,qa_sha256=digest(Q/'receipt.json'),software=software)
        if (R/'session.json').exists():
            if cached_json(R/'session.json')!=session:raise ValueError('Session fingerprint changed; no budget reset')
        else:save_verified(R/'session.json',session)
        meter=MeteredHttp(R/'http-ledger.jsonl',max_requests=60,max_bytes=100_000_000,response_cap=2_000_000)
        missing=p['priority'];rows={r['aoi']:r for r in p['aois']}
        chunks=[p['aois'][i:i+2] for i in range(0,len(p['aois']),2)]
        all_meta=all((R/f'metadata_{i:02d}.json').exists() for i in range(len(chunks)))
        all_raw=all((R/k.replace(':','_')/'receipt.json').exists() for k in missing)
        if not(all_meta and all_raw):
            import ee
            from google.oauth2.credentials import Credentials
            from config.settings import project_id
            args=ee.oauth.get_credentials_arguments()
            if not args.get('refresh_token'):raise ValueError('Explicit existing EE credentials required')
            ee.data.setMaxRetries(0);ee.Initialize(credentials=Credentials(None,**args),project=project_id(),http_transport=meter)
            for i,chunk in enumerate(chunks):
                path=R/f'metadata_{i:02d}.json';keys=[r['aoi'] for r in chunk]
                if path.exists():data=cached_json(path)
                else:
                    data=ee.Dictionary({r['aoi']:ee.Dictionary(graph(ee,r,c)[1]) for r in chunk}).getInfo();validate_metadata(data,keys);save_verified(path,data)
                validate_metadata(data,keys)
            for k in missing:
                folder=R/k.replace(':','_');folder.mkdir(exist_ok=True);path=folder/'context.tif'
                if (folder/'receipt.json').exists():
                    receipt=cached_json(folder/'receipt.json')
                    if digest(path)!=receipt['sha256']:raise ValueError('Cached context changed')
                    validate_raw(path.read_bytes(),rows[k]);continue
                if path.exists():
                    if digest(path)!=(folder/'context.sha256').read_text().strip():raise ValueError('Partial cached context changed')
                else:
                    image,_=graph(ee,rows[k],c,metadata=False);a=Affine(30,0,rows[k]['bounds'][0],0,-30,rows[k]['bounds'][3])
                    url=image.toFloat().unmask(-9999,False).getDownloadURL(dict(format='GEO_TIFF',crs='EPSG:32646',crs_transform=list(a)[:6],dimensions=[64,64]))
                    response,raw=meter.request(url)
                    if response.status!=200:raise RuntimeError('Context response failed')
                    with path.open('xb') as f:f.write(raw)
                    (folder/'context.sha256').write_text(digest(path)+'\n',encoding='utf-8')
                validate_raw(path.read_bytes(),rows[k])
                save_verified(folder/'receipt.json',dict(aoi=k,sha256=digest(path),bands=NAMES,grid=rows[k]['bounds'],plan_sha256=PLAN_SHA,
                    source_graph_sha256=hashlib.sha256(graph(ee,rows[k],c,metadata=False)[0].serialize().encode()).hexdigest(),status='GRID_VERIFIED_NOT_REFERENCE'))
                print(json.dumps(dict(aoi=k,status='CONTEXT_ACCEPTED',traffic=meter.summary())),flush=True)
        # All cached artifacts are revalidated on resume, without new authentication if complete.
        for i,chunk in enumerate(chunks):validate_metadata(cached_json(R/f'metadata_{i:02d}.json'),[r['aoi'] for r in chunk])
        for k in missing:
            folder=R/k.replace(':','_');receipt=cached_json(folder/'receipt.json')
            if digest(folder/'context.tif')!=receipt['sha256']:raise ValueError('Completed source hash mismatch')
            validate_raw((folder/'context.tif').read_bytes(),rows[k])
        if not (R/'summary.json').exists():save_verified(R/'summary.json',dict(status='COMPLETED',context_rasters=len(missing),traffic=meter.summary()))
        print(json.dumps(cached_json(R/'summary.json')),flush=True)
    except BaseException as exc:
        with (R/'last_attempt.json').open('w',encoding='utf-8') as f:json.dump(dict(status='STOPPED_PARTIAL',error_type=type(exc).__name__,traffic=meter.summary() if meter else {}),f,indent=2)
        print(json.dumps(dict(status='STOPPED_PARTIAL',error_type=type(exc).__name__)),flush=True)
        raise SystemExit(1) from None
    finally:lock.unlink(missing_ok=True)


def build(backup):
    start=time.perf_counter();cpu=time.process_time();p,c,cfg,hashes,original,area,protected,preserved=verify(backup);q=checked_qa();acq=cached_json(R/'summary.json')
    if acq['status']!='COMPLETED' or D.exists():raise ValueError('Acquisition incomplete or dataset already exists')
    metadata={}
    source_meta_hashes={}
    for i in range(10):
        path=R/f'metadata_{i:02d}.json';metadata.update(cached_json(path));source_meta_hashes[path.as_posix()]=digest(path)
    validate_metadata(metadata,[a['aoi'] for a in p['aois']]);parents=[];source_hashes={**q['source_hashes'],**source_meta_hashes,str(Q/'receipt.json'):digest(Q/'receipt.json'),str(R/'http-ledger.jsonl'):digest(R/'http-ledger.jsonl')};specs=[s['name'] for s in cfg['layers']]
    for row in p['aois']:
        key=row['aoi'];v,f,g,sources,m=read_development(key,original['aois'][key],hashes,area,protected)
        y=read_grid(Q/(key.replace(':','_')+'_pseudo.tif'),g,['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE'])[0];y=np.where(np.isfinite(y),y,255).astype('uint8')
        receipt_row=next(a for a in q['aois'] if a['aoi']==key)
        source_hashes[str(Q/(key.replace(':','_')+'_pseudo.tif'))]=q['pseudo_hashes'][key]
        if key in p['priority']:
            path=R/key.replace(':','_')/'context.tif';r=cached_json(path.parent/'receipt.json')
            if digest(path)!=r['sha256']:raise ValueError('Context hash changed')
            a=validate_raw(path.read_bytes(),row);rain=(a[4]==152)&(a[5]==151)
            context=dict(elevation=a[0],land_cover=np.where(np.isin(a[1],[10,20,30,40,50,60,70,80,90,95,100]),a[1],np.nan),
                rainfall=np.where(rain,a[3]-a[2],np.nan),surface_water=np.where((a[6]>=0)&(a[6]<=100),a[6],np.nan))
            source_hashes[path.as_posix()]=digest(path)
        else:
            path=Path('outputs/phase25/datasets/25b1-v1')/key.replace(':','_')/'integrated/features.tif';r=cached_json(path.parent/'receipt.json')
            if digest(path)!=r['output_hashes']['features.tif']:raise ValueError('Prior context changed')
            a=read_grid(path,g,specs);context={name:a[specs.index(name)] for name in ['elevation','land_cover','rainfall','surface_water']}
            source_hashes[path.as_posix()]=digest(path)
        layers=signals(v);layers['slope']=v['slope'];layers.update(context)
        x=np.stack([layers.get(n,np.full(g.shape,np.nan)) for n in BANDS]).astype('float32');valid=np.isfinite(x)
        counts=np.stack([v['before_count'],v['after_count'],v['before_sar_count'],v['after_sar_count'],f[6]])
        info=metadata[key];r=dict(acquisition=r,current_query=info,original_ids='INCOMPLETE; current queries are not original cache certification',
            original_s2_timestamp_match={s:sorted(info[s]['s2_dates_ms'])==sorted(m['meta'][s]['s2_days']) for s in ['before','after']},
            original_s1_count_match={s:len(info[s]['s1_ids'])==m['meta'][s]['s1_scenes'] for s in ['before','after']},
            follow_ids='CURRENT QUERY ONLY; original identities remain incomplete',licensing=c['rights'],native_support=c['support'])
        parents.append(dict(key=key,grid=g,values=v,features=x,valid=valid,counts=counts,states=y,receipt=receipt_row,context=r,sources=sources,meta=m))
    patches=[dict(r,patch_id=r['patch_id'].replace('planned_','mci25c2_')) for r in p['proposed_patches']];spatial_check(patches)
    traffic=dict(acq['traffic'],raster_downloads=acq['context_rasters'])
    package(parents,patches,cfg,source_hashes,dict.fromkeys(q['source_hashes']),out=D,version='25c2-v1',start=start,cpu=cpu,traffic=traffic,
        context_note='Per-band masks govern availability; context is historical/coarse, never certified mining truth; unsupported layers missing')
    for path,h in preserved.items():
        if digest(path)!=h:raise ValueError('Historical artifact changed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--backup',required=True)
    modes=parser.add_mutually_exclusive_group(required=True)
    for name in ['qa','acquire','build']:modes.add_argument('--'+name,action='store_true')
    args=parser.parse_args();(qa if args.qa else acquire if args.acquire else build)(args.backup)
