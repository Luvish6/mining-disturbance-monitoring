import copy
import json
from pathlib import Path

import numpy as np
import pytest

from src.phase25.features import Grid, align, stack_layers, pseudo_states, require_calibration_partition
from scripts.phase25b_cached import choose, read_development, run, validate_config

CFG = json.loads(Path('config/phase25b_v1.json').read_bytes())


def example():
    b=np.ones((6,2,2))*.1; b[3]=.8; b[4]=-.2; b[5]=-.1
    a=b.copy(); f=b.copy();a[3]=.4;a[4]=.1;f[3]=.3;f[4]=.1
    counts=np.ones((2,2))*3;vv=np.ones((2,2))*-10;vh=vv-5
    return b,a,f,counts,counts.copy(),counts.copy(),vv,vv-2,vh,vh-2,counts.copy(),counts.copy(),np.ones((2,2))*50


def test_three_states_and_missing_follow_sar_are_not_background():
    x=list(example());x[7]=x[7].copy();x[7][0,1]=np.nan;x[2][:,1,0]=np.nan
    # One spectrally stable cell, still only a potential background pseudo state.
    x[1][:,1,1]=x[0][:,1,1];x[2][:,1,1]=x[0][:,1,1];x[7][1,1]=x[6][1,1];x[9][1,1]=x[8][1,1]
    state,e=pseudo_states(*x,CFG['rules'])
    assert state.tolist()==[[1,255],[255,0]]
    assert e['steep_context'].all() and state[0,0]==1


def test_water_cloud_counts_and_nonfinite_values_are_ignored():
    x=list(example());x[4][0,0]=1;x[1][5,0,1]=.2;x[1][3,1,0]=np.nan
    state,_=pseudo_states(*x,CFG['rules'])
    assert state.tolist()==[[255,255],[255,1]]
    x[3][0,0]=1.5
    with pytest.raises(ValueError):pseudo_states(*x,CFG['rules'])


def test_missing_sources_are_nan_false_not_zero():
    grid=Grid('EPSG:32646',(30,0,400000,0,-30,2800000),(2,2))
    stack,masks,status=stack_layers({},grid,CFG['layers'])
    assert stack.shape==(12,2,2) and np.isnan(stack).all() and not masks.any()
    assert set(status.values())=={'UNAVAILABLE'}


def test_alignment_rejects_wrong_affine_and_requires_opt_in():
    a=Grid('EPSG:32646',(30,0,0,0,-30,90),(3,3))
    b=Grid('EPSG:32646',(30,0,15,0,-30,90),(3,3))
    x=np.arange(9).reshape(3,3);m=np.ones((3,3),bool)
    with pytest.raises(ValueError):align(x,m,a,b,'continuous')
    y,valid=align(x,m,a,b,'categorical',allow_resampling=True)
    assert np.isin(y[valid],x).all()
    with pytest.raises(ValueError):Grid('EPSG:4326',(30,0,0,0,-30,90),(3,3))
    with pytest.raises(ValueError):align(x+.5,m,a,a,'count')


def test_official_test_split_is_rejected_before_payload_access(monkeypatch):
    import scripts.phase25b_cached as mod
    def forbidden(*args,**kwargs): raise AssertionError('Payload touched')
    monkeypatch.setattr(mod,'frozen',forbidden);monkeypatch.setattr(np,'load',forbidden)
    with pytest.raises(ValueError,match='No TEST'):
        read_development('80:559',dict(split='test',bounds=[1,2,3,4]),{},None,None)


def test_deterministic_metadata_only_selection_is_site_disjoint():
    plan=dict(aois={str(i):dict(split=s) for i,s in enumerate(['train']*8+['validation']*4+['test']*3)})
    a=choose(plan,dict(train=3,validation=1))
    plan['aois']=dict(reversed(list(plan['aois'].items())))
    assert a==choose(plan,dict(train=3,validation=1))
    assert len(set(a))==4 and all(plan['aois'][k]['split']!='test' for k in a)


def test_calibration_and_context_roles_cannot_imply_reference_accuracy():
    require_calibration_partition('train')
    for split in ['validation','test']:
        with pytest.raises(ValueError):require_calibration_partition(split)
    validate_config(CFG)
    c=copy.deepcopy(CFG);c['calibration']['independent_evaluation']=True
    with pytest.raises(ValueError):validate_config(c)
    c=copy.deepcopy(CFG);c['layers'][7]['role']='signal'
    with pytest.raises(ValueError):validate_config(c)
    c=copy.deepcopy(CFG);c['seasons']['before'][0]='2020-01-01'
    with pytest.raises(ValueError):validate_config(c)


def test_run_refuses_overwrite_and_traversal_before_any_read(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    p=Path('outputs/phase25/experiments/frozen');p.mkdir(parents=True)
    with pytest.raises(ValueError,match='overwrite'):run(None,'frozen')
    with pytest.raises(ValueError,match='run ID'):run(None,'../../historical')


def test_stack_checks_each_source_origin_instead_of_only_dimensions():
    a=Grid('EPSG:32646',(30,0,0,0,-30,60),(2,2))
    b=Grid('EPSG:32646',(30,0,15,0,-30,60),(2,2))
    spec=CFG['layers'][:1]
    with pytest.raises(ValueError,match='Grid mismatch'):
        stack_layers({'vegetation_change':(np.ones((2,2)),np.ones((2,2),bool),b)},a,spec)
