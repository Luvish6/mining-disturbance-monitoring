# Phase 22V — Sentinel-1 vs Sentinel-2 vs fusion ablation: feasibility and pilot

The preregistration was committed as `08f3601` before acquisition ([phase22v-preregistration.json](phase22v-preregistration.json)). Pilot results are in [phase22v-pilot-summary.json](phase22v-pilot-summary.json). The code is `scripts/phase22v_fusion_pilot.py`, with tests in `tests/test_phase22v_fusion_pilot.py`.

**Label status.** The labels are **Maus v2 weak, static mining-footprint labels (2019, peninsular India)**. They are not verified labels, not Meghalaya labels and not change labels.

**Scope.** No model was trained or evaluated. VAL was not used for selection, and TEST stayed sealed.

## Stage A — verified inputs (offline)

**Optical patches.** There are 153 frozen Phase 22H patches:
- **TRAIN:** 120 patches in 40 groups across 12 states, 40 of them weak-positive.
- **VAL:** 33 Odisha patches in 11 groups, 11 of them weak-positive.

Each patch is 128 × 128 at 10 m in its local UTM zone (EPSG 32642–32645). The bands are B3, B4, B8 and an optical count, taken from the **2019 Q1 masked median** over [2019-01-01, 2019-04-01). Source dates are recorded per patch and run from 2019-01-01 to 2019-03-31. The manifest and split hashes are unchanged.

The images sit in three caches: the 114 new patches in `phase22h_maus`, and the original 39 in `phase22e_r_maus` / `phase22e_maus`. Each is resolved by its frozen `image_sha256`.

**Pairing design.** Sentinel-1 is taken over the **same Q1 2019 window** and run through the unchanged Phase 2 graph:
- IW GRD, 10 m, VV + VH, DESCENDING pass;
- per patch, the relative orbit with the most scenes (`choose_orbit`);
- linear-power 20 m focal mean, then the median in dB, with at least 2 observations.

The result is exported on each patch's exact optical grid. This is a *static same-season* pairing, not an acquisition-matched one. That is appropriate because the labels are static footprints.

**Cached SAR.** None existed for these patches. Zero VV/VH rasters were found in the Phase 22H/22I caches.

**Spatial separation.** The frozen Phase 22H groups and buffers are reused unchanged. TRAIN groups come from 12 states and VAL is Odisha-only, so the two splits are disjoint by state.

## Stage B — pilot

**Selection.** Four TRAIN patches were chosen in sha256 hash order: 2 weak-positive and 2 background, from four distinct groups and four states.

**Usage.** 9 Earth Engine requests and 402,692 bytes, against a cap of 12 requests and 2 MB.
- 7 of these were the preregistered acquisition: 1 orbit-metadata request plus 3 patches × (URL + download).
- 1 was a diagnostic: an unfiltered S1 scene count at Goa.
- 1 was an availability check: scene-count histograms for all 153 patch footprints. It returned metadata only, with no imagery and no VAL outcomes.

| Patch (state, weak class) | Orbit (scenes) | SAR valid | Joint S1 ∩ S2 valid | dB in range / VH < VV | Gate |
|---|---|---|---|---|---|
| Telangana, positive | 92 (7) | 1.000 | 0.999 | 1.00 / 1.00 | PASS |
| Bihar, positive | 121 (7) | 1.000 | 1.000 | 1.00 / 1.00 | PASS |
| Rajasthan, background | 34 (**2**) | 1.000 | 1.000 | 1.00 / 1.00 | PASS (minimum count) |
| Goa, background | — | — | — | — | **FAIL: NO COVERAGE** |

Every acquired grid exactly matched its optical patch (EPSG, affine, 128 × 128). The Goa footprint has **zero** S1 GRD scenes of any mode or pass in Q1 2019, and only 8 in all of 2019. That is a real acquisition gap, not a filtering artefact.

**Georegistration.** The check covers grid identity only. EE GRD is terrain-corrected, but no independent tie-point check was made.

## Availability for the full run (scene metadata, all 153 patches)

| Split | Patches with ≥ 2 descending scenes in one orbit | Complete groups | Best-orbit scenes (min / median / max) |
|---|---|---|---|
| TRAIN | **108 / 120** (all 12 Goa patches fail) | 36 / 40 | 0 / 7 / 11 |
| VAL | **33 / 33** | 11 / 11 | 7 / 7 / 8 |

Goa provides 4 TRAIN groups with no Q1 2019 SAR. All other states are fully covered. Pixel-level validity still has to be confirmed per patch in the full run.

## Proposed fixed RF ablation protocol (preregister before the full run)

**Support.** All arms use identical common-support patches: 108 TRAIN (Goa groups excluded from **every** arm) and all 33 VAL. Pixels must be valid for both S1 and S2, and unknown or invalid cells are excluded. As a sensitivity check, the optical-only arm is also run on all 120 TRAIN patches.

**Arms.** There are 100 trees, seed 42, and the same 100,000 balanced unique TRAIN pixels, drawn once and shared across arms. No feature selection is done.

| Arm | Features |
|---|---|
| SAR-only | VV, VH, VH − VV |
| Optical-only | B3, B4, B8 |
| Fused | optical + SAR |
| Fused + terrain | fused + SRTM elevation and slope, from 30 m native sampled to 10 m |

**Threshold.** A fixed cutoff of 0.50, the same as Phase 22H RF-A. There is **no** VAL tuning.

**Metrics.** Computed against the weak VAL labels:
- pooled and per-group precision, recall, F1, IoU, FPR and background-only FPR;
- group-bootstrap 95% CIs (11 groups, 10,000 resamples, seed 42);
- paired arm differences with the same group bootstrap.

These are reported as "agreement with weak Maus labels, Odisha VAL". They are not mining accuracy and not Meghalaya results.

**Limitations to state:**
- weak and incomplete negatives;
- VAL is a single state;
- terrain can encode site-level confounds;
- SAR smoothing at 20 m is coarser than optical;
- the Rajasthan-type 2-scene medians are noisy.

## Full-run estimate

- **Requests.** About 141 patches × 2 (URL + download), with SRTM elevation and slope bundled as extra bands, plus about 2 metadata requests. That is **≈ 285 requests**.
- **Data.** About 220 KB per 5-band float32 patch, so **≈ 31 MB**. Encoding int16 dB × 100 would roughly halve that.
- **Compute.** RF fitting takes CPU minutes. No GPU is needed.

## Decision

**GO for the full acquisition, conditional on your approval** of roughly 285 requests and 31 MB, and on the Goa exclusion being preregistered. Pairing quality passed on every covered pilot patch. The only blocker is the documented Goa S1 coverage gap, handled by excluding those groups from every arm. No final models were trained.
