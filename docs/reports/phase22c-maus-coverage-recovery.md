# Phase 22C — Maus coverage recovery and weak-label decision

## Phase 22D decisions

| Experiment | Decision | Remaining gate |
|---|---|---|
| Optical-only provisional binary training | **NO-GO** | The two QA patches pass optical coverage, but no eligible binary training or validation manifest exists. Check coverage and conservative weak interiors across additional frozen development groups, and acquire explicit TRAIN negatives. No negative is inferred from the complement of Maus. A separate validation roster with usable labels is required for model selection. |
| Fused provisional binary training | **NO-GO** | Same blockers, plus no Q1 SAR at the TRAIN QA site. Verify at least 70% common optical/SAR/DEM coverage across sufficient other frozen TRAIN groups with both classes. |
| Verified evaluation | **NO-GO** | Acquire independently dated reference images with reviewer-use rights and documented positional suitability, then obtain independent decisions and adjudication on positive and hard-negative interiors. Keep TEST sealed until all selection and checkpoints are frozen. |

Phase 22C authorizes no fitting. The versioned [preregistration amendment](../preregistration-phase22c-v1.md) permits historical Maus TRAIN interiors as weak, unverified positives subject to quality and date-context checks. Candidate masks used on validation can support only separately reported weak-label agreement. Verified metrics require independently reviewed, adjudicated examples. No labels were generated or admitted, including negatives. Indian temporal training remains NO-GO.

## Coverage and cause

The fixed QA sample was the original first TRAIN and first validation window. The SAR query checked dates and footprint intersection before IW, nominal 10 m, dual VV/VH, direction and relative orbit. The absence of intersecting Q1 GEE GRD scenes at the TRAIN site explains its zero descending count. There is no evidence of a local polarization or orbit filter removing its Q1 scenes. This result is specific to the queried collection, dates and geometry.

| Window | Joint-mask S2 scenes / counts per cell | S1 direction and relative orbit | SAR scenes / valid cells | Optical valid cells | Fused + DEM valid cells |
|---|---|---|---|---:|---:|
| TRAIN Q1 | 36 joined / 0–35 | Neither direction available | 0 / 0 | 4,074 / 4,096 | 0 / 4,096 |
| Validation Q1 | 34 joined / 2–31 | Descending 121 | 7 / 4,096 | 4,096 / 4,096 | 4,096 / 4,096 |

A Q4 metadata-only check at the TRAIN site found eight descending dual-polarization IW scenes on relative orbit 136, with no compatible ascending scenes. This establishes later availability and does not establish Q4 usable pixels. Q4 scenes were excluded from the Q1 composite. The 22 other development windows are explicitly unassessed. The validation cache was reused after checking split, scene IDs and its Phase 22B raster hash, with one aligned DEM download. The TRAIN optical-plus-DEM export and validation DEM response totalled 52,688 bytes. Both windows had 4,096 finite DEM cells. Checks confirmed exact grid, ordered bands, affine, CRS, NoData and sensor support counts. Source IDs, UTC acquisition dates, selected orbit metadata, feature configuration and raster hashes are recorded locally. [Earth Engine S1 GRD](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD) · [Earth Engine S2 SR Harmonized](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED) · [SRTM GL1](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003)

## Split integrity and review handoff

The copied split manifest is byte-identical to Phase 22B, SHA-256 `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`. The authenticated Maus geometry recheck found no buffer conflicts across the 355 frozen groups or among the 24 windows and opposing candidate groups. Assignments remain 244 TRAIN, 45 validation, 53 sealed TEST and 13 excluded groups. The original TEST seal matches exactly. The geometry check used source footprints for separation. No TEST images, model targets or metrics were opened.

Ignored local outputs are under `outputs/phase22c_maus/`. The coverage ledger keeps all 24 development windows. The review sheet and locator overlay preserve the same windows and the 72 blank review rows. Two windows carry dated context references to model-input scenes, which cannot serve as independent evidence. The other 22 await input metadata as well as independent references. The sheet records Maus attribution, class criteria and separate independent source/date/rights, reviewer and adjudication fields. All independent evidence fields and verdicts remain empty.

To reproduce the bounded two-window QA in a fresh output directory, run `python -B -m scripts.phase22c_maus` from the repository root. The runner refuses an existing directory to preserve prior outputs. The next acquisition should begin with dated, licensed positive and hard-negative review material in multiple frozen TRAIN and validation groups, paired with an optical preflight of those same windows before requesting additional TIFFs.
