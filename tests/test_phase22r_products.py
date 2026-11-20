import numpy as np

from scripts.phase22r_product_agreement import (background_mask, clusters, frac_any, translation_null,
                                                 valid_offsets, wilson)


def test_background_excludes_candidates_and_buffer():
    elig = np.ones((9, 9), bool); cand = np.zeros((9, 9), bool); cand[4, 4] = True
    bg = background_mask(elig, cand)
    assert not bg[2:7, 2:7].any() and bg.sum() == 81 - 25


def test_translations_preserve_shape_inside_pool():
    pool = np.zeros((5, 5), bool); pool[:2, :] = True
    offs = valid_offsets(np.array([[3, 0], [3, 1]]), pool)
    assert len(offs) == 8 and all(pool[3 + dr, dc] and pool[3 + dr, dc + 1] for dr, dc in offs)


def test_translation_null_detects_enrichment_and_handles_zero():
    grid = np.zeros((20, 20), bool); grid[2, 2] = grid[10, 10] = True
    cand = np.zeros_like(grid); cand[2, 2] = cand[10, 10] = True
    pool = np.ones_like(grid); pool[cand] = False
    cl = clusters(cand)
    obs, null = translation_null([(cl, pool, grid)], frac_any, draws=500)
    assert obs == 1.0 and null["null_median"] == 0 and null["p_two_sided"] < .01
    obs, null = translation_null([(cl, pool, np.zeros_like(grid))], frac_any, draws=200)
    assert obs == 0 and null["p_two_sided"] == 1.0


def test_wilson():
    assert wilson(0, 0) is None
    lo, hi = wilson(0, 18)
    assert lo == 0 and 0.15 < hi < 0.2
