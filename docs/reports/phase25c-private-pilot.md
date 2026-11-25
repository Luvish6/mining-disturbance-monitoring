# Phase 25C — MineChange-India private pilot dataset

2026-11-25. Built offline from `5b360da` on `phase25-minechange-india`. This is a versioned private engineering pilot, not a public dataset or admitted Indian mining-reference dataset. [Dataset card](phase25c-dataset-card.md); [sanitized statistics](phase25c-summary.json).

## Safety and selection

The existing backup inventory fingerprint, verification status and storage gates passed. Sixteen selected historical cache/metadata files and their backup copies were SHA-256 checked; the previously verified full backup was not recopied. The stable tag and original branch remain preserved. The backup shares the system physical disk, so off-device protection remains advisable.

All four unchanged Phase25B parent AOIs passed the existing original-district, seed42 5km block, 120m buffered-core and expanded TEST exclusion guards **before payload reads**. Only development TRAIN/VAL data were opened. The whole original roster and frozen config were verified. Raw acquisition-plan/backup identities remain byte-identical; Git content comparison accounts only for Windows CRLF versus repository LF. No TEST payload, new site selection, acquisition or fitting occurred.

Each 64×64 parent is partitioned into four exhaustive, non-overlapping **32×32 crops**, 960×960m at 30m in EPSG:32646. Entire crop footprints inherit parent containment and guard eligibility; patch-center assignment is not used. IDs include the block and original row/column offsets. All 16,384 pixel IDs are unique. Adjacent crops within a block are dependent, not new independent sites. Zero overlap and zero cross-split buffer violations were found; original group assignments remain fixed.

## Actual counts

| Partition | Patches | Independent spatial blocks | Cells | Potential disturbance | Potentially stable background | Uncertain/ignore |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 12 | 3 | 12,288 | 36 | 3,360 | 8,892 |
| VAL (debug only) | 4 | 1 | 4,096 | 0 | 1,477 | 2,619 |
| Total | **16** | **4** | **16,384** | **36** | **4,837** | **11,511** |

Five TRAIN patches contain potential-disturbance cells, spanning all three TRAIN blocks. All 16 patches contain potentially stable cells. VAL contains **no potential-disturbance cells**. These are frozen pseudo-state counts, not mining class prevalence or verified negatives. Total geographic area is 14.7456km²; potential disturbance remains 3.24ha. Subdivision creates no additional source observations or labels.

## Feature and mask contract

`minechange-india-private/1`, version `25c-v1`, has **29 ordered feature slots**:

- BEFORE and AFTER, each: VV, VH, B2, B3, B4, NDVI, BSI, NDWI (16 bands).
- After-minus-before dVV, dVH, dNDVI, dBSI (4 bands).
- Slope, elevation, land cover, rainfall, surface-water occurrence, fire history, roads, geology and mining context (9 slots).

SAR is dB with inherited descending relative-orbit77 processing; visible optical is surface reflectance, indices unitless. Cached B8/SWIR raw bands are **not available** and are not reconstructed from indices. No NDTI is produced. Counts are separate QA-only bands: two optical, two SAR and retrospective follow-up optical counts. Follow-up values do not enter model features. No normalization was fitted; native units remain explicit. This 29-slot contract is not the existing registered 14-band model input, and is not automatically accepted by historical runners.

| Context or signal | TRAIN valid cells | VAL valid cells | Limitation |
|---|---:|---:|---|
| dNDVI | 12,219 | 4,096 | Existing cloud/land/count screening; residual illumination uncertainty |
| dVV | 12,288 | 4,096 | SAR acquisition/processing limitations retained |
| Slope | 12,288 | 4,096 | Historical SRTM terrain context |
| Elevation | 12,288 | 0 | No Phase25B.1 VAL acquisition; explicitly missing |
| WorldCover | 12,288 | 0 | 2021 categorical/model-derived context, native10m |
| CHIRPS | 12,288 | 0 | 0.05° approximately5.6km; repeated coarse values are not independent30m rain |
| JRC occurrence | 110 | 0 | 1984–2021 context, sparse valid support; missing is not no water |
| Fire / roads / geology / mining context | 0 each | 0 each | Explicitly unavailable/unsupported |

