"""Phase 23M: offline provenance audit of the Phase 23L reach routing counts.

Re-derives every per-station count from the local Phase 23A per-cluster routes and the local Phase 22Y class
table, and checks them against the committed 23A, 23H and 23L artifacts and their recorded hashes.
Read-only: nothing is recomputed upstream of the saved routes; no Earth Engine, no TEST data.

  python -B -m scripts.phase23m_routing_audit
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

R = Path("docs/reports")
ROUTES = Path("outputs/phase23a_linkage/routes.json")           # local, per-cluster (contains no coordinates)
Y_CLUSTERS = Path("outputs/phase22y_persistence/clusters.json")  # local, per-cluster classes
OUT = R / "phase23m-routing-audit.json"
STATION_GOID = {"Lukha-Khaddum-4315": 4103404, "Lukha-Sunapur-3376": 4110349,
                "Myntdu-Mihmyntdu-4316": 4090610, "Myntdu-Leshka-3379": 4100220}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def per_station(routes):
    out = {}
    for st in STATION_GOID:
        up = [r for r in routes if st in r.get("stations", [])]
        c = Counter(r["cls"] for r in up)
        out[st] = dict(upstream_clusters=len(up), persistent=c["PERSISTENT"], partial=c["PARTIAL"], recovering=c["RECOVERING"],
                       upstream_ha=round(sum(r["ha"] for r in up), 2))
    return out


def audit():
    checks, gaps = [], []

    def check(name, ok, detail=""):
        checks.append(dict(check=name, ok=bool(ok), detail=detail))

    # 1. Phase 23L recorded source hashes still match the files
    l23 = json.loads((R / "phase23l-reach-integration.json").read_bytes())
    for k, s in l23["sources"].items():
        check(f"23L source hash: {k}", Path(s["file"]).exists() and sha(s["file"]) == s["sha256"], s["file"])
    # 2. 23A prereg hash recorded in the 23A summary
    a23 = json.loads((R / "phase23a-linkage-summary.json").read_bytes())
    check("23A preregistration hash", sha(R / "phase23a-linkage-preregistration.json") == a23["preregistration_sha256"])
    # 3. station identity: 23A preregistration GOIDs == Phase 4A receipt reach GOIDs == audit constants
    pre = json.loads((R / "phase23a-linkage-preregistration.json").read_bytes())["method"]["stations"]
    check("23A station GOIDs equal audit constants", pre == STATION_GOID, json.dumps(pre))
    p4a = Path("outputs/phase4a_river_feasibility/receipt.json")
    if p4a.exists():
        rec = json.loads(p4a.read_bytes())["stations"]
        check("Phase 4A receipt reach GOIDs match", all(rec[s]["reach_properties"]["GOID"] == g for s, g in STATION_GOID.items()))
    else:
        gaps.append("Phase 4A receipt (local) missing: station GOID cross-check not possible")
    # 4. per-cluster routes -> per-station counts (re-derived) == 23A summary == 23H == 23L
    if not ROUTES.exists():
        gaps.append(f"{ROUTES} missing: per-station counts cannot be re-derived")
        return checks, gaps, None
    routes = json.loads(ROUTES.read_bytes())
    check("routes cover all 174 clusters, all routed", len(routes) == 174 and all(r["status"] == "ROUTED" for r in routes), f"{len(routes)} routes")
    derived = per_station(routes)
    for st, d in derived.items():
        s = a23["per_station"][st]
        check(f"{st}: re-derived == 23A summary", (d["upstream_clusters"], d["persistent"], d["upstream_ha"]) ==
              (s["upstream_clusters"], s["persistent"], s["upstream_ha"]) and
              (d["partial"], d["recovering"]) == (s["classes"]["PARTIAL"], s["classes"]["RECOVERING"]), json.dumps(d))
    h23 = {r["station"]: r for r in json.loads((R / "phase23h-reach-priority.json").read_bytes())["reaches"]}
    for st, d in derived.items():
        h = h23[st]
        check(f"{st}: 23A == 23H", (d["upstream_clusters"], d["persistent"], d["partial"], d["recovering"]) ==
              (int(h["upstream_clusters"]), int(h["upstream_persistent"]), int(h["upstream_partial"]), int(h["upstream_recovering"])))
    l_rows = {r["station"]: r for r in l23["reaches"]}
    for st, d in derived.items():
        r = l_rows[st]
        check(f"{st}: 23H == 23L", (d["upstream_clusters"], d["persistent"], d["partial"], d["recovering"], d["upstream_ha"]) ==
              (r["upstream_clusters"], r["upstream_persistent"], r["upstream_partial"], r["upstream_recovering"], r["upstream_cluster_ha"]))
    # 5. persistence join: route classes == 22Y per-cluster classes, same order; totals == 22Y summary
    if Y_CLUSTERS.exists():
        y = json.loads(Y_CLUSTERS.read_bytes())
        ids = [f"{c['aoi']}/C{c['cluster']:03d}" for c in y]
        check("persistence join: route IDs and classes equal 22Y clusters", [r["id"] for r in routes] == ids and
              [r["cls"] for r in routes] == [c["cls"] for c in y])
    else:
        gaps.append(f"{Y_CLUSTERS} missing: persistence join cannot be re-checked")
    ys = json.loads((R / "phase22y-summary.json").read_bytes())["shares"]
    tot = Counter(r["cls"] for r in routes)
    check("class totals equal 22Y summary", all(tot[c] == ys[c]["clusters"] for c in ("PERSISTENT", "PARTIAL", "RECOVERING")), json.dumps(dict(tot)))
    # 6. routing uncertainty fields in 23L equal 23A and the routes
    check("routing uncertainty: ambiguous snaps", l23["routing"]["ambiguous_snaps"] == a23["ambiguous_snaps"] == sum(r.get("ambiguous", False) for r in routes))
    check("routing uncertainty: TEST crossings", l23["routing"]["test_block_crossings"] == a23["paths_crossing_test_blocks"] == sum(bool(r.get("test_blocks_crossed")) for r in routes))
    # 7. main-stem nesting implied by 'cumulative' counts
    for up, down in (("Lukha-Khaddum-4315", "Lukha-Sunapur-3376"), ("Myntdu-Mihmyntdu-4316", "Myntdu-Leshka-3379")):
        check(f"nesting {up.split('-')[1]} within {down.split('-')[1]}",
              all(down in r["stations"] for r in routes if up in r.get("stations", [])))
    return checks, gaps, derived


def main():
    checks, gaps, derived = audit()
    gaps.append("Phase 23B: no report, output folder or commit exists under any name; routing provenance is Phase 23A")
    gaps.append("Per-cluster routes and 22Y class table are local (git-ignored; exact cluster positions are kept private), "
                "so re-derivation requires the local outputs; committed artifacts carry their hashes")
    res = dict(phase="23M", checks=checks, passed=sum(c["ok"] for c in checks), total=len(checks), gaps=gaps,
               derived_per_station=derived, routes_sha256=sha(ROUTES) if ROUTES.exists() else None,
               verdict="COMPLETE" if all(c["ok"] for c in checks) else "INCOMPLETE")
    OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    for c in checks:
        print("OK " if c["ok"] else "FAIL", c["check"])
    print(res["verdict"], f"{res['passed']}/{res['total']}")


if __name__ == "__main__":
    main()
