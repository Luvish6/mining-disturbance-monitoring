import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase12d_matched_brahmani import REACHES, compare


def record(before, after, value):
    return dict(before=before, after=after, before_ndti=value, after_ndti=value + .1)


def test_intersects_seasons_before_matching_and_preserves_direction():
    obs = {
        REACHES[0]: {"spectra": [record("2023-11-01", "2024-11-03", .1),
                                 record("2023-11-03", "2024-11-01", .2),
                                 record("2024-02-03", "2025-02-03", .4)]},
        REACHES[1]: {"spectra": [record("2023-11-01", "2024-11-01", .3),
                                 record("2024-02-03", "2025-02-03", .5)]},
    }
    summary, *dates = compare(obs, [25, 30])
    assert summary["matched_pairs"] == 2
    assert dates[0]["downstream_minus_upstream"] == pytest.approx(.2)
    assert dates[1]["downstream_minus_upstream"] == pytest.approx(.1)
    assert len(compare(obs, [24, 30])) == 1
    obs[REACHES[1]]["spectra"].pop()
    assert compare(obs, [25, 30])[0]["status"] == "INSUFFICIENT DATA"
