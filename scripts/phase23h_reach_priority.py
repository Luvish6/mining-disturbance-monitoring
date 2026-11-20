"""Phase 23H: offline reach-level river-exposure and inspection-priority table (4 CPCB station reaches).

Combines frozen results only: Phase 22O (river NDTI), 22X/22Y (clusters, persistence), 23A (D8 drainage
linkage) and 23C/23D (official water-quality availability). Zero Earth Engine requests, zero downloads.
Categories and priority levels are rule-based review labels, not risk scores; mining attribution stays UNKNOWN.

  python -B -m scripts.phase23h_reach_priority
"""
import csv
import json
from pathlib import Path

from scripts.phase22p_sar_corroboration import save, sha

O22 = Path("docs/reports/phase22o-summary.json")
L23 = Path("docs/reports/phase23a-linkage-summary.json")
OUT_CSV = Path("docs/reports/phase23h-reach-priority.csv")
OUT_JSON = Path("docs/reports/phase23h-reach-priority.json")

# Rules fixed before the table was computed (reusing preregistered 22O / 23A minima where they exist).
RULES = dict(
    min_dates_per_season=5,            # 22O preregistered seasonal minimum
    min_scl_water_share=0.5,           # water identity: median share of interior pixels classed SCL water, EACH season
    shift="after-minus-before median NDTI with date-bootstrap 95% CI excluding 0 (22O statistic)",
    min_upstream_clusters=3,           # 23A preregistered minimum for a linked station
    priority=dict(HIGH="river unobservable and >= 10 upstream persistent clusters",
                  MEDIUM="river unobservable or UNKNOWN, with 3-9 upstream persistent clusters",
                  LOW="< 3 upstream persistent clusters"),
)
STATIONS = ("Lukha-Khaddum-4315", "Lukha-Sunapur-3376", "Myntdu-Mihmyntdu-4316", "Myntdu-Leshka-3379")
DOWNSTREAM_OF = {"Lukha-Sunapur-3376": "Lukha-Khaddum-4315", "Myntdu-Leshka-3379": "Myntdu-Mihmyntdu-4316"}
CONFOUNDERS = {
    "Lukha-Khaddum-4315": "narrow channel; bright mixed pixels pass MNDWI/JRC but 0% SCL water; karst; station-to-reach snap 57 m",
    "Lukha-Sunapur-3376": "narrow channel (<= 22 m water clearance); Lunar tributary joins near Sonapur (literature), position "
                          "relative to CPCB point unverified; snap 101 m; karst",
    "Myntdu-Mihmyntdu-4316": "narrow channel; Jowai bypass road-construction debris upstream (NGT OA 1271/2024); domestic sources",
    "Myntdu-Leshka-3379": "impounded reservoir/backwater of Myntdu-Leshka Stage I (dam releases); SCL classifies the same water "
                          "differently between seasons; upstream road construction",
}
COMMON = "after season ~45% drier (CHIRPS station cell); no discharge or release records; 90 m DEM routing; clusters UNKNOWN"


def river_observation(station_22o):
    """-> (observed: bool|None, reason). None = observations exist but water identity is inconsistent."""
    seasons = station_22o.get("seasons") or {}
    if not seasons:
        return False, "no interior water (unresolved before acquisition)"
    dates = {s: seasons[s]["usable_dates"] for s in ("before", "after")}
    if min(dates.values()) < RULES["min_dates_per_season"]:
        return False, f"insufficient dates {dates['before']}/{dates['after']} (< {RULES['min_dates_per_season']})"
    share = {s: (seasons[s].get("posthoc_diagnostics") or {}).get("median_scl_water_share") for s in ("before", "after")}
    if all(v is not None and v < RULES["min_scl_water_share"] for v in share.values()):
        return False, f"water identity not established (SCL water share {share['before']}/{share['after']})"
    if any(v is None or v < RULES["min_scl_water_share"] for v in share.values()):
        return None, f"water identity inconsistent between seasons (SCL water share {share['before']:.2f}/{share['after']:.2f})"
    return True, f"{dates['before']}/{dates['after']} dates; water identity consistent"


def shift_detected(station_22o):
    ci = station_22o.get("difference_ci95")
    return None if ci is None else bool(ci[0] > 0 or ci[1] < 0)


def category(linked, observed, shift):
    if observed is None:
        return "UNKNOWN"
    if observed is False:
        return "RIVER_UNOBSERVABLE"
    if shift is None:
        return "UNKNOWN"
    if linked and shift:
        return "LINKED_CANDIDATE"
    if linked and not shift:
        return "LAND_DISTURBANCE_ONLY"
    if shift and not linked:
        return "RIVER_SHIFT_ONLY"
    return "UNKNOWN"


def priority(cat, persistent):
    if persistent < 3:
        return "LOW"
    if cat == "RIVER_UNOBSERVABLE" and persistent >= 10:
        return "HIGH"
    return "MEDIUM"


def main():
    o, l = json.loads(O22.read_bytes())["stations"], json.loads(L23.read_bytes())
    rows = []
    for st in STATIONS:
        s, e = o[st], l["per_station"][st]
        linked = e["upstream_clusters"] >= RULES["min_upstream_clusters"]
        observed, why = river_observation(s)
        shift = shift_detected(s) if observed else None
        cat = category(linked, observed, shift)
        seasons = s.get("seasons") or {}
        rows.append(dict(
            station=st, river=st.split("-")[0], downstream_of=DOWNSTREAM_OF.get(st, ""),
            upstream_clusters=e["upstream_clusters"], upstream_persistent=e["persistent"],
            upstream_partial=e["classes"]["PARTIAL"], upstream_recovering=e["classes"]["RECOVERING"],
            upstream_cluster_ha=e["upstream_ha"], drainage_link="D8-routed (23A)" if linked else "below minimum",
            ndti_dates_before=(seasons.get("before") or {}).get("usable_dates", 0),
            ndti_dates_after=(seasons.get("after") or {}).get("usable_dates", 0),
            river_observation=("OBSERVED" if observed else "UNOBSERVABLE" if observed is False else "INCONSISTENT"),
            observation_reason=why,
            ndti_shift_after_minus_before=(round(s["after_minus_before_median"], 4) if observed and "after_minus_before_median" in s else ""),
            ndti_shift_ci95=(f"[{s['difference_ci95'][0]:.3f}, {s['difference_ci95'][1]:.3f}]" if observed and s.get("difference_ci95") else ""),
            shift_detected={True: "YES", False: "NO", None: "NOT_ASSESSED"}[shift],
            official_wq_at_station="NONE VERIFIED (CPCB NWMP unreachable/truncated; MSPCB portal does not list this code)",
            evidence_category=cat, inspection_priority=priority(cat, e["persistent"]),
            confounders=f"{CONFOUNDERS[st]}; {COMMON}"))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    save(OUT_JSON, dict(phase="23H", earth_engine_requests=0, downloads=0, rules=RULES,
                        inputs={str(O22): sha(O22), str(L23): sha(L23)}, reaches=rows,
                        separate_official_records=dict(
                            note="MSPCB monthly portal stations NOT linked to any reach (coordinates unverified)",
                            stations=["3375 Lunar (Lukha tributary) at Myndihati", "1428 Kyrhuhkhla", "1631 Myntdu at Jowai"],
                            source="docs/reports/phase23c-official-water-records.md"),
                        interpretation="review and monitoring priority only; no pollution, degradation or causation claim"))
    for r in rows:
        print(r["station"], r["upstream_clusters"], r["upstream_persistent"], r["river_observation"], r["evidence_category"], r["inspection_priority"])


if __name__ == "__main__":
    main()
