"""One new offline missing-modality stress comparison; frozen SSL fit is never rerun."""
import json,time
from pathlib import Path
import numpy as np
import torch,rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom
from scripts.indian_ssl_pilot import verify,Encoder,eligible,components,compare,load
from src.phase25.minemind import change,physical,cutoff
from src.phase25.dataset import sha
from src.phase3.regional_inference import write_tile,NODATA
from scripts.phase25b_cached import backup_gate

BASE=Path('outputs/indian_ssl_pilot_v1')
OUT=Path('outputs/phase25/experiments/minemind-cached-v1')


def save(path,data):
 Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def candidates(tile,score,mask,threshold,site,method,replica):
 binary,n=components(score,mask,threshold);features=[];v=tile['values'];allscore=np.full(mask.shape,np.nan);allscore[mask]=score
 for geo,value in shapes(binary.astype('uint8'),mask=binary,transform=tile['profile']['transform'],connectivity=4):
  from rasterio.features import geometry_mask
  region=geometry_mask([geo],out_shape=mask.shape,transform=tile['profile']['transform'],invert=True)
  stats={name:float(a[region].mean()) for name,a in [('dVV',v[4]-v[0]),('dVH',v[5]-v[1]),('dNDVI',v[6]-v[2]),('dNDTI',v[7]-v[3])]}
  props=dict(id=f'{site}-{method}-r{replica}-{len(features)+1}',status='REVIEW_REQUIRED',evidence_status='UNKNOWN',model_validation='NOT_VALIDATED',score_type='UNCALIBRATED_EMBEDDING_DISTANCE' if method.startswith('ssl') else 'UNCALIBRATED_ROBUST_DEVIATION',pixel_count=int(region.sum()),area_m2=int(region.sum())*900,score_mean=float(allscore[region].mean()),score_max=float(allscore[region].max()),signed_changes=stats,slope_range_degrees=[float(v[13][region].min()),float(v[13][region].max())],elevation_mean_m=float(v[12][region].mean()),alternatives=dict(vegetation_change_or_seasonality='SUPPORTED_SIGN_ONLY:'+('decrease' if stats['dNDVI']<0 else 'increase'),moisture_roughness_geometry='POSSIBLE_RADAR_ALTERNATIVE',agriculture='UNKNOWN:no accepted crop-cycle/context evidence at this site',construction='UNKNOWN:no dated built-up transition',landslide_erosion='UNKNOWN:terrain alone insufficient',mining='UNKNOWN:no independent attribution'),available_context=['SRTM_elevation','SRTM_slope'],missing_context=['matched_rainfall','land_cover','roads','fire','water','followup_persistence'],operational_alerts=0)
  features.append(dict(type='Feature',geometry=transform_geom(tile['profile']['crs'],'EPSG:4326',geo),properties=props))
 return dict(type='FeatureCollection',features=features),binary


