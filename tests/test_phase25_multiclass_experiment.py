import numpy as np
import pytest
import torch
from src.phase25.multiclass_experiment import remap,metrics,masked_ce,sample_indices,fit_preprocessing,feature_families


def test_taxonomy_remap_excludes_unsupported_and_unknown():
    assert remap(np.array([0,1,2,3,4,255])).tolist()==[0,1,255,255,2,255]
    with pytest.raises(ValueError):remap(np.array([9]))


def test_metrics_undefined_class_and_predicted_counts():
    m=metrics(np.array([0,1,2,255]),np.array([0,1,0,2]),np.array([True,True,True,False]))
    assert m['confusion_matrix']==[[1,0,0],[0,1,0],[1,0,0]]
    assert m['classes']['4']['recall']==0 and m['support']==3
    z=metrics(np.array([0]),np.array([2]),np.array([True]))
    assert z['classes']['4']['recall'] is None and z['classes']['4']['f1'] is None
    assert z['predicted_counts']==[0,0,1]


def test_masked_multiclass_ce_equivalence_and_zero_ignored_gradient():
    torch.manual_seed(42);x=torch.randn(1,3,4,4,requires_grad=True);y=torch.randint(0,3,(1,4,4));y[:,0]=255;w=torch.tensor([1.,2.,3.])
    a=masked_ce(x,y,w);b=torch.nn.functional.cross_entropy(x,y,weight=w,ignore_index=255)
    assert torch.allclose(a,b,atol=1e-7)
    a.backward();assert x.grad[:,:,0].abs().sum()==0 and x.grad[:,:,1:].abs().sum()>0
    with pytest.raises(ValueError):masked_ce(x,torch.full_like(y,255),w)


def record(group,split='train'):
    return dict(row=dict(group_id=group,split=split,patch_id=group),y=np.arange(1024).reshape(32,32)%3,mask=np.ones((32,32),bool))


def test_sampling_unique_group_balanced_train_only():
    d=[record('a'),record('b')];a=sample_indices(d,cap=120);b=sample_indices(d,cap=120)
    assert np.array_equal(a,b) and len(a)==len(set(a))==120
    assert sum(a<1024)==60
    d[1]['row']['split']='validation'
    with pytest.raises(ValueError,match='validation'):sample_indices(d)


def test_imputer_fits_train_indices_not_validation_or_ignored():
    x=np.array([[1.,np.nan],[3.,2.],[999.,999.]])
    assert np.array_equal(fit_preprocessing(x,np.array([0,1])),[2.,2.])


def test_feature_family_excludes_future_scores_and_qa():
    names=['before_B2','before_VV','rainfall','surface_water','before_dw_count','follow_NDVI','confidence','weak_labels']
    train=[dict(row=dict(split='train'),x=np.array([[[1.]],[[2.]],[[3.]],[[np.nan]],[[5.]],[[6.]],[[7.]],[[8.]]]),mask=np.ones((1,1),bool))]
    f=feature_families(names,train)
    assert f==dict(optical=['before_B2'],sar=['before_VV'],fused=['before_B2','before_VV','rainfall'])


def test_invalid_new_snapshot_withdraws_instead_of_reusing_history(tmp_path):
    from scripts.phase25_model_portal import experimental_files,CACHE
    from scripts.phase25_multiclass_portal import NEW_CACHE
    old=tmp_path/CACHE;old.mkdir(parents=True);(old/'integrity.json').write_text('{}')
    (tmp_path/NEW_CACHE).mkdir(parents=True)
    assert experimental_files(tmp_path)=={}


def test_unet_checkpoint_loader_rejects_wrong_hash(tmp_path):
    from src.phase25.multiclass_experiment import load_unet
    p=tmp_path/'invalid.pt';p.write_bytes(b'not a model')
    with pytest.raises(ValueError,match='integrity'):load_unet(p,'wrong',p)
