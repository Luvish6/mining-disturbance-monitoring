import numpy as np
import pytest
import torch

from scripts import phase22f_maus as pilot


def test_rf_support_is_common_and_unknown_is_omitted():
    x = np.array([[[.2, .2, .2, .2]], [[.2, .0, .2, .2]], [[.6, .0, .6, .6]]])
    v = np.array([[True, True, True, False]])
    y = np.array([[1, 0, 255, 0]])
    features, labels, groups, backgrounds, ndvi_excluded = pilot.rf_arrays([
        ({"group_id": "A", "negative_stratum": None}, x, v, y)
    ])
    np.testing.assert_allclose(features, [[.2, .2, .6, .5]])
    assert labels.tolist() == [1] and groups.tolist() == ["A"]
    assert backgrounds.tolist() == [False] and ndvi_excluded == 1


def test_sampling_is_unique_balanced_and_deterministic():
    y = np.array([0, 0, 0, 0, 1, 1])
    a = pilot.balanced_pixels(y)
    assert np.array_equal(a, pilot.balanced_pixels(y))
    assert len(np.unique(a)) == len(a) == 4
    assert y[a].sum() == 2
    with pytest.raises(ValueError, match="Both"):
        pilot.balanced_pixels(np.ones(7))


def test_threshold_tie_uses_higher_cutoff_and_background_fpr():
    y = np.array([1,0])
    p = np.array([.8,.1])
    row = pilot.evaluate(y,p,np.array(["a","a"]),np.array([False,True]))
    assert row["threshold"] == .75
    assert row["pooled"]["confusion"] == [[1,0],[0,1]]
    assert row["background_only"] == {"false_positives":0,"pixels":1,"fpr":0.}


def test_stability_requires_all_five_final_checkpoints_and_strict_loss():
    track = [dict(step=s,iou=.90,loss=.14) for s in range(900,1001,25)]
    assert pilot.stability_pass(track)
    assert not pilot.stability_pass(track[:-1])
    assert not pilot.stability_pass(track[:-1]+[track[-1] | {"loss":.15}])
    assert not pilot.stability_pass(track[:1]+[track[1] | {"iou":.89}]+track[2:])


def test_static_unet_and_mask_ignore_invalid_target():
    model = pilot.StaticUNet()
    pred = model(torch.zeros((1,3,8,8)))
    assert pred.shape == (1,1,8,8)
    y = torch.zeros_like(pred)
    valid = torch.ones_like(pred,dtype=torch.bool)
    valid[...,0,0] = False
    initial = pilot.masked_loss(pred,y,valid)
    y[...,0,0] = 255
    assert torch.equal(initial,pilot.masked_loss(pred,y,valid))
