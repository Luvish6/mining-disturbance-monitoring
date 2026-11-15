# Indian Sentinel self-supervised screening feasibility

**NO-GO for fitting on the present cache.** The CPU environment exposes 16 logical processors and PyTorch reports no CUDA. A small masked encoder is computationally feasible. The main constraints are independent site diversity and repeat observations, rather than memory or pixel count.

| Cache | Real 14-band windows | Verified common-valid cells | Design |
| --- | ---: | ---: | --- |
| Phase 6B Meghalaya | 6 × 64 × 64 | 24,576 | Two frozen blocks per split. Two fit blocks would represent one East and one West Jaintia Hills window. Keep test blocks sealed. |
| Gevra and Bhubaneswari Phase 16A | 2 × 32 × 32 | 2,048 | One window per distinct region. Hold both as regional comparison windows. |
| Other Phase 11C discovery sites | 0 additional complete stacks | — | Cached visualization composites lack the exact canonical terrain-inclusive stack. |

All eight complete rasters have one composite per season. Observation counts and source IDs give provenance and coverage. They cannot recreate scene-disjoint composites from the saved summary pixels. Nearby cells do not constitute independent site observations. Two Meghalaya training blocks are too narrow for this regional question, and fitting on the two comparison windows would hide site leakage. No independent repeats are cached to evaluate temporal repeatability.

## Baseline replay

Recomputed Phase 15C scores and masks from the same cached real features and observation counts. Both anomaly rasters and masks matched their saved arrays exactly. On the unchanged terrain, coverage and four-cell component rules, Gevra had 1,021 eligible cells, 32 above threshold and 3 retained polygons. Bhubaneswari had 1,024 eligible cells, 4 above threshold and zero retained polygons. This establishes deterministic replay only. All retained polygons remain REVIEW_REQUIRED and UNKNOWN, with zero operational alerts. No representation-learning result or false-alarm estimate was computed.

## One bounded design

Use a shared two-layer pointwise encoder with an eight-value bottleneck and a small reconstruction head. Feed the valid VV, VH, NDVI and NDTI from one sensor/date composite, with one sensor pair masked and an explicit mask indicator. Predict the held-out co-window sensor channels with Huber loss. Alternate which sensor is masked and use the same shared encoder for both epochs. Fit robust scales and the encoder using before-window data from development blocks only. Use the normalized norm of after-minus-before embeddings as the anomaly score. Treat cross-sensor reconstruction error as a pretext diagnostic. A model might simply encode terrain, water, vegetation or acquisition effects.

Freeze the AOI/site groups, run seed 42, two CPU threads, at most five epochs and a ten-minute cap. Use distinct training and calibration groups. Preserve the Meghalaya block buffers and grouping, and hold Gevra and Bhubaneswari out of fitting and calibration. Fit no backbone weights from MineNetCD and use no scores, anomaly outlines or pseudo-labels as the reconstruction target. Separate source acquisition IDs between replicate composites within each site and season. Keep later imagery and all evaluation windows out of fitting, normalization and threshold selection.

On each identical Phase 15C site window and common eligible mask, compare rank Spearman correlation across independent composite replicas, top-5% overlap (Jaccard), and retained component repeatability at matched review area with the same minimum component size. Use same-season, scene-disjoint comparisons as a background exceedance proxy. They may contain real short-term change, so do not call the exceedance a true false-positive rate. Report per-site values, candidate area, coverage exclusions and embedding/reconstruction stability. Calibrate review cutoffs on calibration groups only; compare untouched sites after the operating points are frozen. Do not report mining precision, recall or F1.

Next: cache a small set of additional disjoint, terrain-diverse development and calibration blocks and two source-disjoint composite builds per season for the held-out comparison windows. Check common support before authorizing one CPU fit.
