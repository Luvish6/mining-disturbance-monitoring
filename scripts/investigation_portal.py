"""Local-only investigation endpoints; no arbitrary model paths, downloads or labels."""
import json,io,csv,pickle,hashlib
from pathlib import Path
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.features import shapes
from rasterio.warp import transform_geom
from shapely.geometry import box
from scipy.ndimage import label
from scripts.investigation_dataset import OUT,array,preview
from src.phase25.dataset import sha
from src.phase25.investigation import components,combine,NAMES

RF=Path('outputs/external_minenetcd256/phase17d_run/rf.pkl')
RF_SHA='937c5c8c7165c0e0bc19425a48136a10dbe4ae009067249669c785e443bcf5bc'
UPLOADS={}


def studio_files(root):
 root=Path(root);folder=root/OUT
 if not (folder/'integrity.json').exists():return {}
 inventory=json.loads((folder/'integrity.json').read_bytes())
 for name,digest in inventory.items():
  p=(folder/name).resolve()
  if not p.is_relative_to(folder.resolve()) or sha(p)!=digest:raise ValueError('Studio dataset integrity')
 m=json.loads((folder/'manifest.json').read_bytes());cfg=json.loads((folder/'config.json').read_bytes())
 if not m['test_sealed'] or any(r['split'] not in ['train','validation'] for r in m['patches']):raise ValueError('Studio split gate')
 if sha(root/m['parent']/'manifest.json')!=m['parent_manifest_sha256']:raise ValueError('Parent provenance changed')
 for r in m['patches']:
  if sha(root/r['source_observations'])!=r['source_sha256'] or sha(root/r['weak_labels_source'])!=r['weak_labels_sha256']:raise ValueError('Original patch provenance changed')
 for source in cfg['sources']:
  if 'archive' in source and sha(root/'data/Indian Sources'/source['archive'])!=source['sha256']:raise ValueError('NGDR archive changed')
 rows=[dict(id=r['patch_id'],split=r['split'],group=r['group_id']) for r in m['patches']]
 payload=dict(patches=rows,config=cfg,lithology_dictionary=m['lithology_dictionary'],status='EXPLORATORY',operational_alerts=0,dataset_path=OUT.as_posix(),dataset_manifest_sha256=sha(folder/'manifest.json'),rgb_model_available=(root/RF).exists() and sha(root/RF)==RF_SHA)
 files={'studio/snapshot.json':('application/json',json.dumps(payload).encode())}
 for r in m['patches']:
  p=folder/r['folder']/'studio.json';files[f"studio/{r['patch_id']}.json"]=('application/json',p.read_bytes())
 return files


def filtered(result):
 ids,n=label(result['candidate']);counts=np.bincount(ids.ravel());keep=counts>=4;keep[0]=False;return keep[ids]


