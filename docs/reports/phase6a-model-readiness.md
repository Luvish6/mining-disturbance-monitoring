# Phase 6A — Scientific model readiness

## Decision

**Ready for bounded real feature acquisition and synthetic software checks. Real supervised training and held-out evaluation remain blocked.** The RF and Siamese U-Net already run end to end on synthetic fixtures. The multi-tile experiment needs an audited feature handoff, a multi-source manifest, and independently admitted references. Phase 3G and Phase 5B verified real observations on bounded extents. The Phase 5B live run did not check district-wide coverage.

## Input contract

The [Phase 2 modules](../../src) and [paired Earth Engine graph](../../src/phase3/ee_inputs.py) produce the following north-up 30 m EPSG:32646 stack. Temporal quantities are seasonal medians. Changes are after minus before.

| Band positions (1-based) | Exact order | Model use |
| --- | --- | --- |
| 1–4 | before_VV, before_VH, before_NDVI, before_NDTI | Before branch |
| 5–8 | after_VV, after_VH, after_NDVI, after_NDTI | After branch |
| 9–12 | dVV, dVH, dNDVI, dNDTI | RF SAR, optical and fused ablations |
| 13–14 | elevation, slope | RF fused-plus-terrain ablation and the paired runner's RF baseline |

VV/VH use IW GRD, one pass and relative orbit, joint source masks and 20 m linear-power focal mean before the median and conversion to dB. Sentinel-2 harmonized SR joins cloud probability on scene index, uses the existing scene, SCL, edge and joint index masks, and applies reflectance scale 1/10000. NDVI is (B8−B4)/(B8+B4). This project's NDTI is (B4−B3)/(B4+B3). Each seasonal sensor composite requires at least two observations by default. Elevation is SRTM in metres and slope is derived at the DEM projection in degrees before clipping.

Each Siamese branch receives four standardized temporal measurements followed by four binary flags in the same channel order. Both dates share per-channel mean and standard deviation fitted from individually valid pixels in **training patches only**. Invalid measurements become standardized zero with flag zero. Supervision and evaluation require a reviewed binary label and valid, finite support in all 14 source bands. Unknown is 255 in the label array. Raster NoData and nonfinite values are excluded. GeoTIFF export uses explicit −9999, and ingestion does no local resampling. Partial and boundary-crossing patches are dropped. A common footprint makes ablations comparable but excludes potential SAR-only coverage benefits.

The saved [Phase 3G visualization](phase3g-visualization.md) is a real 27-band 32 × 32 display product with EPSG:32646 and NoData −9999. Direct inspection found suffix-form temporal names such as VV_before, and no elevation or slope bands. The training contract requires prefix-form names and all 14 bands. Terrain contributes to the viewer's common mask but is absent as individual bands. Use the paired graph for feature acquisition. Check exact affine origin, band order and units, per-band masks, and registered provenance across all exports. A common grid does not establish physical co-registration or resolve terrain and seasonal artifacts.

## Model audit

| Component | Verified behavior | Before real use |
| --- | --- | --- |
| Siamese U-Net | Shared three-level encoder, absolute feature differences at all skip levels, bilinear decoder and one logit per input pixel. Paired N × 8 × H × W inputs yield N × 1 × H × W. Synthetic odd-size 2 × 8 × 63 × 65 probe returned 2 × 1 × 63 × 65 and identical output after swapping dates. | Document temporal symmetry as a limitation for a directional target. Signed RF changes can distinguish the sign of change. Keep the current architecture as the prespecified baseline and interpret comparison accordingly. |
| Loss, training and inference | Masked weighted BCE with logits, training-only class ratio clipped to [1,20], Adam at 0.001, validation-loss scheduling and early stopping. Inference loads the best state with weights_only and CPU mapping, verifies manifest digest and metadata, applies sigmoid and uses the fixed 0.5 threshold. | Record artifact digests and finalized run identity across training and inference. Limit pickle loading to trusted local artifacts. Georeferenced Siamese inference currently covers retained manifest patches, including unlabeled valid pixels inside them. Define a separate bounded inference contract before claiming full-tile coverage. |
| RF | Standalone uses raw features and four 100-tree ablations, max depth 16, minimum leaf 2, balanced class weight, single worker. Same seeded cap of 100,000 training pixels and same validation/test footprints across ablations. Validation positive-class F1 selects an ablation. The paired runner fits a separate six-feature RF. | Declare which RF artifacts constitute the comparison. Join saved common IDs and verify labels, block IDs, order and masks explicitly. Do not present the paired runner's baseline as the selected standalone ablation. |
| Splits | 5 km UTM blocks, 120 m interior buffer, seed 42 and deterministic hash assignment. Preparation excludes boundary-crossing shapes and patches. Reader verifies patch hashes, affine-derived blocks, consistent origin, assigned splits and both classes in every split. | Real admission currently does not enforce the frozen block size, buffer and seed against caller overrides. A valid manifest can still encode alternate values. A multi-tile schema must enforce canonical settings, verify district containment and detect geographic overlap and shared evidence groups across sources. |
| Evaluation | Paired inference gathers RF and Siamese scores on the same mask in one loop and records IDs. Shared metrics include confusion matrix, classwise precision/recall/F1/IoU/support and block resampling of paired F1 differences. Standalone RF saves test IDs, per-block metrics and ablation differences. | Shared evaluation checks array shapes, not independent ID identity. Freeze the comparison and threshold before test access, verify IDs externally or at the API boundary, and report undefined metrics and independent block counts. Validation choices and final test evaluation need separate run receipts. Avoid treating pixels as independent replicates. |

