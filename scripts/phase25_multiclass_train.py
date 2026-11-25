"""Bounded offline multiclass RF ablations and existing Siamese U-Net adaptation."""
import json,time,random,hashlib
from pathlib import Path
import numpy as np
from src.phase25.multiclass_experiment import *


def unet(data,m,config):
    import torch
    from src.phase3.model import SiameseUNet
    if not torch.cuda.is_available():return [],{'skipped':'CUDA unavailable; bounded RF retained'}
    torch.set_num_threads(1);torch.cuda.set_per_process_memory_fraction(.6,0)
    train=[d for d in data if d['row']['split']=='train'];val=[d for d in data if d['row']['split']=='validation'];bands=m['model_input_bands']
    raw=matrix(train,bands,CORE);mask=frame(train)['valid'];mean=raw[mask].mean(0);std=np.maximum(raw[mask].std(0),1e-6)
    save(OUT/'unet_normalization.json',dict(bands=CORE,mean=mean.tolist(),std=std.tolist(),fit='TRAIN labelled valid pixels only',dataset_inventory_sha256=INTEGRITY))
    for d in data:
        x=d['x'][[bands.index(b) for b in CORE]].copy();x=(x-mean[:,None,None])/std[:,None,None];x=np.nan_to_num(x,nan=0,posinf=0,neginf=0)
        d['input']=torch.from_numpy(x.astype('float32')).unsqueeze(0);d['target']=torch.from_numpy(np.where(d['mask'],d['y'],255).astype('int64')).unsqueeze(0)
    counts=np.bincount(frame(train)['labels'][mask],minlength=3);weights=np.sqrt(counts.max()/counts);weights=np.minimum(weights,10).astype('float32')
    positive=[i for i,d in enumerate(train) if (d['mask']&(d['y']>0)&(d['y']!=255)).any()];background=[i for i,d in enumerate(train) if d['mask'].any() and i not in positive]
    results=[];used=0.;resources={}
    for seed in [42,43]:
        if used>=285:break
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
        model=SiameseUNet(channels=5,width=16);model.head=torch.nn.Conv2d(16,3,1);model=model.cuda();weight=torch.tensor(weights,device='cuda');opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001);rng=np.random.default_rng(seed)
        dest=OUT/f'unet_seed{seed}';dest.mkdir(exist_ok=True)
        if list(dest.iterdir()):raise ValueError('Refusing duplicate/completed U-Net fit')
        history=[];elapsed=0.;interrupted=False;torch.cuda.reset_peak_memory_stats()
        for epoch in range(1,11):
            start=time.monotonic();model.train();losses=[]
            # Every usable TRAIN patch once; append positive patches until >=1:1 positive/background exposures.
            order=positive+background
            if positive and len(positive)<len(background):order+=rng.choice(positive,len(background)-len(positive),replace=True).tolist()
            order=rng.permutation(order)
            for i in order:
                if used+elapsed+time.monotonic()-start>=285:interrupted=True;break
                d=train[i];x=d['input'].cuda();target=d['target'].cuda();opt.zero_grad(set_to_none=True);loss=masked_ce(model(x[:,:5],x[:,5:]),target,weight)
                if not torch.isfinite(loss):raise ValueError('Nonfinite CE')
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step();losses.append(float(loss.detach()))
            torch.cuda.synchronize();elapsed+=time.monotonic()-start
            if interrupted:break
            history.append(dict(epoch=epoch,loss=float(np.mean(losses)),training_seconds=elapsed,patch_exposures=len(order)))
            metadata=dict(schema='mci-multiclass-model/1',channels=5,width=16,outputs=3,class_order=[0,1,4],bands=CORE,normalization_sha256=sha(OUT/'unet_normalization.json'),dataset_inventory_sha256=INTEGRITY,status='NOT_VALIDATED',claim=CLAIM,seed=seed)
            torch.save(dict(state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},metadata=metadata,epoch=epoch),dest/'last_complete.pt')
            print(json.dumps(dict(seed=seed,**history[-1])),flush=True)
        used+=elapsed
        if not history:
            save(dest/'interrupted.json',dict(training_seconds=elapsed,no_completed_epoch=True));break
        # Never evaluate partially updated weights: reload the last complete epoch. No VAL checkpoint selection.
        saved=torch.load(dest/'last_complete.pt',map_location='cuda',weights_only=True);model.load_state_dict(saved['state_dict']);model.eval();prob=[]
        with torch.no_grad():
            for d in val:
                x=d['input'].cuda();prob.append(torch.softmax(model(x[:,:5],x[:,5:]),1)[0].permute(1,2,0).cpu().numpy().reshape(-1,3))
        result=save_result(f'unet_seed{seed}',np.concatenate(prob),val,sha(dest/'last_complete.pt'),dict(kind='multiclass',feature_family='paired B2/B3/B4/VV/VH; no context',seed=seed,epochs=len(history),history=history,training_seconds=elapsed,interrupted=interrupted,class_weights=weights.tolist(),selection='last complete epoch, argmax; no VAL tuning',normalization_sha256=sha(OUT/'unet_normalization.json')))
        results.append(result);resources[str(seed)]=dict(cuda_allocated_bytes=torch.cuda.max_memory_allocated(),cuda_reserved_bytes=torch.cuda.max_memory_reserved());del model,opt;torch.cuda.empty_cache()
    return results,dict(training_seconds=used,resources=resources)


