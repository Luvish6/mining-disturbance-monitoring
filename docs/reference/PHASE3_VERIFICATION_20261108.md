> Publication copy prepared 11 November 2026. Local paths/session-bearing URL components sanitized; scientific findings unchanged. Original local document preserved and excluded from Git. Historical statuses describe their report context, not necessarily the latest implementation.

# Phase 3 verification and Phase 4 gate — 8 November 2026

## Decision: PARTIAL — Phase 4 blocked

The existing Phase 3 software is implemented and its synthetic regression tests pass. The essential scientific gates do not pass: independently reviewed reference labels, real imagery inputs, actual held-out evaluation, reproducible real model outputs and a usable real georeferenced disturbance layer are absent. No Phase 4 implementation was started, as explicitly required by the task. This is not a finding that the classifier has failed on real observations; its real performance is unknown.

Project: `<PROJECT_ROOT>`.
Existing interpreter: `<PROJECT_PARENT>/.venv/Scripts/python.exe`.
No dependencies installed, no existing results or model artifacts overwritten, no production model trained or retrained. The requested regression suite trains a tiny synthetic model for one epoch as an existing software test; it is not satellite evidence.

## Inspection and evidence

Inspected entry points `main.py`, `phase3.py`, `phase3_data.py`; `README.md`; `docs/PHASE3.md`, `docs/LABELING.md`; `requirements.txt`, `requirements-phase3.txt`; `config/settings.py`, `config/phase2_settings.py`; `src/gee_setup.py`, `src/study_area.py`, `src/change_features.py`, `src/sar_preprocessing.py`, `src/optical_preprocessing.py`; all nine modules under `src/phase3/` (`__init__`, `data`, `labels`, `spatial`, `model`, `evaluate`, `run`, `ee_inputs`, `workflow`); test files `test_settings.py`, `test_phase2.py`, `test_ee_graphs.py`, `test_coverage_evaluation.py`, `test_phase3.py`, `test_phase3_ee_graph.py`, `test_labeling_workflow.py`; and the data/output file inventories. No applicable AGENTS.md was found in the project or checked ancestors.

### Reference samples

`data/labels/draft.geojson` is a FeatureCollection with **zero features**. `outputs/label-readiness-initial.json` also reports blocked readiness and zero polygons/blocks in every partition. This audit directly confirmed the empty source rather than relying only on that earlier report.

| Class | Available reviewed polygons | Usable real supervised pixels |
|---|---:|---:|
| 0: reviewed non-mining/stable | 0 | 0 |
| 1: mining-related disturbance | 0 | 0 |

No prepared real manifest or satellite raster exists under the active project's data/outputs. Thus class imbalance, geographic validity/containment of samples, missing-feature attrition, seasonal label alignment and label independence cannot be evaluated empirically. There are no reference coordinates or duplicates to assess in the empty file. Planning geometries are not labels. Synthetic fixture class counts and accuracy must never be substituted for real sample counts or metrics.

`labels.py` requires unique IDs, reviewed high/medium-confidence binary polygons, source/provenance/reviewer text and a valid interpretation date; rejects invalid WGS84 ranges, invalid geometry and positive-area overlaps. Unknown pixels are 255, never implicit class 0. These metadata checks cannot independently establish mining identity or rule out circular labels. The code does not enforce membership in the two districts, independent evidence dates or the specified seasonal interpretation. `data/planning/study_area.geojson` exists but is not used as a mandatory containment gate.

### Features and imagery

RF order is `dVV,dVH,dNDVI,dNDTI,elevation,slope`, fixed by the 14-band ingestion contract and positional extraction during both training and inference. dVV/dVH are after-minus-before dB; dNDVI/dNDTI are dimensionless index differences; elevation is metres; slope is degrees. No other optical features feed the current RF. The Siamese model uses before/after VV,VH,NDVI,NDTI with validity flags; it does not ingest terrain.

The paired EE graph reuses Phase 2 preprocessing: single pinned SAR orbit/pass, linear-power smoothing and seasonal composites; harmonized Sentinel-2 surface reflectance, cloud-probability join, SCL shadow/cloud exclusions and edge masks; SRTM terrain. Source masks stay separate. Dataset ingestion requires EPSG:32646, north-up square pixels and exact band descriptions; supervision uses a common finite valid mask across all 14 channels, a stricter footprint than just the six RF features. RF input order is consistent in inspected code, but the saved RF metadata could state feature names/hyperparameters more explicitly.

`register_raster` validates 30 m source grids, seasons, checksums and a successful matching coverage report. However, `prepare` can be called directly on a raster tagged `real`, bypassing those provenance checks, and accepts square resolutions other than 30 m. No actual real raster exists to verify units, masks, alignment, data range, dates or export metadata. Phase 2 optical NDTI is not water-only or an NTU measurement; it is not yet a river-analysis product.

### Models, splits and evaluation

