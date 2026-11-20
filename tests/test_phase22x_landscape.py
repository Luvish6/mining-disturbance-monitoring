from src.phase3.spatial import block_for

from scripts.phase22x_landscape import block_rect, bootstrap_mean_ci, draw_sample


def test_centred_aoi_is_inside_its_block_core_on_30m_grid():
    for key in ("94:559", "81:557", "88:560"):
        b = block_rect(key)
        assert block_for(b) == key and b[2] - b[0] == 1920 and b[3] - b[1] == 1920
        assert all(v % 30 == 0 for v in b)


def test_sample_is_deterministic_and_stratified():
    cand = {f"{i}:1": ("East" if i % 2 else "West") for i in range(40)}
    a, b = draw_sample(cand, 5), draw_sample(dict(reversed(list(cand.items()))), 5)
    assert a == b and set(a) == {"East", "West"} and all(len(v) == 5 for v in a.values())
    assert all(cand[k] == d for d, ks in a.items() for k in ks)


def test_bootstrap_ci_brackets_mean():
    lo, hi = bootstrap_mean_ci([0, 0, 1, 2, 3])
    assert lo <= 1.2 <= hi
