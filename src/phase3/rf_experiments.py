"""Standalone 100-tree RF ablations on one frozen common-valid spatial dataset."""
import argparse
import json
import pickle
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window
import sklearn
from sklearn.ensemble import RandomForestClassifier
from config.phase2_settings import ABLATIONS
from .data import FEATURES,BANDS,read_manifest,digest,save_json
from .evaluate import metrics


def indices(experiment):
    return [FEATURES.index(name) for name in ABLATIONS[experiment]]


def samples(manifest,split,cap=None,seed=42):
    m=read_manifest(manifest,require_splits=True)
    records=[r for r in m['records'] if r['split']==split]
    count=sum(m['counts'][split]); rng=np.random.default_rng(seed)
    selected=np.sort(rng.choice(count,min(cap,count),replace=False)) if cap else None
    xs,ys,ids,blocks=[],[],[],[]; offset=0
    for r in records:
        with np.load(Path(manifest).parent/r['path']) as z:
            flat=np.flatnonzero(z['mask']); n=len(flat)
            local=np.arange(n) if selected is None else selected[(selected>=offset)&(selected<offset+n)]-offset
            if len(local):
                xs.append(z['features'].reshape(6,-1)[:,flat[local]].T)
                ys.append(z['label'].ravel()[flat[local]])
                ids.extend(f"{r['path']}:{p}" for p in flat[local]); blocks.extend([r['block']]*len(local))
            offset+=n
    if not xs: raise ValueError('No valid supervised pixels')
    return np.concatenate(xs),np.concatenate(ys),np.array(ids),np.array(blocks)


def fit(manifest,output,seed=42,max_train_pixels=100000,synthetic_smoke=False):
    if max_train_pixels<2: raise ValueError('Training cap must allow both classes')
    m=read_manifest(manifest,require_splits=True)
    if (m['data_kind']=='synthetic')!=synthetic_smoke:
        raise ValueError('Synthetic fixtures require --synthetic-smoke; real mode requires real evidence')
    x,y,ids,_=samples(manifest,'train',max_train_pixels,seed)
    if len(np.unique(y))!=2: raise ValueError('Pixel cap removed a class; increase cap')
    vx,vy,vids,vblocks=samples(manifest,'validation')
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    config=dict(n_estimators=100,max_depth=16,min_samples_leaf=2,class_weight='balanced',random_state=seed,n_jobs=1)
    result=dict(schema=1,manifest_sha256=digest(manifest),data_kind=m['data_kind'],seed=seed,
                feature_schema=list(FEATURES),config=config,sklearn_version=sklearn.__version__,
                threshold=.5,threshold_policy='fixed before held-out evaluation',
                train_pixels=len(y),validation_pixels=len(vy),train_class_counts=np.bincount(y,minlength=2).tolist(),
                experiments={},selection_partition='validation',test_used_for_selection=False)
    for name,bands in ABLATIONS.items():
        model=RandomForestClassifier(**config); model.fit(x[:,indices(name)],y)
        probability=model.predict_proba(vx[:,indices(name)])[:,list(model.classes_).index(1)]
        metadata=dict(experiment=name,features=list(bands),manifest_sha256=digest(manifest),config=config,data_kind=m['data_kind'])
        file=output/f'{name}.pkl'
        with file.open('xb') as stream: pickle.dump(dict(model=model,metadata=metadata),stream)
        result['experiments'][name]=dict(features=list(bands),artifact=file.name,sha256=digest(file),
                                          validation=metrics(vy,probability))
    result['selected_experiment']=max(ABLATIONS,key=lambda name:result['experiments'][name]['validation']['classes'][1]['f1'] or 0)
    save_json(output/'run.json',result)
    save_json(output/'reference_provenance.json',m.get('label_provenance',[]))
    np.savez_compressed(output/'selection_pixels.npz',train_ids=ids,validation_ids=vids,validation_blocks=vblocks)
    return result


def load_model(run,name):
    run=Path(run); metadata=json.loads((run/'run.json').read_text()); entry=metadata['experiments'][name]
    if entry['features']!=list(ABLATIONS[name]): raise ValueError('Feature-order mismatch')
    path=run/entry['artifact']
    if path.resolve().parent!=run.resolve() or digest(path)!=entry['sha256']:
        raise ValueError('Model artifact integrity failure')
    # Locally created trusted artifacts only; checksums do not make foreign pickle safe.
    with path.open('rb') as stream: artifact=pickle.load(stream)
    if (artifact['metadata']['features']!=entry['features']
            or artifact['metadata']['manifest_sha256']!=metadata['manifest_sha256']):
        raise ValueError('Model metadata mismatch')
    return artifact['model'],metadata


