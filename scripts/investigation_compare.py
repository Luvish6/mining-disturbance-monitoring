"""Descriptive shared-support comparisons; no accuracy or parameter selection."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from scripts.investigation_dataset import OUT
from scripts.investigation_portal import filtered
from src.phase25.dataset import sha
from src.phase25.investigation import combine


def run(output):
 output=Path(output)
 if output.exists():raise ValueError('Preserve prior comparison; choose new output')
 inventory=json.loads((OUT/'integrity.json').read_bytes())
 for name,digest in inventory.items():
  if sha(OUT/name)!=digest:raise ValueError('Private dataset integrity')
 cfg=json.loads((OUT/'config.json').read_bytes());m=json.loads((OUT/'manifest.json').read_bytes());table=json.loads((OUT/'sensitivity.json').read_bytes());results={};pooled=[]
 for split in ['train','validation']:
  a=[];b=[];legacy_cells=0;inter=0;union=0
  for r in m['patches']:
   if r['split']!=split:continue
   d=json.loads((OUT/r['folder']/'studio.json').read_bytes());p=d['modes']['pair'];parts=dict(values=np.asarray(p['contributions'],float),valid=np.asarray(p['valid'],bool),competitors=np.asarray(p['competitors'],float));x=combine(parts,[1/7]*7);y=combine(parts,cfg['adaptive_weights']['pair']);common=np.isfinite(x['score'])&np.isfinite(y['score']);a.extend(x['score'][common]);b.extend(y['score'][common]);baseline=dict(candidate=np.asarray(d['legacy_rule'],bool)&common);old=filtered(baseline);new=filtered(y)&common;legacy_cells+=int(old.sum());inter+=int((old&new).sum());union+=int((old|new).sum())
  corr=spearmanr(a,b).statistic if len(a)>1 else np.nan
  results[split]=dict(common_cells=len(a),equal_adaptive_spearman=float(corr) if np.isfinite(corr) else None,legacy_filtered_candidate_cells=legacy_cells,legacy_adaptive_jaccard=inter/union if union else None,comparison='Inherited shared-source NDVI/BSI/SAR rule; NOT ground truth or exact Phase15C')
  for preset in ['equal','physical','adaptive']:
   for threshold in [40,60,80]:
    rows=[r for r in table if r['split']==split and r['mode']=='pair' and r['weighting']==preset and r['threshold']==threshold];pooled.append(dict(split=split,weighting=preset,threshold=threshold,candidate_cells=sum(r['candidate_cells'] for r in rows),clusters=sum(r['clusters'] for r in rows)))
 summary=json.loads((OUT/'summary.json').read_bytes());result=dict(version=m['version'],dataset_path=OUT.as_posix(),dataset_manifest_sha256=sha(OUT/'manifest.json'),patches=len(m['patches']),splits={s:r['patches'] for s,r in summary['splits'].items()},source_features=summary['source_features'],context_cells={s:{k:r[k] for k in ['geology_cells','lease_cells']} for s,r in summary['splits'].items()},summary=results,sensitivity=pooled,adaptive_weights=cfg['adaptive_weights'],scales=cfg['scales'],scope='Descriptive sensitivity only; no model training,VAL tuning or independent mining accuracy',baseline_compatibility='Frozen SSL requires original seasonal NDTI; V2 lacks that exact feature. No ratio-of-composite or fabricated channel substituted. Existing results retained in frozen workspace.',rights='Private data; NGDR product-specific redistribution and Bhuvan approval unresolved',operational_alerts=0)
 output.mkdir(parents=True);(output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
