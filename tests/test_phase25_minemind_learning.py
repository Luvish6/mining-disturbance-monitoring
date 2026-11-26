import numpy as np
import pytest
import torch
from scripts.indian_ssl_pilot import Encoder
from src.phase25.minemind_learning import fit_reliability, score


def fixture():
    torch.manual_seed(42)
    model=Encoder().eval();x=np.random.default_rng(42).normal(size=(30,4)).astype('float32');c=np.full((30,2),4.)
    return model,x,c,fit_reliability(model,x,c,np.zeros(4),np.ones(4))


def test_weights_are_normalized_and_count_quality_is_used():
    m,x,c,s=fixture();q=c.copy();q[:,0]=2
    a,w=score(m,x,x+.1,c,q,np.zeros(4),np.ones(4),s)
    assert np.isfinite(a).all() and np.allclose(w.sum(1),1)
    _,other=score(m,x,x+.1,c,c,np.zeros(4),np.ones(4),s)
    assert (w[:,0]<other[:,0]).all()


def test_missing_modalities_are_not_imputed_as_observations():
    m,x,c,s=fixture();y=x.copy();y[:,:2]=np.nan
    a,w=score(m,x,y,c,c,np.zeros(4),np.ones(4),s)
    assert np.isfinite(a).all() and (w[:,0]==0).all() and (w[:,1]==1).all()
    y[:,2:]=np.nan
    a,w=score(m,x,y,c,c,np.zeros(4),np.ones(4),s)
    assert np.isnan(a).all() and (w==0).all()


def test_withheld_values_cannot_change_optical_result():
    m,x,c,s=fixture();y=x+.1;z=x.copy();z[:,:2]=999
    a,w=score(m,x,y,c,c,np.zeros(4),np.ones(4),s,'optical')
    b,_=score(m,z,y,c,c,np.zeros(4),np.ones(4),s,'optical')
    assert np.array_equal(a,b) and (w[:,1]==1).all()


def test_same_input_zero_change_and_invalid_mode():
    m,x,c,s=fixture();a,_=score(m,x,x,c,c,np.zeros(4),np.ones(4),s)
    assert (a==0).all() and s['fit_season']=='TRAIN_BEFORE_ONLY'
    with pytest.raises(ValueError):score(m,x,x,c,c,np.zeros(4),np.ones(4),s,'fake')


def test_temporal_loss_reaches_encoder_without_labels():
    torch.manual_seed(42);m=Encoder();head=torch.nn.Linear(8,4);x=torch.randn(16,4);y=x+.1
    loss=torch.nn.functional.huber_loss(head(m.view(y,0)-m.view(x,0)),y-x)
    loss.backward()
    assert any(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum()>0 for p in m.encoder.parameters())


def test_corrupt_train_state_and_invalid_fit_fail_closed():
    m,x,c,s=fixture();s['latent_scale'][0][0]=0
    with pytest.raises(ValueError):score(m,x,x,c,c,np.zeros(4),np.ones(4),s)
    x[0,0]=np.nan
    with pytest.raises(ValueError):fit_reliability(m,x,c,np.zeros(4),np.ones(4))
