from pathlib import Path

import pytest

from scripts import minenetcd256_phase17f as phase


def test_budgeted_site_coverage_diversity_and_exposure():
    groups = [
        {"domains": ["A_01"]*4 + ["A_02"]*4, "cost": 6},
        {"domains": ["B_01"]*4 + ["C_01"]*4 + ["seen_01"]*5, "cost": 7},
        {"domains": ["D_01"]*4, "cost": 8},
    ]
    eligible = {"A_01", "A_02", "B_01", "C_01", "D_01"}
    assert phase.pick(groups, eligible, 9, 2) == ((1,), {"B_01", "C_01"})
    assert phase.pick(groups, eligible, 15, 2) == ((0, 1), eligible - {"D_01"})
    with pytest.raises(ValueError, match="No eligible bounded"):
        phase.pick(groups, eligible, 7, 2)


def test_no_partial_mine_selection():
    groups = [{"domains": ["A_01"]*2, "cost": 3}, {"domains": ["A_01"]*2, "cost": 3}]
    assert phase.pick(groups, {"A_01"}, 7, 1) == ((0, 1), {"A_01"})


def test_wrong_receipt_stops_before_asset_open(monkeypatch, tmp_path):
    monkeypatch.setattr(phase, "verify", lambda *a: (_ for _ in ()).throw(ValueError("freeze failed")))
    monkeypatch.setattr(phase.fit, "load", lambda *a: pytest.fail("asset opened"))
    with pytest.raises(ValueError, match="freeze failed"):
        phase.evaluate(Path("."), {}, "wrong", tmp_path / "out")
    assert not (tmp_path / "out").exists()
