import torch

from scripts.minenetcd256_improve import choose, weighted_dice


def test_validation_only_selection_breaks_ties_with_higher_threshold():
    def entry(f1):
        return {"pooled":{"classes":[{},{"f1":f1}]}}
    result = choose({"original":{"0.5":entry(.1)}, "new":{"0.25":entry(.2), "0.65":entry(.2)}})
    assert result == dict(model="new", threshold=.65, validation_f1=.2, original_f1=.1, improved=True)


def test_weighted_dice_masks_pixels_and_has_finite_gradient():
    logits = torch.zeros(3, requires_grad=True)
    target = torch.tensor([0.,1.,255.])
    valid = torch.tensor([True,True,False])
    result = weighted_dice(logits,target,valid)
    result.backward()
    assert torch.isfinite(result)
    assert logits.grad[0] > 0 and logits.grad[1] < 0 and logits.grad[2] == 0
