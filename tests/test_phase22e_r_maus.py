import json

import pytest

from scripts import phase22e_r_maus as recovery


def test_manifest_verifies_original_and_recovery_bytes(tmp_path, monkeypatch):
    source, dest = tmp_path / "source", tmp_path / "recovery"
    source.mkdir()
    plan = {"patches": [{"split": "train"}] * 39}
    raw = json.dumps(plan).encode()
    (source / "plan.json").write_bytes(raw)
    monkeypatch.setattr(recovery, "PLAN_SHA", recovery.digest(raw))
    monkeypatch.setattr(recovery, "read_plan", lambda *_: (plan, recovery.digest(raw)))
    assert recovery.frozen_plan(source, source, dest) == plan
    assert (dest / "plan.json").read_bytes() == raw
    (dest / "plan.json").write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="differs"):
        recovery.frozen_plan(source, source, dest)
    (source / "plan.json").write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        recovery.frozen_plan(source, source, dest)


def test_batch_fails_closed_without_valid_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, "frozen_plan",
                         lambda *_: {"patches": [{"split": "train", "patch_id": "first"}]})
    monkeypatch.setattr(recovery, "export_all", lambda *_: pytest.fail("batch contacted exporter"))
    with pytest.raises(FileNotFoundError):
        recovery.run_batch(tmp_path, tmp_path, tmp_path)
    (tmp_path / "smoke.json").write_text(json.dumps({"status": "REJECTED"}))
    with pytest.raises(ValueError, match="smoke receipt"):
        recovery.run_batch(tmp_path, tmp_path, tmp_path)


def test_failed_smoke_propagates_rejection_before_raster_read():
    with pytest.raises(ValueError, match="coverage below"):
        recovery.smoke_gate({"state_of_patch": "REJECTED", "reason": "coverage below threshold"},
                            None, None, {}, {})