`run.py` actually constructs RandomForestClassifier with **100 trees**, max_depth=16, min_samples_leaf=2, class_weight='balanced', random_state=42 by default and n_jobs=1. Other parameters use installed sklearn defaults. RF uses raw features and training-only pixels, capped deterministically at 100,000; it errors if the cap removes a class. The RF is trained only after the Siamese training loop, so there is no standalone RF/ablation runner.

The Siamese U-Net uses a shared encoder, default width 16, train-only temporal statistics, validity flags, Adam lr=0.001, masked weighted BCE, validation early stopping and seed controls. Checkpoint, RF pickle, run metadata and hashes support reload. Only trusted local pickle files should be loaded. Real saved artifacts are absent. The existing synthetic integration test trains, reloads, evaluates and opens a georeferenced output; it does not establish real prediction quality or bit-for-bit reproducibility across environments. No additional real training was justified or attempted.

`spatial.py` assigns metric **5,000 m blocks** by deterministic SHA-256, nominal 60/20/20 train/validation/test. Default block interiors have a 120 m buffer, giving a minimum 240 m separation between adjacent retained cores. Cross-core polygons/patches are excluded. `prepare` writes these partitions; `train` fits only train records, selects the neural checkpoint on validation, and `infer` defaults to test. This is actually wired into training/inference, not just an unused utility. No random pixel train/test split was found. Normalization uses train blocks only, and RF has no fitted preprocessing or feature selection. Synthetic tests verify block disjointness and train-only statistics.

This is one spatial holdout, not five-fold cross-validation. The block size is configurable; 5 km is the default. The buffer does not prove absence of landscape autocorrelation or independent reference interpretation. Manifest checks compare hashes, block IDs, split assignments, window uniqueness and counts, but do not independently reconstruct block membership from stored geotransforms. Real partition sufficiency and class balance remain unverified.

Phase 2 defines SAR-only, optical-only, fused and fused+terrain feature selections. **Phase 3 does not train/evaluate all four ablations.** Its RF always uses all six features and is compared with the Siamese model on common ordered labeled test pixels. No real ablation or evaluation metrics are available.

`evaluate.py` implements per-class precision/recall/F1/IoU/support, confusion matrices, accuracy, positive fraction and per-block evaluation; undefined values are null. Paired block bootstrap is available for RF-versus-Siamese comparisons, with warnings for few blocks. Synthetic scores are software fixtures only and are intentionally not reported here as scientific results.

### Detection outputs

`infer` can write EPSG:32646 GeoTIFF patch outputs with RF/Siamese probabilities, thresholded classes, reference labels, common validity and seasonal NDVI; invalid predictions use nodata=-9999. Predictions extend to common-valid unlabeled pixels within retained labeled patches. It is not full-tile or full-district inference: only patches retained during labeled dataset preparation and selected for the requested partition are processed. No real disturbance raster, Earth Engine prediction asset or real inference artifact is present. A future river workflow must document the incomplete mapped footprint and cannot treat unmapped regions as zero disturbance. Satellite screening cannot establish illegality.

## Issues and disposition

| Severity | Exact affected file(s) | Finding / disposition |
|---|---|---|
| Critical gate | `data/labels/draft.geojson` | Empty; no independent reference evidence. Supervised classification blocked; obtain and review genuine labels. |
| Critical gate | `src/phase3/ee_inputs.py`, `src/phase3/workflow.py`; expected real data/outputs absent | No registered real seasonal tile or current successful district coverage report in active outputs. Validate coverage and acquire bounded genuine input. |
| Critical gate | `src/phase3/run.py`; expected run/evaluation/raster artifacts absent | No real trained model, held-out metrics or usable real disturbance layer. Must follow verified data preparation and training. |
| High | `src/phase3/labels.py`, `src/phase3/workflow.py` | No mandatory study-area containment or structured seasonal/independent-evidence verification; free-text metadata cannot validate truth. Add machine checks plus independent human evidence review. |
| High | `src/phase3/data.py` | Direct prepare path bypasses registration/season provenance enforcement and allows non-30 m square grids. Unify a backward-compatible real-data validation contract before real training. |
| High | `src/phase3/run.py`, `src/phase3/evaluate.py` | Four required sensor ablations missing. Implement train-only models sharing one frozen spatial evaluation set, then report actual metrics. |
| High | `src/phase3/data.py` | Manifest revalidation trusts stored block/transform metadata rather than independently checking geometric block membership. Harden before accepting externally edited manifests. |
| High | `src/phase3/run.py` | Output footprint limited to retained labeled patches in a split. Add or explicitly constrain valid-support inference before computing catchment exposure. |
| Fixed | `src/phase3/data.py`, `tests/test_phase3.py` | Reject NaN/Inf feature values marked valid when validating prepared manifests; checksum alone did not enforce this numerical contract. Added one regression case. |
| Fixed | `src/phase3/data.py`, `tests/test_phase3.py` | Require both classes in validation and test, in addition to train, after actual count reconstruction. Added two regression cases. |
| Medium | `src/phase3/run.py`, `requirements-phase3.txt` | Broad dependency ranges and partial metadata do not reproduce a full environment; preserve versions, explicit RF params and feature schema with real runs. |

