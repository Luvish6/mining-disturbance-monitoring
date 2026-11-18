import numpy as np
import pytest
from scripts import phase22k_rules as rules


def test_indices_and_zero_denominators():
    x=np.array([[.2,.3],[.1,.2],[.3,.1]])
    v=rules.indices(x)
    np.testing.assert_allclose(v[0],[.5,.2,-.2])
    with pytest.raises(ValueError,match="denominators"):
        rules.indices(np.array([[1.],[0.],[0.]]))


def test_histogram_selection_matches_direct_train_search():
    from itertools import product
    rng=np.random.default_rng(42)
    x=rng.uniform(-.5,.8,(70,3))
    x=np.concatenate((x,np.array([[.2,.04,-.1],[.3,.1,.2]])))
    y=rng.integers(0,2,len(x))
    selected=rules.select_train(x,y)
    for n,key in enumerate(("A","B","C"),1):
        expected=None
        best=-1
        for t in product(*rules.GRIDS[:n]):
            pred=rules.rule(x,t)
            tp=int((pred&(y==1)).sum())
            fp=int((pred&(y==0)).sum())
            score=2*tp/(int(y.sum())+tp+fp)
            if score>best:
                expected=list(t)
                best=score
        assert selected[key]==expected


def test_strict_rule_boundaries_and_masked_unknown():
    x=np.array([[.2,.10,0.],[.19,.10,0.],[.19,.11,.1],[.19,.11,.09]])
    assert rules.rule(x,[.2,.1,.1]).tolist()==[False,False,False,True]
    row={"group_id":"a","negative_stratum":"random"}
    samples=[(row,np.ones((3,1,3)),np.array([[True,False,True]]),np.array([[0,1,255]]))]
    values,y,_,_=rules.flatten(samples)
    assert len(y)==1 and y[0]==0 and len(values)==1
