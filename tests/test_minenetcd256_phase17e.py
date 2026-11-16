import numpy as np
import pytest
import torch

from scripts import minenetcd256_phase17e as run


def test_masked_weighted_logits_and_sign():
    logits = torch.tensor([0., 0., float("nan")], requires_grad=True)
    target = torch.tensor([0., 1., 99.])
    valid = torch.tensor([True, True, False])
    loss = run.masked_loss(logits, target, valid, pos_weight=3.)
    assert loss.item() == pytest.approx(2 * np.log(2))
    loss.backward()
    assert logits.grad.tolist() == pytest.approx([.25, -.75, 0.])
    assert (torch.sigmoid(torch.tensor([-1., 0., 1.])) >= .5).tolist() == [False, True, True]


def test_weight_is_inverse_train_prevalence_with_cap():
    def rows(y):
        return [(None, None, None, np.array(y, dtype=bool))]
    assert run.weight(rows([0, 0, 0, 1]))["pos_weight"] == 3.
    assert run.weight(rows([0]*15 + [1]))["pos_weight"] == 10.
    with pytest.raises(ValueError, match="TRAIN classes"):
        run.weight(rows([0, 0]))


def test_binary_calibration_and_threshold_direction():
    rows = [(None, None, None, np.array([False, True]))]
    out = run.distribution(rows, [np.array([0., 1.])])
    assert out["brier"] == 0 and out["ece"] == 0
    assert out["thresholds"][0]["positive_recall"] == 1
    assert out["thresholds"][0]["negative_recall"] == 1
