"""One offline geographic comparison; expanded TRAIN reliability only, no encoder refit."""
import json,time
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from scripts.minemind_geography import ROOT,save,rank
from scripts.indian_ssl_pilot import Encoder,read_tile,verify,eligible,compare
from scripts.phase25_minemind import BASE,candidates
from scripts.phase25_minemind_learning import rows
from scripts.phase15c_screen import anomaly
from src.phase25.minemind import change,cutoff
from src.phase25.minemind_learning import fit_reliability,score
from src.phase25.dataset import sha
from src.phase3.regional_inference import NODATA,write_tile

OUT=Path('outputs/phase25/experiments/minemind-geographic-comparison-v1')
METHODS=['phase15c','frozen_ssl','prior_adaptive','expanded_adaptive','frozen_sar','frozen_optical']


def expansion_gate(records):
    good=[r for r in records if r['passes']];families=set()
    for r in good:
        counts=r['worldcover'].get('Map',{});den=sum(counts.values())
        for code,name in [('10','forest'),('20','shrub'),('30','grass'),('40','cropland'),('50','built'),('60','bare'),('80','water')]:
            if den and counts.get(code,0)/den>=.25:families.add(name)
    okay=len(good)>=4 and len({r['state'] for r in good})>=4 and sum(r['role']=='ssl_fit' for r in good)>=2 and sum(r['role']=='geographic_holdout' for r in good)>=1 and len(families)>=3
    return okay,sorted(families)


def source_sets(pair):
    return {sid for t in pair for season in t['scenes'] for key in ('s1','s2') for sid,_ in season[key]}


