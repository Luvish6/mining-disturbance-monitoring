from scripts import phase24c_evidence_summary as m


def test_tiers_are_separated_and_verified_classification_blocked():
    s = m.build()
    t = s["tiers"]
    assert t["verified_classification"] == dict(status="BLOCKED", count=0, reason=t["verified_classification"]["reason"])
    assert s["mining_attribution"] == "UNKNOWN"
    assert "Not accuracy" in t["weak_label_experiments"]["claim"]
    assert t["unsupervised_screening"]["items"][2]["national_coverage"] is False


def test_values_trace_to_committed_reports():
    s = m.build()
    weak = s["tiers"]["weak_label_experiments"]["items"]
    assert weak[0]["val_f1_mean"] == 0.713 and weak[2]["val_f1"] == 0.437
    fo = weak[3]["fusion_minus_optical"]
    assert fo["median"] == 0.006 and fo["ci95"][0] < 0 < fo["ci95"][1]
    for tier in ("unsupervised_screening", "weak_label_experiments"):
        for item in s["tiers"][tier]["items"]:
            assert item["source"]["path"].startswith("docs/reports/") and len(item["source"]["sha256"]) == 64
