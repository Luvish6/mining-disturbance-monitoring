import json

import numpy as np
import pytest

from scripts.phase22h_maus_acquire import Journal
from scripts.phase22h_maus_train import at_threshold, batches, objective_rank


def test_request_caps_persist_across_restart(tmp_path, monkeypatch):
    monkeypatch.setitem(__import__("scripts.phase22h_maus_acquire",fromlist=["CAPS"]).CAPS,"tiff",1)
    path=tmp_path/"counts.jsonl"
    Journal(path).charge("tiff")
    with pytest.raises(ValueError,match="cap"):
        Journal(path).charge("tiff")
    assert json.loads(path.read_text())=={"kind":"tiff","request":1}


def test_unique_background_supply_is_not_oversampled():
    groups=batches([0,1],[2,3,4,5],np.random.default_rng(42))
    assert len(groups)==2
    assert {g[0] for g in groups}=={0,1}
    assert sorted(x for g in groups for x in g[1:])==[2,3,4,5]


def test_objective_tie_prefers_lower_fpr_and_nearer_threshold():
    assert objective_rank(dict(iou=.5,fpr=0),.40,5)>objective_rank(dict(iou=.55,fpr=.20),.50,1)
    assert objective_rank(dict(iou=.5,fpr=.1),.50,9)>objective_rank(dict(iou=.5,fpr=.1),.45,2)
    assert objective_rank(dict(iou=.5,fpr=.1),.50,1)>objective_rank(dict(iou=.5,fpr=.1),.50,2)


def test_group_state_and_subset_at_fixed_threshold():
    rows=[({"state":"Odisha","group_id":"g"},None,None,None)]
    y=np.array([0,1])
    p=np.array([.6,.9])
    g=np.array(["g","g"])
    b=np.array([True,False])
    out=at_threshold(y,p,g,b,rows,.75)
    assert out["pooled"]["confusion"]==[[1,0],[0,1]]
    assert out["per_state"]["Odisha"]["groups"]==1
    assert out["threshold"]==.75
