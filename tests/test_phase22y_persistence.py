import numpy as np

from scripts.phase22y_persistence import aoi_bootstrap_shares, classify, within_aoi_permutation


def test_classes_use_fixed_rule_bounds():
    assert classify(-0.30, 0.11, True) == "PERSISTENT"
    assert classify(-0.30, 0.10, True) == "PARTIAL"
    assert classify(-0.10, 0.5, True) == "RECOVERING"
    assert classify(-0.20, 0.0, True) == "PARTIAL"
    assert classify(-0.9, 0.9, False) == "UNOBSERVED"


def test_within_aoi_permutation_detects_and_handles_degenerate():
    labels = ["PERSISTENT", "RECOVERING"] * 20
    aois = [f"a{i // 4}" for i in range(40)]
    r = within_aoi_permutation(labels, [1.0 if l == "PERSISTENT" else 0.0 for l in labels], aois, draws=500)
    assert r["observed"] == 1.0 and r["p_two_sided"] < .01
    assert within_aoi_permutation(["RECOVERING"] * 4, [1, 2, 3, 4], ["a"] * 4) is None


def test_shares_sum_to_one():
    s = aoi_bootstrap_shares(["PERSISTENT", "PARTIAL", "RECOVERING", "RECOVERING"], ["a", "a", "b", "b"], draws=200)
    assert abs(sum(v["share"] for v in s.values()) - 1) < 1e-9 and s["RECOVERING"]["clusters"] == 2
