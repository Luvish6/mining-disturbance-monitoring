import json

from scripts.phase23_dashboard_data import FORBIDDEN_KEYS, build, strip


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_payload_is_aggregate_only_and_traceable():
    p = build()
    assert not (set(_keys(p)) & FORBIDDEN_KEYS)
    assert p["earth_engine_requests"] == 0 and p["mining_attribution"] == "UNKNOWN"
    for block in ("landscape", "persistence", "ablation", "exposure", "review"):
        assert p[block]["source"]["file"].startswith("docs/reports/") and len(p[block]["source"]["sha256"]) == 64
    json.dumps(p, allow_nan=False)


def test_values_match_frozen_reports():
    p = build()
    x = json.load(open("docs/reports/phase22x-summary.json"))
    assert p["landscape"]["density"]["overall"]["mean"] == x["density"]["overall"]["mean"]
    assert len(p["landscape"]["per_aoi"]) == 20
    assert p["persistence"]["shares"]["PERSISTENT"]["clusters"] == 53
    assert {r["evidence_category"] for r in p["exposure"]["reaches"]} == {"RIVER_UNOBSERVABLE", "UNKNOWN"}
    assert "NOT Meghalaya" in p["ablation"]["context"]


def test_review_pending_without_results():
    p = build()
    assert p["review"]["status"] == "PENDING" and p["review"]["total_items"] == 30
    assert not any(k in json.dumps(p["review"]) for k in ("visible_disturbance", "review_A.csv", "crosswalk"))


def test_strip_removes_nested_coordinates():
    assert strip({"a": [{"lat": 1, "b": {"x": 2, "ok": 3}}]}) == {"a": [{"b": {"ok": 3}}]}
