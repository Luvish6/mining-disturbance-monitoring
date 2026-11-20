# Phase 22Z — Mining-context validation and alternative-explanation audit

**Starting point:** commit `bf9db3a`.

**Constraints:** zero Earth Engine requests, no training, no new labelling and no TEST access.

**Code and data:** the script is `scripts/phase22z_context.py` and the tests are `tests/test_phase22z_context.py`. Results and the shortlist are in [phase22z-summary.json](phase22z-summary.json). The shortlist carries IDs and context only; exact centroids stay local in `outputs/phase22z_context/`.

**Decision: NO-GO for mining attribution.** All 53 persistent clusters remain **UNKNOWN**.

## Evidence available offline

**Cached data.** The Phase 22X seasonal stacks (S2, S1, slope), the Phase 22Y follow-up season and the Phase 22R samples (GFC v1.13 and WRI/GDM drivers v1.2) were reused. The cluster classes reproduce Phase 22Y exactly, and the script checks this.

**Independent mining-site geometry.** Only **one** archived, non-TEST official geometry exists: the MoEFCC environmental-clearance *application polygon* "Lumshnong Limestone Mine (70 ha)" in VAL block 87:556.
- It is an administrative perimeter in WGS84 KML.
- Its positional accuracy is unknown, and it gives no activity dates.
- It does not show where excavation occurred.

**Excluded sources:**
- KORPET and Sumon KMLs: TEST block 81:557, never used.
- IBM pit grids: no stated CRS ([Phase 22S](phase22s-official-mining-data-audit.md)).
- Earlier screening "R" search areas: not independent.
- Mineral occurrences and coarse probability maps: never treated as footprints.

**Not available locally.** Roads and settlements at 30 m (no OSM or Bhuvan cache), active excavation footprints, and field or expert verification.

## Findings

**Distribution.** There are 53 persistent clusters (25.6 ha in total, mostly 0.09–0.5 ha each) across 13 AOIs: 34 in East and 19 in West Jaintia Hills. 28 lie in the two adjacent Lumshnong blocks (87:556 with 12, 87:557 with 16).

**Proximity to the documented site.**
- **No** persistent cluster lies inside the application polygon.
- 8 lie within 1 km of it, all in 87:556, at 0.40–0.95 km.

**Dominant 1 km driver class at the persistent clusters.**

| Driver (WRI/GDM, 2001–2024) | Lumshnong locality | Elsewhere |
|---|---|---|
| Hard commodities | 14 | 0 |
| Settlements and infrastructure | 14 | 4 |
| Logging | 0 | 10 |
| Shifting cultivation | 0 | 7 |
| Permanent agriculture | 0 | 4 |

Even at Lumshnong, half the persistent clusters sit in cells dominated by *settlements and infrastructure*. The locality contains cement plants and the related built-up area. Mining, plant construction, roads and dumps are all compatible explanations.

**Is the Lumshnong association robust?**
- The two blocks are adjacent, so they were treated as **one locality**.
- Its pooled persistent share is 52% (28 of 54), against 21% elsewhere (25 of 120).
- No single other AOI reaches 52%; the maximum elsewhere is 50%.
- But **12 of the 153 possible AOI pairs** (7.8%) pool to an equal or higher share.
- With one locality and spatially dependent clusters, the elevated share is **descriptive and not distinguishable from between-locality variability**. No significance is claimed.

**Alternative explanations outside Lumshnong (120 clusters).**

| Class | n | Mean slope (°) | treecover2000 | Shifting-cultivation-dominant cell | GFC 2024/25 loss | Prior GFC loss |
|---|---|---|---|---|---|---|
| PERSISTENT | 25 | 7.9 | 54 | 28% | 48% | 40% |
| PARTIAL | 59 | 11.5 | 67 | 61% | 41% | 27% |
| RECOVERING | 36 | 13.3 | 76 | 86% | 56% | 42% |

- **Recovering clusters** are steep, formerly forested and mostly in shifting-cultivation cells. That is the expected jhum signature.
- **Persistent clusters** are flatter and less forested, and are more often in logging, settlement or agricultural cells. The gentler slope also holds *within* Lumshnong (8.3°), so it is a general trait of persistence, not a mining signature.

## Review-priority shortlist (UNKNOWN; not labels)

The tier rule was fixed before computation:

| Tier | Rule | Clusters |
|---|---|---|
| **1** | Inside or within 1 km of the official application perimeter, **or** in a hard-commodity-dominant 1 km cell | **16** (all in 87:556 / 87:557) |
| **2** | Persistent, with 2024/25 GFC loss | 13 |
| **3** | Other persistent | 24 |

Each row in the summary JSON records:
- cluster ID, AOI, district and split;
- size, persistence deltas, dVH, slope, GFC loss and tree cover;
- dominant driver class, hard-commodities probability and distance to the perimeter.

The tiers order clusters for future DMR/MBDA or expert review only.

## What can and cannot be answered

- **Answered offline:** spatial distribution, the locality comparison, distance to the single administrative perimeter, and terrain, forest-loss, driver and persistence context.
- **Requires unavailable independent data:**
  - active excavation footprints (the DMR/MBDA drone survey, IBM georeferenced plans);
  - 30 m roads and settlements;
  - dated lease boundaries beyond one polygon;
  - field or expert verification.

## Decision

**NO-GO: mining attribution has not improved to a defensible level.**
- The only independent geometry is administrative.
- No cluster falls inside it.
- The 1 km driver map is too coarse, and at Lumshnong it splits between hard commodities and settlements.
- Persistence and gentle slope fit infrastructure as well as quarrying.

The project can defensibly claim *persistent, multi-sensor-corroborated land disturbance concentrated near a documented limestone-mining and cement locality*. It cannot claim mining detections.

**Next step:** obtain the DMR/MBDA drone-survey footprints. The letter is already drafted in `docs/outreach/`. Then check the Tier 1–2 clusters against them, and add a 30 m roads/settlement layer (OSM extract) as a preregistered exclusion test.
