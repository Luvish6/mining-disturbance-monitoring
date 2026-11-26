"""One metered, label-blind TRAIN-geography expansion; preserve historical VAL/TEST."""
import argparse,json,math,hashlib,re
from dataclasses import asdict,replace
from pathlib import Path
import numpy as np
from pyproj import Transformer
from shapely.geometry import box
from shapely import transform as geographic_transform

def transform(fn, geometry):
    return geographic_transform(geometry, fn, interleaved=False)
from scripts.phase25b_cached import backup_gate
from src.phase25.dataset import sha
from src.phase3.spatial import block_for,partition

ROOT=Path('outputs/phase25/datasets/minemind-geography-v1')
PLAN=Path('outputs/phase22g_r_maus/proposed-geometry.json')
SPLIT=Path('outputs/phase22b_maus_frozen/split.json')
PLAN_SHA='00f87cbbe5f26a5166165582bacff8492f89f928d13750b5f991d01bbcc503ea'
SPLIT_SHA='603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60'


def save(path,data):
    raw=(json.dumps(data,indent=2,allow_nan=False)+'\n').encode()
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('Immutable output differs')
    else:path.write_bytes(raw)


def rank(x):return hashlib.sha256(('42:MineMind-geography:'+str(x)).encode()).hexdigest()


def windows(patches,groups):
    """Inner footprints inherit authenticated 2050m source guard; no label values used."""
    by_state={}
    for row in sorted(patches,key=lambda r:rank(r['patch_id'])):
        if row['split']!='train':continue
        if groups[row['group_id']]['split']!='train':raise ValueError('Frozen group conflict')
        b=row['bounds'];crs=f"EPSG:{row['crs']}";candidates=[]
        for x in range(math.ceil(b[0]/30)*30,int(b[2]-960)+1,30):
            for y in range(math.ceil(b[1]/30)*30,int(b[3]-960)+1,30):
                bounds=[x,y,x+960,y+960];block=block_for(bounds)
                if block and partition(block)=='train':candidates.append((rank(bounds),bounds,block))
        if not candidates:continue
        _,bounds,block=min(candidates)
        metric=transform(Transformer.from_crs(crs,7755,always_xy=True).transform,box(*bounds))
        item=dict(id=row['patch_id'],state=row['state'],group_id=row['group_id'],split='train',crs=crs,bounds=bounds,block=block,source_footprint=b,source_patch=row['patch_id'])
        by_state.setdefault(row['state'],(item,metric))
    pool=list(by_state.values());chosen=[]
    while pool and len(chosen)<6:
        candidate=min(pool,key=lambda r:(-min([r[1].distance(c[1]) for c in chosen] or [0]),rank(r[0]['id'])))
        pool.remove(candidate)
        if chosen and min(candidate[1].distance(c[1]) for c in chosen)<50000:continue
        chosen.append(candidate)
    if len(chosen)!=6:raise ValueError('Six independent TRAIN states unavailable; no new geography invented')
    return [dict(item,role='geographic_holdout' if i in (1,4) else 'ssl_fit') for i,(item,_) in enumerate(chosen)]


def freeze():
    backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    if sha(PLAN)!=PLAN_SHA or sha(SPLIT)!=SPLIT_SHA:raise ValueError('Frozen geometry/split hash')
    p=json.loads(PLAN.read_bytes());s=json.loads(SPLIT.read_bytes())
    if not p['test_sealed'] or p['split_sha256']!=SPLIT_SHA:raise ValueError('TEST seal')
    aois=windows(p['patches'],s['groups'])
    # Previously examined application regions remain outside the expansion.
    old=json.loads(Path('outputs/phase25/experiments/minemind-cached-v1/metrics.json').read_bytes())
    for row in aois:
        g=transform(Transformer.from_crs(row['crs'],7755,always_xy=True).transform,box(*row['bounds']))
        for app in old['sites'].values():
            h=transform(Transformer.from_crs(app['crs'],7755,always_xy=True).transform,box(*app['bounds']))
            if g.distance(h)<10000:raise ValueError('Application-region exclusion')
    cfg=dict(schema='minemind-geography/1',seed=42,aois=aois,source_manifest_sha256=PLAN_SHA,split_sha256=SPLIT_SHA,
        grid='32x32/30m/native UTM; inner footprint of already guarded1280mTRAIN patch; existing2050m cross-split protection inherited',
        selection='One seed-hash-first eligible patch/state; farthest-first states,>=50km; positions1/4are new geographic holdouts within originalTRAIN; no foreground labels or results used',
        seasons=[['2023-11-01','2024-04-01'],['2024-11-01','2025-04-01']],
        budget=dict(max_requests=40,max_bytes=100000000,response_cap=2000000),
        preprocessing='Existing canonical14bands; descending single-orbit max-min seasonal count tie lowestorbit; paired date-disjoint replica groups; original masks/QA',
        sources=['COPERNICUS/S1_GRD','COPERNICUS/S2_SR_HARMONIZED','COPERNICUS/S2_CLOUD_PROBABILITY','USGS/SRTMGL1_003','ESA/WorldCover/v200/2021'],
        rights='Copernicus research attribution; SRTM NASA/USGS; WorldCoverCCBY4.0. Private rasters, no public data release.',
        context='WorldCover2021historical landcover only; no current agriculture/construction/mining labels',
        expansion_gate='>=4eligible AOIs across>=4states,>=2ssl_fit plus>=1geographic_holdout, and>=3context families with>=25percent coverage; otherwise STOP optimization',
        training='If eligible, frozen checkpoint unchanged; fit adaptive reliability on BEFORE expandedTRAIN only; one fit, fixed formulas; no temporal recovery based on prior failure',
        evaluation='Fixed historical GEO/VAL/TEST unchanged; new holdouts only; same common<=25degree mask for methods; TRAIN99.5percentile cutoff for new methods, no holdout tuning; review raw ranking metrics separately from cutoff areas',
        test_access=False,replacements=False)
    ROOT.mkdir(parents=True,exist_ok=True);save(ROOT/'plan.json',cfg)
    print(json.dumps(dict(states=[r['state'] for r in aois],plan_sha256=sha(ROOT/'plan.json'))))
    return cfg


