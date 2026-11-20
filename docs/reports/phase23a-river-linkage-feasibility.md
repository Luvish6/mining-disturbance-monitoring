# Phase 23A — Downstream river degradation feasibility and mining–river linkage (Stage 1 audit)

This audit starts from `201b188`. It made **no** new data requests: 0 Earth Engine requests and no downloads. The evidence table is [phase23a-summary.json](phase23a-summary.json), built offline by `scripts/phase23a_river_audit.py` from the local Phase 4A, 12B and 22O receipts. TEST data was not touched, and mining attribution remains UNKNOWN.

**NDTI** = (B4 − B3)/(B4 + B3) is a relative optical turbidity proxy only. It is not NTU, acidity or metals.

## 1. Why the previous river analyses failed

| Window (phase) | Mean discharge (HydroSHEDS, m³/s) | Max water clearance before / after (m) | Interior dates before / after | Status |
|---|---|---|---|---|
| Lukha · Khaddum (4A, 22O) | 19.2 | 0 / 0 | 0 / 0 | No interior water. The 22O screen passed, but 0% of the pixels are SCL water, so water identity is doubtful. |
| Lukha · Sunapur (4A, 22O) | **68.6** (largest in the study area) | 22 / 10 | 1 / 0 | Insufficient |
| Myntdu · Mihmyntdu (4A, 22O) | 6.2 | 10 / 10 | 0 / 0 | No interior water |
| Myntdu · Leshka (4A, 4B, 22O) | 35.2 | 149 / 150 | 11 / 6 | Supported, but **potentially impounded** (Stage I dam). The 22O change CI spans 0, and 4B found only 12 fixed cells. |
| 5 adjacent reaches (12B) | — | — | 0–2 / 0–4 | All insufficient: at most 2 matched pairs and 0 common cells |

Across **9 windows** screened, the main causes are:
1. **Narrow channels.** Even the highest-discharge Lukha reach inside the districts gives at most 22 m of water clearance, about two 10 m pixels. After one-pixel erosion, almost no interior water remains. Mixed land and water pixels contaminate everything else.
2. **Uncertain water identification.** At Khaddum, JRC occurrence plus MNDWI admitted bright pixels that SCL never classifies as water.
3. **Impoundment.** The one wide water body is a hydropower reservoir, so it cannot represent flowing-river degradation.
4. **Season and weather.** Dry-season low flow narrows the channels further. The monsoon would widen them but brings near-continuous cloud. CHIRPS shows the after season was about 45% drier at every station, so the seasons are not hydrologically comparable.
5. **Missing data.** There are no discharge, dam-release or synchronous field turbidity measurements.

The wider downstream Lukha and Myntdu reaches lie **outside the study districts, in Bangladesh**. They are out of scope and lack project guards.

## 2. Can disturbances be linked to river reaches through drainage paths?

**Not with the data currently cached.**
- The project has HydroSHEDS FFR *topology* (GOID → NDOID for 478 reaches) and line geometry only for 3 station windows. That is enough to confirm main-stem order: Khaddum → Sunapur in 14 hops, and Mihmyntdu → Leshka in 18 hops.
- It has **no flow-direction raster or sub-basin polygons**. The 174 Phase 22X clusters therefore cannot be routed to a reach. Straight-line distance is not a drainage path, so it was not used.
- The MSPCB Lukha action plan documents, in narrative, that streams from the Lumshnong mining area feed the Lunar before it joins the Lukha. No cluster-specific trace exists.

## 3. Alternative observation options (judged on width and coverage, never on turbidity)

| Option | Feasibility | Limitation |
|---|---|---|
| Sentinel-2, 10 m, other in-district reaches | Low. Nine windows on the two largest rivers have already failed. | Channels narrower than about 30 m; dry-season low flow |
| Landsat, 30 m | Lower than Sentinel-2 | Coarser than the channel widths |
| PlanetScope, 3 m (commercial) | Possible resolution | Licence and cost; no access verified for this purpose; water-specific calibration is absent |
| Leshka reservoir only | Supported support | A regulated reservoir, not a downstream flowing reach. The 22O comparison found no change. |
| CPCB/MSPCB station records (Khaddum 4315, Sunapur 3376, Mihmyntdu 4316, Leshka 3379) | **Most direct** measured evidence: pH, conductivity and related parameters at mapped stations | Not cached. Availability for 2023–25, parameter set and sampling dates are unverified. Usually monthly or quarterly. |

## 4. Rainfall and seasonal control

CHIRPS station-cell series are cached and give antecedent rainfall. But at about 5 km resolution, without catchment rainfall, discharge or dam-release timing, rainfall cannot be controlled well enough for a defensible before/after attribution. Matching by month and antecedent rain only narrows the comparison.

## Decision

| Component | Decision |
|---|---|
| Sentinel-2 NDTI pilot on Lukha/Myntdu flowing reaches | **NO-GO.** No credible water support exists. Changing masks or sites to obtain values is not justified. |
| Drainage linkage of clusters to monitored reaches (exposure mapping) | **CONDITIONAL GO, pending your approval of the requests below.** |
| Official water-quality records at the 4 CPCB stations | **CONDITIONAL GO, pending your approval to locate and download public CPCB/MSPCB files.** |

The realistic river contribution is an **exposure map plus official records**:
- how much (UNKNOWN-cause) candidate disturbance drains to each monitored station;
- the stations' published water-quality records, reported descriptively with **no causal inference**. There are only 4 stations, which are not independent along a main stem, and the record is short.