def exported(data,request):
 mode=request.get('mode','pair')
 if mode not in data['modes']:raise ValueError('Unavailable evidence mode')
 p=data['modes'][mode];parts=dict(values=np.asarray(p['contributions'],float),valid=np.asarray(p['valid'],bool),competitors=np.asarray(p['competitors'],float))
 result=combine(parts,request['weights'],float(request.get('threshold',60)));mask=filtered(result)
 from affine import Affine
 grid=Affine(*data['affine']);features=[]
 from rasterio.features import geometry_mask
 for geom,value in shapes(mask.astype('uint8'),mask=mask,transform=grid,connectivity=4):
  use=geometry_mask([geom],out_shape=mask.shape,transform=grid,invert=True);area=abs(grid.a*grid.e-grid.b*grid.d)*int(use.sum())
  props=dict(id=data['id']+'-'+str(len(features)+1),score_mean=float(np.mean(result['score'][use])),area_m2=area,pixels=int(use.sum()),uncertainty_mean=float(np.mean(result['uncertainty'][use])),contributions={n:float(np.mean(result['contributions'][i,use])) for i,n in enumerate(NAMES)},status='REVIEW_REQUIRED',mining_attribution='UNKNOWN',operational_alerts=0,mode=mode,threshold=request.get('threshold',60),weights=request['weights'],source_sha256=data['source_sha256'],interpretation='Mining-like evidence score,NOT validated probability or mining label')
  features.append(dict(type='Feature',geometry=transform_geom(data['crs'],'EPSG:4326',geom),properties=props))
 b=io.StringIO();fields=['id','score_mean','area_m2','pixels','uncertainty_mean','status','mining_attribution','mode','threshold'];w=csv.DictWriter(b,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows([f['properties'] for f in features])
 return dict(geojson=dict(type='FeatureCollection',features=features,provenance=dict(source=data['source_sha256'],dates=data['dates'],future_observations_used=(mode=='retrospective'),follow_window=['2025-11-01','2026-04-01'] if mode=='retrospective' else None,crs=data['crs'],affine=data['affine'],operational_alerts=0,source_kind=data.get('source_kind','CACHED_V2_EXTENSION'),evidence_config_sha256=data.get('evidence_config_sha256'),studio_payload_sha256=data.get('studio_payload_sha256'))),csv=b.getvalue(),candidate_cells=int(mask.sum()),clusters=len(features))


def inspect_upload(root,raw):
 if len(raw)>8_000_000:raise ValueError('Upload cap8MB')
 root=Path(root);m=json.loads((root/OUT/'manifest.json').read_bytes());cfg=json.loads((root/OUT/'config.json').read_bytes())
 with MemoryFile(raw) as memory,memory.open() as ds:
  if ds.crs is None or ds.crs.to_epsg()!=32646:raise ValueError('EPSG32646 metre grid required; no guessed georeferencing or area units')
  if ds.transform.b!=0 or ds.transform.d!=0 or ds.transform.a<=0 or ds.transform.e>=0:raise ValueError('North-up registered input required; no implicit warping')
  if ds.crs is None or ds.width>256 or ds.height>256 or ds.count>64 or ds.width<1 or ds.height<1:raise ValueError('Georeferenced image<=256x256/64bands required')
  # Header-only spatial gate BEFORE pixel reads; never inspect frozen TEST payloads.
  bounds=box(*ds.bounds);approved=[]
  for r in m['patches']:
   allowed=box(*r['bounds']);geo=transform_geom(r['crs'],ds.crs.to_string(),allowed.__geo_interface__)
   from shapely.geometry import shape
   if shape(geo).buffer(1e-8).covers(bounds):approved.append(r)
  if not approved:raise ValueError('Upload outside approved TRAIN/VAL footprint; TEST and unknown regions blocked')
  names=list(ds.descriptions)
  if any(n is None for n in names) or len(set(names))!=len(names):raise ValueError('Explicit unique named-band descriptions required; no guessed channels')
  a=ds.read(masked=True).astype('float32').filled(np.nan);a[a==-9999]=np.nan;v=dict(zip(names,a));tags=ds.tags();crs=ds.crs.to_string();affine=list(ds.transform)[:6];shape_out=[ds.height,ds.width];native_dtype=ds.dtypes
 required=[s+'_'+b for s in ['before','after'] for b in ['NDVI','BSI','VV','VH']]
 score_ready=all(n in v for n in required) and tags.get('sar_units')=='dB' and bool(tags.get('before_date')) and bool(tags.get('after_date'))
 if score_ready:
  from datetime import date
  if date.fromisoformat(tags['before_date'])>=date.fromisoformat(tags['after_date']):raise ValueError('Ordered before/after acquisition dates required')
 modes={}
 if score_ready:
  for s in ['before','after']:
   for family in ['optical','sar']:
    name=s+'_'+family+'_count'
    if name in v:
     q=v[name][np.isfinite(v[name])]
     if np.any(q<0) or np.any(q!=np.floor(q)):raise ValueError('Observation counts must be nonnegative integers')
  for name in ['before_NDVI','after_NDVI','before_BSI','after_BSI']:
   values=v[name][np.isfinite(v[name])]
   if np.any(np.abs(values)>1.01):raise ValueError('Index units/range incompatible')
  p=components(v,cfg['scales']);modes['pair']=dict(contributions=array(p['values']),valid=p['valid'].tolist(),competitors=array(p['competitors']))
 rgb_names=[s+'_'+b for s in ['before','after'] for b in ['R','G','B']];rgb=all(n in v for n in rgb_names) and set(native_dtype)=={'uint8'}
 images={s:preview(v,s) for s in ['before','after']};rgb_score=None
 if rgb:
  # RGB benchmark inputs are native uint8,not fabricated NIR/SWIR or rescaled SR.
  from PIL import Image
  import base64
  for s in ['before','after']:
   x=np.stack([v[s+'_'+b] for b in ['R','G','B']],-1);valid=np.isfinite(x).all(-1);b=io.BytesIO();Image.fromarray(np.dstack([np.nan_to_num(x).astype('uint8'),valid.astype('uint8')*255])).save(b,format='PNG');images[s]='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
  path=root/RF
  if path.exists() and sha(path)==RF_SHA:
   model=pickle.loads(path.read_bytes());x=np.stack([v['after_'+b]-v['before_'+b] for b in ['R','G','B']],-1).reshape(-1,3);valid=np.isfinite(x).all(1);probs=np.full(len(x),np.nan)
   if model.n_features_in_!=3 or list(model.classes_)!=[0,1]:raise ValueError('Frozen RGB contract mismatch')
   probs[valid]=model.predict_proba(x[valid])[:,1];rgb_score=array(probs.reshape(shape_out))
 if not any(images.values()) and not modes:raise ValueError('No compatible registered feature stack or named native uint8 paired RGB. No bands fabricated.')
 if all(images.values()) and not rgb and tags.get('reflectance_units')!='0_1':images={'before':None,'after':None}
 data=dict(id='upload-'+__import__('hashlib').sha256(raw).hexdigest()[:16],split=approved[0]['split'],group=approved[0]['group_id'],crs=crs,affine=affine,shape=shape_out,bounds=list(bounds.bounds),images=images,modes=modes,context={},source_sha256=__import__('hashlib').sha256(raw).hexdigest(),source_kind='UPLOAD_UNVERIFIED_PRIVATE',bands=names,dates={s:tags.get(s+'_date','UNAVAILABLE') for s in ['before','after']},status='UNKNOWN',operational_alerts=0,rgb_probabilities=rgb_score,rgb_model_status='EXTERNAL_RGB_BENCHMARK_ONLY_NOT_VALIDATED_INDIA',unavailable='Missing channels/QA stay unavailable. RGB preview is not a multi-sensor mining result; fixed RGB cutoff0.65, no calibration.')
 if len(UPLOADS)>=2:UPLOADS.pop(next(iter(UPLOADS)))
 UPLOADS[data['id']]=data
 return data


def studio_post(root,path,raw,rights=False):
 if path=='/__studio__/inspect':
  if not rights:raise ValueError('Confirm private authorized use and no TEST input')
  return inspect_upload(root,raw)
 if path!='/__studio__/export':raise ValueError('Unknown Studio endpoint')
 request=json.loads(raw);pid=request.get('id');folder=Path(root)/OUT;m=json.loads((folder/'manifest.json').read_bytes())
 if pid in UPLOADS:data=UPLOADS[pid]
 else:
  r=next((r for r in m['patches'] if r['patch_id']==pid),None)
  if r is None:raise ValueError('Unknown approved patch')
  p=folder/r['folder']/'studio.json';inventory=json.loads((folder/'integrity.json').read_bytes())
  if sha(p)!=inventory[p.relative_to(folder).as_posix()]:raise ValueError('Studio source changed')
  data=json.loads(p.read_bytes());data['studio_payload_sha256']=sha(p)
 data['evidence_config_sha256']=sha(folder/'config.json')
 return exported(data,request)
