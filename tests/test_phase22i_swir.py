import numpy as np
import pytest
import torch

from scripts import phase22i_swir_acquire as acquisition
from scripts import phase22i_swir_train as training


def test_common_support_keeps_unknowns_out_of_metrics():
    old=np.ones((10,10),dtype=bool)
    new=old.copy()
    new[0,0]=False
    y=np.zeros((10,10),dtype="uint8")
    y[0,1]=255
    common=acquisition.common_support(old,new,y)
    arrays=training.flatten([({"group_id":"g","negative_stratum":"random"},
                              np.zeros((6,10,10)),common,y)])
    assert common.sum()==99 and len(arrays[1])==98
    assert old.all()
    with pytest.raises(ValueError,match="common support"):
        acquisition.common_support(old,new & False,y)


def test_request_and_actual_byte_caps_persist(tmp_path,monkeypatch):
    monkeypatch.setattr(acquisition,"CAP",2)
    monkeypatch.setattr(acquisition,"BODY_LIMIT",10)
    journal=acquisition.Transfer(tmp_path/"transfer.jsonl")
    assert journal.wrapped(lambda u,n:b"abcde")("placeholder",5)==b"abcde"
    reopened=acquisition.Transfer(journal.path)
    with pytest.raises(ValueError,match="cap"):
        reopened.wrapped(lambda *_:pytest.fail("over-budget request"))("placeholder",6)
    assert reopened.wrapped(lambda *_:b"abc")("placeholder",5)==b"abc"
    with pytest.raises(ValueError,match="cap"):
        reopened.wrapped(lambda *_:pytest.fail("over-count request"))("placeholder",1)
    assert (reopened.count,reopened.bytes)==(2,8)


def test_swir_unet_uses_six_bands_and_existing_spatial_head():
    torch.set_num_threads(1)
    model=training.SwirUNet()
    with torch.no_grad():
        result=model(torch.zeros((1,6,16,16)))
    assert result.shape==(1,1,16,16)
    assert training.BANDS["F2"]==["B2","B3","B4","B8","B11","B12"]


def test_partial_pair_excluded_from_seed_averages():
    m={"pooled":dict(precision=.5,recall=.5,f1=.5,iou=.3,fpr=.2)}
    row=dict(expanded=m,original=m)
    result=training.aggregate_pairs([dict(seed=42,F1=row,F2=row),
                                    dict(seed=43,F1=row,F2=row | {"failure":"CPU cap"})])
    assert result["completed_seeds"]==[42]
    assert result["arms"]["F2"]["expanded"]["f1"]=={"mean":.5,"sample_sd":None}


def test_support_receipt_hashes_common_valid_cells_and_excludes_unknowns():
    v=np.array([[True,False],[True,True]])
    y=np.array([[1,0],[255,0]])
    row=({},None,v,y)
    receipt=training.support_receipt({"F1":{"train":[row]}})
    assert receipt["train"]["known_cells"]==2
    assert receipt["train"]["mask_sha256"]==training.digest(np.packbits(v).tobytes())


def test_rf_recovery_dispatch_is_scoring_only(tmp_path,monkeypatch):
    monkeypatch.setattr(training,"DEST",tmp_path)
    monkeypatch.setattr(training,"inputs",lambda:({"F1":{}},{},set(),True))
    monkeypatch.setattr(training,"rf_run",lambda *_:pytest.fail("RF fit triggered during recovery"))
    monkeypatch.setattr(training,"unet_run",lambda *_:pytest.fail("U-Net fit triggered during recovery"))
    calls=[]
    monkeypatch.setattr(training,"recover_results",
                        lambda name,*args:calls.append(name) or {"restored":True})
    training.run("rf-recover")
    assert calls==["rf"]
    assert (tmp_path/"models"/"rf-results.json").exists()
