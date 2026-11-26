import json
from pathlib import Path
import pytest
from shapely.geometry import box
from scripts.minemind_geography import windows,PLAN,SPLIT,PLAN_SHA,SPLIT_SHA,save
from src.phase25.dataset import sha
from src.phase3.spatial import block_for,partition
from src.phase25.acquisition import MeteredHttp,BudgetStop


def test_frozen_metadata_selection_reproducible_and_inner_footprints():
    assert sha(PLAN)==PLAN_SHA and sha(SPLIT)==SPLIT_SHA
    p=json.loads(PLAN.read_bytes());g=json.loads(SPLIT.read_bytes())['groups']
    a=windows(p['patches'],g);b=windows(list(reversed(p['patches'])),g)
    assert a==b and len({r['state'] for r in a})==6
    assert sum(r['role']=='ssl_fit' for r in a)==4
    assert sum(r['role']=='geographic_holdout' for r in a)==2
    for r in a:
        assert box(*r['source_footprint']).covers(box(*r['bounds']))
        assert block_for(r['bounds'])==r['block'] and partition(r['block'])=='train'
        assert g[r['group_id']]['split']=='train'
        assert r['bounds'][2]-r['bounds'][0]==960 and all(x%30==0 for x in r['bounds'])


def test_conflicting_group_role_fails_without_acquisition():
    p=json.loads(PLAN.read_bytes());g=json.loads(SPLIT.read_bytes())['groups']
    row=next(r for r in p['patches'] if r['split']=='train');g[row['group_id']]['split']='test'
    with pytest.raises(ValueError):windows([row],g)


def test_no_silent_replacement_when_geographic_supply_insufficient():
    with pytest.raises(ValueError):windows([],{})


def test_immutable_plan_and_request_cap_no_network(tmp_path):
    p=tmp_path/'plan.json';save(p,dict(x=1));save(p,dict(x=1))
    with pytest.raises(ValueError):save(p,dict(x=2))
    class Never:
        def request(self,*a,**k):raise AssertionError('Network must not occur')
    m=MeteredHttp(tmp_path/'ledger',max_requests=0,max_bytes=100000000,session=Never())
    with pytest.raises(BudgetStop):m.request('https://earthengine.googleapis.com/test')
    m=MeteredHttp(tmp_path/'ledger',max_requests=40,max_bytes=10,response_cap=11,session=Never())
    with pytest.raises(BudgetStop):m.request('https://earthengine.googleapis.com/test')


def test_context_gate_reports_missing_built_context_without_fabrication():
    from scripts.minemind_geography_compare import expansion_gate
    rows=[dict(id=str(i),passes=True,state=str(i),role='ssl_fit' if i<3 else 'geographic_holdout',worldcover={'Map':{str(code):1024}}) for i,code in enumerate([10,20,40,80])]
    passes,families=expansion_gate(rows)
    assert passes and 'built' not in families and 'cropland' in families
    assert not expansion_gate(rows[:2])[0]


def test_replica_provenance_source_overlap_can_be_detected():
    from scripts.minemind_geography_compare import source_sets
    p=[dict(scenes=[dict(s1=[['A',1]],s2=[['B',2]])])]
    assert source_sets(p)=={'A','B'}


def test_completed_acquisition_never_initializes_network(tmp_path,monkeypatch):
    import scripts.minemind_geography as module
    import scripts.indian_ssl_pilot as loader
    import ee
    module.save(tmp_path/'plan.json',{'frozen':True});digest=sha(tmp_path/'plan.json')
    folder=tmp_path/'A'/'r1';folder.mkdir(parents=True);module.save(folder/'receipt.json',dict(plan_sha256=digest))
    folder=tmp_path/'A'/'r2';folder.mkdir();module.save(folder/'receipt.json',dict(plan_sha256=digest))
    module.save(tmp_path/'acquisition.json',dict(plan_sha256=digest,accepted=[dict(id='A',bounds=[0,0,960,960])],traffic=dict(requests=33)))
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'freeze',lambda:{})
    monkeypatch.setattr(loader,'read_tile',lambda _:dict(bounds=[0,0,960,960]))
    def forbidden(*a,**k):raise AssertionError('Completed acquisition must not initialize EE')
    monkeypatch.setattr(ee,'Initialize',forbidden);module.acquire()
    assert (tmp_path/'cache-integrity.json').is_file()
