"""Phase 24C: reproducible evidence-tier summary built only from committed metric reports.

Separates (1) unsupervised screening, (2) weak-label experiments and (3) verified classification.
Every number is read from a committed JSON report (source path + SHA-256 recorded); nothing is
recomputed, retrained or read from frozen TEST data. Verified Indian classification is BLOCKED.
"""
import json
from hashlib import sha256
from pathlib import Path
from statistics import mean, stdev

R = Path("docs/reports")
OUT = R / "phase24c-evidence-summary.json"


def load(name):
    p = R / name
    return json.loads(p.read_text(encoding="utf-8")), dict(path=p.as_posix(), sha256=sha256(p.read_bytes()).hexdigest())


def r3(x):
    return None if x is None else round(float(x), 3)


def build():
    x, sx = load("phase22x-summary.json")
    y, sy = load("phase22y-summary.json")
    b, sb = load("phase24b-india-screening.json")
    h, sh = load("phase22h-expanded-metrics.json")
    k, sk = load("phase22k-rule-metrics.json")
    w, sw = load("phase22w-metrics.json")
    ov = x["density"]["overall"]
    unet = [r["expanded"]["pooled"]["f1"] for r in h["unet"]["runs"]]
    rfa = h["rf"]["models"]["RF-A"]["candidates"]["0.5"]["f1"]
    arms = {a: dict(features=v["features"], f1=r3(v["pooled"]["f1"]), ci95=[r3(c) for c in v["group_bootstrap_ci95"]["f1"]])
            for a, v in w["arms"].items()}
    fo = w["paired_differences"]["C_fusion-minus-B_optical"]
    unsup = dict(
        label="Unsupervised screening (no labels; descriptive)",
        items=[
            dict(phase="22X", what="Meghalaya 22L rule over 20 sampled AOIs",
                 density_ha_per_100ha=r3(ov.get("mean")), ci95=[r3(c) for c in ov.get("ci95", [])],
                 clusters=x["sar_dvh"]["clusters"], dvh_cluster_minus_background_db=r3(x["sar_dvh"]["mean_cluster_minus_background_db"]),
                 aois_negative_dvh=x["sar_dvh"]["aois_negative_direction"], source=sx),
            dict(phase="22Y", what="Persistence typology of the 22X clusters",
                 shares={c: dict(clusters=v["clusters"], share=r3(v["share"])) for c, v in y["shares"].items()}, source=sy),
            dict(phase="24B", what="Change-feature summaries over configured Indian AOI tiles",
                 aois=b["coverage"]["aois_screened"], states=b["coverage"]["states"], screened_km2=b["coverage"]["screened_km2"],
                 national_coverage=False, source=sb),
        ],
        claim="Spatial patterns and S1/S2 co-change only; mining attribution UNKNOWN.")
    weak = dict(
        label="Weak-label experiments (agreement with unverified Maus v2 footprints; validation split only)",
        items=[
            dict(phase="22H", model="U-Net (3 seeds), B3/B4/B8", val_f1_mean=r3(mean(unet)), val_f1_sd=r3(stdev(unet)), source=sh),
            dict(phase="22H", model="RF-A, B3/B4/B8 @0.50", val_f1=r3(rfa), source=sh),
            dict(phase="22K", model="Index rule A (TRAIN-selected)", val_f1=r3(k["rules"]["A"]["validation"]["pooled"]["f1"]), source=sk),
            dict(phase="22W", model="Sensor ablation RF (11 Odisha groups)", arms=arms,
                 fusion_minus_optical=dict(median=r3(fo["f1_diff_median"]), ci95=[r3(c) for c in fo["f1_diff_ci95"]],
                                           share_positive=r3(fo["share_resamples_positive"])), source=sw),
        ],
        claim="Not accuracy: labels are unverified weak footprints; TEST split sealed (test_sealed=true).")
    for d in (h, k):
        assert d.get("test_sealed") is True, "TEST must remain sealed"
    return dict(
        phase="24C", generated_from="committed docs/reports JSON only; no retraining, no TEST access",
        tiers=dict(unsupervised_screening=unsup, weak_label_experiments=weak,
                   external_benchmark=dict(label="External RGB benchmark (MineNetCD256, non-Indian sites)",
                                           note="See docs/reports/final-model-experiment-consolidation.md and phase17g-rf-heldout-results.md (markdown tables); not Indian accuracy."),
                   verified_classification=dict(status="BLOCKED", count=0,
                                                reason="No accepted independent Indian reference labels; reviewer adjudication (Phase 23I) and field/official data pending.")),
        mining_attribution="UNKNOWN")


def main():
    s = build()
    OUT.write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(json.dumps({t: v.get("label", v.get("status")) for t, v in s["tiers"].items()}, indent=2))


if __name__ == "__main__":
    main()
