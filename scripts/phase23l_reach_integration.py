"""Phase 23L: auditable reach-level join of upstream disturbance burden and downstream satellite observability.

Inputs (all committed, hash-recorded): Phase 23H reach table (22X/22Y burden + 22O Sentinel-2 observability),
Phase 23A drainage-linkage summary, Phase 23K PlanetScope screens, Phase 23C official-record status.
Burden and observability are kept as SEPARATE axes; the monitoring label is a transparent lookup, not a risk score.
No coordinates, no imagery, zero Earth Engine requests. Mining attribution stays UNKNOWN.

  python -B -m scripts.phase23l_reach_integration
"""
import csv
import hashlib
import json
from pathlib import Path

R = Path("docs/reports")
SOURCES = {"reach_table": R / "phase23h-reach-priority.json", "linkage": R / "phase23a-linkage-summary.json",
           "planet_2025_02_20": R / "phase23k-20250220_045741_92_2534-screen.json",
           "planet_2024_11_08": R / "phase23k-20241108_044308_36_24f0-screen.json",
           "official_records": R / "phase23c-official-water-records.md"}
OUT_JSON, OUT_CSV = R / "phase23l-reach-integration.json", R / "phase23l-reach-integration.csv"
STATIONS = ("Lukha-Khaddum-4315", "Lukha-Sunapur-3376", "Myntdu-Mihmyntdu-4316", "Myntdu-Leshka-3379")
RULES = dict(
    burden=dict(HIGH=">= 10 upstream persistent clusters", MODERATE="3-9", LOW="< 3", basis="Phase 23A D8 routing of 22Y classes"),
    observability=dict(
        OBSERVABLE="a preregistered gate passes AND all sensitivities pass on at least one date (none so far)",
        MARGINAL="primary gate passes on a date but >= 1 preregistered sensitivity fails",
        UNOBSERVABLE="every assessed date fails the gate (insufficient valid interior water)",
        UNKNOWN="observations exist but water identity is inconsistent, or the reach was never assessed at a finer scale"),
    monitoring_label={"HIGH+UNOBSERVABLE": "PRIORITY FIELD MONITORING", "HIGH+MARGINAL": "PRIORITY FIELD MONITORING",
                      "HIGH+UNKNOWN": "PRIORITY FIELD MONITORING", "MODERATE+*": "FIELD MONITORING",
                      "LOW+*": "REFERENCE / LOW", "*+OBSERVABLE": "SATELLITE-TRACKABLE (add field validation)"},
    note="Labels prioritise where measurements are missing relative to modelled exposure; they are not pollution-risk scores.")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def burden_class(persistent):
    return "HIGH" if persistent >= 10 else "MODERATE" if persistent >= 3 else "LOW"


def planet_status(window):
    """-> (status, detail) for one 23K window record."""
    if not window or not window.get("covered"):
        return "NOT_COVERED", "window not covered"
    p = window.get("primary", {})
    if window.get("window_clear_fraction", 0) < 0.5 and not p.get("gate"):
        return "FAIL_CONDITIONS", f"clear {window['window_clear_fraction']:.1%} (haze {window.get('window_haze_light_fraction', 0):.1%})"
    if not p.get("gate"):
        return "FAIL_GATE", f"{p.get('interior_px', 0)} interior px (< 25); water px {p.get('water_px_corridor', 0)}; width ~{p.get('width_estimate_m', 0)} m"
    sens_fail = [k for k, v in window.get("sensitivity", {}).items() if not v.get("gate")]
    if sens_fail:
        return "PASS_MARGINAL", f"{p['interior_px']} interior px; fails sensitivities {', '.join(sens_fail)}"
    return "PASS", f"{p['interior_px']} interior px; all sensitivities pass"


def observability(s2_obs, planet):
    statuses = [s for s, _ in planet.values()]
    if "PASS" in statuses:
        return "OBSERVABLE"
    if "PASS_MARGINAL" in statuses:
        return "MARGINAL"
    if s2_obs == "INCONSISTENT":
        return "UNKNOWN"
    if statuses and all(s in ("FAIL_GATE", "FAIL_CONDITIONS") for s in statuses):
        return "UNOBSERVABLE"
    return "UNOBSERVABLE" if s2_obs == "UNOBSERVABLE" else "UNKNOWN"


