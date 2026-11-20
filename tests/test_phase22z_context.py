from scripts.phase22z_context import pair_rank, tier


def test_tier_rule_is_fixed_and_ordered():
    base = dict(site_distance_km=5.0, hard_commodity_dominant=False, recent_loss=False)
    assert tier(base) == 3
    assert tier(base | dict(recent_loss=True)) == 2
    assert tier(base | dict(site_distance_km=1.0)) == 1
    assert tier(base | dict(hard_commodity_dominant=True, recent_loss=True)) == 1


def test_pair_rank_counts_ties_and_pools_by_size():
    shares = dict(a=1.0, b=0.0, c=0.5)
    counts = dict(a=1, b=3, c=2)
    r = pair_rank(shares, counts, ("a", "c"))
    assert r["pairs"] == 3 and abs(r["target_share"] - 2 / 3) < 1e-12 and r["pairs_at_or_above"] == 1
