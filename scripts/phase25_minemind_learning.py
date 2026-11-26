"""One bounded offline TRAIN-only temporal/reliability experiment; no TEST or acquisition."""
import copy, json, time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from scipy.stats import spearmanr
from scripts.indian_ssl_pilot import Encoder, verify, eligible, compare, load
from scripts.phase25_minemind import BASE, candidates, save
from scripts.phase25b_cached import backup_gate
from src.phase25.dataset import sha
from src.phase25.minemind_learning import views, fit_reliability, score
from src.phase3.regional_inference import write_tile, NODATA

OUT=Path('outputs/phase25/experiments/minemind-learning-v1')
CONFIG=dict(seed=42,epochs=5,batch_size=512,lr=.001,threads=2,fit_wall_cap_seconds=120,
    configurations=['frozen_adaptive','temporal_uniform','temporal_adaptive'],
    loss='masked cross-sensor Huber + 0.25*TRAIN paired-difference Huber; random sensor-view dropout',
    reliability='TRAIN BEFORE latent SD floor0.05, cross-reconstruction median MSE floor0.05, observation count saturation; weighted sensor distance avoids vector cancellation',
    cutoff='TRAIN temporal score quantile0.995; no VAL/site tuning',
    separation='4TRAIN fit;4VAL descriptive generalization;2 previously studied application sites;TEST sealed',
    future='No follow-up/pseudo-labels/reviewer labels; TRAIN original seasonal pair only',
    promotion='Remain experimental regardless of evaluation; no label-based explanation separation available')


def rows(tile):
    m=eligible(tile);v=tile['values'];c=tile['counts']
    return v[:4,m].T,v[4:8,m].T,c[[0,2]][:,m].T,c[[1,3]][:,m].T


def retrain(initial, a, b, center, spread):
    torch.manual_seed(42);rng=np.random.default_rng(42)
    model=copy.deepcopy(initial).train().requires_grad_(True);delta=nn.Linear(8,4)
    opt=torch.optim.Adam(list(model.parameters())+list(delta.parameters()),lr=CONFIG['lr']);loss_fn=nn.HuberLoss()
    a=torch.tensor((a-center)/spread,dtype=torch.float32);b=torch.tensor((b-center)/spread,dtype=torch.float32)
    history=[];start=time.monotonic()
    for epoch in range(CONFIG['epochs']):
        totals=[]
        for ids in np.array_split(rng.permutation(len(a)),max(1,int(np.ceil(len(a)/512)))):
            if time.monotonic()-start>120:raise TimeoutError('No retry: bounded fit limit')
            x,y=a[ids],b[ids];sensor=int(rng.integers(2));sl=slice(sensor*2,sensor*2+2)
            hx,hy=model.view(x,sensor),model.view(y,sensor)
            reconstruction=(loss_fn(model.head(hx)[:,sl],x[:,sl])+loss_fn(model.head(hy)[:,sl],y[:,sl]))/2
            temporal=loss_fn(delta(hy-hx),y-x);loss=reconstruction+.25*temporal
            if not torch.isfinite(loss):raise ValueError('Nonfinite TRAIN loss')
            opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(list(model.parameters())+list(delta.parameters()),1.);opt.step()
            totals.append([float(loss.detach()),float(reconstruction.detach()),float(temporal.detach())])
        history.append(dict(epoch=epoch+1,total=float(np.mean(totals,0)[0]),reconstruction=float(np.mean(totals,0)[1]),temporal=float(np.mean(totals,0)[2])))
        torch.save(dict(state=model.state_dict(),delta_head=delta.state_dict(),epoch=epoch+1),OUT/f'epoch{epoch+1}.pt')
    return model.eval().requires_grad_(False),history,time.monotonic()-start


def uniform(model,a,b,center,spread):
    x,_=views(model,a,center,spread);y,_=views(model,b,center,spread)
    return np.linalg.norm(y.mean(1)-x.mean(1),axis=1)