Every feature has a per-band validity mask; missing values are -9999 in GeoTIFF, NaN on loading and blank CSV fields. Binary pseudo masks separately represent states0/1/255. **None is verified mining ground truth.** Unknown is never mapped to background. Frozen NDVI/BSI/SAR/persistence rules were not changed or recalculated; original pseudo rasters were cropped losslessly. Context never changes pseudo states.

## Provenance, rights and deliverables

The private root is `outputs/phase25/datasets/25c-v1/`:

- `schema.json`, `manifest.json`/SHA256, `summary.json`;
- 16 patch folders, each containing georeferenced features, validity, counts, pseudo states, three binary pseudo masks, feature CSV and hash receipt;
- four parent provenance receipts and four private RGB/NDVI-change/pseudo-state QA examples.

Manifest SHA256: `540b2479e062877ac41090dfa7ed04d4deb90e7422f3a8b3583b333766461e08`.
There are 122 hash-bound artifacts, 52 rechecked unchanged source files and 16,384 verified CSV rows. Private payload size including manifest is **10,977,371 bytes**. Build: **8.50s wall / 6.52s process CPU** before final integrity replay; independent complete raster/CSV/source verification: **3.22s**. Peak RAM was not instrumented. Requests/downloads/training runs: **zero**.

`src/phase25/dataset.py` loads and checks schema, hashes, bands, masks, arithmetic, canonical seed42 assignments and spatial IDs. `read_patch(..., allow_pseudo=True)` is explicit opt-in; default returns no pseudo label, and the verified-reference interface always rejects this dataset. `scripts/phase25c_dataset.py` is a crop-only builder that refuses an existing output directory. Build fingerprints and expanded quality statistics are private under `outputs/phase25/receipts/25c-build-software.json` and `outputs/phase25/qa/25c-v1-integrity/`.

Legacy source identities and follow-up exact item dates remain **INCOMPLETE**. Phase25B.1 recovered 24 unique S1 and214 S2 IDs for current filtered queries, matching legacy counts/timestamps, but did not certify original cache membership. Private receipts preserve this distinction. No scene identity, positional accuracy, independent review or permission is invented.

Source rights and citations follow [Phase25B.1](phase25b1-recovery.md): Copernicus S1/S2 acknowledgement, NASA/USGS/JPL SRTM attribution, WorldCover CC-BY4.0, public-domain CHIRPS citation and JRC/Copernicus ECJRC/Google acknowledgement. Historical and coarse support remain explicit. No Planet/LISS-IV pixels, OSM payload, licensed private imagery or original third-party geodata are published. GSI/Bhuvan/Bhoonidhi product rights/access remain unresolved; unavailable layers are not scraped or substituted. Public redistribution is **NO-GO**, pending source-membership certification, source-specific redistribution/attribution review, spatial/privacy review and independent label admission. Public code/docs do not release the dataset.

## QA and next gate

26 focused tests passed, including ten new dataset tests covering crop coverage, duplicate/overlap rejection, frozen splits, pixel offsets, NoData/validity, tampering, band/affine/change arithmetic, explicit pseudo access and refusal of reference promotion. All actual patches and CSV values passed replay. A private example was visually checked for honest dates, legend, geographic axes and missing areas; this is rendering QA, not mining interpretation. Full offline regression: **399 passed in 54.34s** using a fresh Phase25 QA directory. Staged publication/privacy audit passed; only code, tests and sanitized aggregate documentation are staged. A final loading-time integrity review also added an assertion that every required raster appears in the hash inventory.

**Private engineering pilot GO. Verified Indian supervised training, independent performance evaluation and public dataset release remain NO-GO.** The existing30-item human review, historical results/checkpoints, river analysis, pseudo thresholds and all four source pseudo-state hashes are preserved. Operational alerts remain zero and attribution UNKNOWN. The main next evidence gate is independently dated reference imagery/positional evidence and two-reviewer adjudication for both classes across multiple spatial blocks. VAL's one block, zero pseudo-disturbance support and missing context prevent a fair multi-source evaluation. No acquisition, training or Phase25D work is authorized. Stop after25C.
