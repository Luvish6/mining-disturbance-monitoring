import json

from scripts.phase23l_reach_integration import build, burden_class, monitoring_label, observability, planet_status


def test_burden_and_label_rules_are_transparent():
    assert [burden_class(n) for n in (0, 2, 3, 9, 10, 28)] == ["LOW", "LOW", "MODERATE", "MODERATE", "HIGH", "HIGH"]
    assert monitoring_label("HIGH", "UNOBSERVABLE") == "PRIORITY FIELD MONITORING"
    assert monitoring_label("MODERATE", "UNKNOWN") == "FIELD MONITORING"
    assert monitoring_label("LOW", "MARGINAL") == "REFERENCE / LOW"
    assert monitoring_label("HIGH", "OBSERVABLE").startswith("SATELLITE-TRACKABLE")


def test_planet_status_and_observability_never_upgrade_without_evidence():
    assert planet_status(None)[0] == "NOT_COVERED"
    hazy = dict(covered=True, window_clear_fraction=0.005, window_haze_light_fraction=0.995, primary=dict(gate=False))
    assert planet_status(hazy)[0] == "FAIL_CONDITIONS"
    fail = dict(covered=True, window_clear_fraction=1.0, primary=dict(gate=False, interior_px=0, water_px_corridor=41, width_estimate_m=8.5))
    assert planet_status(fail)[0] == "FAIL_GATE"
    marg = dict(covered=True, window_clear_fraction=1.0, primary=dict(gate=True, interior_px=44), sensitivity=dict(a=dict(gate=False), b=dict(gate=True)))
    assert planet_status(marg)[0] == "PASS_MARGINAL"
    assert observability("UNOBSERVABLE", {}) == "UNOBSERVABLE"
    assert observability("INCONSISTENT", {}) == "UNKNOWN"
    assert observability("UNOBSERVABLE", {"d": ("PASS_MARGINAL", "")}) == "MARGINAL"
    assert observability("UNOBSERVABLE", {"d": ("FAIL_GATE", ""), "e": ("FAIL_CONDITIONS", "")}) == "UNOBSERVABLE"


def test_built_table_matches_frozen_evidence_and_has_no_coordinates():
    out = build()
    rows = {r["station"]: r for r in out["reaches"]}
    assert rows["Lukha-Sunapur-3376"]["monitoring_label"] == "PRIORITY FIELD MONITORING"
    assert rows["Lukha-Sunapur-3376"]["observability"] == "UNOBSERVABLE" and rows["Lukha-Sunapur-3376"]["upstream_persistent"] == 28
    assert rows["Lukha-Khaddum-4315"]["observability"] == "MARGINAL" and "fragile" in rows["Lukha-Khaddum-4315"]["ndti_availability"]
    assert rows["Myntdu-Leshka-3379"]["observability"] == "UNKNOWN" and rows["Myntdu-Mihmyntdu-4316"]["planet_status"] == "NOT_ACQUIRED"
    assert all(r["mining_attribution"] == "UNKNOWN" for r in rows.values())
    text = json.dumps(out)
    assert not any(k in text for k in ('"lon"', '"lat"', "centroid", "lonlat", "crosswalk"))
    assert out["earth_engine_requests"] == 0 and all(len(s["sha256"]) == 64 for s in out["sources"].values())
