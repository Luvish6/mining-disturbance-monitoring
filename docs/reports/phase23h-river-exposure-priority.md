# Phase 23H — Reach-level river exposure and inspection priority (Lukha and Myntdu)

This phase starts from `f0bd161`. It is offline only: zero Earth Engine requests, zero downloads, no model training and no TEST data. The table is [phase23h-reach-priority.csv](phase23h-reach-priority.csv), with the same content plus rules and provenance in [phase23h-reach-priority.json](phase23h-reach-priority.json). It is built by `scripts/phase23h_reach_priority.py` and tested in `tests/test_phase23h_reach_priority.py`.

**Categories and priority levels are rule-based review labels, not risk scores.** No pollution, degradation or mining causation is claimed.

## Method (for an IEEE-style methods section)

**Units.** The four CPCB station reaches (Khaddum 4315 and Sunapur 3376 on the Lukha; Mihmyntdu 4316 and Leshka 3379 on the Myntdu). The reaches are snapped to HydroSHEDS FFR lines as in Phase 4A.

**Inputs (all frozen).**
- Disturbance exposure: the 174 Phase 22X clusters and their 22Y persistence classes, D8-routed to the reaches in Phase 23A. Counts are cumulative down the main stem.
- River observations: Phase 22O relative NDTI = (B4 − B3)/(B4 + B3), from the preregistered water screen (JRC ≥ 50%, MNDWI > 0, cloud/shadow/edge masks, 1-pixel erosion, at least 3 interior pixels per date).
- Official water quality: Phases 23C and 23D.

**Rules.** These were fixed before the table was computed, reusing the preregistered minima of 22O and 23A where they exist.

1. **Drainage link:** at least 3 D8-routed upstream clusters.
2. **River observed** requires, in **each** season, both:
   - at least 5 valid dates; and
   - a median share of SCL-water pixels among the interior pixels of at least 0.5.

   If only one season meets the water-identity test, the reach is *INCONSISTENT* and gets the category UNKNOWN.
3. **Shift:** the 22O after-minus-before median NDTI, with a date-bootstrap 95% CI that excludes 0. This is assessed only for observed reaches. A non-significant shift is **not** taken as evidence of no effect.
4. **Category:**
   - LINKED_CANDIDATE: link and shift.
   - LAND_DISTURBANCE_ONLY: link, river observed, no detectable shift.
   - RIVER_SHIFT_ONLY: shift, no link.
   - RIVER_UNOBSERVABLE: insufficient valid observations.
   - Otherwise **UNKNOWN**; no category is forced.
5. **Inspection priority** is an ordinal review heuristic, not a score:
   - **HIGH:** river unobservable and at least 10 upstream persistent clusters.
   - **MEDIUM:** unobservable or UNKNOWN, with 3–9 upstream persistent clusters.
   - **LOW:** fewer than 3.
6. **Official records** are attached to a reach **only** if the station's identity *and* location are verified.

## Results

| Reach | Upstream clusters (persistent / partial / recovering) | Upstream cluster area (ha) | NDTI dates before / after | River observation | Category | Priority |
|---|---|---|---|---|---|---|
| Lukha · Khaddum 4315 | 11 (1 / 4 / 6) | 24.7 | 19 / 24 | UNOBSERVABLE: 0% SCL water in both seasons, so water identity is not established | RIVER_UNOBSERVABLE | LOW |
| Lukha · **Sunapur 3376** (below Khaddum) | **80 (28 / 32 / 20)** | 47.1 | 4 / 0 | UNOBSERVABLE: too few dates | RIVER_UNOBSERVABLE | **HIGH** |
| Myntdu · Mihmyntdu 4316 | 15 (7 / 5 / 3) | 4.1 | 0 / 0 | UNOBSERVABLE: no interior water | RIVER_UNOBSERVABLE | MEDIUM |
| Myntdu · Leshka 3379 (below Mihmyntdu) | 17 (8 / 6 / 3) | 5.3 | 15 / 13 | INCONSISTENT: SCL water share 1.00 before, 0.06 after | **UNKNOWN** | MEDIUM |

**No reach qualifies as LINKED_CANDIDATE, LAND_DISTURBANCE_ONLY or RIVER_SHIFT_ONLY.** For context, Phase 22O reported a Leshka after-minus-before shift of +0.025 [−0.105, 0.130]. It is not used here because of the water-identity inconsistency, and it would not have been a detected shift anyway.

**Official water quality at the four reaches: none verified.**
- The CPCB NWMP files were unreachable (23C) or truncated (23D).
- The MSPCB monthly portal does not list these four station codes.

**Kept separate, not linked to any reach:** the MSPCB monthly series for **3375 Lunar (a Lukha tributary) at Myndihati**, with pH 2.5–3.1 in all 10 study months, as well as 1428 Kyrhuhkhla and 1631 Myntdu at Jowai. Their coordinates are unverified (23C). pH is an acidity measurement and is **not comparable to NDTI**.

**Why Sunapur is the top monitoring priority.** It has the largest modelled upstream disturbance exposure: 28 persistent clusters, mostly Lumshnong drainage entering between Khaddum and Sunapur. It also has **no usable NDTI** and no verified official record. Its priority reflects a *monitoring gap at the most exposed reach*. It does not reflect demonstrated pollution.

## Confounders and uncertainty (per reach, also in the CSV)

- **Khaddum:** narrow channel; mixed bright pixels; karst; 57 m station-to-reach snap.
- **Sunapur:** water clearance of 22 m or less. The Lunar joins near Sonapur, but its position relative to the CPCB point is unverified. 101 m snap; karst.
- **Mihmyntdu:** narrow channel; Jowai-bypass road-construction debris upstream (NGT OA 1271/2024); domestic sources.
- **Leshka:** impounded reservoir with dam releases; seasonal SCL inconsistency; upstream road works.
- **All reaches:**
  - the after season was about 45% drier;
  - no discharge or release data;
  - the 90 m DEM routing cannot see 30 m drainage, roads or culverts;
  - the cluster causes are UNKNOWN.

## Data provenance

The input hashes are in the JSON:
- `docs/reports/phase22o-summary.json`;
- `docs/reports/phase23a-linkage-summary.json`.

Upstream phases: 22X `23622e9`, 22Y `bf9db3a`, 23A linkage `0740c20`, 23C/23D `fcaa3e3`/`e99475e`.

## Future validation requirements

1. **Sunapur and Khaddum observations.** Dated official measurements (turbidity/TSS, conductivity, sulphate, iron, pH), or field samples matched to Sentinel-2 overpasses. Request them from MSPCB; see `docs/outreach/`.
2. **Verified station coordinates.** For 3375 Lunar/Myndihati and the 4 CPCB stations, to confirm their positions relative to the Lunar confluence and the routed inflows.
3. **Finer optical data.** PlanetScope at 3 m, or a dated bank survey, to resolve the narrow channels. Keep the same preregistered water and shift rules.
4. **Hydrology.** Discharge and Myntdu–Leshka release records to interpret any future shift.
5. **Cause of disturbance.** Independent mining-activity footprints (DMR/MBDA survey) to move clusters out of UNKNOWN.
