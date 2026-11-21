"""Build frontend/public/local/research.json from COMMITTED Phase 22-23 report artifacts only.

Aggregate results only: no imagery, no cluster/cell coordinates, no blinded-review crosswalk, no reviewer
answers. Every block records its source file and SHA-256. Zero Earth Engine requests.

  python -B -m scripts.phase23_dashboard_data
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs/reports"
TARGET = ROOT / "frontend/public/local/research.json"
REVIEW_RETURNS = ROOT / "outputs/phase23i_review/returns"  # reviewer CSVs, if any, are never read for values
FORBIDDEN_KEYS = {"x", "y", "row", "col", "lon", "lat", "centroid", "centroid_wgs84", "bounds", "geometry", "key", "crosswalk"}


def src(name):
    p = REPORTS / name
    return p, {"file": f"docs/reports/{name}", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def load(name):
    p, prov = src(name)
    return json.loads(p.read_bytes()), prov


def r(v, n=4):
    return None if v is None else round(float(v), n)


def strip(obj):
    """Defensive: drop any coordinate-like keys from nested structures."""
    if isinstance(obj, dict):
        return {k: strip(v) for k, v in obj.items() if k not in FORBIDDEN_KEYS}
    if isinstance(obj, list):
        return [strip(v) for v in obj]
    return obj


def build():
    x, px = load("phase22x-summary.json")
    y, py = load("phase22y-summary.json")
    w, pw = load("phase22w-metrics.json")
    rz, pr = load("phase23h-reach-priority.json")
    i, pi = load("phase23i-sample-design.json")
    landscape = dict(
        source=px, aois=len(x["aois"]), clusters_tested=x["clusters_tested"],
        density=dict(overall={k: x["density"]["overall"][k] for k in ("mean", "ci95", "aois", "aois_with_candidates")},
                     by_district=x["density"]["by_district"], unit="ha of candidate cells per 100 eligible ha"),
        sar_dvh=dict(mean_db=r(x["sar_dvh"]["mean_cluster_minus_background_db"], 3), null=x["sar_dvh"]["translation_null"],
                     aois_negative=x["sar_dvh"]["aois_negative_direction"]),
        sar_dvv=dict(mean_db=r(x["sar_dvv"]["mean_cluster_minus_background_db"], 3), null=x["sar_dvv"]["translation_null"]),
        gfc_recent_loss=dict(clusters=x["products_H1"]["clusters_with_recent_loss"], fraction=r(x["products_H1"]["fraction"]),
                             wilson95=x["products_H1"]["wilson95"], null_median=r(x["products_H1"]["translation_null"]["null_median"])),
        hard_commodities=dict(mean_probability=r(x["products_H2"]["mean_cluster_probability"]),
                              null_median=r(x["products_H2"]["translation_null"]["null_median"])),
        per_aoi=[dict(aoi=k, district=v["district"], split=v["split"], candidate_cells=v["candidate_cells"], clusters=v["clusters"],
                      candidate_ha=r(v["candidate_ha"], 2), density=r(v["density_ha_per_100ha"], 3),
                      dvh_db=r(v.get("dVH_candidate_median_minus_background_db"), 2), status=v.get("status", "TESTED"))
                 for k, v in sorted(x["aois"].items())])
    persistence = dict(source=py, clusters=y["clusters"], shares=y["shares"], by_district=y["by_district"],
                       lumshnong=y["lumshnong_blocks"],
                       slope_by_class=y["associations"]["slope_by_class"],
                       follow_up_season="2025-11-01 to 2026-04-01")
    ablation = dict(source=pw, context="EXTERNAL weak-label benchmark: Maus v2 static mining footprints, peninsular India, "
                                       "Odisha VAL (11 groups). Agreement with weak labels - NOT Meghalaya accuracy.",
                    cohort=w["cohort"], cutoff=w["cutoff"],
                    arms={k: dict(features=v["features"], **{m: r(v["pooled"][m]) for m in ("precision", "recall", "f1", "iou", "fpr")},
                                  f1_ci95=v["group_bootstrap_ci95"]["f1"], iou_ci95=v["group_bootstrap_ci95"]["iou"])
                          for k, v in w["arms"].items()},
                    paired=w["paired_differences"])
    exposure = dict(source=pr, rules=rz["rules"], reaches=rz["reaches"], separate_official=rz["separate_official_records"])
    official = dict(source={"file": "docs/reports/phase23c-official-water-records.md",
                            "sha256": hashlib.sha256((REPORTS / "phase23c-official-water-records.md").read_bytes()).hexdigest()},
                    portal="MSPCB monthly WQI portal (megspcb.gov.in/wqi); station coordinates unverified; NOT linked to any reach",
                    stations=[dict(code="3375", name="Lunar river (Lukha tributary) at Myndihati", ph_2023_24=[2.5, 2.9], ph_2024_25=[2.8, 3.1], months="10/10"),
                              dict(code="1428", name="Kyrhuhkhla", ph_2023_24=[2.8, 3.7], ph_2024_25=[3.0, 3.4], months="10/10"),
                              dict(code="1631", name="Myntdu at Jowai", ph_2023_24=[6.7, 7.0], ph_2024_25=[6.9, 7.0], months="9/10")],
                    note="pH is acidity, not comparable with NDTI; no causal attribution")
    returned = sorted(p.name for p in REVIEW_RETURNS.glob("review_*.csv")) if REVIEW_RETURNS.exists() else []
    review = dict(source=pi, status="PENDING" if len(returned) < 2 else "RETURNS_RECEIVED_NOT_ANALYSED",
                  reviews_returned=len(returned), total_items=i["total"], seed=i["seed"],
                  strata={k: dict(frame_size=v["frame_size"], sampled=v["sampled"]) for k, v in i["strata"].items()},
                  note="No reviewer results are shown until both independent reviews are complete and analysed.")
    payload = strip(dict(schema=1, generated_from="committed docs/reports artifacts", earth_engine_requests=0,
                         mining_attribution="UNKNOWN", landscape=landscape, persistence=persistence, ablation=ablation,
                         exposure=exposure, official_water_quality=official, review=review))
    return payload


def main():
    payload = build()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, indent=1, allow_nan=False), encoding="utf-8")
    print("wrote", TARGET.relative_to(ROOT), TARGET.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