def run():
    backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    frozen=load(BASE/'manifest.json');prior_root=Path('outputs/phase25/experiments/minemind-cached-v1')
    for name,digest in load(prior_root/'integrity.json').items():
        if sha(prior_root/name)!=digest:raise ValueError('Frozen comparison integrity')
    prior=load(prior_root/'metrics.json')
    if sha(BASE/'encoder.pt')!=frozen['encoder_sha256']:raise ValueError('Frozen encoder hash')
    splits,held,cache_hash=verify(Path('outputs'))
    if cache_hash!=frozen['cache_manifest_sha256']:raise ValueError('Cache hash')
    OUT.mkdir(parents=True,exist_ok=False);save(OUT/'preregistered_config.json',CONFIG)
    w=torch.load(BASE/'encoder.pt',weights_only=True,map_location='cpu');original=Encoder();original.load_state_dict(w['state']);original.eval().requires_grad_(False)
    center=np.array(w['center']);spread=np.array(w['spread']);data={g:rows(t) for g,t in splits['train'].items()}
    a,b,ca,cb=[np.concatenate([r[i] for r in data.values()]) for i in range(4)]
    diagnosis={}
    for g,(ga,gb,_,_) in data.items():
        h,e=views(original,ga,center,spread);k,_=views(original,gb,center,spread);d=k-h
        den=np.linalg.norm(d[:,0],axis=1)+np.linalg.norm(d[:,1],axis=1)
        diagnosis[g]=dict(rows=len(ga),latent_sd=h.std((0,1)).tolist(),effective_rank=int(np.linalg.matrix_rank(h.reshape(-1,8))),cross_reconstruction_mse=e.mean(0).tolist(),delta_cancellation_median=float(np.median(np.linalg.norm(d.sum(1),axis=1)/np.maximum(den,1e-8))))
    model,history,seconds=retrain(original,a,b,center,spread)
    configs={'frozen_adaptive':original,'temporal_uniform':model,'temporal_adaptive':model}
    states={k:fit_reliability(v,a,ca,center,spread) for k,v in configs.items()}
    def infer(key,r,mode='both'):
        x,y,c,d=r
        return uniform(configs[key],x,y,center,spread) if key=='temporal_uniform' else score(configs[key],x,y,c,d,center,spread,states[key],mode)[0]
    thresholds={k:float(np.quantile(infer(k,(a,b,ca,cb)),.995)) for k in configs}
    # Freeze TRAIN outputs before any VAL/application predictions.
    save(OUT/'train_fit.json',dict(config=CONFIG,history=history,seconds=seconds,train_groups={g:len(r[0]) for g,r in data.items()},states=states,thresholds=thresholds,diagnosis=diagnosis,source_hashes={g:t['hashes'] for g,t in splits['train'].items()},normalization_source_sha256=sha(BASE/'encoder.pt')))
    validation={}
    for g,t in splits['validation'].items():
        r=rows(t);validation[g]={k:dict(cells=len(r[0]),score_quantiles=np.quantile(infer(k,r),[0,.5,.95,1]).tolist(),exceedance=float(np.mean(infer(k,r)>=thresholds[k]))) for k in configs}
    report={}
    for site,pair in held.items():
        mask=eligible(pair[0])&eligible(pair[1]);site_results={}
        rs=[(t['values'][:4,mask].T,t['values'][4:8,mask].T,t['counts'][[0,2]][:,mask].T,t['counts'][[1,3]][:,mask].T) for t in pair]
        for key in configs:
            scores=[infer(key,r) for r in rs];metrics=compare(*scores,mask,thresholds[key]);metrics['same_season_exceedance']=[]
            for season in [0,1]:
                r=(pair[0]['values'][season*4:season*4+4,mask].T,pair[1]['values'][season*4:season*4+4,mask].T,pair[0]['counts'][[season,2+season]][:,mask].T,pair[1]['counts'][[season,2+season]][:,mask].T)
                metrics['same_season_exceedance'].append(float(np.mean(infer(key,r)>=thresholds[key])))
            missing={}
            if key!='temporal_uniform':
                for mode in ['sar','optical']:
                    ss=[infer(key,r,mode) for r in rs];missing[mode]=dict(spearman=float(spearmanr(*ss).statistic),rank_vs_both=[float(spearmanr(x,y).statistic) for x,y in zip(scores,ss)])
            for i,(t,s) in enumerate(zip(pair,scores),1):
                folder=OUT/site/key;folder.mkdir(parents=True,exist_ok=True);geo,binary=candidates(t,s,mask,thresholds[key],site,key,i)
                for f in geo['features']:f['properties']['score_type']='RELIABILITY_WEIGHTED_DISTANCE' if key!='temporal_uniform' else 'EMBEDDING_DISTANCE'
                save(folder/f'r{i}-candidates.geojson',geo);grid=np.full(mask.shape,NODATA,'float32');grid[mask]=s
                write_tile(folder/f'r{i}.tif',t['profile'],('anomaly_score','common_valid','candidate_mask'),np.stack([grid,mask,binary]).astype('float32'),dict(status='REVIEW_REQUIRED',operational_alerts='0',model_validation='NOT_VALIDATED'))
            site_results[key]=dict(metrics=metrics,missing_modality=missing,threshold=thresholds[key])
        report[site]=dict(eligible_cells=int(mask.sum()),methods=site_results,baselines=prior['sites'][site]['methods'])
    save(OUT/'metrics.json',dict(sites=report,validation=validation,history=history,training_seconds=seconds,diagnosis=diagnosis,cache_sha256=cache_hash,status='EXPLORATORY',operational_alerts=0,decision='NO_PROMOTION:descriptive ablation only',explanation_separation='UNDEFINED:no independent competing-explanation labels; retain signed evidence and UNKNOWN attribution',limitations=['Four TRAIN groups only','Old baselines use frozen calibration cutoffs;new cutoffs TRAIN-only:areas not equal-quota comparisons','Cross-reconstruction residual can downweight genuine discordant change','No TRAIN scene-disjoint replicas:temporal objective cannot disentangle seasonal change from nuisance','No independent mining accuracy or causal attribution']))
    save(OUT/'integrity.json',{p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()})
    print(json.dumps(dict(seconds=seconds,history=history,sites={s:{k:v['metrics'] for k,v in r['methods'].items()} for s,r in report.items()})))

if __name__=='__main__':run()
