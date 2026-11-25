import json
import numpy as np
import pytest
from src.phase25.competing_classes import competing_evidence,reducer_limit,thematic_gate
from scripts.phase25_competing_recover import choose
from src.phase25.acquisition import MeteredHttp,BudgetStop

T=json.loads(__import__('pathlib').Path('config/phase25_multiclass_v1.json').read_bytes())['thresholds']


def fixture():
 a=lambda x:np.full((2,2),x,dtype='float32')
 v={s+'_'+b:a(x) for s in ['before','after'] for b,x in [('NDVI',.6),('BSI',0),('NDWI',-.3),('VV',-10),('VH',-18),('optical_count',3),('sar_count',3),('crops',0),('built',0),('dw_count',3)]}
 v.update({n:a(x) for n,x in [('follow_NDVI',.6),('follow_BSI',0),('follow_NDWI',-.3),('follow_count',3),('burn_after',np.nan),('land_cover',40),('follow_built',0),('follow_dw_count',3)]})
 for s in ['before','after']:
  for p in ['early','late']:
   for b,x in [('NDVI',.6),('BSI',0),('count',3)]:v[s+'_'+p+'_'+b]=a(x)
 return v


def test_agriculture_does_not_require_mining_like_decline_or_sar_decrease():
 v=fixture();v['after_NDVI'][:]=.7;v['after_VV'][:]=-8;v['after_VH'][:]=-16
 v['before_early_NDVI'][:]=.2;v['before_early_BSI'][:]=.2
 assert (competing_evidence(v,T)['labels']==2).all()
 v['before_early_count'][:]=1
 assert not (competing_evidence(v,T)['labels']==2).any()


def test_static_landcover_without_temporal_evidence_cannot_label_agriculture():
 assert not (competing_evidence(fixture(),T)['labels']==2).any()


def test_construction_needs_paired_gain_follow_persistence_not_static_urban():
 v=fixture();v['land_cover'][:]=50;v['before_built'][:]=.1;v['after_built'][:]=.8;v['after_NDVI'][:]=.4;v['follow_built'][:]=.8
 assert (competing_evidence(v,T)['labels']==3).all()
 v['follow_built'][:]=np.nan
 assert not (competing_evidence(v,T)['labels']==3).any()


def test_fire_and_missing_observation_abstain():
 v=fixture();v['before_early_NDVI'][:]=.2;v['before_early_BSI'][:]=.2;v['burn_after'][:]=1
 assert (competing_evidence(v,T)['labels']==255).all()
 v=fixture();v['before_optical_count'][:]=0
 assert (competing_evidence(v,T)['labels']==255).all()


def test_corrected_multiband_reducer_limit():
 assert reducer_limit((32,32),2)==4096
 with pytest.raises(ValueError):reducer_limit((0,32),2)


def test_selection_train_only_deterministic_no_quotas():
 rows=[dict(aoi='a',split='train'),dict(aoi='b',split='train')];scores={'a':dict(crop_context_cells=2,built_gain_context_cells=0),'b':dict(crop_context_cells=1,built_gain_context_cells=0)}
 assert choose(rows,scores)==choose(rows,scores) and len(choose(rows,scores))==2
 assert choose(rows,{k:dict(crop_context_cells=0,built_gain_context_cells=0) for k in scores})==[]
 rows[0]['split']='validation'
 with pytest.raises(ValueError):choose(rows,scores)


def test_new40request_cap_no_reset(tmp_path):
 ledger=tmp_path/'new.jsonl';ledger.write_text(''.join(json.dumps(dict(state='COMPLETE',response_bytes=1,reserved_bytes=2000000))+'\n' for _ in range(40)))
 meter=MeteredHttp(ledger,max_requests=40)
 with pytest.raises(BudgetStop):meter.request('https://earthengine.googleapis.com/no_request')
 assert meter.summary()['requests']==40


def test_wms_rgb_and_missing_legend_or_permission_cannot_be_labels():
 with pytest.raises(ValueError):thematic_gate(dict(representation='RGB',source_url='https://bhuvan.nrsc.gov.in'))
 m=dict(source_url='https://bhuvan.nrsc.gov.in',reference_dates=['2015-16'],crs='EPSG:4326',pixel_size_m=10,numeric_legend={1:'crop'},legend_sha256='a'*64,research_permission_evidence='document_hash',representation='numeric_class_ids')
 assert thematic_gate(m)['independent_reference'] is False
 with pytest.raises(ValueError):thematic_gate(dict(m,rendered_rgb=True))


def test_explicit_gee_fill_is_invalid_even_without_tiff_nodata_tag():
 from rasterio.io import MemoryFile
 from affine import Affine
 from src.phase25.competing_data import read_export_values
 with MemoryFile() as memory:
  with memory.open(driver='GTiff',width=2,height=2,count=1,dtype='float32',crs='EPSG:32646',transform=Affine(30,0,400000,0,-30,2800000)) as ds:ds.write(np.array([[[0,1],[-9999,2]]],dtype='float32'))
  with memory.open() as ds:
   assert ds.nodata is None
   a=read_export_values(ds)
   assert np.isnan(a[0,1,0]) and a[0,0,0]==0
