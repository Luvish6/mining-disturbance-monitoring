import json
import numpy as np
import pytest
import torch
from src.phase3.model import SiameseUNet
from src.phase25.unet_experiment import payload_metadata,load_model,metrics
from src.phase25.dataset import sha
from src.phase25.learning import masked_bce_dice


def test_ignored_uncertain_pixels_have_zero_loss_gradient():
    z=torch.zeros(1,1,2,2,requires_grad=True);y=torch.tensor([[[[1.,0.],[255.,255.]]]]);mask=y!=255
    loss=masked_bce_dice(z,y,mask,10);loss.backward()
    assert torch.isfinite(loss) and torch.all(z.grad[~mask]==0)


def test_checkpoint_load_contract_and_hash(tmp_path):
    model=SiameseUNet(channels=5,width=16);p=tmp_path/'model.pt'
    torch.save(dict(state_dict=model.state_dict(),metadata=payload_metadata(42)),p)
    p.with_suffix('.json').write_text(json.dumps(dict(sha256=sha(p))))
    loaded,meta=load_model(p)
    with torch.no_grad():assert loaded(torch.zeros(1,5,32,32),torch.zeros(1,5,32,32)).shape==(1,1,32,32)
    assert meta['model_validation_status']=='NOT_VALIDATED' and meta['label_kind']=='ALGORITHM_PSEUDO_LABEL_NOT_REFERENCE'
    p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):load_model(p)


def test_wrong_normalization_contract_rejected(tmp_path):
    p=tmp_path/'bad.pt';meta=payload_metadata(42);meta['contract_sha256']='wrong'
    torch.save(dict(state_dict={},metadata=meta),p);p.with_suffix('.json').write_text(json.dumps(dict(sha256=sha(p))))
    with pytest.raises(ValueError,match='contract'):load_model(p)


def test_constant_baseline_and_zero_positive_group():
    m=metrics(dict(labels=[0,1,0,255],probabilities=[0,0,0,.9],valid=[True,True,True,False],group_ids=['a','a','b','b']))
    assert m['pooled']['confusion_matrix']==[[2,0],[1,0]] and m['pooled']['dice_f1']==0
    assert m['per_group']['b']['recall'] is None and m['pooled']['precision'] is None
