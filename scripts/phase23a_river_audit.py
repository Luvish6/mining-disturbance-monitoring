"""Phase 23A Stage 1: offline river-feasibility evidence table for Lukha/Myntdu (no data requests).

Compiles every Meghalaya river window already screened (Phase 4A, 12B, 22O) from local receipts and
records why each failed. No new imagery, no Earth Engine, no TEST access.

  python -B -m scripts.phase23a_river_audit
"""
import csv
import json
from pathlib import Path

from scripts.phase22p_sar_corroboration import save, sha

A4 = Path("outputs/phase4a_river_feasibility/receipt.json")
B12 = Path("outputs/phase12b_site_selection")
O22 = Path("docs/reports/phase22o-summary.json")
SUMMARY = Path("docs/reports/phase23a-summary.json")
MIN_INTERIOR_DATES = 5  # Phase 22O preregistered seasonal minimum


def window_status(before_interior, after_interior, min_dates=MIN_INTERIOR_DATES):
    if before_interior == 0 and after_interior == 0:
        return "NO_INTERIOR_WATER"
    if min(before_interior, after_interior) < min_dates:
        return "INSUFFICIENT_DATES"
    return "INTERIOR_SUPPORTED"


def main():
    a4 = json.loads(A4.read_bytes())["stations"]
    o22 = json.loads(O22.read_bytes())["stations"]
    rows = []
    for st, v in a4.items():
        p, s = v["reach_properties"], v["seasons"]
        bi, ai = s["before"]["core_dates"], s["after"]["core_dates"]
        rows.append(dict(window=st, river=st.split("-")[0], phase="4A (+22O)", reach_goid=p["GOID"],
                         mean_discharge_m3s=p["DIS_AV_CMS"], upland_km2=p["UPLAND_SKM"],
                         max_clearance_m=[round(s["before"]["max_clearance_m"], 1), round(s["after"]["max_clearance_m"], 1)],
                         interior_dates=[bi, ai], status_4a=window_status(bi, ai),
                         status_22o=o22.get(st, {}).get("status"),
                         note={"Myntdu-Leshka-3379": "potentially impounded (Myntdu-Leshka Stage I); 22O CI spans 0",
                               "Lukha-Khaddum-4315": "22O screen passes but 0% SCL water: water identity doubtful",
                               }.get(st, "")))
    for f in sorted(B12.glob("[0-9]*.csv")):
        r = next(csv.DictReader(f.open()))
        bi, ai = int(r["before_interior_dates"]), int(r["after_interior_dates"])
        rows.append(dict(window=f"{r['station']}->{r['candidate_noid']}", river=r["station"].split("-")[0], phase="12B",
                         reach_goid=int(r["candidate_noid"]), mean_discharge_m3s=None, upland_km2=None, max_clearance_m=None,
                         interior_dates=[bi, ai], status_4a=window_status(bi, ai), status_22o=None,
                         note=f"{r['mapped_direction']} of anchor; matched pairs {r['matched_pairs']}, common cells {r['common_cells']}"))
    flowing_ok = [r["window"] for r in rows if r["status_4a"] == "INTERIOR_SUPPORTED" and "Leshka" not in r["window"]]
    save(SUMMARY, dict(
        phase="23A-stage1", earth_engine_requests=0, inputs={str(A4): sha(A4), str(O22): sha(O22)},
        windows=rows, windows_screened=len(rows),
        flowing_reaches_with_supported_interior=flowing_ok,
        widest_flowing_reach=dict(window="Lukha-Sunapur-3376", mean_discharge_m3s=a4["Lukha-Sunapur-3376"]["reach_properties"]["DIS_AV_CMS"],
                                  max_clearance_m=[22.4, 10.0]),
        decision=dict(sentinel2_ndti_pilot="NO-GO", drainage_linkage="CONDITIONAL (needs flow-direction data; approval)",
                      official_water_quality="CONDITIONAL (CPCB/MSPCB station records not cached; approval to download)")))
    for r in rows:
        print(r["window"], r["interior_dates"], r["status_4a"], r["status_22o"])


if __name__ == "__main__":
    main()
