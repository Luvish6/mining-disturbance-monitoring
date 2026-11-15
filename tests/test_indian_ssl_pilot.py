import numpy as np
import pytest
import torch

from scripts.indian_ssl_pilot import Encoder, compare, development_rows, NODATA


def test_development_eligibility_does_not_depend_on_after():
    tile = dict(values=np.ones((14,2,2)),counts=np.full((4,2,2),2),
                common=np.zeros((2,2),dtype=bool))
    tile["values"][4:] = NODATA
    tile["counts"][[1,3]] = 0
    assert development_rows(tile).shape == (4,4)
    tile["values"][0,0,0]=NODATA
    assert development_rows(tile).shape == (3,4)


def test_sensor_mask_is_blind_to_hidden_values():
    model = Encoder()
    a = torch.zeros(4,4)
    b = a.clone()
    b[:,0:2]=999
    assert torch.equal(model.view(a,0),model.view(b,0))
    assert model.embed(a).shape==(4,8)


def test_constant_scores_and_empty_candidate_union_are_undefined():
    mask = np.ones((5,5),dtype=bool)
    result = compare(np.zeros(25),np.zeros(25),mask,1.)
    assert result["spearman"] is None
    assert result["candidate_jaccard"] is None
    assert result["candidate_area_m2"]==[0,0]
    assert result["top5_jaccard"]==pytest.approx(1.)