def run():
    start=time.monotonic();torch.set_num_threads(2)
    acquisition=json.loads((ROOT/'acquisition.json').read_bytes());plan=json.loads((ROOT/'plan.json').read_bytes())
    if sha(ROOT/'plan.json')!=acquisition['plan_sha256']:raise ValueError('Plan changed')
    passes,families=expansion_gate(acquisition['accepted'])
    OUT.mkdir(parents=True,exist_ok=False)
    save(OUT/'protocol.json',dict(methods=METHODS,fit='One reliability-statistics fit on BEFORE expandedTRAIN; no encoder optimizer',per_group_cap=1024,seed=42,selection='seed-hash pixel permutation, balanced blocks; no VAL/holdout fitting',threshold='All methods matched TRAIN .5percent review quota, explicit ties. Historical cutoffs not overwritten.',context_families=families,expansion_passes=passes,stop='No temporal recovery, further acquisition or optimization. No promotion based on this comparison.',natural_missingness=False,explanation_separation='No independent class labels:undefined; report historical AOI context only'))
    if not passes:
        save(OUT/'decision.json',dict(decision='INSUFFICIENT_EXPANSION:STOP_OPTIMIZATION',context_families=families));return
    splits,_,old_cache_hash=verify(Path('outputs'));pairs={};records={r['id']:r for r in acquisition['accepted'] if r['passes']}
    for key,r in records.items():pairs[key]=[read_tile(ROOT/key/f'r{i}') for i in (1,2)]
    fitkeys=[k for k,r in records.items() if r['role']=='ssl_fit'];heldkeys=[k for k,r in records.items() if r['role']=='geographic_holdout']
    if set.union(set(),*(source_sets(pairs[k]) for k in fitkeys)) & set.union(set(),*(source_sets(pairs[k]) for k in heldkeys)):raise ValueError('TRAIN/holdout shared source scene')
    for key,pair in pairs.items():
        if source_sets(pair[:1]) & source_sets(pair[1:]):raise ValueError('Replica source scene overlap')
    frozen=json.loads((BASE/'manifest.json').read_bytes())
    if sha(BASE/'encoder.pt')!=frozen['encoder_sha256']:raise ValueError('Frozen model integrity')
    w=torch.load(BASE/'encoder.pt',map_location='cpu',weights_only=True);model=Encoder();model.load_state_dict(w['state']);model.eval().requires_grad_(False);center=np.array(w['center']);spread=np.array(w['spread'])
    oldroot=Path('outputs/phase25/experiments/minemind-learning-v1')
    for name,digest in json.loads((oldroot/'integrity.json').read_bytes()).items():
        if sha(oldroot/name)!=digest:raise ValueError('Prior comparison integrity')
    oldstate=json.loads((oldroot/'train_fit.json').read_bytes())['states']['frozen_adaptive']
    train=dict(splits['train']);train.update({k:pairs[k][0] for k in fitkeys});before=[];counts=[];support={};cal=[]
    for key,t in train.items():
        v=t['values'];c=t['counts'];m=(v[:4]!=NODATA).all(0)&(c[[0,2]]>=2).all(0)
        a=v[:4,m].T;n=c[[0,2]][:,m].T;ids=np.random.default_rng(int(rank(key)[:8],16)).permutation(len(a))[:1024]
        if len(ids)<25:raise ValueError('Insufficient TRAIN support')
        before.append(a[ids]);counts.append(n[ids]);support[key]=len(ids);cal.append((t,eligible(t)))
    fit_start=time.monotonic();state=fit_reliability(model,np.concatenate(before),np.concatenate(counts),center,spread);fit_seconds=time.monotonic()-fit_start
    def predict(key,t,m,mode='both'):
        a=t['values'][:4,m].T;b=t['values'][4:8,m].T;c=t['counts'][[0,2]][:,m].T;d=t['counts'][[1,3]][:,m].T
        if key=='phase15c':return anomaly(t['values'],t['counts'],2)[0][m]
        if key.startswith('frozen_'):return change(model,a,b,center,spread,{'frozen_ssl':'both','frozen_sar':'sar','frozen_optical':'optical'}[key])[0]
        return score(model,a,b,c,d,center,spread,oldstate if key=='prior_adaptive' else state,mode)[0]
    # Same deterministic <=1024/group calibration cells for every method; TRAIN only.
    calibrators={k:[] for k in METHODS}
    for key,t in train.items():
        m=eligible(t);ids=np.random.default_rng(int(rank(key)[:8],16)).permutation(int(m.sum()))[:1024]
        for method in METHODS:calibrators[method].append(predict(method,t,m)[ids])
    thresholds={k:cutoff(np.concatenate(v),int(np.ceil(.005*sum(map(len,v))))) for k,v in calibrators.items()}
    save(OUT/'train_fit.json',dict(state=state,prior_state_source_sha256=sha(oldroot/'train_fit.json'),support=support,fit_seconds=fit_seconds,thresholds=thresholds,selected={k:int((np.concatenate(v)>=thresholds[k]).sum()) for k,v in calibrators.items()},model_sha256=sha(BASE/'encoder.pt'),source_hashes={k:t['hashes'] for k,t in train.items()},old_cache_sha256=old_cache_hash))
    results={}
    for key in heldkeys:
        pair=pairs[key];r=records[key];m=eligible(pair[0])&eligible(pair[1]);record={}
        if m.sum()<25:raise ValueError('Insufficient paired holdout support')
        for method in METHODS:
            ss=[predict(method,t,m) for t in pair];metrics=compare(*ss,m,thresholds[method]);same=[]
            for season in [0,1]:
                a=pair[0]['values'][season*4:season*4+4,m].T;b=pair[1]['values'][season*4:season*4+4,m].T
                if method=='phase15c':
                    from scripts.indian_ssl_pilot import scores
                    raw=scores(pair[0]['values'][season*4:season*4+4],pair[1]['values'][season*4:season*4+4],pair[0]['values'][12:],m,model,center,spread)[0]
                elif method.startswith('frozen_'):raw=change(model,a,b,center,spread,{'frozen_ssl':'both','frozen_sar':'sar','frozen_optical':'optical'}[method])[0]
                else:raw=score(model,a,b,pair[0]['counts'][[season,season+2]][:,m].T,pair[1]['counts'][[season,season+2]][:,m].T,center,spread,oldstate if method=='prior_adaptive' else state)[0]
                same.append(float((raw>=thresholds[method]).mean()))
            metrics['same_season_exceedance']=same;missing={}
            if method in ['prior_adaptive','expanded_adaptive']:
                for mode in ['sar','optical']:
                    ms=[predict(method,t,m,mode) for t in pair];missing[mode]=dict(replica_spearman=float(spearmanr(*ms).statistic),rank_vs_both=[float(spearmanr(a,b).statistic) for a,b in zip(ss,ms)])
            for i,(t,s) in enumerate(zip(pair,ss),1):
                folder=OUT/key/method;folder.mkdir(parents=True,exist_ok=True);geo,binary=candidates(t,s,m,thresholds[method],key,method,i)
                for f in geo['features']:
                    f['properties'].update(model_validation='NOT_VALIDATED',context_scope='AOI historical2021WorldCover histogram only;not polygon attribution',historical_context=r['worldcover'],score_type='UNSUPERVISED_DISTANCE_OR_DEVIATION')
                save(folder/f'r{i}-candidates.geojson',geo);grid=np.full(m.shape,NODATA,'float32');grid[m]=s
                write_tile(folder/f'r{i}.tif',t['profile'],('anomaly_score','common_valid','candidate_mask'),np.stack([grid,m,binary]).astype('float32'),dict(status='REVIEW_REQUIRED',operational_alerts='0',evidence_status='UNKNOWN'))
            record[method]=dict(metrics=metrics,missing=missing,threshold=thresholds[method])
        results[key]=dict(state=r['state'],eligible_cells=int(m.sum()),context=r['worldcover'],methods=record)
    save(OUT/'metrics.json',dict(holdouts=results,fit_seconds=fit_seconds,analysis_seconds=time.monotonic()-start,training_seconds=0,context_families=families,status='EXPLORATORY',operational_alerts=0,decision='STOP_OPTIMIZATION;Phase15C_PRIMARY',limitations=['Two new geographic holdouts are cropland-context,not a representative mining test','Built-up support limited; historicalWorldCover not current reference labels','Original Maus sampling frame,not unbiased India sample','Missing-modality stress is controlled withholding','Four new TRAIN regions cannot establish national generalization','Phase15C uses its original per-AOI robust scaling; all new cutoffs TRAIN-only','No independent explanation labels,accuracy or causal claims']))
    save(OUT/'integrity.json',{p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()})
    print(json.dumps(dict(fit_seconds=fit_seconds,support=support,holdouts={k:{'state':v['state'],'cells':v['eligible_cells'],'methods':{m:x['metrics'] for m,x in v['methods'].items()}} for k,v in results.items()})))

