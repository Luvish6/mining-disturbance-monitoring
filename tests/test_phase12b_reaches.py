from datetime import date
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase12b_reaches import confirms_link, fixed_support


def test_link_must_be_reciprocal():
    assert confirms_link(42, "downstream", {"NUOID": "41_42"})
    assert confirms_link(42, "upstream", {"NDOID": 42})
    assert not confirms_link(42, "downstream", {"NUOID": "41"})


def test_fixed_support_excludes_moving_water_and_unmatched_months():
    a = np.ones((6, 6), dtype=bool)
    b = a.copy()
    b[:, 0] = False
    c = b.copy()
    c[0, :] = False
    d = np.zeros_like(a)
    before = {date(2023, 11, 6): (0, "", a), date(2024, 2, 6): (0, "", b),
              date(2024, 3, 6): (0, "", d)}
    after = {date(2024, 11, 6): (0, "", b), date(2025, 2, 6): (0, "", c)}
    pairs, mask = fixed_support([before, after])
    assert len(pairs) == 2
    assert mask.sum() == 25
    assert fixed_support([before, {}]) == ([], None)