def inventory(ee,rows):
    from config.phase2_settings import Phase2Config
    from config.settings import BEFORE,AFTER
    from src import optical_preprocessing as optical,sar_preprocessing as sar
    result={}
    for row in rows:
        region=ee.Geometry.Rectangle(row['bounds'],row['crs'],False);cfg=Phase2Config(analysis_crs=row['crs']);seasons=[]
        for season in (BEFORE,AFTER):
            s=sar.collection(region,season,cfg).sort('system:index');o=optical.collections(region,season,cfg)[1].sort('system:index')
            seasons.append(ee.Dictionary(dict(s1=s.aggregate_array('system:index').zip(s.aggregate_array('system:time_start')).zip(s.aggregate_array('relativeOrbitNumber_start')),s2=o.aggregate_array('system:index').zip(o.aggregate_array('system:time_start')))))
        wc=ee.Image('ESA/WorldCover/v200/2021').select('Map').reduceRegion(ee.Reducer.frequencyHistogram(),region,crs=row['crs'],crsTransform=[30,0,row['bounds'][0],0,-30,row['bounds'][3]],maxPixels=4096)
        result[row['id']]=ee.Dictionary(dict(seasons=ee.List(seasons),worldcover=wc))
    return ee.Dictionary(result).getInfo()


def image(ee,row,cfg,sources):
    from config.settings import BEFORE,AFTER
    from src import sar_preprocessing as sar,optical_preprocessing as optical
    from src.change_features import build_stack
    from src.coverage_diagnostics import COUNT_BANDS,validity_image
    from src.phase3.data import BANDS
    region=ee.Geometry.Rectangle(row['bounds'],row['crs'],False);radar=[];opts=[];rc=[];oc=[]
    for season,ids in zip((BEFORE,AFTER),sources):
        r=sar.collection(region,season,cfg).filter(ee.Filter.inList('system:index',[sid for sid,_ in ids['s1']]))
        o=optical.collections(region,season,cfg)[1].filter(ee.Filter.inList('system:index',[sid for sid,_ in ids['s2']]))
        a,n=sar.seasonal(r,cfg.relative_orbit,region,cfg);b,m=optical.seasonal(o,region,cfg);radar.append(a);opts.append(b);rc.append(n);oc.append(m)
    v=ee.Image.cat([radar[0],opts[0],radar[1],opts[1],build_stack(radar[0],radar[1],opts[0],opts[1],region)]).rename(list(BANDS))
    c=ee.Image.cat(rc+oc).rename(list(COUNT_BANDS)).unmask(0,False)
    return ee.Image.cat([v,c,validity_image(v.select(list(BANDS[8:])),c,cfg)]).toFloat().unmask(-9999,False)


