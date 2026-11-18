import numpy as np
from scripts.phase22l_temporal import select_candidates


def test_temporal_rule_masks_water_counts_and_nonfinite_slope():
    b=np.ones((6,1,6))*.1
    a=b.copy()
    b[3]=.7
    a[3]=.4
    a[4]=.3
    b[5]=a[5]=-.1
    slope=np.zeros((1,6))
    cb=np.full((1,6),2)
    ca=cb.copy()
    ca[0,1]=1
    a[5,0,2]=.1
    slope[0,3]=np.nan
    a[4,0,4]=.15
    a[3,0,5]=.6
    valid,mask,_,_=select_candidates(b,a,cb,ca,slope)
    assert valid.tolist()==[[True,False,False,False,True,True]]
    assert mask.tolist()==[[False,False,False,False,False,False]]
    a[3,0,0]=.39
    assert select_candidates(b,a,cb,ca,slope)[1][0,0]


def test_steep_slope_is_context_without_exclusion():
    b=np.zeros((6,1,1))
    a=b.copy()
    b[3]=.8
    a[3]=.4
    b[5]=a[5]=-.1
    a[4]=.2
    _,m,_,_=select_candidates(b,a,np.array([[2]]),np.array([[2]]),np.array([[60.]]))
    assert m[0,0]