Current data preparation accepts one raster per manifest. Paths and row/column IDs are tile-local, and full validation requires one origin. Hand-concatenating manifests could collide IDs or bypass leakage checks. RF paired training accumulates all eligible training rows before capping, and held-out arrays are materialized in memory. Profile and bound these paths before scaling.

## Reproducibility and resources

Local CPU runtime reported PyTorch 2.15.0+cpu and scikit-learn 1.9.1. The default width-16 network has 119,313 parameters (about 0.46 MiB of float32 weights). Two input branches at batch four, 8 channels and 64 × 64 occupy 1 MiB before activations, gradients, optimizer and loader memory. RF capped raw features at 100,000 × 6 float32 values occupy about 2.29 MiB before preprocessing, copies, tree storage and evaluation buffers. These are array estimates, not peak memory. Existing training uses seeded Python/NumPy/Torch, deterministic PyTorch algorithms, two Torch threads and zero loader workers. CPU smoke coverage exists. CUDA was unavailable locally and the current runner falls back to CPU if CUDA is requested but unavailable. Record requested and effective device, dependency versions, hashes, elapsed time and peak memory for future trials. Check deterministic operation on the actual GPU before relying on it.

Full suite **106 passed** with `python -B -m pytest -q -p no:cacheprovider` and a fresh temp directory. Tests exercise synthetic masked training, checkpoint reload, held-out scoring and GeoTIFF output, four RF ablations, reproducibility, partition tampering and reference-admission rejection. These are software tests.

## Remaining evidence and experiment order

- Admit conservative, independently reviewed interiors for new or expanded mining-related disturbance and independently verified stable/background or non-mining disturbance. Record actual observations in both seasonal windows, source IDs and permissions, geometry and documented positional error ≤30 m. Obtain a second independent review and adjudicate uncertainty. Keep ambiguous cases UNKNOWN. Applications, screening scores and archive coverage alone cannot supply reference classes. [Reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md)
- Collect both classes across several independent blocks in each partition, with verified district containment and evidence groups confined to one partition. Freeze the raster and reference hashes, feature schema, exact common-pixel IDs, selection procedure, exclusions and final test plan. Report class and block support after mask exclusions. Expand admitted evidence if coverage or class support is insufficient.
- Continue bounded Earth Engine feature QA, multi-tile ingestion software, trusted artifact checks and public evidence review without Planet or IBM. Existing Landsat observations and Resourcesat archives can be screened for admissibility. The [Phase 3F public-data pilot](phase3f-public-data.md) established no verified paired reference evidence.
- River analysis remains separate. Leshka had five matched date pairs and 12 connected common 10 m cells against a 25-cell pilot floor. Flow regulation, mixed banks, contributing-area rainfall and synchronous field calibration remain unresolved. Station-cell rainfall supplies coarse context. No degradation or causal estimate was produced. [Phase 4B pilot](phase4b-leshka-spectral-pilot.md)

Proceed with the [bounded tile experiment plan](phase6a-multitile-plan.md).
