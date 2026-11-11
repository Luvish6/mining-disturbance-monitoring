# Phase 6C — Multi-tile integration and leakage safeguards

## Data contract

The Phase 3 preparation command accepts repeated `--additional-raster` options. Multiple tiles use manifest schema 2. A single registered real source also uses schema 2 so the same admission gates apply. Existing schema 1 synthetic manifests and the original synthetic single-raster command remain supported. Historical schema 1 real manifests can be inspected, but must be rebuilt with original district and coverage evidence before supervised use.

Schema 2 requires north-up float32 GeoTIFFs on the global 30 m EPSG:32646 lattice, exact 14-band order, and explicit NoData −9999. Registered real bands carry dB, dimensionless, metres and degrees as applicable. Source windows may touch at their edges. Positive-area overlap and duplicate sources are rejected even when filenames differ. Source identity is the source SHA-256, patch identity adds tile-local row and column, and pixel identity adds the row-major in-patch index. The manifest records source paths, hashes, dimensions, bounds, transforms, CRS, units and provenance. It also binds local snapshots of references and, for real data, the original district geometry and successful coverage receipt.

Validation reopens the sources and reconstructs the expected patch values, reference rasterization, validity masks, supervised masks, counts and spatial assignments. It compares them with the stored patches and manifest. Rehashing a modified patch alone cannot make it admissible. The mask combines the GDAL validity mask, explicit NoData and finite values. Unknown reference areas stay outside supervision. Source paths are local and must remain accessible for verification.

Real datasets enforce 5 km blocks, 120 m buffered cores, seed 42 and the unchanged block assignment function. Each source extent and admitted reference geometry must be contained in a single original unsimplified GAUL district. Each real reference needs a reviewed `evidence_group_id`. The validator rejects a group or declared site crossing partitions. Group IDs describe genuinely shared independent evidence, and must be assigned consistently during review. Software checks cannot establish the independence of mislabeled groups or authenticate a supplied provenance document.

## Evaluation contract

Both model paths use the same complete-case supervised footprint. The paired runner checks ordered RF and Siamese pixel IDs, labels, source IDs and blocks before scoring. Standalone RF test output carries the same fields and per-patch hashes of validity and supervision masks. The paired inference command can verify the standalone archive with `--rf-evaluation`, including its manifest and archive hashes, before producing evaluation outputs. This check verifies sample parity. The paired runner continues to report its own six-feature RF baseline, and standalone RF ablations retain validation-only model selection.

Fitting and model selection use training and validation partitions. Test evaluation is explicit and requires both classes and at least one independent block in each split. Those checks are engineering minima. A meaningful study needs multiple independently supported blocks per class and partition. Keep the final test set out of scientific model selection and report spatial support alongside any future metrics.

The Siamese U-Net architecture is unchanged. Absolute differences between shared encoder features make the output symmetric under swapping the dates. That limits its ability to distinguish the direction of change.

## Phase 6B structural compatibility

All six saved Phase 6B feature/diagnostic pairs passed read-only checks for source and roster hashes, band order, size, grid, non-overlap, NoData, count and mask consistency and after-minus-before arithmetic. All 24,576 cells met the existing common-support rule. The original source receipts identify terrain units, while the exploratory GeoTIFFs lack per-band unit declarations and supervised registration provenance. No supervised manifest was created from those rasters. See the [acquisition report](phase6b-multitile-acquisition.md).

The local compatibility receipt is under `outputs/phase6c_multitile_integration/phase6b_structural_compatibility.json`. The six source tiles were opened read-only.

## Supervised prerequisites

1. Obtain and retain a successful matching district coverage receipt. Register genuine paired rasters through the existing registration command. Keep the original source exports and original unsimplified GAUL snapshot available.
2. Admit independently dated, second-reviewed positive and negative reference interiors under the [real-reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md). Document positional error ≤30 m and freeze reviewed evidence groups across the unchanged partitions.
3. Verify usable class support across multiple independent blocks in each split after NoData exclusions. Freeze the exact dataset, selection criteria and test comparison before fitting.

Example command once those prerequisites exist. Repeat the additional raster option for each source after the first.

```powershell
python -B phase3.py prepare first.tif reviewed.geojson local_dataset --additional-raster second.tif --boundary original_gaul.geojson --coverage phase2_report.json
```

Verification used synthetic multi-tile fixtures for RF and Siamese training and inference, and read-only real raster checks for Phase 6B compatibility. No real classifier was trained or evaluated.
