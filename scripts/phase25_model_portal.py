"""Private static VAL-only experimental model snapshots; no inference endpoint."""
import io,json
from pathlib import Path
import numpy as np
import rasterio
from PIL import Image
from src.phase25.dataset import load_manifest,BANDS,sha

PREFIX='/__experimental__/'
CACHE=Path('outputs/phase25/experiments/25e3-portal-v2')


def png(rgb,valid):
    rgb=np.clip(np.nan_to_num(rgb)*255,0,255).astype('uint8');a=np.dstack([rgb,valid.astype('uint8')*255]);b=io.BytesIO();Image.fromarray(a).save(b,format='PNG');return b.getvalue()


def export():
    from scripts.phase25_unet_recovery import BASE,OUT
    root=Path('outputs/phase25/datasets/25c2-v1');m=load_manifest(root);rows=[r for r in m['patches'] if r['split']=='validation']
    if len(rows)!=12:raise ValueError('Frozen12VALpatches required')
    summary=json.loads((OUT/'summary.json').read_bytes());base=json.loads((BASE/'seed_42/metrics.json').read_bytes())
    runs=[('original_seed42',BASE/'seed_42',{'0.5':base['validation']},base['checkpoint_sha256'])]+[(r['id'],OUT/r['id'],r['metrics'],r['checkpoint_sha256']) for r in summary['results']]
    assets={};models=[]
    with np.load(BASE/'seed_42/validation_predictions.npz') as z:reference={k:z[k] for k in ['pixel_ids','labels','valid','group_ids']}
    for name,run,metrics,checkpoint_hash in runs:
        if sha(run/'best.pt')!=checkpoint_hash:raise ValueError('Checkpoint provenance mismatch')
        with np.load(run/'validation_predictions.npz') as z:
            if any(not np.array_equal(z[k],v) for k,v in reference.items()):raise ValueError('Validation identity/mask mismatch')
        patches=[]
        for row in rows:
            pid=row['patch_id'];pred=run/'georeferenced_predictions'/(pid+'.tif')
            with rasterio.open(pred) as ds:
                if ds.crs.to_string()!=row['crs'] or list(ds.transform)[:6]!=row['affine'] or ds.shape!=(32,32) or ds.tags().get('model_validation_status')!='NOT_VALIDATED':raise ValueError('Prediction grid/status mismatch')
                probability=ds.read(1);binary=ds.read(2);support=probability!=ds.nodata
            if not np.isfinite(probability[support]).all() or np.any((probability[support]<0)|(probability[support]>1)) or not np.array_equal(binary[support],(probability[support]>=.5).astype('float32')):raise ValueError('Invalid fixed-cutoff prediction')
            with rasterio.open(root/row['files']['features']) as ds:
                x=ds.read();x=np.where(x==ds.nodata,np.nan,x)
            stem=name+'/'+pid
            for season in ['before','after']:
                rgb=np.stack([x[BANDS.index(season+'_'+b)] for b in ['B4','B3','B2']],-1);valid=np.isfinite(rgb).all(2)
                assets[stem+'_'+season+'.png']=png(np.clip(rgb/.3,0,1),valid)
            t=np.clip(probability,0,1)
            assets[stem+'_probability.png']=png(np.stack([t,.2+.6*t,1-t],-1),support)
            assets[stem+'_binary.png']=png(np.broadcast_to([1.,.7,.15],(32,32,3)),support&(probability>=.5))
            patches.append(dict(id=pid,group=row['group_id'],split='validation',crs=row['crs'],bounds=row['bounds'],affine=row['affine'],shape=[32,32],assets={k:stem+'_'+k+'.png' for k in ['before','after','probability','binary']},source_feature_sha256=sha(root/row['files']['features']),source_provenance_sha256=sha(root/row['provenance']),prediction_sha256=sha(pred),support=int(support.sum()),predicted_cells=int((support&(probability>=.5)).sum())))
        models.append(dict(id=name,metrics=metrics,checkpoint_sha256=checkpoint_hash,patches=patches))
    payload=dict(data=dict(models=models,default_model=summary['selected_research_candidate'] or 'original_seed42',status='NOT_VALIDATED',label_kind='ALGORITHM_PSEUDO_LABEL_NOT_REFERENCE',operational_alerts=0,threshold=.5,windows=[['2023-11-01','2024-04-01'],['2024-11-01','2025-04-01']],limitations='Agreement with unverified algorithm pseudo-labels, not mining accuracy. VAL was previously used for baseline selection. Probability is uncalibrated. Source scene identities remain incomplete. No live inference or operational alerts.',attribution='Copernicus Sentinel-1/2; private local research snapshot'),sha256=sha(OUT/'summary.json'))
    assets['snapshot.json']=json.dumps(payload,allow_nan=False).encode()
    CACHE.mkdir(parents=True,exist_ok=False)
    for name,data in assets.items():
        p=CACHE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    (CACHE/'integrity.json').write_text(json.dumps({name:sha(CACHE/name) for name in assets},indent=2))
    print('Private experimental snapshot',len(models),'models',len(rows),'VAL patches each')


def experimental_files(root):
    new=Path(root)/'outputs/phase25/experiments/25e4-portal-v2'
    cache=new if new.exists() else Path(root)/CACHE
    if not (cache/'integrity.json').is_file():return {}
    receipt=json.loads((cache/'integrity.json').read_bytes());files={}
    for name,digest in receipt.items():
        p=(cache/name).resolve()
        if not p.is_relative_to(cache.resolve()) or p.suffix not in ['.png','.json'] or sha(p)!=digest:raise ValueError('Experimental snapshot integrity failure')
        files[name]=('application/json' if p.suffix=='.json' else 'image/png',p.read_bytes())
    data=json.loads(files['snapshot.json'][1])['data']
    if data['status']!='NOT_VALIDATED' or data['label_kind']!='ALGORITHM_PSEUDO_LABEL_NOT_REFERENCE' or data['threshold']!=.5 or data['operational_alerts']!=0 or any(p['split']!='validation' for m in data['models'] for p in m['patches']):raise ValueError('Experimental evidence/partition gate')
    return files


if __name__=='__main__':export()
