"""Phase25B.1: preregistered context/provenance recovery, one metered resumable pilot."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
from affine import Affine

from scripts.phase25b_cached import backup_gate,digest,frozen,guarded,save,tif
from src.phase25.features import Grid

PREREG=Path('docs/reports/phase25b1-preregistration.json')
OUT=Path('outputs/phase25/datasets/25b1-v1')
LEGACY=Path('outputs/phase25/experiments/25b-v1')
XPLAN=Path('docs/reports/phase22x-preregistration.json')
X=Path('outputs/phase22x_landscape')
BEFORE=('2023-11-01','2024-04-01');AFTER=('2024-11-01','2025-04-01')
NAMES=['elevation','land_cover','rain_before_mm','rain_after_mm','rain_before_count','rain_after_count',
       'water_occurrence','burn_before','burn_after','burn_before_count','burn_after_count']


def checked_json(path, sha):
    if digest(path)!=sha:raise ValueError('Changed frozen artifact')
    return json.loads(Path(path).read_bytes())


def plan(backup):
    hashes=backup_gate(backup)
    from scripts.phase22n_temporal import guards
    area,protected=guards();frozen(XPLAN,hashes)
    original=json.loads(XPLAN.read_bytes());old=json.loads((LEGACY/'summary.json').read_bytes())
    ids=[r['aoi'] for r in old['aois'] if r['split']=='train']
    if len(ids)>6 or len(ids)!=3:raise ValueError('Use exactly the existing three TRAIN AOIs')
    rows={}
    cross=Path('outputs/phase23i_review/crosswalk.json');mm=Path('outputs/phase23i_review/s2_10m/metadata.json')
    frozen(cross,hashes);frozen(mm,hashes)
    items=json.loads(cross.read_bytes());metadata=json.loads(mm.read_bytes())
    local={}
    from shapely.geometry import box
    from shapely import transform
    from pyproj import Transformer
    project=Transformer.from_crs(32646,4326,always_xy=True).transform
    for key in ids:
        r=original['aois'][key];g=guarded(key,r,area,protected)
        halo=box(*r['bounds']).buffer(1000,join_style=2)
        roads_ok=area.covers(halo) and not any(halo.intersects(p) for _,p in protected)
        west,south,east,north=transform(halo,project,interleaved=False).bounds
        query_box=transform(box(west,south,east,north),Transformer.from_crs(4326,32646,always_xy=True).transform,interleaved=False)
        roads_ok=roads_ok and area.covers(query_box) and not any(query_box.intersects(p) for _,p in protected)
        query=f'[out:json][timeout:25][maxsize:1000000][date:"2025-03-31T23:59:59Z"];way["highway"]({south:.8f},{west:.8f},{north:.8f},{east:.8f});out geom;'
        rows[key]=dict(bounds=r['bounds'],split='train',guard=g,osm_query=query,osm_halo_eligible=roads_ok)
        local[key]={}
        for season in ('before','after','follow'):
            candidates=set()
            for it in items:
                if it['aoi']==key:candidates.update(metadata[it['review_id']][season]['ids'])
            local[key][season]=dict(candidate_s2_ids=sorted(candidates),status='spatial subset from existing review-chip metadata, NOT exact legacy AOI source certification')
    OUT.mkdir(parents=True,exist_ok=False)
    save(OUT/'local_source_recovery.json',local)
    p=dict(version='25b1-v1',date='2026-11-25',base='ce5f675',aois=rows,grid=dict(crs='EPSG:32646',size=64,metres=30),
        seasons=dict(before=BEFORE,after=AFTER),budget=dict(max_requests=60,max_bytes=100_000_000,response_cap=2_000_000),
        selection='All three existing Phase25B TRAIN AOIs, no VAL, no replacements or outcome-based reselection',
        sources=dict(elevation='USGS/SRTMGL1_003',land_cover='ESA/WorldCover/v200/2021',rain='UCSB-CHG/CHIRPS/DAILY',
                     water='JRC/GSW1_4/GlobalSurfaceWater',fire='MODIS/061/MCD64A1',roads='Overpass official public API; historical snapshot 2025-03-31'),
        support=dict(elevation_m=30,land_cover_m=10,rain_degrees=.05,water_m=30,fire_m=500,
                     sampling='nearest-neighbor native values onto frozen 30m grid; no fine-scale evidence claim'),
        qa=dict(rain_required_days=dict(before=152,after=151),fire_required_months=5,fire_land_bit=0,fire_valid_bit=1,
                osm_max_distance_m=1000,osm_max_ways=1000),
        provenance='Local candidate IDs remain partial; current query identities compared with original acquisition timestamps/counts, never silently certified as original sources',
        preserved_pseudo_outputs={a['aoi']:digest(LEGACY/a['aoi'].replace(':','_')/'pseudo_states.tif') for a in old['aois']},
        original_plan_sha256=digest(XPLAN),legacy_summary_sha256=digest(LEGACY/'summary.json'),
        local_source_recovery_sha256=digest(OUT/'local_source_recovery.json'),
        interpretation='Context only; no threshold recalibration, reference labels, causal attribution or model training',
        licensing=dict(worldcover='CC-BY-4.0',chirps='public domain; cite',jrc='Copernicus; EC JRC/Google attribution',
                       modis='LP DAAC unrestricted use; cite',srtm='NASA/USGS/JPL use policy; cite',osm='ODbL; attribution/share-alike obligations; private outputs only'))
    save(PREREG,p)
    print('Preregistered',list(rows),'local candidate S2 IDs',sum(len(x['candidate_s2_ids']) for r in local.values() for x in r.values()))


def fire_graph(ee,col,start,end):
    def one(img):
        qa=img.select('QA');bd=img.select('BurnDate')
        valid=qa.bitwiseAnd(1).neq(0).And(qa.bitwiseAnd(2).neq(0)).And(qa.bitwiseAnd(4).eq(0)).And(qa.rightShift(5).eq(0)).And(bd.gte(0)).And(bd.lte(366))
        year=ee.Date(img.get('system:time_start')).get('year')
        time=bd.subtract(1).multiply(86400000).add(ee.Date.fromYMD(year,1,1).millis())
        burned=bd.gt(0).And(time.gte(ee.Date(start).millis())).And(time.lt(ee.Date(end).millis()))
        return burned.updateMask(valid).rename('burn')
    c=col.map(one);count=c.count().unmask(0)
    return c.max().updateMask(count.eq(5)),count


def graphs(ee,key,row):
    from config.phase2_settings import Phase2Config
    from config.settings import Season
    from src.optical_preprocessing import collections
    from src.sar_preprocessing import collection
    region=ee.Geometry.Rectangle(row['bounds'],'EPSG:32646',False)
    dem=ee.Image('USGS/SRTMGL1_003').select('elevation')
    cover=ee.Image('ESA/WorldCover/v200/2021').select('Map')
    water=ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence')
    rain=[];counts=[];burn=[];bc=[];info={}
    for name,dates in [('before',BEFORE),('after',AFTER)]:
        c=ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterDate(*dates)
        n=(dt.date.fromisoformat(dates[1])-dt.date.fromisoformat(dates[0])).days
        count=c.select('precipitation').count().unmask(0)
        rain.append(c.select('precipitation').sum().updateMask(count.eq(n)));counts.append(count)
        f=ee.ImageCollection('MODIS/061/MCD64A1').filterDate(*dates)
        b,k=fire_graph(ee,f,*dates);burn.append(b);bc.append(k)
        cfg=Phase2Config(relative_orbit=77)
        _,s2=collections(region,Season(name,*dates),cfg)
        s1=collection(region,Season(name,*dates),cfg).filter(ee.Filter.eq('relativeOrbitNumber_start',77))
        info[name]=dict(rain_ids=c.aggregate_array('system:index'),rain_count=c.size(),fire_ids=f.aggregate_array('system:index'),fire_count=f.size(),
             s2_ids=s2.aggregate_array('system:index'),s2_dates_ms=s2.aggregate_array('system:time_start'),
             s1_ids=s1.aggregate_array('system:index'),s1_dates_ms=s1.aggregate_array('system:time_start'))
    stack=ee.Image.cat([dem,cover,rain[0],rain[1],counts[0],counts[1],water,burn[0],burn[1],bc[0],bc[1]]).rename(NAMES)
    info['native']={k:dict(crs=im.projection().crs(),transform=im.projection().transform(),nominal_metres=im.projection().nominalScale()) for k,im in [('dem',dem),('cover',cover),('water',water),('rain',ee.Image(c.first()).select('precipitation')),('fire',ee.Image(f.first()).select('BurnDate'))]}
    return stack,info


def cached_json(path):
    path=Path(path)
    return checked_json(path,(path.with_suffix(path.suffix+'.sha256')).read_text().strip())


def save_verified(path,obj):
    save(path,obj)
    Path(str(path)+'.sha256').write_text(digest(path)+'\n',encoding='utf-8')


def road_distance(data,grid):
    from shapely.geometry import LineString,Point
    from shapely.ops import unary_union
    from shapely import transform
    from pyproj import Transformer
    if data.get('remark') or len(data.get('elements',[]))>1000:raise ValueError('Incomplete/oversized OSM response')
    project=Transformer.from_crs(4326,32646,always_xy=True).transform
    lines=[]
    for e in data.get('elements',[]):
        if e.get('type')!='way' or 'highway' not in e.get('tags',{}):continue
        xy=[(p['lon'],p['lat']) for p in e.get('geometry',[]) if 'lon' in p and 'lat' in p]
        if len(xy)>=2:lines.append(transform(LineString(xy),project,interleaved=False))
    values=np.full(grid.shape,np.nan)
    if lines:
        roads=unary_union(lines);a=Affine(*grid.affine)
        for r in range(grid.shape[0]):
            for c in range(grid.shape[1]):
                d=Point(*(a*(c+.5,r+.5))).distance(roads)
                if d<=1000:values[r,c]=d
    return values,len(lines)


def integrate(key,row,plan,metadata,raw):
    import rasterio
    from rasterio.io import MemoryFile
    from src.phase25.features import stack_layers
    bounds=row['bounds'];affine=Affine(30,0,bounds[0],0,-30,bounds[3]);grid=Grid('EPSG:32646',tuple(affine)[:6],(64,64))
    with MemoryFile(raw) as m,m.open() as ds:
        if ds.shape!=(64,64) or ds.count!=len(NAMES) or ds.crs.to_string()!=grid.crs or ds.transform!=affine:
            raise ValueError('Acquired grid differs from frozen lattice')
        if any(ds.descriptions) and tuple(ds.descriptions)!=tuple(NAMES):raise ValueError('Acquired band order mismatch')
        a=ds.read().astype(float);a[a==-9999]=np.nan
    v=dict(zip(NAMES,a));info=metadata[key]
    if any(info[s]['rain_count']!=n or info[s]['fire_count']!=5 for s,n in [('before',152),('after',151)]):
        raise ValueError('Unexpected seasonal source support; do not certify')
    base=LEGACY/key.replace(':','_');br=json.loads((base/'receipt.json').read_bytes())
    if digest(base/'features.tif')!=br['outputs']['features.tif']:raise ValueError('Phase25B baseline changed')
    with rasterio.open(base/'features.tif') as ds:
        if ds.transform!=affine or ds.crs.to_string()!=grid.crs or ds.shape!=grid.shape:raise ValueError('Baseline alignment mismatch')
        old=ds.read().astype(float);old[old==ds.nodata]=np.nan
    cfg=json.loads((LEGACY/'selection.json').read_bytes())['config']
    layers={spec['name']:(old[i],np.isfinite(old[i]),grid) for i,spec in enumerate(cfg['layers']) if np.isfinite(old[i]).any()}
    rain_ok=(v['rain_before_count']==152)&(v['rain_after_count']==151)
    fire_ok=(v['burn_before_count']==5)&(v['burn_after_count']==5)
    additions=dict(elevation=v['elevation'],land_cover=np.where(np.isin(v['land_cover'],[10,20,30,40,50,60,70,80,90,95,100]),v['land_cover'],np.nan),
        rainfall=np.where(rain_ok,v['rain_after_mm']-v['rain_before_mm'],np.nan),
        surface_water=np.where((v['water_occurrence']>=0)&(v['water_occurrence']<=100),v['water_occurrence'],np.nan),
        fire_history=np.where(fire_ok,np.maximum(v['burn_before'],v['burn_after']),np.nan))
    folder=OUT/key.replace(':','_')
    road_note=dict(status='UNAVAILABLE',license='ODbL',source_date='2025-03-31T23:59:59Z',maximum_supported_distance_m=1000)
    if (folder/'roads.json').exists():
        road_data=cached_json(folder/'roads.json');road,n=road_distance(road_data,grid);additions['roads']=road
        road_note.update(status='AVAILABLE_CENSORED' if np.isfinite(road).any() else 'NO_SUPPORTED_DISTANCE',ways=n,
                         source_hash=digest(folder/'roads.json'),attribution='OpenStreetMap contributors; ODbL',
                         warning='No mapped road or distance>1000m is missing, not proof of road absence; snapshot is not construction date')
    for name,x in additions.items():layers[name]=(x,np.isfinite(x),grid)
    stack,valid,status=stack_layers(layers,grid,cfg['layers'])
    target=folder/'integrated'
    if target.exists():raise ValueError('No overwrite of integrated artifacts')
    target.mkdir()
    names=[s['name'] for s in cfg['layers']]
    tif(target/'features.tif',stack,grid,names);tif(target/'validity.tif',valid,grid,names,dtype='uint8',nodata=None)
    tif(target/'context_diagnostics.tif',a,grid,NAMES)
    for file in ['features.tif','validity.tif','context_diagnostics.tif']:
        with rasterio.open(target/file) as ds:
            if ds.transform!=affine or ds.shape!=grid.shape or ds.crs.to_string()!=grid.crs:raise ValueError('Written grid mismatch')
    legacy_meta=json.loads((X/(key.replace(':','_')+'_meta.json')).read_bytes())['meta']
    agreement={s:sorted(info[s]['s2_dates_ms'])==sorted(legacy_meta[s]['s2_days']) for s in ('before','after')}
    r=dict(aoi=key,status='CONTEXT_INTEGRATED_NOT_REFERENCE_DATA',availability=status,
        valid_cells={name:int(valid[i].sum()) for i,name in enumerate(names)},grid=dict(crs=grid.crs,affine=list(affine)[:6],shape=grid.shape),
        source_metadata=info,sources=plan['sources'],native_support=plan['support'],licensing=plan['licensing'],roads=road_note,
        dates=plan['seasons'],rainfall='after seasonal total minus before seasonal total (mm); 151 vs152days, coarse cells, no fine spatial precision',
        fire='At least one MODIS mapped burn in either season; all five months valid in each season; 0 is not proof of no fire',
        provenance=dict(query_source_ids_status='EXACT FOR CURRENT FILTERED QUERY, NOT RETROACTIVELY CERTIFIED ORIGINAL SOURCES',s2_timestamp_multiset_matches_legacy=agreement,
            s1_legacy_counts_match={s:len(info[s]['s1_ids'])==legacy_meta[s]['s1_scenes'] for s in ('before','after')},
            missing='Original S1 identities/dates and follow-up identities remain ambiguous unless separately evidenced'),
        old_pseudo_hash=plan['preserved_pseudo_outputs'][key],thresholds_changed=False,training=False,reference_labels=False,
        operational_alerts=0,mining_attribution='UNKNOWN',download_sha256=digest(folder/'context_download.tif'),
        output_hashes={p.name:digest(p) for p in target.glob('*.tif')})
    save_verified(target/'receipt.json',r)
    return r


def execute(backup):
    import subprocess
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='phase25-minechange-india':raise ValueError('Wrong branch')
    if subprocess.check_output(['git','rev-parse','pre-minechange-india^{commit}'],text=True).strip()!='08604dea4fe39641ea32ebda8a37532669b52933':raise ValueError('Stable tag changed')
    hashes=backup_gate(backup);p=json.loads(PREREG.read_bytes())
    checked_json(XPLAN,p['original_plan_sha256']);checked_json(LEGACY/'summary.json',p['legacy_summary_sha256'])
    for key,h in p['preserved_pseudo_outputs'].items():
        if digest(LEGACY/key.replace(':','_')/'pseudo_states.tif')!=h:raise ValueError('Historical pseudo result changed')
    from scripts.phase22n_temporal import guards
    from scripts.phase22w_ablation import acquire_lock
    area,protected=guards();original=json.loads(XPLAN.read_bytes())
    for key,row in p['aois'].items():guarded(key,original['aois'][key],area,protected)
    global_lock=Path('outputs/phase25/receipts/.acquire.lock');lock=acquire_lock(global_lock)
    from src.phase25.acquisition import MeteredHttp
    meter=None
    try:
        meter=MeteredHttp(OUT/'http-ledger.jsonl',**p['budget'])
        session=OUT/'session.json'
        if not session.exists():save(session,dict(plan_sha256=digest(PREREG),script_sha256=digest(__file__),transport_sha256=digest('src/phase25/acquisition.py')))
        session_info=json.loads(session.read_bytes())
        if session_info!=dict(plan_sha256=digest(PREREG),script_sha256=digest(__file__),transport_sha256=digest('src/phase25/acquisition.py')):
            raise ValueError('Frozen acquisition code/plan changed; do not restart budget')
        completed=[]
        # Resume without authentication when every frozen row already has verified integrated output.
        if not all((OUT/k.replace(':','_')/'integrated/receipt.json').exists() for k in p['aois']):
            import ee
            from google.oauth2.credentials import Credentials
            from config.settings import project_id
            args=ee.oauth.get_credentials_arguments()
            if not args.get('refresh_token'):raise ValueError('Existing explicit EE refresh credentials required; no auth fallback')
            credentials=Credentials(None,**args)
            ee.data.setMaxRetries(0)
            ee.Initialize(credentials=credentials,project=project_id(),http_transport=meter)
            meta_path=OUT/'query_metadata.json'
            if meta_path.exists():metadata=cached_json(meta_path)
            else:
                metadata=ee.Dictionary({k:ee.Dictionary(graphs(ee,k,row)[1]) for k,row in p['aois'].items()}).getInfo()
                save_verified(meta_path,metadata)
            for key,row in p['aois'].items():
                folder=OUT/key.replace(':','_');folder.mkdir(exist_ok=True)
                receipt=folder/'integrated/receipt.json'
                if receipt.exists():
                    existing=cached_json(receipt)
                    for name,h in existing['output_hashes'].items():
                        if digest(folder/'integrated'/name)!=h:raise ValueError('Cached integrated output changed')
                    continue
                target=folder/'context_download.tif'
                if target.exists():
                    if digest(target)!=target.with_suffix('.sha256').read_text().strip():raise ValueError('Cached download hash mismatch')
                    raw=target.read_bytes()
                else:
                    stack,_=graphs(ee,key,row);a=Affine(30,0,row['bounds'][0],0,-30,row['bounds'][3])
                    url=stack.toFloat().unmask(-9999,False).getDownloadURL(dict(format='GEO_TIFF',crs='EPSG:32646',crs_transform=list(a)[:6],dimensions=[64,64]))
                    response,raw=meter.request(url)
                    if response.status!=200:raise RuntimeError('Raster request failed')
                    with target.open('xb') as f:f.write(raw)
                    target.with_suffix('.sha256').write_text(digest(target)+'\n',encoding='utf-8')
                if row['osm_halo_eligible'] and not (folder/'roads.json').exists() and not (folder/'roads_unavailable.json').exists():
                    response,body=meter.request('https://overpass-api.de/api/interpreter',method='POST',body=row['osm_query'],headers={'Content-Type':'text/plain'})
                    if response.status==200:
                        try:
                            roads=json.loads(body);road_distance(roads,Grid('EPSG:32646',(30,0,row['bounds'][0],0,-30,row['bounds'][3]),(64,64)))
                            save_verified(folder/'roads.json',roads)
                        except (ValueError,KeyError,TypeError):save(folder/'roads_unavailable.json',dict(status='INCOMPLETE_OR_INVALID_RESPONSE'))
                    else:save(folder/'roads_unavailable.json',dict(status='HTTP_FAILURE',http_status=response.status))
                integrate(key,row,p,metadata,raw)
        for key in p['aois']:
            r=cached_json(OUT/key.replace(':','_')/'integrated/receipt.json')
            for name,h in r['output_hashes'].items():
                if digest(OUT/key.replace(':','_')/'integrated'/name)!=h:raise ValueError('Completed output hash mismatch')
            completed.append({k:r[k] for k in ('aoi','availability','valid_cells','provenance')})
        summary=dict(status='COMPLETED',aois=completed,traffic=meter.summary(),pseudo_results_preserved=True,training=False,reference_labels=0,operational_alerts=0)
        if not (OUT/'summary.json').exists():save(OUT/'summary.json',summary)
        print(json.dumps(summary))
    except BaseException as exc:
        # No secret-bearing exception messages or signed URLs in the public-facing receipt.
        with (OUT/'last_attempt.json').open('w',encoding='utf-8') as f:json.dump(dict(status='STOPPED_PARTIAL',error_type=type(exc).__name__,traffic=meter.summary() if meter else dict(status='LEDGER_INVALID')),f,indent=2)
        print(json.dumps(dict(status='STOPPED_PARTIAL',error_type=type(exc).__name__,traffic=meter.summary() if meter else dict(status='LEDGER_INVALID'))))
        raise SystemExit(1) from None
    finally:lock.unlink(missing_ok=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--backup',required=True)
    g=parser.add_mutually_exclusive_group(required=True);g.add_argument('--plan',action='store_true');g.add_argument('--execute',action='store_true')
    a=parser.parse_args();(plan if a.plan else execute)(a.backup)
