import copy
import numpy as np
import pytest
import torch
from torch import nn

from src.phase25.dataset import BANDS
from src.phase25.learning import (MEAN,SCALE,STD,RAW_BANDS,CONTRACT_SHA,adapt_patch,token_support,
    masked_bce_dice,FrozenEncoder,compare_contract,metric_counts)
from src.phase3.model import SiameseUNet


def sample():
    x=np.full((len(BANDS),32,32),np.nan,dtype='float32')
    for s in ['before','after']:
        for i,b in enumerate(RAW_BANDS):x[BANDS.index(s+'_'+b)]=MEAN[i]/SCALE[i]
    y=np.zeros((32,32),dtype='uint8');y[20:22,20:22]=1;y[31,31]=255
    return dict(features=x,validity=np.isfinite(x),pseudo_states=y)


def test_actual_band_mapping_once_and_identical_modality_inputs():
    d=adapt_patch(sample());assert d['before'].shape==(1,5,32,32)
    assert torch.allclose(d['before'],torch.zeros_like(d['before']),atol=1e-6)
    assert torch.equal(d['terramind_before']['S2L2A'],d['before'][:,:3])
    assert torch.equal(d['terramind_after']['S1GRD'],d['after'][:,3:])
    assert not d['mask'][0,0,31,31] and d['target'][0,0,31,31]==255
    with pytest.raises(ValueError,match='NIR'):adapt_patch(sample(),bands=['B2','B3','B4','B8'])


def test_common_token_mask_is_label_independent_no_spatial_resampling():
    r=sample();r['features'][BANDS.index('before_B2'),0,0]=np.nan;r['validity']=np.isfinite(r['features'])
    d=adapt_patch(r);assert not d['token_common_valid'][:16,:16].any()
    assert d['token_common_valid'][16:,16:].all() and d['before'].shape[-2:]==(32,32)
    with pytest.raises(ValueError):token_support(np.ones((30,32),bool))
    r['pseudo_states']=None
    with pytest.raises(ValueError):adapt_patch(r)


def test_masked_gradient_ignore_background_and_empty_cases():
    z=torch.zeros((1,1,2,2),requires_grad=True);y=torch.tensor([[[[1.,0.],[255.,0.]]]])
    mask=torch.tensor([[[[True,True],[False,True]]]])
    loss=masked_bce_dice(z,y,mask,pos_weight=10);loss.backward()
    assert torch.isfinite(loss) and z.grad[0,0,1,0]==0 and z.grad[0,0,0,0]!=0
    with pytest.raises(ValueError):masked_bce_dice(z,y,torch.zeros_like(mask))
    with pytest.raises(ValueError):masked_bce_dice(z,y,mask,pos_weight=11)
    assert torch.isfinite(masked_bce_dice(z,torch.zeros_like(y),torch.ones_like(mask)))


def test_existing_unet_five_channels_forward_backward_only_no_updates():
    torch.manual_seed(42);torch.set_num_threads(1);model=SiameseUNet(channels=5,width=16)
    before={k:v.detach().clone() for k,v in model.state_dict().items()};d=adapt_patch(sample())
    z=model(d['before'],d['after']);assert z.shape==d['target'].shape
    masked_bce_dice(z,d['target'],d['mask']).backward()
    assert all(torch.equal(before[k],v) for k,v in model.state_dict().items())
    assert torch.allclose(z,model(d['after'],d['before']))  # preserved temporal symmetry


def test_frozen_encoder_never_updates_norm_or_backpropagates():
    encoder=nn.Sequential(nn.Conv2d(5,2,1),nn.BatchNorm2d(2));f=FrozenEncoder(encoder);f.train()
    state={k:v.detach().clone() for k,v in f.state_dict().items()};z=f(torch.randn(1,5,4,4,requires_grad=True))
    assert not z.requires_grad and not encoder.training
    assert all(not p.requires_grad for p in encoder.parameters())
    assert all(torch.equal(state[k],v) for k,v in f.state_dict().items())


def frame():
    return dict(contract_sha256=CONTRACT_SHA,dataset_sha256='3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa',
        split='validation',pixel_ids=['80:559:r0:c0','80:559:r0:c1'],group_ids=['80:559','80:559'],labels=[1,0],valid=np.array([True,True]),probabilities=[.8,.2])


def test_comparison_requires_exact_frozen_ids_labels_masks_and_groups():
    a=frame();compare_contract(a,copy.deepcopy(a),a)
    for key,value in [('pixel_ids',list(reversed(a['pixel_ids']))),('labels',[0,0]),('valid',np.array([False,True])),('split','test')]:
        b=copy.deepcopy(a);b[key]=value
        with pytest.raises(ValueError):compare_contract(a,b,a)
    a['group_ids']=['88:556','88:556']
    with pytest.raises(ValueError,match='group'):compare_contract(a,a,a)


def test_metrics_undefined_positive_support_and_uncertainty():
    z=metric_counts([0,0,255],[.9,.1,float('nan')],[True,True,False])
    assert z['recall'] is None and z['iou'] is None and z['dice_f1'] is None and z['fpr']==.5
    assert z['excluded_pixels']==1 and z['predicted_positive_pixels']==1
    z=metric_counts([1,0],[.1,.1],[True,True]);assert z['recall']==0 and z['dice_f1']==0 and z['precision'] is None
    with pytest.raises(ValueError):metric_counts([255],[.5],[True])


def test_all_ignored_metrics_and_duplicate_frame_are_explicit():
    z=metric_counts([255],[float('nan')],[False])
    assert z['recall'] is None and z['fpr'] is None and z['excluded_pixels']==1
    a=frame();a['pixel_ids']=['same','same']
    with pytest.raises(ValueError,match='Duplicate'):compare_contract(a,a,a)


def test_readiness_entry_has_no_model_loader_fit_or_network_calls():
    import ast
    from pathlib import Path
    source=Path('scripts/phase25d1_readiness.py').read_text(encoding='utf-8-sig')
    tree=ast.parse(source)
    forbidden={'fit','backward','step','from_pretrained','hf_hub_download','getInfo','getDownloadURL','Initialize','load_state_dict','load'}
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
            assert name not in forbidden


def test_frozen_frame_loader_rejects_tampering(tmp_path):
    import json,hashlib
    from src.phase25.learning import load_evaluation_frame
    f=frame();f['valid']=f['valid'].tolist();f.pop('probabilities')
    path=tmp_path/'frame.json';path.write_text(json.dumps(f))
    h=hashlib.sha256(path.read_bytes()).hexdigest()
    assert load_evaluation_frame(path,h)['pixel_ids']==f['pixel_ids']
    path.write_text('{}')
    with pytest.raises(ValueError,match='hash'):load_evaluation_frame(path,h)
