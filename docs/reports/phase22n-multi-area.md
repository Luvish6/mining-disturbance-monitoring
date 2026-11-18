# Phase 22N — Guarded multi-area temporal pilot

Preregistration was committed as `37cbb7111edfa51afdfef96db560b834a47ec28f` before cached imagery replay. No imagery was requested. The eligible roster and exact source hashes are frozen in [phase22n-preregistration.json](phase22n-preregistration.json). Results are summarized in [phase22n-summary.json](phase22n-summary.json).

## Full-footprint eligibility

| Proposed AOI | Center WGS84 longitude, latitude | Full rectangle guard | Processing |
|---|---|---|---|
| Original Phase22L development lead east-94-559-c74 | 92.7178365971532, 25.2919334050181 | Inside verified districts and TRAIN core 94:559; 1,210 m to nearest expanded TEST block | Compatible frozen cache replayed |
| Lumshnong development location | 92.36492230074244, 25.16639280941408 | District-contained, but fails complete-footprint 120 m buffered block-core containment | Unmeasured; no relocation |
| User-proposed forest context | 92.8486306, 25.3517647 | Outside complete district containment, intersects protected TEST 96:560 and touches expanded TEST 97:561; fails single development core | Unmeasured; no acquisition |

The protected geometry conservatively uses every canonical TEST 5 km block intersecting the study-area envelope, expanded by 120 m. Assignments use the existing seed-42 partition function, unchanged. The control rectangle overlaps 2,515,200 m² of protected geometry. Rectangle-to-buffer separation is 0 m because it intersects. Its supplied center is inside TEST 96:560's expanded geometry, 350.878 m from its boundary. This is a planar metric eligibility calculation, not a positional-accuracy estimate. Full rectangles, not centers, determine admission. Only one rectangle passed, so there are no selected-AOI overlaps. No alternate or shifted location was used. Lumshnong's location is an application-context lead, not an assertion of active mining.

The proposed control remains **proposed forest-context control, NOT verified mining-free**. User-reported Google Earth selection 2024-04-26 and Esri versions 2024-09-19/2026-05-28 with reported source date 2021-02-23 are contextual observations only. Neither brown patches nor lack of obvious excavation establish a control label. The complete square was not visually verified. These screenshots supplied no measurements.

## Cached real observations and unchanged rule

The source receipt and raster hashes were frozen and rechecked. The export is 64 × 64 cells at 30 m in EPSG:32646, north-up, with exact band order, affine and NoData checks. Before is [2023-11-01,2024-04-01); after is [2024-11-01,2025-04-01). Original Phase22L scene IDs/timestamps remain in the private source receipt. The 52/59 joined assets span 28/29 independent UTC capture days. Scene counts include overlapping granules and are not independent days.

The original seasonal graph is reused without changes: cloud probability <40, scene cloud ≤80%, SCL 4/5, native-edge/required-band masks, NDWI <0, mean green/red/NIR ≥0.04 and at least two accepted observations per season. NDVI decrease ≤−0.30 and BSI increase >+0.10 select 8-connected review components. BSI uses native 20 m B11 on the original 30 m export grid. Terrain slope is context, not a flat-ground filter.

| Processed AOI | Eligible cells / all cells | Coverage | Before/after capture days | Candidate cells | Clusters | ha | Candidate slope ° |
|---|---|---|---|---|---|---|---|
| east-94-559-c74 | 4,096 / 4,096 | 100% | 28 / 29 | 9 | 6 | 0.81 | 7.20–20.75 |

Cell scene-sample counts range 13–38 before and 23–55 after. Existing Phase22L counts reproduce exactly; this is a replay, not a new independent experiment. Both rejected AOIs have unavailable candidate counts, area and coverage, not measured zeros.

## Fixed low-NDVI description