def run():
 backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125');start=time.monotonic();torch.set_num_threads(2)
 manifest=load(BASE/'manifest.json');old=load(BASE/'metrics.json')
 if sha(BASE/'encoder.pt')!=manifest['encoder_sha256']:raise ValueError('Frozen SSL checkpoint changed')
 for name,digest in manifest['outputs'].items():
  if sha(BASE/name)!=digest:raise ValueError('Frozen experiment output changed')
 splits,held,cache_hash=verify(Path('outputs'))
 if cache_hash!=manifest['cache_manifest_sha256']:raise ValueError('Frozen source cache changed')
 weights=torch.load(BASE/'encoder.pt',map_location='cpu',weights_only=True);model=Encoder();model.load_state_dict(weights['state'],strict=True);model.eval().requires_grad_(False);center=np.array(weights['center']);spread=np.array(weights['spread'])
 OUT.mkdir(parents=True,exist_ok=False);quota=old['calibration']['baseline_selected_cells'];modes=['both','sar','optical'];thresholds={};cal={}
 config=dict(schema='minemind-cached/1',fit='NONE:reuse frozen8dim masked-sensor encoder',checkpoint_sha256=manifest['encoder_sha256'],normalization='original BEFORE TRAIN only; unchanged',modes=modes,pretext='existing SAR/optical masked Huber reconstruction',calibration='same four spatially disjoint frozen calibration groups;match frozen81cellreviewquota per method/mode;no heldout tuning',decision='no promotion based on this stress test;Phase15Cremains primary',study='controlled sensor withholding on real observed replica pixels;not naturally missing-sensor validation',future_information='No follow-up,pseudo-label,human review,NRSCorTESTinput',runtime_cap_seconds=300,status='EXPLORATORY',operational_alerts=0)
 save(OUT/'frozen_config.json',config)
 for mode in modes:
  for method in ['ssl','physical']:
   key=method+'_'+mode
   if key=='ssl_both':thresholds[key]=old['calibration']['thresholds']['ssl'];continue
   values=[]
   for tile in splits['validation'].values():
    m=eligible(tile);a=tile['values'][:4,m].T;b=tile['values'][4:8,m].T
    values.append(change(model,a,b,center,spread,mode)[0] if method=='ssl' else physical(a,b,spread,mode))
   values=np.concatenate(values);thresholds[key]=cutoff(values,quota);cal[key]=dict(cells=len(values),selected=int((values>=thresholds[key]).sum()))
 report={}
 for site,replicas in held.items():
  mask=eligible(replicas[0])&eligible(replicas[1]);methods={};identity=__import__('hashlib').sha256(mask.tobytes()+str(replicas[0]['bounds']).encode()).hexdigest()
  for key in ['phase15c','ssl_both','physical_both','ssl_sar','physical_sar','ssl_optical','physical_optical']:
   if time.monotonic()-start>300:raise TimeoutError('Bounded no-fit analysis cap')
   folder=OUT/site/key;folder.mkdir(parents=True);is_frozen=key in ['phase15c','ssl_both'];scores=[];threshold=old['calibration']['thresholds']['phase15c'] if key=='phase15c' else thresholds[key]
   for i,tile in enumerate(replicas,1):
    if is_frozen:
     source=BASE/f"{site}-{'phase15c' if key=='phase15c' else 'ssl'}-r{i}.tif"
     with rasterio.open(source) as ds:
      if not np.array_equal(ds.read(2).astype(bool),mask) or ds.transform!=tile['profile']['transform']:raise ValueError('Frozen identical-support gate')
      score=ds.read(1)[mask]
    else:
     method,mode=key.split('_');a=tile['values'][:4,mask].T;b=tile['values'][4:8,mask].T
     score=change(model,a,b,center,spread,mode)[0] if method=='ssl' else physical(a,b,spread,mode)
    if not np.isfinite(score).all():raise ValueError('Unscorable common evaluation population')
    scores.append(score);geo,binary=candidates(tile,score,mask,threshold,site,key,i);save(folder/f'r{i}-candidates.geojson',geo)
    gridscore=np.full(mask.shape,NODATA,'float32');gridscore[mask]=score
    write_tile(folder/f'r{i}.tif',tile['profile'],('anomaly_score','common_valid','candidate_mask'),np.stack([gridscore,mask,binary]).astype('float32'),dict(status='REVIEW_REQUIRED',evidence_status='UNKNOWN',operational_alerts='0',score_kind='NOT_A_PROBABILITY',checkpoint_sha256=manifest['encoder_sha256'],mode=key))
   if is_frozen:
    metrics=old['sites'][site]['methods']['phase15c' if key=='phase15c' else 'ssl'];provenance='REUSED_FROZEN_RESULTS_NO_RECOMPUTATION'
   else:
    metrics=compare(*scores,mask,threshold);same=[]
    method,mode=key.split('_')
    for season in [0,1]:
     a=replicas[0]['values'][season*4:season*4+4,mask].T;b=replicas[1]['values'][season*4:season*4+4,mask].T
     p=change(model,a,b,center,spread,mode)[0] if method=='ssl' else physical(a,b,spread,mode);same.append(float((p>=threshold).mean()))
    metrics['same_season_exceedance']=same;provenance='NEW_CONTROLLED_WITHHOLDING_OR_TRAIN_SCALED_BASELINE'
   methods[key]=dict(metrics=metrics,threshold=threshold,evaluation_identity_sha256=identity,source=provenance)
  report[site]=dict(eligible_cells=int(mask.sum()),bounds=replicas[0]['bounds'],crs=str(replicas[0]['profile']['crs']),shape=list(mask.shape),methods=methods)
 save(OUT/'metrics.json',dict(sites=report,calibration=cal,thresholds=thresholds,training_seconds=0,analysis_seconds=time.monotonic()-start,weights_unchanged=sha(BASE/'encoder.pt')==manifest['encoder_sha256'],cache_sha256=cache_hash,status='EXPLORATORY',operational_alerts=0,decision='RETAIN_PHASE15C_PRIMARY;SSL_EXPERIMENTAL',limitations=['Previously examined application sites,not a freshTEST','Controlled withholding,not natural missingness','Pointwise encoder,no learned spatial context','Terrain context only;other context missing,not fabricated','Same-season exceedance is NOT trueFPR','Fixed <=25degree slope mask limits coverage;not a universal mining criterion']))
 save(OUT/'integrity.json',{p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()});print(json.dumps({s:{k:{'spearman':v['metrics']['spearman'],'top5':v['metrics']['top5_jaccard'],'polygons':v['metrics']['polygons']} for k,v in r['methods'].items()} for s,r in report.items()}),flush=True)

if __name__=='__main__':run()