def run():
    from scripts.phase25b_cached import backup_gate
    from sklearn.ensemble import RandomForestClassifier
    import joblib
    backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    m,data=load();train=[d for d in data if d['row']['split']=='train'];val=[d for d in data if d['row']['split']=='validation'];bands=m['model_input_bands'];families=feature_families(bands,train)
    OUT.mkdir(parents=True,exist_ok=False);config=dict(schema='mci-multiclass-experiment/1',claim=CLAIM,taxonomy=CLASSES,internal_to_original=[0,1,4],ignore=255,feature_families=families,rf=dict(n_estimators=100,max_depth=16,min_samples_leaf=2,random_state=42,n_jobs=1,class_weight='balanced'),sampling='TRAIN only; <=600 unique pixels/group; equal class allocation then redistribute available remainder; no replacement; same indices all ablations',unet=dict(seeds=[42,43],epochs=10,combined_training_cap_seconds=285,lr=.0003,loss='masked class-weighted CE; sqrt inverse TRAIN frequency capped10',batch_size=1,checkpoint='last complete epoch; no VAL selection',decision='argmax',normalization='TRAIN-only',sampling='all usable TRAIN patches once; positive-bearing oversampling to at least1:1'),selection='highest VAL macro-F1 among frozen completed experiments; selection-biased agreement, no retraining',annotation_dependence='Persistent/transient labels use 2025-26 follow-up unavailable to model; retrospective classification, NOT prospective early warning',forbidden_inputs=m['annotation_only_bands']+m['quality_only_bands']+['evidence_scores','confidence','uncertainty','weak_labels'])
    save(OUT/'frozen_config.json',config);tf=frame(train);vf=frame(val);indices=sample_indices(train,cap=600*len(set(tf['groups'])))
    np.savez_compressed(OUT/'sampling.npz',training_pixel_ids=tf['pixel_ids'][indices],validation_pixel_ids=vf['pixel_ids'],validation_mask=vf['valid'],validation_labels=vf['labels'])
    support={split:dict(patches=len(ds),groups=len(set(frame(ds)['groups'])),valid_pixels=int(frame(ds)['valid'].sum()),class_counts=np.bincount(frame(ds)['labels'][frame(ds)['valid']],minlength=3).tolist(),positive_groups={str(o):sorted(set(frame(ds)['groups'][frame(ds)['valid']&(frame(ds)['labels']==i)])) for i,o in enumerate(CLASSES)}) for split,ds in [('train',train),('validation',val)]}
    save(OUT/'support.json',support);save(OUT/'sampling.json',dict(unique_pixels=len(indices),class_counts=np.bincount(tf['labels'][indices],minlength=3).tolist(),per_group={g:int((tf['groups'][indices]==g).sum()) for g in sorted(set(tf['groups']))},validation_identity_sha256=hashlib.sha256(vf['pixel_ids'].tobytes()+vf['valid'].tobytes()+vf['labels'].tobytes()).hexdigest()))
    results=[]
    for family,names in families.items():
        start=time.monotonic();x=matrix(train,bands,names);v=matrix(val,bands,names);median=fit_preprocessing(x,indices);model=RandomForestClassifier(**config['rf']);model.fit(impute(x[indices],median),tf['labels'][indices]);dest=OUT/('rf_'+family);dest.mkdir();joblib.dump(dict(model=model,features=names,median=median,config_sha256=sha(OUT/'frozen_config.json'),class_order=[0,1,4],status='NOT_VALIDATED'),dest/'model.joblib');prob=model.predict_proba(impute(v,median));result=save_result('rf_'+family,prob,val,sha(dest/'model.joblib'),dict(kind='multiclass',feature_names=names,training_seconds=time.monotonic()-start,preprocessing_medians=median.tolist(),training_samples=len(indices)));results.append(result);print(family,json.dumps(result['validation']['pooled']),flush=True)
    baseline=score(vf,np.zeros(len(vf['labels']),np.uint8),val)
    save(OUT/'baselines.json',dict(constant_train_majority=baseline,frozen_rule=dict(status='NOT_COMPARABLE',reason='Frozen multiclass rule is the annotation generator and requires future follow-up; self-agreement is tautological, not a predictive benchmark. No teacher outputs used as inputs.')))
    extra,gpu=unet(data,m,config);results+=extra
    # Every run must have exactly the same evaluation population.
    with np.load(OUT/results[0]['id']/'validation_predictions.npz') as z:reference={k:z[k] for k in ['labels','valid','groups','pixel_ids']}
    for result in results:
        with np.load(OUT/result['id']/'validation_predictions.npz') as z:
            if any(not np.array_equal(z[k],v) for k,v in reference.items()):raise ValueError('Evaluation sample mismatch')
    best=max(results,key=lambda r:r['validation']['pooled']['macro_f1']);save(OUT/'summary.json',dict(claim=CLAIM,status='NOT_VALIDATED',operational_alerts=0,selected_experiment=best['id'],selection_bias='VAL selection among prespecified models, no independent accuracy',support=support,results=results,gpu=gpu,config_sha256=sha(OUT/'frozen_config.json'),source_inventory_sha256=INTEGRITY,retrospective=config['annotation_dependence']))
    print('SELECTED',best['id'],json.dumps(best['validation']['pooled']),flush=True)


