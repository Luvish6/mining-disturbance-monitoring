> Publication copy prepared 11 November 2026. Local paths/session-bearing URL components sanitized; scientific findings unchanged. Original local document preserved and excluded from Git. Historical statuses describe their report context, not necessarily the latest implementation.

# Real-reference admission and RF experiment protocol

Project: `<PROJECT_ROOT>`.
No real reference samples were established by the 8 November 2026 discovery.
The downloaded historical inventory and control points yielded no intersections
with the district planning outline. They must not be substituted for labels.

## Target and evidence

Class 1 means new or expanded mining-related surface disturbance between the
specified before and after seasons. It does not mean mine presence, all bare
soil, all land-cover change, all mining leases or confirmed illegal mining.
Class 0 means independently verified stable/background or non-mining disturbance.
Historical mining with no change is class 0 only after independently verifying
its unchanged state for these windows. Ambiguous areas remain unknown.

Use a two-stage design: independent reference interpretation first, model feature
extraction second. Reviewers must not see change-feature thresholds, model scores
or the final test metrics while assigning reference classes. Include forest,
agriculture, settlements, natural bare ground and independently identified
non-mining disturbances as hard-negative interpretation strata. A land-cover
product or the absence of a known mining record does not establish class 0.

1. Freeze the existing 5 km block layout, seed 42 and buffered cores before
   observing model performance. Collect both classes across several independent
   blocks in each partition, rather than collecting only sites near one mine.
2. Identify candidates from government records, field evidence and dated imagery.
   Classify candidates separately as known location, confirmed seasonal
   disturbance, new disturbance, verified historical unchanged area, or uncertain.
   Only confirmed target-aligned reviewed interiors enter supervised data.
3. Use actual dated independent evidence for both windows. Record acquisition
   dates, source identifiers/URLs, interpretation method, positional accuracy
   and confidence. A proposed lease perimeter is not an observed disturbed mask.
4. Digitize conservative polygon interiors. Separate a single site's evidence
   groups from other partitions; omit ambiguous edge pixels and unresolvable
   subpixel disturbances. Verify district containment using the original GAUL
   geometry, not merely the simplified planning outline. The current automatic
   loader checks WGS84 ranges but does not itself prove district containment.
5. Obtain a second review independent of the first interpretation. Adjudicate
   disagreement; retain reviewed high/medium confidence only. Unknown location
   accuracy must not be replaced by the satellite pixel size.
6. Retain all interpretation strata in a sampling log, including rejections.
   If point subsampling is needed, sort stable polygon IDs, use NumPy seed 42,
   sample without replacement, require at least 60 m between point centers,
   and reject overlaps/duplicates across reference IDs. Do not invent point
   coordinates. The current patch dataset uses polygon pixels; it does not
   claim these dense pixels are independent samples.
7. After rasterization, inspect per-class missing-data exclusions, class pixel
   counts and independent block counts in all partitions. If a class or
   partition is absent, acquire more evidence; do not random-split pixels,
   relax masks or choose a seed based on final test results.

Keep the existing label properties described in LABELING.md. Real dataset
preparation now additionally requires these structured admission fields on
every polygon:

```
synthetic: false
independent_reference: true
target_definition: "new_mining_related_disturbance_2023_2025"
before_evidence_date: actual YYYY-MM-DD in [2023-11-01, 2024-04-01)
after_evidence_date: actual YYYY-MM-DD in [2024-11-01, 2025-04-01)
spatial_accuracy_m: documented finite positional error in [0, 30]
second_reviewer: actual identifier distinct from reviewer
evidence_urls: nonempty list of actual independent evidence URLs
evidence_group_id: reviewed identifier shared by polygons from the same independent evidence group
```

These are a conservative initial admission policy for the 30 m experiment, not
universal scientific thresholds. Metadata checks cannot authenticate evidence
or the truth of a human interpretation. If reliable reference positional error
cannot be established, leave the reference unadmitted and document the blocker.
The property template above contains no labels or fabricated coordinates.

## Real-raster checks

Register the genuine paired export with the existing `phase3_data.py
register-raster` command, preserving the raw download. Use actual provenance,
source and coverage hashes and the verified orbit/pass. Direct `prepare` and
manifest loading now also require structured real raster/label admission, so
a `data_kind=real` tag alone is insufficient. The real grid must be north-up,
30 m EPSG:32646. Masks remain explicit and normalization remains train-only.

Manifest verification now reconstructs each patch's block from its transform,
checks a common source-grid origin and rejects inconsistent positions. Existing
ID, duplicate-window, checksum, class-support and finite-mask checks remain.

## Standalone RF experiments, once admission passes

The commands below are implemented but **were not run on real data**:

```powershell
cd <PROJECT_ROOT>
$py='<PROJECT_PARENT>\.venv\Scripts\python.exe'
& $py -B phase3.py prepare data\paired-v2.tif data\labels\reviewed-v2.geojson data\dataset_v2 --boundary data\original-gaul.geojson --coverage outputs\phase2_report.json
& $py -B -m src.phase3.rf_experiments fit data\dataset_v2\manifest.json outputs\rf_v1
& $py -B -m src.phase3.rf_experiments evaluate data\dataset_v2\manifest.json outputs\rf_v1 outputs\rf_v1_test
& $py -B -m src.phase3.rf_experiments map data\paired-v2.tif outputs\rf_v1 outputs\rf_v1_small_tile.tif --evaluation outputs\rf_v1_test\evaluation.json
```

All output paths must be new. `fit` trains four 100-tree RFs: dVV/dVH,
dNDVI/dNDTI, the four changes, and all six changes/terrain bands. Configuration
remains max_depth=16, min_samples_leaf=2, class_weight=balanced, seed 42,
n_jobs=1. RF uses raw inputs and has no fitted scaling transformation.
All models use exactly the same capped training pixels (default 100,000),
validation pixels and final test pixels from the common 14-channel valid
footprint. The footprint is stricter than a SAR-only coverage experiment;
coverage advantages under cloud must be analyzed separately.

Select the model on validation positive-class F1 only, with fixed threshold
0.5, and evaluate final test once after selection. Save the common IDs,
classwise precision/recall/F1/IoU/support, confusion matrices, supplementary
accuracy, per-block scores and actual fusion-minus-single-sensor differences.
Do not assume fusion improves performance. Keep independent block counts
visible; one spatial holdout is not cross-validation or proof of generalization.

Saved artifacts include feature names/order, configuration, sklearn version,
dataset hash, seeds, artifact hashes and selection policy. Only load trusted
locally produced pickle artifacts. The whole-tile mapper reads bounded windows
up to 4,000,000 pixels, covers valid unlabeled pixels and writes probability,
binary, common-valid and entropy bands with nodata/CRS/resolution. Entropy of
uncalibrated RF scores is not an empirical confidence interval. Real mapping
requires a matching real held-out evaluation receipt. Verify the first small
map in GIS before planning larger regions. District-scale export orchestration,
river processing and the dashboard remain deferred.

## Reproduce source discovery

```powershell
& $py -B -m src.phase3.reference_sources data\planning\study_area.geojson data\reference_discovery_v2
```

This fetches two PANGAEA.942325 GeoPackages, with a 32 MiB per-file cap, records
hashes and citation/license, and subsets original geometries by the planning
outline. All outputs are explicitly historical candidates, not training labels.
The 2019 source is licensed CC-BY-SA-4.0; preserve attribution and share-alike
conditions when redistributing the source or derived reference subsets.