## Proposed Stage 2 (not run; needs approval)

**1. Linkage pilot: preregister, then request.**
- `WWF/HydroSHEDS/03DIR` (90 m D8 flow direction) over the bounding box of the two districts. About 800 × 700 int8 pixels, one URL plus one download, **about 0.6 MB**.
- `WWF/HydroSHEDS/v1/FreeFlowingRivers` reach geometries plus GOID/NDOID for the same bounding box, in one `getInfo`, **about 1–2 MB**.
- Optionally, `WWF/HydroSHEDS/v1/Basins/hybas_12` polygons with NEXT_DOWN, in one `getInfo`, **about 1–2 MB**.
- **Total: about 4 Earth Engine requests and at most 5 MB.** It runs under the existing lock and ledger.

**Offline method:**
- Route each of the 174 cluster centroids along the D8 path to the first FFR reach.
- Follow the NDOID chain to identify the downstream stations.
- Report upstream cluster count and area, and persistence class, per station.

**Failure criteria:**
- the D8 path leaves the bounding box;
- the snapped reach is ambiguous (more than 1 reach within 90 m);
- a station has fewer than 3 upstream clusters.

**Guards.** The flow-direction raster is static terrain, not TEST imagery, labels or predictions. Only non-TEST 22X clusters are routed. Paths crossing TEST blocks are recorded, but no TEST data is read.

**2. Official records.** Locate the CPCB NWMP and MSPCB publications for stations 4315, 3376, 4316 and 3379 covering 2023–2025. Report their URLs, sizes and licences for approval before downloading. Then tabulate the parameters and dates as published.

## Evidence still missing for any degradation claim

- Synchronous field turbidity or suspended-sediment samples.
- Discharge and dam-release records.
- Verified mining outfalls and their activity dates.
- Water-specific atmospheric correction.

Without these, even a successful linkage and records pilot yields **co-location and description, not causation**.

## Stage 2 — drainage-linkage pilot results (approved; run 2026-11-21)

**Records.** The preregistration is `a9555a4` ([phase23a-linkage-preregistration.json](phase23a-linkage-preregistration.json)). Results are in [phase23a-linkage-summary.json](phase23a-linkage-summary.json). Code is in `scripts/phase23a_linkage.py` and tests in `tests/test_phase23a_linkage.py`. The per-cluster routes stay local in `outputs/phase23a_linkage/`.

**Usage.** 5 Earth Engine requests and 1,123,960 bytes, against a cap of 6 requests and 6 MB.
- One request was wasted: an `ee.Dictionary` wrapping the reach FeatureCollection returned only metadata. It is recorded in the ledger, and the code now fetches the collection directly.
- The native 3-arc-second D8 grid was verified, so no direction codes were resampled.
- 2,558 FFR reaches were returned.

**Routing.** All **174 of 174** clusters routed, with no sink, bbox exit or step-limit failures. The median D8 path to the first mapped reach is 0.99 km. One snap was ambiguous (88:558/C005). No path crossed a TEST block.

| Monitored station reach | Upstream clusters | Upstream cluster area (ha) | PERSISTENT / PARTIAL / RECOVERING | Status |
|---|---|---|---|---|
| Lukha · Khaddum 4315 | 11 | 24.7 | 1 / 4 / 6 | LINKED |
| Lukha · Sunapur 3376 (downstream of Khaddum) | **80** | 47.1 | **28** / 32 / 20 | LINKED |
| Myntdu · Mihmyntdu 4316 | 15 | 4.1 | 7 / 5 / 3 | LINKED |
| Myntdu · Leshka 3379 (downstream of Mihmyntdu) | 17 | 5.3 | 8 / 6 / 3 | LINKED |

Counts are cumulative down the main stem: Sunapur includes Khaddum's 11 clusters, and Leshka includes Mihmyntdu's 15. **77 clusters** route to reaches that reach none of the four monitored stations: other tributaries, or reaches leaving the district.

**Lumshnong.** Of the 28 persistent Lumshnong clusters:
- **22 enter the Lukha *between* Khaddum and Sunapur**;
- 1 passes Khaddum;
- 5 reach no monitored station.

This agrees with the MSPCB narrative of Lumshnong-area streams feeding the Lunar–Lukha system. It gives a DEM-supported **upstream/downstream bracket**: Khaddum is weakly exposed (1 persistent cluster upstream) and Sunapur is strongly exposed (28).

### Interpretation and limits

The disturbance clusters **can be linked to river reaches through modelled drainage paths**, not just straight-line distance. Khaddum–Sunapur forms the most defensible exposure bracket in the study area.

This is **exposure geometry, not impact**:
- **DEM resolution.** The 90 m DEM routing cannot resolve 30 m clusters' local drainage, roads or culverts.
- **Karst.** Lumshnong is limestone karst, where subsurface flow can bypass surface routes.
- **Station position.** Each station's reach is the nearest mapped line to the CPCB coordinate (27–101 m away). If a sampling point lies below a confluence, the bracket changes.
- **Cluster status.** The clusters remain UNKNOWN land disturbance.

The bracket's *river observations* still fail at 10 m (Sunapur: 1/0 interior dates). So the defensible next step is **official station records** (CPCB/MSPCB) at Khaddum vs Sunapur and Mihmyntdu vs Leshka, reported descriptively. That needs your approval to locate and download them. No degradation or causal claim is supported.
