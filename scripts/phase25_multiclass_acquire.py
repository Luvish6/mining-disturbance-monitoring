"""One locked capped context acquisition on frozen development AOIs only."""
import json
from pathlib import Path
import numpy as np
from affine import Affine
from rasterio.io import MemoryFile
from scripts.phase25b_cached import backup_gate,digest,save,guarded
from scripts.phase25b1_recover import fire_graph,cached_json,save_verified
from src.phase25.acquisition import MeteredHttp

CONFIG=Path('outputs/phase25/datasets/multiclass-context-v1/frozen_plan.json')
OUT=Path('outputs/phase25/datasets/multiclass-context-v1')
NAMES=[s+'_'+n for s in ['before','after'] for n in ['crops','built','water','bare','dw_count']]+['burn_before','burn_after','fire_before_count','fire_after_count']


def graph(ee,row,cfg):
    region=ee.Geometry.Rectangle(row['bounds'],'EPSG:32646',False);images=[];info={};burn=[];fire_count=[]
    for s in ['before','after']:
        dates=cfg['seasons'][s]
        c=ee.ImageCollection(cfg['sources']['dynamic_world']).filterBounds(region).filterDate(*dates)
        names=['crops','built','water','bare'];blank=ee.Image.constant([0]*4).rename(names).updateMask(ee.Image.constant(0))
        values=ee.Image(ee.Algorithms.If(c.size().gt(0),c.select(names).median(),blank))
        count=ee.Image(ee.Algorithms.If(c.size().gt(0),c.select('crops').count(),ee.Image.constant(0))).unmask(0)
        images += [values.updateMask(count.gte(2)),count]
        f=ee.ImageCollection(cfg['sources']['fire']).filterBounds(region).filterDate(*dates);b,n=fire_graph(ee,f,*dates);burn.append(b);fire_count.append(n)
        info[s]=dict(dw_ids=c.aggregate_array('system:index'),dw_dates_ms=c.aggregate_array('system:time_start'),fire_ids=f.aggregate_array('system:index'),fire_dates_ms=f.aggregate_array('system:time_start'))
    images+=burn+fire_count
    return ee.Image.cat(images).rename(NAMES).clip(region),info


def validate(raw,row):
    with MemoryFile(raw) as memory,memory.open() as ds:
        if ds.shape!=(64,64) or ds.count!=len(NAMES) or ds.crs.to_string()!='EPSG:32646' or ds.transform!=Affine(30,0,row['bounds'][0],0,-30,row['bounds'][3]):raise ValueError('Acquired grid mismatch')
        if any(ds.descriptions) and list(ds.descriptions)!=NAMES:raise ValueError('Band order mismatch')
        a=ds.read().astype('float32');a[a==-9999]=np.nan
    if np.isinf(a).any():raise ValueError('Infinite context')
    for i,name in enumerate(NAMES):
        z=a[i][np.isfinite(a[i])]
        if name.endswith('count'):
            if np.any(z<0) or np.any(z!=np.floor(z)):raise ValueError('Invalid observation count')
        elif np.any((z<0)|(z>1)):raise ValueError('Invalid probability/burn flag')
    return a


def run():
    cfg=json.loads(CONFIG.read_bytes());backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    from scripts.phase22n_temporal import guards
    area,protected=guards();original=json.loads(Path('docs/reports/phase22x-preregistration.json').read_bytes())['aois']
    for row in cfg['aois']:
        base=original[row['aoi']]
        if row['bounds']!=base['bounds'] or row['split']!=base['split']:raise ValueError('Frozen AOI changed')
        guarded(row['aoi'],base,area,protected)
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'config.sha256').exists():
        if (OUT/'config.sha256').read_text().strip()!=digest(CONFIG):raise ValueError('Acquisition plan changed')
    else:(OUT/'config.sha256').write_text(digest(CONFIG)+'\n')
    from scripts.phase22w_ablation import acquire_lock
    lock=acquire_lock(Path('outputs/phase25/receipts/.acquire.lock'));meter=MeteredHttp(OUT/'http-ledger.jsonl',**cfg['budget'])
    try:
        if all((OUT/r['aoi'].replace(':','_')/'receipt.json').exists() for r in cfg['aois']):
            for r in cfg['aois']:
                p=OUT/r['aoi'].replace(':','_')/'context.tif'
                if digest(p)!=cached_json(p.parent/'receipt.json')['sha256']:raise ValueError('Cached source hash changed')
                validate(p.read_bytes(),r)
            print(__import__('json').dumps(dict(status='REUSED_VERIFIED_CACHE_NO_HTTP',traffic=meter.summary())));return
        import ee
        from google.oauth2.credentials import Credentials
        from config.settings import project_id
        args=ee.oauth.get_credentials_arguments()
        if not args.get('refresh_token'):raise ValueError('Existing explicit GEE credentials required')
        ee.data.setMaxRetries(0);ee.Initialize(credentials=Credentials(None,**args),project=project_id(),http_transport=meter)
        for index in range(0,len(cfg['aois']),4):
            chunk=cfg['aois'][index:index+4];meta=OUT/f'metadata_{index//4}.json'
            if not meta.exists():save_verified(meta,ee.Dictionary({r['aoi']:ee.Dictionary(graph(ee,r,cfg)[1]) for r in chunk}).getInfo())
            values=cached_json(meta)
            if set(values)!={r['aoi'] for r in chunk}:raise ValueError('Missing source identities')
        for i,row in enumerate(cfg['aois']):
            folder=OUT/row['aoi'].replace(':','_');folder.mkdir(exist_ok=True);path=folder/'context.tif'
            if (folder/'receipt.json').exists():
                receipt=cached_json(folder/'receipt.json')
                if digest(path)!=receipt['sha256']:raise ValueError('Cached context hash mismatch')
                validate(path.read_bytes(),row);continue
            image,_=graph(ee,row,cfg);transform=[30,0,row['bounds'][0],0,-30,row['bounds'][3]]
            url=image.toFloat().unmask(-9999,False).getDownloadURL(dict(format='GEO_TIFF',crs='EPSG:32646',crs_transform=transform,dimensions=[64,64]))
            response,raw=meter.request(url)
            if response.status!=200:raise RuntimeError('Context download failed')
            a=validate(raw,row)
            with path.open('xb') as f:f.write(raw)
            save_verified(folder/'receipt.json',dict(sha256=digest(path),aoi=row['aoi'],split=row['split'],bands=NAMES,config_sha256=digest(CONFIG),graph_sha256=__import__('hashlib').sha256(image.serialize().encode()).hexdigest(),valid_by_band={n:int(np.isfinite(a[j]).sum()) for j,n in enumerate(NAMES)},resampling='nearest; native10m DW/500m MODIS support preserved, not independent30m evidence'))
            print(json.dumps(dict(aoi=row['aoi'],smoke=i==0,traffic=meter.summary())),flush=True)
        save_verified(OUT/'completed.json',dict(status='COMPLETED',traffic=meter.summary(),rasters=len(cfg['aois'])))
    except BaseException as exc:
        (OUT/'stopped.json').write_text(json.dumps(dict(status='PARTIAL_OR_BLOCKED',error=type(exc).__name__,traffic=meter.summary()),indent=2));print(json.dumps(dict(status='PARTIAL_OR_BLOCKED',error=type(exc).__name__,traffic=meter.summary())),flush=True)
    finally:lock.unlink(missing_ok=True)


if __name__=='__main__':run()