def evaluate(manifest,run,output):
    m=read_manifest(manifest,require_splits=True)
    meta=json.loads((Path(run)/'run.json').read_text())
    if digest(manifest)!=meta['manifest_sha256']: raise ValueError('Frozen dataset changed')
    x,y,ids,blocks=samples(manifest,'test')
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    result=dict(data_kind=m['data_kind'],partition='test',selection_partition='validation',
                test_pixels=len(y),test_class_counts=np.bincount(y,minlength=2).tolist(),
                train_pixels=meta['train_pixels'],validation_pixels=meta['validation_pixels'],
                independent_test_blocks=len(np.unique(blocks)),experiments={},
                exclusions=m['quality'],manifest_sha256=digest(manifest),
                uncertainty_note='A single spatial holdout; few independent blocks limit generalization. RF scores are uncalibrated.')
    probabilities={}
    for name in ABLATIONS:
        model,_=load_model(run,name)
        p=model.predict_proba(x[:,indices(name)])[:,list(model.classes_).index(1)]
        probabilities[name]=p
        result['experiments'][name]=dict(features=list(ABLATIONS[name]),overall=metrics(y,p,meta['threshold']),
            per_block={b:metrics(y[blocks==b],p[blocks==b],meta['threshold']) for b in np.unique(blocks)})
    result['selected_experiment']=meta['selected_experiment']
    result['fusion_f1_differences']={name:result['experiments']['fused']['overall']['classes'][1]['f1']-
        result['experiments'][name]['overall']['classes'][1]['f1'] for name in ('sar','optical')}
    save_json(output/'evaluation.json',result)
    np.savez_compressed(output/'common_test_pixels.npz',ids=ids,label=y,blocks=blocks,**probabilities)
    return result


def map_tile(raster,run,output,experiment=None,evaluation=None):
    """Bounded whole-tile RF map including valid unlabeled pixels."""
    meta=json.loads((Path(run)/'run.json').read_text()); experiment=experiment or meta['selected_experiment']
    model,_=load_model(run,experiment); output=Path(output)
    if output.exists(): raise ValueError('Refusing to overwrite map')
    with rasterio.open(raster) as src:
        if (tuple(src.descriptions)!=BANDS or src.crs is None or src.crs.to_epsg()!=32646
                or src.transform.a!=30 or src.transform.e!=-30 or src.transform.b or src.transform.d
                or src.width*src.height>4_000_000):
            raise ValueError('Expected bounded aligned 30 m paired input')
        if src.tags().get('data_kind')!=meta['data_kind']: raise ValueError('Real/synthetic identity mismatch')
        if meta['data_kind']=='real':
            if evaluation is None: raise ValueError('Real mapping requires a held-out evaluation receipt')
            receipt=json.loads(Path(evaluation).read_text())
            if (receipt.get('data_kind')!='real' or receipt.get('partition')!='test'
                    or receipt.get('manifest_sha256')!=meta['manifest_sha256']
                    or set(receipt.get('experiments',{}))!=set(ABLATIONS)):
                raise ValueError('Held-out evaluation does not match this real run')
            from .admission import validate_real_manifest
            frozen=dict(resolution_m=30,crs=str(src.crs),raster_metadata=src.tags(),
                        label_provenance=json.loads((Path(run)/'reference_provenance.json').read_text()))
            validate_real_manifest(frozen)
        profile=src.profile.copy(); profile.update(driver='GTiff',count=4,dtype='float32',nodata=-9999)
        output.parent.mkdir(parents=True,exist_ok=True)
        with rasterio.open(output,'w',**profile) as dst:
            for row in range(0,src.height,128):
                for col in range(0,src.width,128):
                    window=Window(col,row,min(128,src.width-col),min(128,src.height-row))
                    x=src.read(window=window); valid=(src.read_masks(window=window)>0)&np.isfinite(x)
                    common=valid.all(axis=0); p=np.full(common.shape,-9999,dtype='float32')
                    if common.any(): p[common]=model.predict_proba(x[8:][indices(experiment)][:,common].T)[:,list(model.classes_).index(1)]
                    entropy=np.full(common.shape,-9999,dtype='float32')
                    q=np.clip(p[common],1e-7,1-1e-7); entropy[common]=-(q*np.log2(q)+(1-q)*np.log2(1-q))
                    dst.write(np.stack([p,np.where(common,p>=meta['threshold'],-9999),common.astype('float32'),entropy]).astype('float32'),window=window)
            dst.descriptions=('disturbance_probability','disturbance_binary','common_valid','predictive_entropy')
            dst.update_tags(data_kind=meta['data_kind'],experiment=experiment,feature_order=','.join(ABLATIONS[experiment]),
                interpretation='Screening for mining-related disturbance; not confirmed illegality',
                uncertainty='Entropy of uncalibrated RF scores; not an empirical confidence interval',model_sha256=meta['experiments'][experiment]['sha256'])
    return str(output)


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    t=sub.add_parser('fit'); t.add_argument('manifest');t.add_argument('output');t.add_argument('--seed',type=int,default=42)
    t.add_argument('--max-train-pixels',type=int,default=100000);t.add_argument('--synthetic-smoke',action='store_true')
    e=sub.add_parser('evaluate');e.add_argument('manifest');e.add_argument('run');e.add_argument('output')
    e=sub.add_parser('map');e.add_argument('raster');e.add_argument('run');e.add_argument('output');e.add_argument('--experiment',choices=list(ABLATIONS))
    e.add_argument('--evaluation')
    a=vars(p.parse_args());c=a.pop('command');{'fit':fit,'evaluate':evaluate,'map':map_tile}[c](**a)


if __name__=='__main__': main()
