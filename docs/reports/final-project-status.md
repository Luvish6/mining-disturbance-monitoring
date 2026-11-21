# Final project status (Phase 24)

Status as of the Phase 24 completion commit. Every number below links to a committed report.

## Completed

| Area | Result | Source |
|---|---|---|
| Seasonal S1/S2 pipeline | Frozen Nov–Mar 2023/24 vs 2024/25 composites, with coverage gates and terrain | [PHASE1_2_PREPROCESSING.md](../PHASE1_2_PREPROCESSING.md) |
| Meghalaya landscape screening (22X) | 20 AOIs. Density 1.20 ha per 100 ha [0.62, 1.98]. 174 clusters. Cluster dVH −1.45 dB relative to background, negative in 18 of 18 AOIs; translation-null p ≈ 1e-4 | [phase22x-summary.json](phase22x-summary.json) |
| Persistence (22Y) | Persistent 53 (30.5%), partial 77, recovering 44 | [phase22y-summary.json](phase22y-summary.json) |
| Sensor ablation (22W, weak labels) | Validation F1 (Odisha):<br>• SAR 0.378<br>• optical 0.533<br>• fusion 0.539<br>• fusion + terrain 0.463<br>• rule 0.437<br>Fusion − optical: +0.006 [−0.039, 0.058] | [phase22w-metrics.json](phase22w-metrics.json) |
| Weak-label models (22H/22K) | U-Net validation F1 0.713 ± 0.085; RF-A 0.574; index rule 0.437. These are agreement with unverified Maus v2 footprints, not accuracy | [phase24c-evidence-summary.json](phase24c-evidence-summary.json) |
| External RGB benchmark (17G, MineNetCD256) | RF held-out pooled F1 0.246. Applies to non-Indian sites only | [phase17g-rf-heldout-results.md](phase17g-rf-heldout-results.md) |
| River routing (23A) | 174 of 174 clusters routed. Upstream clusters (persistent in brackets): Khaddum 11 (1), Sunapur 80 (28), Mihmyntdu 15 (7), Leshka 17 (8) | [phase23a-linkage-summary.json](phase23a-linkage-summary.json) |
| Routing audit (23M) | 27 of 27 checks pass. The routing source is **Phase 23A**; no Phase 23B exists | [phase23m-routing-audit.json](phase23m-routing-audit.json) |
| Reach integration (23L) | Sunapur: PRIORITY FIELD MONITORING. Mihmyntdu and Leshka: FIELD MONITORING. Khaddum: REFERENCE/LOW (marginal) | [phase23l-reach-integration.json](phase23l-reach-integration.json) |
| River NDTI (22O, 23K) | **Negative.** Sentinel-2 at 10 m cannot resolve the channels. At PlanetScope 3 m, Khaddum is marginal (44 px, NDTI −0.002) and Sunapur has 0 px. Closed | [phase22o-river-ndti.md](phase22o-river-ndti.md), [phase23k-planet-first-scene.md](phase23k-planet-first-scene.md) |
| India screening pipeline (24B) | Config-driven, resumable, budget-guarded. Offline demonstration on 6 cached tiles (5 states, 5.53 km²) with 0 new EE requests | [phase24b-india-screening.json](phase24b-india-screening.json) |
| Dashboard (23J, 24A, 24B) | India discovery overview with tiers, state filter, 24B summaries and provenance. The Meghalaya study, Explorer, Rivers, Analytics and Evidence views are preserved | [phase24a-india-discovery-dashboard.md](phase24a-india-discovery-dashboard.md) |

## Actual coverage compared with capability

- **What the pipeline can do.** It can screen any AOI inside India's envelope, region by region.
- **What was actually analysed:**
  - 20 Meghalaya AOIs, selected by systematic sampling;
  - 6 India tiles of 0.92 km² each.

There is **no national, state or district coverage claim**. Areas without a marker were not analysed.

## Not done: external dependencies

These items are never reported as complete.

| Item | Status | Blocker |
|---|---|---|
| Verified mining classification and Indian accuracy | **BLOCKED** | No accepted independent reference labels |
| Human review of the 30 blinded items (23I) | **PENDING** | Two reviewers. The packages are built, including Reviewer B's share folder |
| Field turbidity or water quality at Sunapur and the other reaches | **PENDING** | Field visit or official CPCB/MSPCB records. The CPCB archive copies were unusable (23F/23G) |
| Official mine or lease boundaries (DMR/MBDA) | **PENDING** | Outreach letters drafted; the user sends them |
| National-scale screening | **BLOCKED** | Needs approved EE quota. Use `--execute` per region with caps |
| Mining attribution for any cluster or lead | **UNKNOWN** | Depends on the items above |
