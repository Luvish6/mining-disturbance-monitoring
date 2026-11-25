import json
from pathlib import Path
import numpy as np
import pytest
from src.phase25.multiclass import evidence
from src.phase25.acquisition import MeteredHttp,BudgetStop

T=json.loads(Path('config/phase25_multiclass_v1.json').read_bytes())['thresholds']

def fixture():
    a=lambda x:np.full((2,2),x,dtype='float32')
    v={s+'_'+b:a(x) for s in ['before','after'] for b,x in [('NDVI',.6),('BSI',0),('NDWI',-.3),('VV',-10),('VH',-18),('optical_count',3),('sar_count',3),('crops',0),('built',0),('water',0),('bare',0),('dw_count',3)]}
    v.update({n:a(x) for n,x in [('follow_NDVI',.6),('follow_BSI',0),('follow_NDWI',-.3),('follow_count',3),('burn_after',np.nan),('slope',20)]});return v

def disturbance(v,persist=True):
    v['after_NDVI'][:]=.1;v['after_BSI'][:]=.3;v['after_VV'][:]=-12;v['after_VH'][:]=-20
    if persist:v['follow_NDVI'][:]=.1;v['follow_BSI'][:]=.3


def test_stable_and_unattributed_persistent_classes():
    v=fixture();assert np.all(evidence(v,T)['labels']==0)
    disturbance(v);r=evidence(v,T);assert np.all(r['labels']==1)
    assert np.all(r['confidence']<=1) and np.all(r['uncertainty']>=0)
    assert 'mining_reference' not in r


def test_specific_classes_require_real_context_support():
    v=fixture();disturbance(v,False);v['before_crops'][:]=.8;v['after_crops'][:]=.8
    assert np.all(evidence(v,T)['labels']==2)
    v=fixture();disturbance(v);v['after_built'][:]=.8;v['before_built'][:]=.1
    assert np.all(evidence(v,T)['labels']==3)
    for k in ['before_crops','after_crops','before_built','after_built']:v[k][:]=np.nan
    assert np.isnan(evidence(v,T)['scores'][2:4]).all()


def test_margin_missing_follow_and_fire_abstain():
    v=fixture();disturbance(v);t=dict(T,minimum_margin=.5)
    assert np.all(evidence(v,t)['labels']==255)
    v['follow_NDVI'][:]=np.nan;assert np.all(evidence(v,T)['labels']==255)
    v=fixture();v['burn_after'][:]=1;assert np.all(evidence(v,T)['labels']==255)
    v=fixture();v['before_sar_count'][:]=np.nan;assert np.all(evidence(v,T)['labels']==255)


def test_shared_request_budget_not_reset(tmp_path):
    p=tmp_path/'ledger.jsonl';p.write_text(''.join(json.dumps(dict(state='COMPLETE',response_bytes=1,reserved_bytes=2))+'\n' for _ in range(60)))
    meter=MeteredHttp(p)
    with pytest.raises(BudgetStop):meter.request('https://earthengine.googleapis.com/forbidden')
    assert meter.summary()['requests']==60


def test_loader_rejects_future_annotation_leak_and_tampering(tmp_path,monkeypatch):
    import src.phase25.multiclass_data as data
    from src.phase25.dataset import sha
    monkeypatch.setattr(data,'spatial_check',lambda rows:None)
    m=dict(schema='mci-multiclass/1',label_semantics='WEAK_ALGORITHMIC_HYPOTHESES_NOT_REFERENCE',reference_labels=None,patches=[],model_input_bands=['follow_NDVI'],annotation_only_bands=['follow_NDVI'])
    path=tmp_path/'manifest.json';path.write_text(json.dumps(m));(tmp_path/'integrity.json').write_text(json.dumps({'manifest.json':sha(path)}))
    with pytest.raises(ValueError,match='leakage'):data.load_dataset(tmp_path)
    path.write_text('changed')
    with pytest.raises(ValueError,match='integrity'):data.load_dataset(tmp_path)
