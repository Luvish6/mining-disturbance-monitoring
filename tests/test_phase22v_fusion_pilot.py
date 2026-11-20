import numpy as np
import pytest

from scripts.phase22v_fusion_pilot import NODATA, quality, select_pilot


def _row(i, pos, state, group=None, split="train"):
    return dict(patch_id=f"p{i}", positive_pixels=50 if pos else 0, state=state, group_id=group or f"g{i}",
                split=split, image_sha256="x")


def test_selection_is_train_only_deterministic_and_diverse():
    rows = [_row(i, i % 3 == 0, f"S{i % 4}") for i in range(30)]
    a, b = select_pilot(rows), select_pilot(list(reversed(rows)))
    assert [r["patch_id"] for r in a] == [r["patch_id"] for r in b]
    assert sum(r["positive_pixels"] > 0 for r in a) == 2 and len(a) == 4
    assert len({r["group_id"] for r in a}) == 4
    with pytest.raises(ValueError):
        select_pilot(rows + [_row(99, True, "S9", split="validation")])


def test_quality_gates():
    vv = np.full((4, 4), -10.0); vh = np.full((4, 4), -17.0); c = np.full((4, 4), 5)
    q = quality(vv, vh, c, np.ones((4, 4), bool))
    assert q["passes"] and q["vh_below_vv_fraction"] == 1 and q["in_db_range_fraction"] == 1
    vv[:2] = NODATA
    assert not quality(vv, vh, c, np.ones((4, 4), bool))["passes"]
    c[:] = 1
    assert quality(np.full((4, 4), -10.0), vh, c, np.ones((4, 4), bool))["sar_valid_fraction"] == 0
