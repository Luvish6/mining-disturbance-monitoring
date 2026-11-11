# Phase 6A — Bounded multi-location Earth Engine experiment plan

## Scope and proposed tile roster

Use six 64 × 64 tiles at 30 m, each 1.92 km square, spanning two districts and three existing partitions. These are planned slots. Exact extents and coverage are pending the geometry and metadata preflight. The Phase 3G tile remains a separate positive software control for the download and QA path.

| District | Frozen split | Proposed emphasis | Selection rationale |
| --- | --- | --- | --- |
| East Jaintia Hills | Train | Higher slope | Inspect radar and terrain support in steep terrain. |
| East Jaintia Hills | Validation | Higher baseline NDVI | Inspect optical support in relatively vegetated terrain. |
| East Jaintia Hills | Test | Lower paired optical observation count | Exercise missingness and acquisition imbalance. |
| West Jaintia Hills | Train | Lower slope | Contrast terrain support with the East train slot. |
| West Jaintia Hills | Validation | Lower baseline NDVI | Include less vegetated conditions. Baseline NDVI is a screening descriptor. |
| West Jaintia Hills | Test | Higher paired optical observation count | Include a comparatively well-observed setting. |

1. Use the original GAUL 2025 district polygons from the existing study-area module. Enumerate existing 5 km EPSG:32646 blocks and assign partitions with the unchanged seed-42 function. For each block, snap a 64 × 64 tile centered near the block centroid to the global 30 m lattice, with a fixed tie break toward the lower coordinate. Keep only tiles fully contained in one original district and the buffered block interior. Record rejected extents and reasons locally. Keep separate blocks for every selected tile.
2. Rank eligible blocks in each district/split by SHA-256 of a fixed plan string and block ID. Screen the first three per slot, up to 18 candidates overall. In one bounded metadata preflight, check orbit 77 descending availability in both windows and compute coarse aligned summaries of median SRTM slope, before NDVI, and the lower of the two seasonal median optical observation counts. Use a 120 m diagnostic grid and record sampling and denominator settings. Choose the documented high or low relative within-slot rank for the stated criterion, with hash order as tie break. Missing strata stay unfilled with an explanation. Keep lower-quality supported cases for QA. Freeze IDs, extents, screening metrics and rationale before generating change maps. No selection uses change magnitude or model scores.
3. Reuse the Phase 2 configuration and the windows [2023-11-01, 2024-04-01) and [2024-11-01, 2025-04-01). Verify the saved coverage report matches the settings before the existing supervised export/registration path. If it is absent or fails, report that gate and keep any bounded diagnostics explicitly exploratory. Use the [Phase 3G bounded retrieval pattern](phase3g-visualization.md) for exploratory feature QA with no batch export. Start with one selected tile. Proceed serially to the other five only after the first raster and receipt pass structural QA. Log empty collections, failed requests and exclusions.

## Outputs and verification

- Local frozen tile inventory with grid bounds and affine, district, block, split, selection rationale, diagnostic support and input geometry source. Include the reviewed rejected candidate log. Keep reviewer evidence packets separate from selection rationale and partition assignments.
- Per tile, one exact 14-band float32 model-input stack and an aligned diagnostic raster with four observation counts, four seasonal validity masks and one common-valid mask. Keep raw downloads and derived copies separate. Record archive/collection IDs, scene IDs and timestamps, source scales, pass/orbit, masks, reduction settings, export ID and content hashes.
- Verify CRS, global lattice, bounds, district containment, buffered blocks, shape, descriptions and NoData round-trip. Compare independently read masks with counts ≥2 and with the intersection of all 14 bands. Check after-minus-before values on shared support, finite data, terrain units and image alignment by stable-feature inspection. Summarize valid and excluded cells against explicit tile denominators. A structurally sound low-support tile is informative for feasibility.
- Generate exploratory continuous change views with validity and observation counts. Store separately from reviewed reference evidence, and do not give reviewers screening ranks or feature maps. No class labels, classifier outputs or performance statistics belong in this run.

## Cost estimate and stop conditions

Six tiles total 24,576 grid cells, about 22.12 km². At 23 float32 bands the uncompressed pixel payload is 2,260,992 bytes (2.16 MiB) across all tiles, approximately 0.36 MiB per tile. An 18-tile, 120 m screening grid samples at most 4,608 coarse cell centers if each tile is fully evaluated. These are output/reduction sizes. Native-resolution scene filtering, smoothing, cloud joining and compositing can read substantially more pixels. Record source scene counts, time and download bytes from the first tile and revise the estimate before expanding. Reserve 100 MiB locally for downloads, copies, receipts and QA views. No Drive or asset tasks and no district-wide export are part of this experiment. Stop on a grid or provenance mismatch, repeated resource failure or exceeded budget. Keep failed tiles in the log.

## Next implementation task and acceptance criteria

Implement a bounded preflight and retrieval command using existing preprocessing and spatial functions. The default emits a local proposed roster without exports. Require an explicit one-tile execution path and cap the final run at six tiles. Accept when the same inputs reproduce the roster, containment and block tests reject invalid geometry, all selected extents align to the common lattice, a real first tile passes the above raster checks, and failures produce explicit receipts without modifying existing files. Keep this output exploratory.

Afterward, implement multi-source manifest ingestion as a separate supervised prerequisite. Acceptance requires immutable source receipts and patch digests, globally unique pixel IDs, rejection of overlapping windows and cross-partition evidence groups, canonical split settings in real mode, and exact RF/Siamese test ID matching on synthetic multi-tile fixtures. Real fitting remains gated on independent reference admission.
