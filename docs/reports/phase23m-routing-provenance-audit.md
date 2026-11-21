# Phase 23M — Routing provenance audit of Phase 23L

**Scope.** This audits commit `007d08f`. It was offline and read-only: no data was reconstructed, no results changed, no TEST data was used and no Earth Engine requests were made. Checks are in [phase23m-routing-audit.json](phase23m-routing-audit.json), produced by `scripts/phase23m_routing_audit.py`.

**Verdict: provenance COMPLETE. 27 of 27 checks pass.** The Phase 23L routing claims stand without qualification.

## Phase 23B

No Phase 23B report, output folder or commit exists under any name. Searched: file names, `outputs/`, `docs/`, `scripts/`, `tests/` and the full git log. Phase 23L already states this, and it used no 23B input. The routing provenance is **Phase 23A** (the drainage-linkage pilot, preregistration `a9555a4`, results `0740c20`).

## What was verified

| Chain link | Result |
|---|---|
| All 5 Phase 23L source hashes (23H table, 23A summary, two 23K screens, 23C report) | Match the current files |
| 23A preregistration hash recorded in the 23A summary | Matches |
| Station identity: 23A preregistration GOIDs = Phase 4A receipt reach GOIDs (4103404, 4110349, 4090610, 4100220) | Match |
| Per-cluster routes (`outputs/phase23a_linkage/routes.json`, local) | 174/174 routed |
| Per-station counts re-derived from the routes | Equal the 23A summary, 23H and 23L for all 4 stations (clusters, persistent, partial, recovering, ha) |
| Persistence join: route cluster IDs and classes against the local 22Y table | Identical, cluster by cluster |
| Class totals (53 / 77 / 44) | Equal the 22Y summary |
| Routing uncertainty (1 ambiguous snap, 0 TEST crossings) | Equal across routes, 23A and 23L |
| "Cumulative" counts: every Khaddum-routed cluster also reaches Sunapur; every Mihmyntdu cluster also reaches Leshka | Holds |

## Residual limitation (not a gap)

Exact re-derivation needs two git-ignored local files: the per-cluster routes and the 22Y class table. They are kept local because cluster identities link to private candidate positions. The committed artifacts record the hashes needed to detect any change. The routes file's own hash is recorded in the audit JSON.

The modelled-routing caveats already stated in Phases 23A and 23L still apply: 90 m D8 routing, karst, culverts, and station snapping of 27–101 m.
