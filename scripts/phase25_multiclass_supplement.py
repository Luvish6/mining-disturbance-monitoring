"""Spend remaining original quota on TRAIN-only competing-context windows, not class quotas."""
import json,math,hashlib
from pathlib import Path
from shapely.geometry import box
from scripts.phase25_multiclass_acquire import CONFIG,OUT,graph,NAMES
from scripts.phase25b_cached import guarded,digest
from scripts.phase25b1_recover import save_verified
from src.phase25.acquisition import MeteredHttp
from scripts.phase22w_ablation import acquire_lock

def run():
    cfg=json.loads(CONFIG.read_bytes())
    from scripts.phase22n_temporal import guards
    area,protected=guards();occupied=[box(*r['bounds']) for r in cfg['aois']];windows=[]
    for r in cfg['aois']:
        if r['split']!='train':continue
        bx,by=map(int,r['aoi'].split(':'));candidates=[]
        for x in range(math.ceil((bx*5000+120)/30)*30,(bx+1)*5000-120-960+1,960):
            for y in range(math.ceil((by*5000+120)/30)*30,(by+1)*5000-120-960+1,960):
                bounds=[x,y,x+960,y+960];g=box(*bounds)
                if any(g.distance(old)<120 for old in occupied):continue
                row=dict(aoi=r['aoi'],split='train',bounds=bounds)
                try:guarded(r['aoi'],row,area,protected)
                except ValueError:continue
                candidates.append(row)
        if candidates:
            chosen=min(candidates,key=lambda r:hashlib.sha256(('42:SUP:'+str(r['bounds'])).encode()).hexdigest());windows.append(chosen)
    plan=OUT/'supplement_plan.json'
    payload=dict(base_config_sha256=digest(CONFIG),windows=windows,selection='One hash-ordered eligible non-overlapping960m window per original TRAIN block; rank crop-context/built-gain counts TRAIN-only, ties by block; at most3context downloads; no dataset admission without paired sensor provenance',budget='Same persistent60request/100MB ledger, no reset')
    if plan.exists():
        if json.loads(plan.read_bytes())!=payload:raise ValueError('Supplement plan changed')
    else:save_verified(plan,payload)
    meter=MeteredHttp(OUT/'http-ledger.jsonl',**cfg['budget'])
    if cfg['budget']['max_requests']-len(meter.rows)<5:raise RuntimeError('Remaining quota cannot cover initialization plus one screened request; no HTTP sent')
    lock=acquire_lock(Path('outputs/phase25/receipts/.acquire.lock'))
    try:
        import ee
        from google.oauth2.credentials import Credentials
        from config.settings import project_id
        args=ee.oauth.get_credentials_arguments();ee.data.setMaxRetries(0);ee.Initialize(credentials=Credentials(None,**args),project=project_id(),http_transport=meter)
        graphs={};metadata={}
        for row in windows:
            image,info=graph(ee,row,cfg);region=ee.Geometry.Rectangle(row['bounds'],'EPSG:32646',False)
            crop=image.select('before_crops').gte(.6).And(image.select('after_crops').gte(.6)).rename('crop_context_cells')
            built=image.select('before_built').lte(.2).And(image.select('after_built').gte(.6)).rename('built_gain_context_cells')
            stats=ee.Image.cat([crop,built]).reduceRegion(ee.Reducer.sum(),region,crs='EPSG:32646',crsTransform=[30,0,row['bounds'][0],0,-30,row['bounds'][3]],maxPixels=4096)
            graphs[row['aoi']]=image;metadata[row['aoi']]=ee.Dictionary(dict(stats=stats,source_ids=info))
        meta_path=OUT/'supplement_screen.json'
        if meta_path.exists():data=json.loads(meta_path.read_bytes())
        else:data=ee.Dictionary(metadata).getInfo();save_verified(meta_path,data)
        selected=sorted(windows,key=lambda r:(-sum(float(x or 0) for x in data[r['aoi']]['stats'].values()),r['aoi']))[:3]
        receipts=[]
        for row in selected:
            key=row['aoi'];folder=OUT/'supplement'/key.replace(':','_');folder.mkdir(parents=True,exist_ok=True);p=folder/'context.tif'
            if not p.exists():
                image=graphs[key];url=image.toFloat().unmask(-9999,False).getDownloadURL(dict(format='GEO_TIFF',crs='EPSG:32646',crs_transform=[30,0,row['bounds'][0],0,-30,row['bounds'][3]],dimensions=[32,32]));response,raw=meter.request(url)
                if response.status!=200:raise ValueError('Supplement request failed')
                from rasterio.io import MemoryFile
                from affine import Affine
                with MemoryFile(raw) as m,m.open() as ds:
                    if ds.shape!=(32,32) or ds.count!=len(NAMES) or ds.crs.to_string()!='EPSG:32646' or ds.transform!=Affine(30,0,row['bounds'][0],0,-30,row['bounds'][3]):raise ValueError('Supplement grid failed')
                with p.open('xb') as f:f.write(raw)
            receipt=dict(**row,sha256=digest(p),screen=data[key]['stats'],dataset_admission='NOT_ADMITTED: context-only, no new paired SAR/optical/follow-up stack; not additional model patches')
            save_verified(folder/'receipt.json',receipt);receipts.append(receipt)
        save_verified(OUT/'supplement_summary.json',dict(status='COMPLETED_CONTEXT_SCREEN_ONLY',screened_windows=len(windows),acquired_context_windows=receipts,traffic=meter.summary()))
        print(json.dumps(dict(screened=len(windows),acquired=receipts,traffic=meter.summary()),indent=2))
    except BaseException as exc:
        (OUT/'supplement_stopped.json').write_text(json.dumps(dict(error=type(exc).__name__,message=__import__('re').sub(r'https?://\S+','[URL]',str(exc))[:1200],traffic=meter.summary()),indent=2));print(json.dumps(dict(status='STOPPED_WITHOUT_QUOTA_INCREASE',error=type(exc).__name__,message=__import__('re').sub(r'https?://\S+','[URL]',str(exc))[:1200],traffic=meter.summary())))
    finally:lock.unlink(missing_ok=True)

if __name__=='__main__':run()
