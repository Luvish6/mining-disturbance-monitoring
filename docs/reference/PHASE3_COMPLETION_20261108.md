> Publication copy prepared 11 November 2026. Local paths/session-bearing URL components sanitized; scientific findings unchanged. Original local document preserved and excluded from Git. Historical statuses describe their report context, not necessarily the latest implementation.

# Phase 3 completion attempt — 8 November 2026

## Final status: PARTIAL

The existing project at `<PROJECT_ROOT>` was extended in place. The Downloads path in the new task was obsolete; no replacement was created. Phases 1–2, credentials, configuration and previous results were preserved. The current 75-test baseline was confirmed before edits. No dependencies were added.

## 1. Reference data

Examined government mining/clearance/inspection records for both districts, pollution-board EIA publications, public geospatial portals, a published global inventory, MineNetCD and dated high-resolution interpretation options. See REFERENCE_SOURCES.md for direct primary-source links, dates, licensing/access, spatial utility and rejection reasons.

Actually downloaded PANGAEA.942325 global mining polygons and validation control points: {'global_mining_polygons_v2.gpkg': 44929, 'validation_points_v2.gpkg': 1220}. Source hashes and URLs are in data/reference_discovery_20261108/discovery.json. Both local spatial subsets are empty. They represent 2019 mine footprints/control labels, not 2023–2025 mining change, and were not admitted as ground truth. This result does not establish absence of mines or completeness of the source inventory.

Government records identify candidate locations, but a permit or planned lease perimeter is not a verified seasonal disturbance mask. The documented June 2025 Saryngkham production date is after the comparison window; earlier disturbance remains unknown. Some indexed EIA documents offer coordinates, but complete direct retrieval, positional accuracy, reuse terms and seasonal interpretation were not verified. No geographic coordinates were invented or imported as class labels. Contemporary independently verified positives and non-mining backgrounds remain unavailable.

| Quantity | Actual accepted count |
|---|---:|
| Mining-related new-disturbance reference polygons | 0 |
| Independently reviewed non-mining/stable polygons | 0 |
| Real train / validation / test supervised pixels | 0 / 0 / 0 |
| Real trained RF models | 0 |

REAL_REFERENCE_PROTOCOL.md documents target classes, hard-negative strata, seed 42, deduplication, spatial grouping, provenance, exact seasonal evidence, confidence, positional accuracy and second review. It prohibits automatic background labels and circular labeling from the same feature thresholds. Human verification of district membership and actual evidence remains necessary.

## 2. Implementation

Inspected the actual README, requirements, config/settings.py, config/phase2_settings.py, main.py, phase2.py, phase3.py, phase3_data.py, source preprocessing/change/coverage/evaluation modules, label/workflow/data/model/training modules, tests, data/output inventory and the latest verification report. Reused Phase2Config, ABLATIONS, the six-band definitions, read_manifest, metrics, the existing label loader, spatial partitions and masked patch contract.

Created code:

- src/phase3/reference_sources.py — bounded primary-source downloads, GeoPackage geometry decoding, read-only local subsetting, citation/license/hashes; outputs explicitly not training labels.
- src/phase3/admission.py — structured real-reference and registered-raster provenance checks. Real labels need independent dated evidence within both windows, documented <=30 m positional accuracy and a different second reviewer. Metadata checks do not authenticate human claims.
- src/phase3/rf_experiments.py — standalone four-ablation RF fitting, validation-only model choice, separate final-test evaluation and bounded whole-tile georeferenced mapping.
- tests/test_rf_experiments.py — eleven added synthetic checks, including parametrized admission failures.

Modified **only src/phase3/data.py**: real preparation/loading now requires evidence and registered temporal raster provenance, the agreed 30 m grid, explicit dataset identity, reconstructed geotransform/block consistency and one aligned source origin. Existing synthetic mode and prior working interfaces remain. Backup: .phase3_audit_backups/real_data_completion_20261108/data.py. Previous finite-mask, checksum, class-support and duplicate checks remain.

Added documentation REAL_REFERENCE_PROTOCOL.md, REFERENCE_SOURCES.md, PHASE4_INPUT_CONTRACT.md and this report. The status JSON records exact gates. Downloaded evidence and the new feature-smoke report are additive under their versioned directories; original results were not overwritten.

## 3. Earth Engine operations