def resume_unet():
    # Compatibility failure occurred before any optimizer step; preserve completed RF fits.
    m,data=load();config=json.loads((OUT/'frozen_config.json').read_bytes());val=[d for d in data if d['row']['split']=='validation']
    if (OUT/'summary.json').exists():raise ValueError('Experiment already complete')
    save(OUT/'cuda_ce_compatibility.json',dict(failure='CUDA nll_loss2d rejects strict deterministic mode before first optimizer step',correction='Equivalent valid-pixel weighted log-softmax/gather CE; unchanged loss/settings',prior_optimizer_steps=0,prior_completed_epochs=0))
    results=[]
    for family in ['optical','sar','fused']:
        dest=OUT/('rf_'+family);r=json.loads((dest/'metrics.json').read_bytes())
        if sha(dest/'model.joblib')!=r['checkpoint_sha256']:raise ValueError('RF checkpoint changed')
        results.append(dict(id='rf_'+family,**r))
    extra,gpu=unet(data,m,config);results+=extra
    with np.load(OUT/results[0]['id']/'validation_predictions.npz') as z:reference={k:z[k] for k in ['labels','valid','groups','pixel_ids']}
    for result in results:
        with np.load(OUT/result['id']/'validation_predictions.npz') as z:
            if any(not np.array_equal(z[k],v) for k,v in reference.items()):raise ValueError('Evaluation sample mismatch')
        # Regenerate only geospatial exports with the full common-input validity mask.
        with np.load(OUT/result['id']/'validation_predictions.npz') as z:prob=z['probabilities']
        write_predictions(data=val,prob=prob,dest=OUT/result['id']/'predictions_common_support',model_hash=result['checkpoint_sha256'])
    best=max(results,key=lambda r:r['validation']['pooled']['macro_f1']);save(OUT/'summary.json',dict(claim=CLAIM,status='NOT_VALIDATED',operational_alerts=0,selected_experiment=best['id'],selection_bias='VAL selection among prespecified models; not independent accuracy',support=json.loads((OUT/'support.json').read_bytes()),results=results,gpu=gpu,config_sha256=sha(OUT/'frozen_config.json'),source_inventory_sha256=INTEGRITY,retrospective=config['annotation_dependence']))
    print('SELECTED',best['id'],json.dumps(best['validation']['pooled']),flush=True)

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--resume-unet']:resume_unet()
    elif not sys.argv[1:]:run()
    else:raise ValueError('Unknown arguments')