def acquire():
    cfg=freeze()
    completed=ROOT/'acquisition.json'
    if completed.exists():
        from scripts.indian_ssl_pilot import read_tile
        result=json.loads(completed.read_bytes())
        if result['plan_sha256']!=sha(ROOT/'plan.json'):raise ValueError('Cached plan mismatch')
        for row in result['accepted']:
            for i in (1,2):
                folder=ROOT/row['id']/f'r{i}';tile=read_tile(folder)
                if tile['bounds']!=row['bounds'] or json.loads((folder/'receipt.json').read_bytes())['plan_sha256']!=result['plan_sha256']:raise ValueError('Cached footprint/provenance mismatch')
        inventory={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name!='cache-integrity.json'}
        save(ROOT/'cache-integrity.json',inventory)
        print(json.dumps(dict(status='REUSED_VERIFIED_CACHE',traffic=result['traffic'],new_requests=0)));return
    from src.phase25.acquisition import MeteredHttp
    from scripts.phase22w_ablation import acquire_lock
    from scripts.indian_ssl_cache import replicas
    from src.sar_preprocessing import choose_orbit
    from config.phase2_settings import Phase2Config
    from scripts.phase6b_multitile import validate_pixels,SCHEMA,DIAGNOSTICS
    from src.phase3.data import BANDS,BAND_UNITS
    from src.phase3.regional_inference import write_tile
    from rasterio.io import MemoryFile
    from affine import Affine
    meter=MeteredHttp(ROOT/'http-ledger.jsonl',**cfg['budget']);lock=acquire_lock(Path('outputs/phase25/receipts/.acquire.lock'));accepted=[];rejected=[]
    try:
        import ee
        from google.oauth2.credentials import Credentials
        from config.settings import project_id
        ee.data.setMaxRetries(0);ee.Initialize(credentials=Credentials(None,**ee.oauth.get_credentials_arguments()),project=project_id(),http_transport=meter)
        meta=ROOT/'inventory.json'
        if meta.exists():raw=json.loads(meta.read_bytes())
        else:raw=inventory(ee,cfg['aois']);save(meta,raw)
        for row in cfg['aois']:
            item=raw[row['id']];seasons=item['seasons'];hist=[]
            for season in seasons:
                h={}
                for _,orbit in season['s1']:h[str(orbit)]=h.get(str(orbit),0)+1
                hist.append(h)
            try:
                orbit=choose_orbit(*hist);pcfg=Phase2Config(analysis_crs=row['crs'],relative_orbit=orbit)
                inv=[dict(s1=[x for x,o in s['s1'] if int(o)==orbit],s2=s['s2']) for s in seasons]
                groups=replicas(inv,pcfg)
            except ValueError as e:
                rejected.append(dict(id=row['id'],reason=str(e)));continue
            results=[]
            for i,scenes in enumerate(groups,1):
                folder=ROOT/row['id']/f'r{i}';folder.mkdir(parents=True,exist_ok=True);rp=folder/'receipt.json'
                if rp.exists():
                    receipt=json.loads(rp.read_bytes())
                    if receipt['scenes']!=scenes or any(sha(folder/n)!=h for n,h in receipt['hashes'].items()):raise ValueError('Cached identity/hash mismatch')
                    results.append(receipt);continue
                g=image(ee,row,pcfg,scenes);affine=Affine(30,0,row['bounds'][0],0,-30,row['bounds'][3])
                url=g.getDownloadURL(dict(format='GEO_TIFF',crs=row['crs'],crs_transform=list(affine)[:6],dimensions=[32,32]))
                response,payload=meter.request(url)
                if response.status!=200:raise RuntimeError('Raster download failed')
                with MemoryFile(payload) as mem,mem.open() as ds:
                    if (ds.crs.to_string(),ds.transform,ds.shape,ds.count)!=(row['crs'],affine,(32,32),len(SCHEMA)) or (any(ds.descriptions) and ds.descriptions!=SCHEMA):raise ValueError('Raster band/grid integrity')
                    a=ds.read();profile=ds.profile
                counts=[len(s[k]) for k in ['s1','s2'] for s in scenes];qa=validate_pixels(a,counts,size=32,cfg=pcfg)
                write_tile(folder/'features.tif',profile,BANDS,a[:14],dict(data_kind='real'),BAND_UNITS);write_tile(folder/'diagnostics.tif',profile,DIAGNOSTICS,a[14:],dict(data_kind='real'))
                receipt=dict(**qa,settings=asdict(pcfg),transform=list(affine)[:6],seasons=[dict(name='2023-24',start='2023-11-01',end='2024-04-01'),dict(name='2024-25',start='2024-11-01',end='2025-04-01')],scenes=scenes,hashes={n:sha(folder/n) for n in ['features.tif','diagnostics.tif']},graph_sha256=hashlib.sha256(g.serialize().encode()).hexdigest(),response_sha256=hashlib.sha256(payload).hexdigest(),plan_sha256=sha(ROOT/'plan.json'))
                save(rp,receipt);results.append(receipt)
            passes=all(r['valid_cells']['common_valid']/1024>=.7 and all(r['valid_cells'][k]/1024>=.9 for k in ['sar_before_valid','sar_after_valid']) for r in results)
            accepted.append(dict(**row,passes=passes,coverage=[r['valid_cells']['common_valid']/1024 for r in results],worldcover=item['worldcover']))
        summary=dict(status='COMPLETED',accepted=accepted,rejected=rejected,traffic=meter.summary(),plan_sha256=sha(ROOT/'plan.json'))
        save(ROOT/'acquisition.json',summary);print(json.dumps(summary))
    except BaseException as e:
        stop=dict(status='STOPPED',error=type(e).__name__,reason=re.sub(r'https?://\S+','[URL]',str(e))[:800],accepted=accepted,rejected=rejected,traffic=meter.summary())
        save(ROOT/f'stop-{len(meter.rows)}.json',stop);print(json.dumps(stop))
    finally:
        lock.unlink(missing_ok=True)
        if sha(PLAN)!=PLAN_SHA or sha(SPLIT)!=SPLIT_SHA:raise ValueError('Historical geometry changed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['plan','acquire']);a=p.parse_args();freeze() if a.command=='plan' else acquire()
