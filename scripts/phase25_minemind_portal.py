"""Private whitelist-only MineMind map/metrics adapter; raw assets and weights never served."""
import json,csv,io
from pathlib import Path
import numpy as np
import rasterio
from PIL import Image
from scripts.phase25_minemind import OUT as RUN
from scripts.indian_ssl_pilot import verify
from scripts.phase13_data import brahmani_snapshot
from src.phase25.dataset import sha

CACHE=Path('outputs/phase25/experiments/minemind-portal-v2')


def png(rgb,valid):
 b=io.BytesIO();a=np.dstack([(np.clip(np.nan_to_num(rgb),0,1)*255).astype('uint8'),valid.astype('uint8')*255]);Image.fromarray(a).save(b,format='PNG');return b.getvalue()


def export():
 m=json.loads((RUN/'metrics.json').read_bytes());inventory=json.loads((RUN/'integrity.json').read_bytes())
 for name,digest in inventory.items():
  if sha(RUN/name)!=digest:raise ValueError('MineMind experiment integrity mismatch')
 _,held,cache_hash=verify(Path('outputs'))
 if cache_hash!=m['cache_sha256']:raise ValueError('Source cache changed')
 assets={};rows=[]
 for site,record in m['sites'].items():
  for key,value in record['methods'].items():
   for replica,tile in enumerate(held[site],1):
    stem=f'minemind/{site}/{key}/r{replica}';source=RUN/site/key/f'r{replica}.tif'
    with rasterio.open(source) as ds:
     a=ds.read();mask=a[1]==1
     if ds.tags().get('status')!='REVIEW_REQUIRED' or ds.tags().get('operational_alerts')!='0':raise ValueError('Alert gate')
    for label,values in [('before',tile['values'][2]),('after',tile['values'][6])]:
     t=np.clip((values+.1)/1.1,0,1);assets[stem+'_'+label+'.png']=png(np.stack([1-t,.2+.7*t,.1+.2*t],-1),mask)
    t=np.clip(a[0]/max(value['threshold']*2,1e-8),0,1);assets[stem+'_score.png']=png(np.stack([t,.3+.5*t,1-t],-1),mask);assets[stem+'_candidates.png']=png(np.broadcast_to([1,.7,.1],(*mask.shape,3)),mask&(a[2]==1))
    geo=json.loads((RUN/site/key/f'r{replica}-candidates.geojson').read_bytes());geo['provenance']=dict(source_hashes=tile['hashes'],scene_groups=tile['scenes'],crs=str(tile['profile']['crs']),bounds=tile['bounds'],frozen_experiment_sha256=sha(RUN/'metrics.json'),operational_alerts=0,model_validation='NOT_VALIDATED',threshold=value['threshold'],method=key);assets[stem+'.geojson']=json.dumps(geo).encode()
    rows.append(dict(site=site,method=key,replica=replica,candidates=len(geo['features']),area_m2=sum(f['properties']['area_m2'] for f in geo['features']),eligible_cells=record['eligible_cells'],spearman=value['metrics']['spearman'],top5_jaccard=value['metrics']['top5_jaccard'],same_season_before=value['metrics']['same_season_exceedance'][0],same_season_after=value['metrics']['same_season_exceedance'][1],status='REVIEW_REQUIRED',mining_attribution='UNKNOWN'))
    value.setdefault('replicas',[]).append(dict(id=replica,assets={k:stem+'_'+k+'.png' for k in ['before','after','score','candidates']},geojson=stem+'.geojson',candidates=geo['features'],source_sha256=sha(source)))
 river_path=Path('outputs/phase12d_brahmani/comparison.csv');river=brahmani_snapshot(river_path)
 existing=json.loads(Path('frontend/public/local/brahmani.json').read_bytes())
 if existing['data']!=river or existing['sha256']!=sha(river_path):raise ValueError('Published river snapshot disagrees with frozen source')
 leshka=json.loads(Path('frontend/public/local/river.json').read_bytes())
 if leshka['pilot']['common_pixels']!=12 or leshka['pilot']['reportable']:raise ValueError('Leshka insufficient-support gate changed')
 m.update(river=river,river_sha256=sha(river_path),leshka=dict(common_cells=12,minimum_cells=25,status='INSUFFICIENT_DATA'),status='EXPLORATORY',label_kind='NO_REFERENCE_LABELS',operational_alerts=0,source_metrics_sha256=sha(RUN/'metrics.json'),context='SRTMterrain available; landcover/rainfall/fire/road/persistence unavailable at these source windows. No substitution from other regions.',limitations='Ranking repeatability is not mining accuracy. Controlled sensor withholding, not natural missingness. Four TRAIN blocks, four calibration blocks; previously studied Gevra/Bhubaneswari application replicas. No future/NRSC/human labels/TEST. Phase15Cremains primary; frozen SSL not promoted. Scores are not probabilities.')
 assets['minemind/snapshot.json']=json.dumps(dict(data=m),allow_nan=False).encode();b=io.StringIO();w=csv.DictWriter(b,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);assets['minemind/comparison.csv']=b.getvalue().encode();assets['minemind/river.csv']=river_path.read_bytes()
 CACHE.mkdir(parents=True,exist_ok=False)
 for name,value in assets.items():
  p=CACHE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
 (CACHE/'integrity.json').write_text(json.dumps({n:sha(CACHE/n) for n in assets},indent=2)+'\n',encoding='utf-8');print('MineMind snapshot:2sites/7methods/2replicas; Brahmani16pairs;Leshka12<25;0alerts')


def minemind_files(root):
 cache=Path(root)/CACHE
 if not (cache/'integrity.json').exists():return {}
 files={}
 for name,digest in json.loads((cache/'integrity.json').read_bytes()).items():
  p=(cache/name).resolve()
  if not p.is_relative_to(cache.resolve()) or p.suffix not in ['.png','.json','.geojson','.csv'] or sha(p)!=digest:raise ValueError('MineMind snapshot integrity')
  files[name]=({'png':'image/png','json':'application/json','geojson':'application/geo+json','csv':'text/csv'}[p.suffix[1:]],p.read_bytes())
 d=json.loads(files['minemind/snapshot.json'][1])['data']
 if d['status']!='EXPLORATORY' or d['operational_alerts']!=0 or d['label_kind']!='NO_REFERENCE_LABELS':raise ValueError('MineMind evidence gate')
 for site in d['sites'].values():
  for method in site['methods'].values():
   for r in method['replicas']:
    if any(c['properties']['status']!='REVIEW_REQUIRED' or c['properties']['evidence_status']!='UNKNOWN' or c['properties']['operational_alerts']!=0 for c in r['candidates']):raise ValueError('Candidate gate')
 return files

if __name__=='__main__':export()
