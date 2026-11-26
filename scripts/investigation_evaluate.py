"""Offline frozen evidence sensitivity; descriptive, never accuracy or model selection."""
import argparse,csv,json,subprocess,time
from pathlib import Path
import numpy as np
from scipy.ndimage import label
from src.phase25.investigation import combine,NAMES,PHYSICAL
from src.phase25.dataset import sha
from scripts.investigation_dataset import OUT
from scripts.investigation_portal import studio_files
from scripts.phase25b_cached import backup_gate


def configurations(cfg,mode):
    bases={'equal':[1/7]*7,'physical':PHYSICAL.tolist(),'adaptive':cfg['adaptive_weights'][mode]}
    for preset,weights in bases.items():
        for ablation in ['none']+NAMES:
            w=list(weights)
            if ablation!='none':w[NAMES.index(ablation)]=0
            yield preset,ablation,w


def connected(mask,minimum):
    if minimum not in (1,2,4,8):raise ValueError('Frozen component sizes')
    ids,n=label(mask);counts=np.bincount(ids.ravel());keep=counts>=minimum;keep[0]=False
    return keep[ids],int(keep.sum())


def jaccard(a,b):
    union=int((a|b).sum());return int((a&b).sum())/union if union else None


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def run(output):
    start=time.perf_counter();output=Path(output)
    if output.exists():raise ValueError('Never overwrite prior evaluation')
    backup_gate(Path('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125'))
    studio_files(Path('.')) # all source, archive, derived and label hashes; TEST gate
    manifest=json.loads((OUT/'manifest.json').read_bytes());cfg=json.loads((OUT/'config.json').read_bytes())
    if len(manifest['patches'])!=82:raise ValueError('Frozen 82 patches required')
    output.mkdir(parents=True);patch_rows=[];score_rows=[];overlap_rows=[];parity_count=0;max_error=0.
    # Real frontend calculate function; no browser, transpilation, network or UI changes.
    worker=subprocess.Popen(['node','--experimental-strip-types','scripts/investigation_parity.js',str(OUT)],stdout=subprocess.PIPE,text=True,encoding='utf-8')
    for r in manifest['patches']:
        data=json.loads((OUT/r['folder']/'studio.json').read_bytes());area=abs(data['affine'][0]*data['affine'][4]-data['affine'][1]*data['affine'][3])/10000
        for mode in ['pair','retrospective']:
            p=data['modes'][mode];parts=dict(values=np.asarray(p['contributions'],float),valid=np.asarray(p['valid'],bool),competitors=np.asarray(p['competitors'],float));base={}
            legacy=np.asarray(data['legacy_rule'],bool)
            for preset,ablation,weights in configurations(cfg,mode):
                result=combine(parts,weights,60);scores=result['score'];finite=np.isfinite(scores)
                js=json.loads(worker.stdout.readline())
                if (js['id'],js['mode'],js['preset'],js['ablation'])!=(r['patch_id'],mode,preset,ablation):raise ValueError('Frontend parity ordering')
                actual=np.asarray(js['score'],float).reshape(scores.shape)
                if not np.array_equal(np.isfinite(actual),finite):raise ValueError('Frontend validity differs')
                error=float(np.max(np.abs(actual[finite]-scores[finite]))) if finite.any() else 0.
                if error>1e-10:raise ValueError('Frontend score differs')
                expected,_=connected(result['candidate'],4)
                if not np.array_equal(np.asarray(js['mask'],bool).reshape(scores.shape),expected):raise ValueError('Frontend candidate differs')
                max_error=max(max_error,error);parity_count+=1
                context=dict(patch_id=r['patch_id'],split=r['split'],group_id=r['group_id'],mode=mode,weighting=preset,ablation=ablation)
                vals=scores[finite];q=np.quantile(vals,[0,.05,.25,.5,.75,.95,1]) if len(vals) else [None]*7
                score_rows.append(dict(**context,supported_cells=int(finite.sum()),mean=float(vals.mean()) if len(vals) else None,**dict(zip(['min','q05','q25','median','q75','q95','max'],q))))
                for threshold in range(20,91,10):
                    raw=result['candidate'] & (scores>=threshold) if threshold>=60 else combine(parts,weights,threshold)['candidate']
                    for minimum in [1,2,4,8]:
                        mask,n=connected(raw,minimum);key=(preset,threshold,minimum)
                        if ablation=='none':base[key]=mask
                        ref=base[key];old,_=connected(legacy&finite,minimum)
                        patch_rows.append(dict(**context,threshold=threshold,min_cells=minimum,supported_cells=int(finite.sum()),candidate_cells=int(mask.sum()),candidate_ha=float(mask.sum()*area),clusters=n,reference_intersection=int((mask&ref).sum()),reference_union=int((mask|ref).sum()),legacy_intersection=int((mask&old).sum()),legacy_union=int((mask|old).sum())))
            for threshold in range(20,91,10):
                for minimum in [1,2,4,8]:
                    for a,b in [('equal','physical'),('equal','adaptive'),('physical','adaptive')]:
                        x,y=base[a,threshold,minimum],base[b,threshold,minimum]
                        overlap_rows.append(dict(patch_id=r['patch_id'],split=r['split'],group_id=r['group_id'],mode=mode,threshold=threshold,min_cells=minimum,left=a,right=b,intersection=int((x&y).sum()),union=int((x|y).sum())))
    if worker.wait()!=0:raise ValueError('Frontend worker failed')
    write_csv(output/'patch_sensitivity.csv',patch_rows);write_csv(output/'patch_scores.csv',score_rows)
    def aggregate(rows,fields,counts):
        groups={}
        for r in rows:
            key=tuple(r[k] for k in fields);g=groups.setdefault(key,{**dict(zip(fields,key)),**{k:0 for k in counts}})
            for k in counts:g[k]+=r[k]
        return list(groups.values())
    fields=['split','mode','weighting','ablation','threshold','min_cells'];counts=['supported_cells','candidate_cells','candidate_ha','clusters','reference_intersection','reference_union','legacy_intersection','legacy_union']
    pooled=aggregate(patch_rows,fields,counts)
    for row in pooled:
        row['ablation_jaccard']=row['reference_intersection']/row['reference_union'] if row['reference_union'] else None
        row['legacy_jaccard']=row['legacy_intersection']/row['legacy_union'] if row['legacy_union'] else None
    write_csv(output/'pooled_sensitivity.csv',pooled)
    # Compact default-setting block tables; full block grid retained privately.
    blocks=aggregate(patch_rows,['group_id']+fields,counts);write_csv(output/'block_sensitivity.csv',blocks)
    write_csv(output/'blocks_default.csv',[r for r in blocks if r['threshold']==60 and r['min_cells']==4])
    overlaps=aggregate(overlap_rows,['split','mode','threshold','min_cells','left','right'],['intersection','union'])
    for row in overlaps:row['jaccard']=row['intersection']/row['union'] if row['union'] else None
    write_csv(output/'weight_overlap.csv',overlaps)
    # Pooled quantiles calculated from actual cells, never average patch quantiles.
    distributions=[]
    for split in ['train','validation']:
        for mode in ['pair','retrospective']:
            for preset,ablation,weights in configurations(cfg,mode):
                values=[]
                for r in manifest['patches']:
                    if r['split']!=split:continue
                    p=json.loads((OUT/r['folder']/'studio.json').read_bytes())['modes'][mode]
                    z=combine(dict(values=np.asarray(p['contributions'],float),valid=np.asarray(p['valid'],bool),competitors=np.asarray(p['competitors'],float)),weights)['score'];values.extend(z[np.isfinite(z)])
                v=np.asarray(values);q=np.quantile(v,[.05,.25,.5,.75,.95])
                distributions.append(dict(split=split,mode=mode,weighting=preset,ablation=ablation,cells=len(v),mean=float(v.mean()),**dict(zip(['q05','q25','median','q75','q95'],q))))
    write_csv(output/'score_distributions.csv',distributions)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'savefig.dpi':220})
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True)
    for i,mode in enumerate(['pair','retrospective']):
        for j,split in enumerate(['train','validation']):
            ax=axes[i,j]
            for preset in ['equal','physical','adaptive']:
                z=[r for r in pooled if r['mode']==mode and r['split']==split and r['weighting']==preset and r['ablation']=='none' and r['min_cells']==4]
                ax.plot([r['threshold'] for r in z],[r['candidate_ha'] for r in z],marker='o',label=preset)
            ax.set(title=f'{split.upper()} / {mode}',ylabel='Candidate area (ha)',xlabel='Evidence threshold (0–100)');ax.grid(alpha=.25);ax.legend()
    fig.suptitle('Exploratory candidate sensitivity — not mining accuracy');fig.tight_layout();fig.savefig(output/'threshold_comparison.png');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for ax,mode in zip(axes,['pair','retrospective']):
        z=[r for r in pooled if r['split']=='validation' and r['mode']==mode and r['weighting']=='adaptive' and r['threshold']==60 and r['min_cells']==4]
        ax.bar([r['ablation'] for r in z],[r['candidate_ha'] for r in z]);ax.tick_params(axis='x',rotation=45);ax.set(title=f'VAL / {mode}',ylabel='Candidate area (ha)');ax.grid(axis='y',alpha=.25)
    fig.suptitle('Single-family weight zero; vegetation AND soil prerequisites retained');fig.tight_layout();fig.savefig(output/'ablation_comparison.png');plt.close(fig)
    files={p.name:sha(p) for p in output.iterdir() if p.is_file()}
    summary=dict(dataset_sha256=sha(OUT/'manifest.json'),patches=82,train=70,validation=12,groups={'train':17,'validation':3},frontend_cases=parity_count,max_score_error=max_error,thresholds=list(range(20,91,10)),minimum_cells=[1,2,4,8],prerequisites='Vegetation>=0.25 AND soil>=0.25 retained even when their weights are zero; core QA, coverage>=0.6 and competing margin>=10 unchanged',clusters='4-neighbor within original patches; no boundary stitching; counts may split cross-patch objects',accuracy='NOT ESTABLISHED: zero admitted independent mining labels; human disturbance reviews and source-derived rules are not mining ground truth',retrospective='Uses 2025-26 follow-up; not prospective',selection='No weights, thresholds or spatial groups selected using VAL',operational_alerts=0,files=files,runtime_seconds=time.perf_counter()-start)
    (output/'receipt.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
