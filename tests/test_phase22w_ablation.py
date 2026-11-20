import numpy as np

from scripts.phase22w_ablation import confusion, eligible_patches, group_bootstrap, scores


def test_eligibility_uses_single_orbit_scene_count():
    rows = [dict(patch_id="a"), dict(patch_id="b"), dict(patch_id="c")]
    avail = {"a": {"desc": {"5": 7}}, "b": {"desc": {}}, "c": {"desc": {"1": 1, "2": 1}}}
    assert eligible_patches(rows, avail) == (["a"], ["b", "c"])


def test_scores_both_classes_and_undefined():
    y = np.array([1, 1, 0, 0]); p = np.array([True, False, True, False])
    s = scores(confusion(y, p))
    assert s["confusion"] == [[1, 1], [1, 1]] and s["f1"] == .5 and s["background_f1"] == .5
    s = scores(confusion(np.array([0, 0]), np.array([False, False])))
    assert s["precision"] is None and s["recall"] is None and s["fpr"] == 0


def test_group_bootstrap_paired_difference_sign():
    good = {g: np.array([90, 10, 10, 90]) for g in "abcd"}
    bad = {g: np.array([50, 50, 50, 50]) for g in "abcd"}
    ci, d = group_bootstrap({"x": bad, "y": good}, draws=200)
    assert ci["y"]["f1"][0] > ci["x"]["f1"][1]
    assert d["y-minus-x"]["share_resamples_positive"] == 1.0
