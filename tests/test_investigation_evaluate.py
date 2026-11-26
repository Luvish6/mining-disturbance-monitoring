import numpy as np
import pytest
from scripts.investigation_evaluate import connected,configurations,jaccard
from src.phase25.investigation import combine

def test_weight_zero_retains_spectral_prerequisite():
    a=np.ones((7,2,2));a[0]=0
    parts=dict(values=a,valid=np.ones((2,2),bool),competitors=np.zeros((3,2,2)))
    assert not combine(parts,[0,1,1,1,1,1,1],20)['candidate'].any()
    a[0]=1;a[1]=0
    assert not combine(parts,[1,0,1,1,1,1,1],20)['candidate'].any()

def test_sizes_and_four_connectivity():
    a=np.eye(3,dtype=bool)
    assert connected(a,1)[1]==3
    assert connected(a,2)[1]==0
    assert jaccard(a,a)==1
    assert jaccard(a&False,a&False) is None
    with pytest.raises(ValueError):connected(a,3)

def test_frozen_all_family_ablation():
    cfg={'adaptive_weights':{'pair':[1/7]*7}}
    rows=list(configurations(cfg,'pair'));assert len(rows)==24
    assert sum(a=='none' for _,a,_ in rows)==3
    for _,a,w in rows:
        if a!='none':assert w[['vegetation','soil','sar','persistence','terrain','geology','environment'].index(a)]==0