Executed the existing Phase 2 command, with network access, over an **unlabeled** point at [92.35,25.35], a 300 m radius and descending relative orbit 77. The live boundary again confirmed approximately 3,818.32 km². Seasonal Sentinel-1/2 preprocessing, SRTM terrain and a bounded 30 m EPSG:32646 reduction succeeded. All six actual features were available: dVV/dVH (after-minus-before dB), dNDVI/dNDTI (index differences), elevation (m), slope (degrees).

Smoke status: `smoke_passed`. Mean common valid fraction: **0.96602142**. This is an infrastructure diagnostic, not labeled feature extraction or evidence of mining. Scene counts and fractional masks are not accuracy measures. No imagery download/export task or model training was submitted to Earth Engine. No new district-scale coverage computation was required; previous audit evidence remains distinct.

## 4. Model evaluation

The real training/validation/test counts are zero, so supervised training was stopped. All real metrics, confusion matrices and four real-ablation results are null/not run; no evidence establishes that sensor fusion improves performance.

The implemented RF configuration preserves **100 trees**, max_depth=16, min_samples_leaf=2, class_weight=balanced, random_state=42 and n_jobs=1. RF uses raw features with no fitted scaling; Siamese train-only normalization is preserved. Training is standalone and does not require neural training first. All four experiments share exactly the same seeded capped training set, validation set and ordered common-valid test pixel IDs. The main comparison deliberately retains the stricter common 14-channel footprint. Separate SAR coverage benefits require another analysis.

Each saved model records its feature schema/order, dataset/configuration/version metadata and checksum. Selection uses validation positive-class F1 at fixed threshold 0.5; test evaluation is a separate command. Both classes must survive in each partition. New spatial checks reconstruct blocks from affine transforms and reject forged block positions. Tests demonstrate deterministic model predictions and artifact reloads in this environment; they do not establish cross-version numerical identity.

The mapper covers valid unlabeled pixels across a bounded whole tile, retaining CRS/30 m grid and nodata. It emits probability, binary, valid mask and entropy. Real mapping requires a matching final held-out evaluation receipt. Entropy of RF scores is not calibrated confidence. District export scheduling and empirical uncertainty calibration remain future work.

## 5. Outputs

Real model artifacts: **none**. Real disturbance rasters/maps: **none**. Real labeled feature tables: **none**. Real metrics/confusion matrices: **none**.

Actual source data: data/reference_discovery_20261108/raw/*.gpkg. Empty discovery subsets and source inventory: data/reference_discovery_20261108/. Real infrastructure diagnostics: outputs/phase3_completion_20261108/feature_smoke/phase2_report.json and phase2.log. Gate report: outputs/phase3_completion_20261108/status.json. Tests create only explicitly synthetic artifacts beneath .phase3_work; they are not scientific deliverables.

## 6. Testing

- Before edits: **75 passed, 0 failed, 0 skipped in 31.43 s**.
- Final suite: **86 passed, 0 failed, 0 skipped in 29.40 s**.
- Unit checks: reference evidence dates/target/independence/accuracy/second-review rejection, provenance, identity, GeoPackage decoding, historical-candidate separation and forged spatial transforms.
- Synthetic integration: four RFs using fixed schemas and common IDs, repeated-seed predictions, reloads, common-set metrics and small GeoTIFF nodata/CRS/resolution.
- Existing regression coverage includes duplicate references, invalid coordinates, source metadata, channel order/masks, training-only statistics and offline EE graph construction.
- Actual external integration: two primary-source downloads, local spatial filtering, configured Earth Engine initialization/boundary and seasonal six-feature smoke reduction.
- Actual scientific validation: **not performed** because valid labels are absent. Real-data admission, real RF fitting, four real experiments and real maps remain unverified. CUDA was not exercised.

## 7. Completion gates and next executable action

Only automated-test completion passes. Essential reference, real labeled-feature, real-training, held-out evaluation, four-ablation, metric, real-map and scientific-reproduction gates remain unmet. Phase 3 is therefore **PARTIAL**, not PASS or evidence of failed real-world classifier performance.

Next action: use the listed candidate records to obtain dated independent imagery/field evidence for both exact seasons; have two reviewers digitize class 0/1 interiors within the frozen spatial cores and verify locations. Record the structured admission properties, register one genuine paired export and prepare a new frozen dataset. If reference coverage cannot support both classes in all partitions, collect more independent areas. Run fit/evaluate/map only after admission and inspect a small map before extending its coverage.

REAL_REFERENCE_PROTOCOL.md contains exact commands for discovery, preparation, standalone RF fitting, separate evaluation and mapping. All require new versioned output paths. PHASE4_INPUT_CONTRACT.md is a deferred interface specification only; no river processing or dashboard was started.
