import json
from pathlib import Path

import pytest

from scripts.phase23m_routing_audit import STATION_GOID, audit, per_station


def test_per_station_counts_are_cumulative_and_class_aware():
    routes = [dict(cls="PERSISTENT", ha=0.09, stations=["Lukha-Khaddum-4315", "Lukha-Sunapur-3376"]),
              dict(cls="PARTIAL", ha=0.18, stations=["Lukha-Sunapur-3376"]),
              dict(cls="RECOVERING", ha=0.27, stations=[])]
    d = per_station(routes)
    assert d["Lukha-Sunapur-3376"] == dict(upstream_clusters=2, persistent=1, partial=1, recovering=0, upstream_ha=0.27)
    assert d["Lukha-Khaddum-4315"]["upstream_clusters"] == 1 and d["Myntdu-Leshka-3379"]["upstream_clusters"] == 0
    assert set(d) == set(STATION_GOID)


def test_committed_audit_is_complete():
    res = json.loads(Path("docs/reports/phase23m-routing-audit.json").read_text())
    assert res["verdict"] == "COMPLETE" and res["passed"] == res["total"] >= 27


def test_live_audit_when_local_routes_present():
    if not Path("outputs/phase23a_linkage/routes.json").exists():
        pytest.skip("local Phase 23A routes not available")
    checks, gaps, derived = audit()
    assert all(c["ok"] for c in checks)
    assert derived["Lukha-Sunapur-3376"]["persistent"] == 28