The changes preserve APIs, valid dataset behavior and all existing test cases. Datasets without a class in a held-out partition now fail explicitly rather than allowing an uninformative scientific evaluation. Broader provenance and inference redesign is deferred and remains visible above; reference evidence cannot be repaired by inventing labels.

## Automated and Earth Engine verification

Before changes: **72 collected, 72 passed, 0 failed, 0 skipped**, 42.83 s.
After changes: **75 collected, 75 passed, 0 failed, 0 skipped**, 41.62 s. No observed regression.

Command: existing venv Python `-m pytest -q -p no:cacheprovider --basetemp <unique audit directory>`, with PYTHONDONTWRITEBYTECODE=1. Cache writing was disabled to avoid touching old cache/results. Test artifacts are separate synthetic outputs under the chat's visualization workspace, not real experimental results.

Environment observed: Python 3.13.2; earthengine-api 1.7.50; torch 2.15.0+cpu; numpy 2.5.4; rasterio 1.5.2; scikit-learn 1.9.1; pytest 9.2.0.

The initial restricted-network attempt could not resolve oauth2.googleapis.com. Retrying with network access succeeded using the existing credentials/configuration; no reauthentication was needed. Live scalar test returned 2. A second bounded request verified GAUL district names and area and sampled one SRTM point:

- Districts: East Jaintia Hills and West Jaintia Hills.
- Combined area: 3818.324601222792 km² (3818.32 rounded).
- Candidate point [92.35, 25.35] is inside the boundary.
- SRTM elevation at that point: 1141 m, first-value reduction at 30 m, maxPixels=10.

These checks establish current EE access, boundary retrieval and one DEM pixel execution. They do not validate seasonal feature pixels, district imagery coverage, reference labels, model accuracy or river datasets. No full-district imagery processing, Drive export, asset creation or full-district download was submitted. Earlier local smoke harness calls used setDeadline before initialization and failed locally; the corrected live calls above are the substantive results.

## Phase 4 implementation and exact next actions

**Completed Phase 4 components: none.** No river/catchment/rainfall sources were selected or verified, no river samples created, no seasonal river NDTI extracted, no risk weights/results invented, and no dashboard built. Existing S2/SRTM datasets were inspected only as Phase 3 inputs. No Phase 4 files, exports, tables or maps were generated.

Files modified in this audit: `src/phase3/data.py`, `tests/test_phase3.py`.
New audit deliverables: `docs/PHASE3_VERIFICATION_20261108.md`, `outputs/phase3_verification_20261108.json`.

To unblock Phase 4:

1. Collect genuine independently supported positive and hard-negative polygons with evidence/acquisition dates for both defined seasons. Verify district containment and label independence; resolve ambiguous mining interpretations by review.
2. Harden/enforce the real-data provenance and geometric validation contracts above. Run lightweight district coverage diagnostics for a deliberately selected orbit/pass, preserving gates and a new report path.
3. Export/register/audit a bounded genuine 14-band 30 m tile; prepare a frozen manifest. Report per-class polygons, valid pixels, attrition and independent block counts in every split. Obtain more labels/tiles if needed; do not search split seeds for favorable scores.
4. Implement the four RF feature ablations on identical frozen held-out spatial locations; run real training only after input gates pass. Preserve all new artifacts and environment/feature metadata; verify saved-model prediction reproduction.
5. Publish actual held-out metrics and uncertainty with valid-support georeferenced disturbance probabilities/classes. Define an adequate inference footprint before catchment exposure analysis, and reassess the Phase 3 PASS gate.

Only after PASS, finish Phase 4 in the requested order:

1. Verify documented river networks, catchments, elevation, flow direction/accumulation and rainfall sources actually cover Lukha/Myntdu; districts are not catchments.
2. Define reproducible monitoring locations and hydrologically verified upstream/downstream connections. Store coordinates, identifiers and selection evidence.
3. Implement cloud/shadow/water masking and robust per-image S2 NDTI, narrow-river/mixed-pixel controls, denominator tolerance, observation counts and missing-data flags.
4. Summarize November 2023–March 2024 versus November 2024–March 2025 using exclusive ends 2024-04-01 and 2025-04-01; validate rainfall coverage and aggregate seasonal/antecedent rainfall as confounders.
5. Measure verified upstream disturbance exposure using compatible mapped support/dates and drainage connectivity, then transparent exploratory indicators with uncertainty. Missing evidence must remain missing.
6. Add CSV/GeoJSON/raster outputs, maps and quality reports, and all ten requested Phase 4 unit-test categories; validate a small representative area before larger exports and rerun regression tests. NDTI indicates relative spectral turbidity, not NTU, acidity, metals or causal mining pollution.