def monitoring_label(burden, obs):
    if obs == "OBSERVABLE":
        return RULES["monitoring_label"]["*+OBSERVABLE"]
    if burden == "HIGH":
        return "PRIORITY FIELD MONITORING"
    return "FIELD MONITORING" if burden == "MODERATE" else "REFERENCE / LOW"


def build():
    h = {r["station"]: r for r in json.loads(SOURCES["reach_table"].read_bytes())["reaches"]}
    link = json.loads(SOURCES["linkage"].read_bytes())
    planet = {k: json.loads(SOURCES[k].read_bytes()) for k in ("planet_2025_02_20", "planet_2024_11_08")}
    rows = []
    for st in STATIONS:
        r = h[st]
        pl = {}
        for k, scene in planet.items():
            if st in scene["windows"]:
                pl[scene["acquired"][:10]] = planet_status(scene["windows"][st])
        obs = observability(r["river_observation"], pl)
        burden = burden_class(int(r["upstream_persistent"]))
        ndti = "none"
        for date, (s, _) in pl.items():
            if s in ("PASS", "PASS_MARGINAL"):
                w = planet["planet_2024_11_08" if date == "2024-11-08" else "planet_2025_02_20"]["windows"][st]["primary"]
                ndti = f"single-date descriptive only ({date}, {'fragile' if s == 'PASS_MARGINAL' else 'robust'}): median {w['ndti_median']}"
        missing = []
        if r["river_observation"] != "OBSERVED":
            missing.append(f"Sentinel-2 10 m: {r['observation_reason']}")
        if not pl:
            missing.append("PlanetScope 3 m: not acquired for this station (Phase 23K covered Khaddum/Sunapur only)")
        else:
            missing += [f"PlanetScope 3 m {d}: {det}" for d, (s, det) in pl.items() if s != "PASS"]
        missing.append("Official station measurements: none verified (CPCB NWMP unreachable/truncated; MSPCB portal lacks this code)")
        missing.append("Paired upstream/downstream NDTI: not feasible (needs both reaches passing on >= 5 dates per season)")
        rows.append(dict(
            station=st, river=r["river"], downstream_of=r["downstream_of"] or "",
            upstream_clusters=int(r["upstream_clusters"]), upstream_persistent=int(r["upstream_persistent"]),
            upstream_partial=int(r["upstream_partial"]), upstream_recovering=int(r["upstream_recovering"]),
            upstream_cluster_ha=float(r["upstream_cluster_ha"]), routing=r["drainage_link"],
            burden_class=burden, s2_observation=r["river_observation"], s2_dates_before_after=f"{r['ndti_dates_before']}/{r['ndti_dates_after']}",
            planet_status="; ".join(f"{d}: {s}" for d, (s, _) in sorted(pl.items())) or "NOT_ACQUIRED",
            observability=obs, ndti_availability=ndti, monitoring_label=monitoring_label(burden, obs),
            missing_measurement_reasons=missing, confounders=r["confounders"], mining_attribution="UNKNOWN"))
    return dict(phase="23L", earth_engine_requests=0, downloads=0, rules=RULES,
                routing=dict(method="90 m HydroSHEDS D8 to FFR reach, NDOID chain (Phase 23A)", clusters_routed=link["routed"],
                             clusters_total=link["clusters"], ambiguous_snaps=link["ambiguous_snaps"],
                             test_block_crossings=link["paths_crossing_test_blocks"], median_path_km=link["path_km_median"],
                             counts="cumulative down the main stem (Sunapur includes Khaddum; Leshka includes Mihmyntdu)"),
                sources={k: dict(file=str(v).replace("\\", "/"), sha256=sha(v)) for k, v in SOURCES.items()},
                note="Phase 23B report does not exist in the repository; not used.", reaches=rows,
                interpretation="burden = modelled exposure geometry; observability = satellite measurability; no pollution, runoff or causal claim")


def main():
    out = build()
    OUT_JSON.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    cols = [c for c in out["reaches"][0] if c != "missing_measurement_reasons"] + ["missing_measurement_reasons"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out["reaches"]:
            w.writerow({**r, "missing_measurement_reasons": " | ".join(r["missing_measurement_reasons"])})
    for r in out["reaches"]:
        print(r["station"], r["upstream_persistent"], r["burden_class"], r["observability"], r["monitoring_label"], "|", r["planet_status"])


if __name__ == "__main__":
    main()