The exploratory before-season NDVI <0.20 cutoff was fixed before replay. Among nine candidate cells, 0/9 (0%) meet it; among all eligible AOI cells, 0/4,096 (0%) meet it. Thus no candidate-versus-background enrichment is observed for this particular low-NDVI descriptor. This does not identify disturbance cause or validate labels. No eligible control AOI exists, so **control fractions and control comparison are unavailable**.

| Cluster | Cells | ha | Before NDVI mean | After NDVI mean | Before BSI mean | After BSI mean | Before NDVI <0.20 |
|---|---|---|---|---|---|---|---|
| C001 | 3 | 0.27 | 0.8230 | 0.4799 | -0.3169 | 0.0872 | 0.0% |
| C002 | 1 | 0.09 | 0.8366 | 0.5183 | -0.3120 | 0.1143 | 0.0% |
| C003 | 1 | 0.09 | 0.5973 | 0.2952 | 0.0260 | 0.1767 | 0.0% |
| C004 | 2 | 0.18 | 0.8712 | 0.5212 | -0.4022 | 0.0658 | 0.0% |
| C005 | 1 | 0.09 | 0.9056 | 0.5690 | -0.4218 | -0.0653 | 0.0% |
| C006 | 1 | 0.09 | 0.6633 | 0.3180 | -0.0347 | 0.2042 | 0.0% |

| Cluster | Cells | ha | Mean NDVI before | Mean NDVI after | Mean BSI before | Mean BSI after | Before NDVI <0.20 |
|---|---|---|---|---|---|---|---|
| C001 | 3 | 0.27 | 0.8230 | 0.4799 | -0.3169 | 0.0872 | 0.0% |
| C002 | 1 | 0.09 | 0.8366 | 0.5183 | -0.3120 | 0.1143 | 0.0% |
| C003 | 1 | 0.09 | 0.5973 | 0.2952 | 0.0260 | 0.1767 | 0.0% |
| C004 | 2 | 0.18 | 0.8712 | 0.5212 | -0.4022 | 0.0658 | 0.0% |
| C005 | 1 | 0.09 | 0.9056 | 0.5690 | -0.4218 | -0.0653 | 0.0% |
| C006 | 1 | 0.09 | 0.6633 | 0.3180 | -0.0347 | 0.2042 | 0.0% |

All detections are **candidate disturbance, UNKNOWN - not validated.** Were a control eligible, its detections would be **candidate in proposed control AOI, UNKNOWN pending review**, never automatic false positives. No significance or mining-causality inference is made.

## Private review products and limitations

`outputs/phase22n_temporal/comparison.png` reuses the common 0–0.30 reflectance RGB rendering and signed NDVI legend; it was visually inspected. `clusters.geojson` preserves cell-outline geometry in WGS84 with per-cluster descriptive statistics. `review.csv` has one row per cluster, coordinates, polygon reference, seasonal acquisition windows and blank reviewer, imagery-date-reviewed, verdict and notes fields. Exact capture timestamps and source provenance remain linked through the original receipt. Permitted future verdicts are excavation / other / uncertain. `product_hashes.json` verifies generated products. Keep these imagery/geodata products local.

Seasonal sampling differs; residual haze, illumination, terrain shadow, registration, forestry, agriculture, construction and erosion remain alternative explanations. The small, coarse components cannot resolve excavations. U-Net remains deferred because native 10 m B3/B4/B8 cannot be recovered from this 30 m stack; no resampling, inference or invented B8 was used. No independent reference labels, training, operational alerts or river conclusions were created.

Reproduce offline with `python -B -m scripts.phase22n_temporal` when the frozen cache is present and the output directory does not already exist. Existing outputs are protected against overwrite. Earth Engine requests and response-body bytes for this task are both zero (caps: 60 and 100 MB). Frozen TEST imagery, labels and predictions were not accessed; geometry alone was used for exclusion.

Verification: seven focused temporal-rule, low-NDVI-denominator and full-footprint guard tests passed. Six valid polygon geometries, six blank reviewer rows, nine candidate cells and all private product hashes were checked. Publication audit passed; no imagery or exact candidate geometry was staged.
