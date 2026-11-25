"""Add frozen multiclass VAL-only snapshots without replacing historical models."""
import json
from pathlib import Path
import numpy as np
import rasterio
from scripts.phase25_model_portal import CACHE, png
from src.phase25.dataset import sha
from src.phase25.multiclass_experiment import ROOT, OUT, load, CLASSES

NEW_CACHE=Path('outputs/phase25/experiments/25e4-portal-v2')


def export():
    m,data=load();summary=json.loads((OUT/'summary.json').read_bytes());old=json.loads((CACHE/'integrity.json').read_bytes());assets={}
    for name,digest in old.items():
        p=(CACHE/name).resolve()
        if not p.is_relative_to(CACHE.resolve()) or sha(p)!=digest:raise ValueError('Historical snapshot integrity')
        assets[name]=p.read_bytes()
    payload=json.loads(assets['snapshot.json']);val=[d for d in data if d['row']['split']=='validation'];bands=m['model_input_bands']
    if summary['source_inventory_sha256']!=sha(ROOT/'integrity.json') or summary['status']!='NOT_VALIDATED' or summary['operational_alerts']!=0:raise ValueError('Model source/status mismatch')
    reference=None
    for result in summary['results']:
        name='multiclass_'+result['id'];run=OUT/result['id'];checkpoint=run/('model.joblib' if result['id'].startswith('rf_') else 'last_complete.pt')
        if sha(checkpoint)!=result['checkpoint_sha256']:raise ValueError('Model checkpoint mismatch')
        with np.load(run/'validation_predictions.npz',allow_pickle=False) as z:
            current={k:z[k].copy() for k in ['labels','valid','pixel_ids','groups']};prob=z['probabilities'].copy()
        if reference is None:reference=current
        if any(not np.array_equal(reference[k],v) for k,v in current.items()):raise ValueError('VAL identity/mask mismatch')
        patches=[]
        for i,d in enumerate(val):
            row=d['row'];pid=row['patch_id'];stem=name+'/'+pid;path=run/'predictions_common_support'/(pid+'.tif')
            if not path.exists():path=run/'georeferenced_predictions'/(pid+'.tif')
            with rasterio.open(path) as ds:
                a=ds.read();support=ds.read(1)!=ds.nodata
                if ds.shape!=(32,32) or ds.crs.to_string()!=row['crs'] or list(ds.transform)[:6]!=row['affine'] or ds.tags().get('model_validation_status')!='NOT_VALIDATED':raise ValueError('Multiclass prediction grid/status mismatch')
            expected=prob[i*1024:(i+1)*1024].reshape(32,32,3)
            if not np.array_equal(support,d['input_valid']) or not np.allclose(a[:3].transpose(1,2,0)[support],expected[support]) or not np.isfinite(a[:,support]).all() or not np.allclose(a[:3,:, :].sum(0)[support],1,atol=1e-5):raise ValueError('Prediction support/probability mismatch')
            predicted=np.array([0,1,4])[expected.argmax(2)]
            if not np.array_equal(a[3][support],predicted[support]):raise ValueError('Class/probability mismatch')
            for season in ['before','after']:
                rgb=np.stack([d['x'][bands.index(season+'_'+b)] for b in ['B4','B3','B2']],-1);assets[stem+'_'+season+'.png']=png(np.clip(rgb/.3,0,1),np.isfinite(rgb).all(2))
            palette=np.array([[.45,.5,.55],[1.,.7,.15],[.1,.85,.9]])
            assets[stem+'_binary.png']=png(palette[expected.argmax(2)],support)
            t=expected.max(2);assets[stem+'_probability.png']=png(np.stack([t,.2+.6*t,1-t],-1),support)
            assets[stem+'_weak.png']=png(palette[np.minimum(d['y'],2)],d['mask'])
            patches.append(dict(id=pid,group=row['group_id'],split='validation',crs=row['crs'],bounds=row['bounds'],affine=row['affine'],shape=[32,32],assets={k:stem+'_'+k+'.png' for k in ['before','after','binary','probability','weak']},source_feature_sha256=sha(ROOT/row['output_folder']/'observations.tif'),source_provenance_sha256=sha(ROOT/'manifest.json'),prediction_sha256=sha(path),support=int(support.sum()),evaluated_cells=int(d['mask'].sum()),predicted_cells=int((support&(predicted!=0)).sum()),class_counts={str(c):int((support&(predicted==c)).sum()) for c in CLASSES}))
        payload['data']['models'].append(dict(id=name,kind='multiclass',metrics={},multiclass_metrics=result['validation'],checkpoint_sha256=result['checkpoint_sha256'],patches=patches,features=result.get('feature_names',result.get('feature_family')),normalization_sha256=result.get('normalization_sha256')))
    payload['data']['multiclass_majority_macro_f1']=json.loads((OUT/'baselines.json').read_bytes())['constant_train_majority']['pooled']['macro_f1'];payload['data']['default_model']='multiclass_'+summary['selected_experiment'];payload['data']['limitations']+=' Multiclass is retrospective: persistent/transient targets depend on 2025-26 follow-up excluded from all inputs. Stable / persistent unattributed exposure / other transient are weak classes, not mining causes. VAL model selection is selection-biased. RF context has coarse temporal/spatial fidelity; U-Net uses paired B2/B3/B4/VV/VH and remains temporally symmetric.'
    payload['sha256']=sha(OUT/'summary.json');assets['snapshot.json']=json.dumps(payload,allow_nan=False).encode('utf-8');NEW_CACHE.mkdir(parents=True,exist_ok=False)
    for name,value in assets.items():
        p=NEW_CACHE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
    (NEW_CACHE/'integrity.json').write_text(json.dumps({n:sha(NEW_CACHE/n) for n in assets},indent=2)+'\n',encoding='utf-8')
    print('Saved private multiclass snapshot',len(summary['results']),'new models; historical models preserved')


if __name__=='__main__':export()
