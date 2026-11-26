"""Versioned private investigation dataset; V2 labels and historical artifacts unchanged."""
import io,json,base64
from pathlib import Path
import numpy as np
import rasterio
from PIL import Image
from scipy.ndimage import label
from scipy.stats import spearmanr
from src.phase25.dataset import sha,spatial_check
from src.phase25.multiclass_data import load_dataset
from src.phase25.ngdr_context import archives,context
from src.phase25.investigation import NAMES,PHYSICAL,fit_scales,components,adaptive_weights,combine
from scripts.phase25b_cached import backup_gate,tif
from src.phase25.features import Grid

PARENT=Path('outputs/phase25/datasets/minechange-india-multiclass-v2')
SUP=Path('outputs/phase25/datasets/competing-supplement-v1')
OUT=Path('outputs/phase25/datasets/minechange-india-investigation-v3_1')


def save(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def array(a):return np.where(np.isfinite(a),a,None).tolist()

def preview(v,season):
 keys=[season+'_'+b for b in ['B4','B3','B2']]
 if not all(k in v for k in keys):return None
 a=np.stack([v[k] for k in keys],-1);valid=np.isfinite(a).all(-1);rgba=np.dstack([(np.clip(np.nan_to_num(a)/.3,0,1)*255).astype('uint8'),valid.astype('uint8')*255]);b=io.BytesIO();Image.fromarray(rgba).save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()


def load_sources():
 if sha(PARENT/'integrity.json')!='bd44f12ab2371f5930e287315c4e3ee86d5599f9a0da82b3bcff508445d98a78':raise ValueError('Frozen V2 inventory changed')
 m=load_dataset(PARENT);rows=[]
 inventory=json.loads((SUP/'integrity.json').read_bytes())
 for name,digest in inventory.items():
  p=(SUP/name).resolve()
  if not p.is_relative_to(SUP.resolve()) or sha(p)!=digest:raise ValueError('Supplement inventory mismatch')
 for r in m['patches']:rows.append((r,PARENT/r['output_folder']/'observations.tif',m['bands'],PARENT/r['output_folder']/'weak_classes.tif'))
 e=json.loads((SUP/'extension_manifest.json').read_bytes())
 if e['parent_integrity_sha256']!=sha(PARENT/'integrity.json') or not e['test_sealed']:raise ValueError('Supplement parent/split integrity')
 plan=json.loads((SUP/'frozen_plan.json').read_bytes())
 for r in e['new_train_patches']:
  original=next(w for w in plan['windows'] if w['aoi']==r['group_id'])
  r=dict(r,parent_bounds=original['bounds'],row_offset=int((original['bounds'][3]-r['affine'][5])/30),col_offset=int((r['affine'][2]-original['bounds'][0])/30))
  folder=SUP/r['folder'];p=folder/'source_stack.tif'
  if r['split']!='train' or sha(p)!=r['source_sha256'] or sha(folder/'source_receipt.json')!=r['source_receipt_sha256']:raise ValueError('Supplement integrity')
  bands=json.loads((folder/'export_band_order.json').read_bytes())['bands'];rows.append((r,p,bands,folder/'weak_classes.tif'))
 spatial_check([r for r,_,_,_ in rows]);data=[]
 for r,p,bands,weak in rows:
  if r['split'] not in ['train','validation']:raise ValueError('TEST excluded')
  with rasterio.open(p) as ds:
   if ds.shape!=(32,32) or ds.crs.to_string()!=r['crs'] or list(ds.transform)[:6]!=r['affine']:raise ValueError('Source grid mismatch')
   a=ds.read().astype('float32');a[a==-9999]=np.nan
  if a.shape[0]!=len(bands):raise ValueError('Band metadata mismatch')
  data.append(dict(row=r,v=dict(zip(bands,a)),source=p,weak=weak))
 return m,data


def build():
 backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
 if OUT.exists():raise ValueError('Never overwrite dataset')
 m,data=load_sources();records,provenance=archives('data/Indian Sources');scales=fit_scales([(d['row'],d['v']) for d in data if d['row']['split']=='train'])
 OUT.mkdir(parents=True);(OUT/'patches').mkdir();parts={};geo_codes=None
 for d in data:
  r=d['row'];ctx,codes=context(records,r);d['context']=ctx;geo_codes=codes
  parts[r['patch_id']]={mode:components(d['v'],scales,ctx[2],mode=='retrospective') for mode in ['pair','retrospective']}
 weights={mode:adaptive_weights([parts[d['row']['patch_id']][mode] for d in data if d['row']['split']=='train']) for mode in ['pair','retrospective']}
 config=dict(schema='investigation-evidence/1.1',families=NAMES,physical_weights=PHYSICAL.tolist(),equal_weights=[1/7]*7,adaptive_weights=weights,scales=scales,minimum_weight_coverage=.6,default_threshold=60,sensitivity_thresholds=[40,60,80],minimum_component_cells=4,competing_margin=10,labels='UNCHANGED WEAK hypotheses, never reference labels',retrospective='Persistence uses2025-26followup; pair mode never uses it',geology='Coal/limestone context0.6,other mapped units0.25; exploratory relevance not mining evidence. Terrain neutral0.5,not flat-land assumption. Lease presence hasZEROweight; lease footprints are not pits.',rights='PRIVATE ONLY; NGDR product-specific redistribution not established; no contact fields retained',sources=provenance,bhuvan=json.loads(Path('outputs/phase25/receipts/studio-source-access-v1.json').read_bytes()),evidence_basis=['https://www.mdpi.com/2072-4292/17/4/630','https://www.sciencedirect.com/science/article/pii/S034181622200251X','https://geodataindia.gov.in/terms_conditions'],terrain_safeguard='Terrain-only competing evidence capped at0.5; steep slope alone never forces rejection',weight_interpretation='Directions informed by vegetation/exposure physics and index confounding literature. Numeric weights/cutoffs are exploratory,not literature-validated mining thresholds; TRAIN-only coverage/redundancy adjusts physical weights.')
 save(OUT/'config.json',config);summary={};patches=[];comparison=[]
 for d in data:
  r=d['row'];pid=r['patch_id'];folder=OUT/'patches'/pid;folder.mkdir();grid=Grid(r['crs'],tuple(r['affine']),tuple(r['shape']));ctx=d['context']
  tif(folder/'ngdr_context.tif',ctx,grid,['NGDR_LITHOLOGY_CODE','NGDR_LEASE_PRESENCE_NOT_EXCAVATION','GEOLOGY_CONTEXT_RELEVANCE'])
  tif(folder/'context_validity.tif',np.isfinite(ctx).astype('uint8'),grid,['LITHOLOGY_VALID','LEASE_KNOWN_PRESENCE','GEOLOGY_VALID'],dtype='uint8',nodata=255)
  results={};payload=dict(id=pid,split=r['split'],group=r['group_id'],crs=r['crs'],affine=r['affine'],shape=r['shape'],bounds=r['bounds'],images={s:preview(d['v'],s) for s in ['before','after']},modes={},context=dict(lithology=array(ctx[0]),lease=array(ctx[1])),source_sha256=sha(d['source']),status='UNKNOWN',operational_alerts=0,dates={'before':['2023-11-01','2024-04-01'],'after':['2024-11-01','2025-04-01']})
  for mode,p in parts[pid].items():
   result=combine(p,weights[mode]);tif(folder/f'{mode}_contributions.tif',p['values'],grid,NAMES);tif(folder/f'{mode}_score.tif',np.stack([result['score'],result['coverage'],result['uncertainty']]),grid,['MINING_LIKE_EVIDENCE_NOT_PROBABILITY','AVAILABLE_WEIGHT_COVERAGE','HEURISTIC_UNCERTAINTY'])
   payload['modes'][mode]=dict(contributions=array(p['values']),valid=p['valid'].tolist(),competitors=array(p['competitors']))
   s=summary.setdefault(r['split'],dict(patches=0,geology_cells=0,lease_cells=0,eligible_cells=0,candidate_cells=0))
   if mode=='pair':s['patches']+=1;s['geology_cells']+=int(np.isfinite(ctx[0]).sum());s['lease_cells']+=int(np.isfinite(ctx[1]).sum());s['eligible_cells']+=int(np.isfinite(result['score']).sum());s['candidate_cells']+=int(result['candidate'].sum())
   for preset,w in [('equal',[1/7]*7),('physical',PHYSICAL),('adaptive',weights[mode])]:
    z=combine(p,w)
    for threshold in [40,60,80]:
     zz=combine(p,w,threshold);ids,n=label(zz['candidate']);counts=np.bincount(ids.ravel());keep=counts>=4;keep[0]=False
     comparison.append(dict(patch=pid,split=r['split'],group=r['group_id'],mode=mode,weighting=preset,threshold=threshold,candidate_cells=int(keep[ids].sum()),clusters=int(keep.sum()),eligible_cells=int(np.isfinite(zz['score']).sum())))
  with rasterio.open(d['weak']) as ds:original_labels=ds.read(1)
  inputs=m['model_input_bands'];x=np.stack([d['v'].get(n,np.full((32,32),np.nan)) for n in inputs]+[ctx[0],ctx[1]])
  np.savez_compressed(folder/'model_ready.npz',features=x,validity=np.isfinite(x),weak_labels=original_labels,label_valid=original_labels!=255)
  # Keep inherited rule as shared-source comparison, never ground truth.
  v=d['v'];old=(v['after_NDVI']-v['before_NDVI']<=-.3)&(v['after_BSI']-v['before_BSI']>.1)&(v['after_VV']<=v['before_VV'])&(v['after_VH']<=v['before_VH'])&parts[pid]['pair']['valid']
  payload['legacy_rule']=old.tolist();save(folder/'studio.json',payload)
  patches.append(dict(patch_id=pid,split=r['split'],group_id=r['group_id'],crs=r['crs'],affine=r['affine'],bounds=r['bounds'],shape=r['shape'],folder=folder.relative_to(OUT).as_posix(),source_observations=d['source'].as_posix(),source_sha256=sha(d['source']),weak_labels_source=d['weak'].as_posix(),weak_labels_sha256=sha(d['weak']),reference_labels=None,status='UNKNOWN'))
 save(OUT/'manifest.json',dict(version='MineChange-India-investigation-v3.1',parent=PARENT.as_posix(),parent_manifest_sha256=sha(PARENT/'manifest.json'),parent_integrity_sha256=sha(PARENT/'integrity.json'),supplement_manifest_sha256=sha(SUP/'extension_manifest.json'),model_input_bands=m['model_input_bands']+['ngdr_lithology_code','ngdr_lease_presence'],categorical_bands=['ngdr_lithology_code'],annotation_only=['retrospective_persistence'],patches=patches,labels='Inherited unverified weak labels unchanged; evidence not ground truth',test_sealed=True,licensing='Private research; provider-specific redistribution pending',lithology_dictionary=geo_codes))
 save(OUT/'summary.json',dict(splits=summary,source_features={k:len(v) for k,v in records.items()},verified_mining_labels=0,operational_alerts=0));save(OUT/'sensitivity.json',comparison)
 (OUT/'DATASET_CARD.md').write_text('# Private MineChange-India investigation v3.1\n\n82original compatible patches; no sampling or split changes. NGDR lithology is mapped context, not30m geology observations. Lease2022is administrative known-presence,not excavation or change. Unmapped/outside coverage isNaN; absence is not verified negative. Contact attributes stripped. All inherited labels remain weak. Pair-only mode excludes future persistence; retrospective mode explicitly uses2025-26follow-up. Numeric weights/cutoffs are exploratory,not learned mining probabilities. Coarse environmental information is contextual only. Bhuvan numeric classes unavailable,approval pending. No external release permission; restricted source/derivatives remain local.\n',encoding='utf-8')
 save(OUT/'integrity.json',{p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()});print(json.dumps(dict(path=OUT.as_posix(),summary=summary)))

if __name__=='__main__':build()