def figure():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for name,digest in json.loads((OUT/'integrity.json').read_bytes()).items():
        if sha(OUT/name)!=digest:raise ValueError('Comparison integrity')
    m=json.loads((OUT/'metrics.json').read_bytes());q=Path('outputs/phase25/qa/minemind-geography-v1');q.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(2,3,figsize=(13,8),layout='constrained');names=['Phase15C','Frozen SSL','Prior adaptive','Expanded adaptive','SAR only','Optical only']
    for r,record in enumerate(m['holdouts'].values()):
        for col,key in enumerate(['spearman','top5_jaccard','candidate_jaccard']):
            ax=axes[r,col];values=[record['methods'][name]['metrics'][key] for name in METHODS]
            ax.bar(range(6),[v if v is not None else 0 for v in values],color=['#64748b','#172554','#0f766e','#14b8a6','#a16207','#6366f1'])
            for i,v in enumerate(values):ax.text(i,(v or 0)+.02,'Undefined' if v is None else f'{v:.3f}',ha='center',fontsize=8,rotation=90 if v is None else 0)
            ax.set_xticks(range(6),names,rotation=55,ha='right',fontsize=8);ax.set_ylim(-.05,1);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.set_title(record['state']+' / '+key.replace('_',' '),fontsize=10)
    fig.suptitle('New geographic development holdouts: 1,024 common cells each',fontsize=14)
    fig.supxlabel('Repeatability only; not mining accuracy. TRAIN-matched review quotas; WorldCover historical context, not ground truth.',fontsize=9)
    fig.savefig(q/'comparison.png',dpi=180);plt.close(fig)
    save(q/'figure-provenance.json',dict(metrics_sha256=sha(OUT/'metrics.json'),figure_sha256=sha(q/'comparison.png'),sources='Saved comparison only; no inference, fitting or requests rerun',operational_alerts=0))
    print(str(q/'comparison.png'))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--figure-only',action='store_true');a=p.parse_args();figure() if a.figure_only else run()
