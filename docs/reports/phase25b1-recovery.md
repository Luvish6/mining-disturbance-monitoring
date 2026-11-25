# Phase 25B.1 — Bounded context and provenance recovery

2026-11-25. Preregistration and acquisition software were committed as `7f9b124` before the single live pilot. Continued from Phase 25B `ce5f675` on `phase25-minechange-india`. No Phase 25C work is authorized or started.

## Safeguards and actual traffic

The essential backup recheck verified 8,765 files / 6,058,419,596 bytes, with no mismatches. The existing full backup, stable tag `pre-minechange-india` at `08604dea`, and historical branch are preserved. Backup is outside the repository/OneDrive but shares the physical system disk; off-device protection remains a limitation. Only backup bytes were inspected for backup verification. Frozen TEST imagery, labels and predictions were not opened.

[Preregistration](phase25b1-preregistration.json) fixes all three existing TRAIN AOIs, source queries, seasons, masks, grid and caps. Full rectangles and road-query halos passed existing district/core/TEST-buffer guards before acquisition. No replacements, VAL acquisition or outcome-based selection occurred. One global acquisition lock, immutable plan/software fingerprints, persistent HTTP ledger and verified cache reuse implement resumability. Authentication, discovery, metadata, download-URL RPCs, TIFF downloads and OSM attempts all use the metered transport; automatic transport retries and redirects are disabled. An interrupted pending attempt retains its conservative byte reservation. Completion releases the lock.

**Completed: 14 HTTP attempts, 1,069,012 response-body bytes, zero pending attempts**, against 60 requests / 100,000,000 body bytes. Three of these were unsuccessful OSM requests (HTTP 406, 156 bytes each); they are included. No second pilot, fallback endpoint or replacement query was attempted. The ledger counts response bodies, not HTTP headers/TLS overhead, as specified by this task.

Ledger SHA-256: `eda798fc68f2dcd7c5263c74675463c70c442e330ac4bb21d663ee54ee0f660d`.
Current source-query receipt SHA-256: `219f119d8559218372945d8ac3224a2f33ab6f5879ed4d3ec6cac4cd6fcc0d3d`.

## Recovered layers and coverage

Every output is 64 × 64 cells on the unchanged 30 m north-up EPSG:32646 grid. Three AOIs cover 11.0592 km²; cells are not independent samples. Downloaded grids, affine transforms, dimensions, ordered graph bands and written GeoTIFF headers/hashes passed checks. Nearest-neighbor sampling preserves native context values; it does not create 30 m information from coarse sources.

| TRAIN AOI | SRTM / WorldCover / CHIRPS supported cells, each | JRC supported cells | MODIS fully supported cells | Roads supported cells |
|---|---:|---:|---:|---:|
| 86:561 | 4,096 / 4,096 / 4,096 | 0 | 0 | 0 (unavailable) |
| 88:556 | 4,096 / 4,096 / 4,096 | 110 (2.69%) | 0 | 0 (unavailable) |
| 89:557 | 4,096 / 4,096 / 4,096 | 0 | 0 | 0 (unavailable) |

- SRTM elevation: approximately 30 m, February 2000 acquisition context, not current excavation topography. Historical slope stays unchanged.
- ESA WorldCover v200: categorical 10 m **2021** land cover; static context, not 2023–25 reference truth. Valid class codes only.
- CHIRPS: 0.05° (approximately 5.6 km), daily seasonal totals; all 152 BEFORE and 151 AFTER dates are present at every sampled cell. New rainfall context is AFTER minus BEFORE seasonal total in mm. Unequal season lengths and coarse support remain explicit; station-cell context is not verified catchment rainfall.
- JRC Global Surface Water v1.4: 30 m occurrence from **1984–2021**. Missing occurrence cells remain missing, never zero water or verified dry land. It is not a replacement for the frozen contemporaneous water mask.
- MODIS MCD64A1 v061: nominal 500 m monthly burned-area product. Five monthly assets exist per season, but no AOI cell passes all five months in both seasons under the preregistered land/valid/complete-mapping/special-condition gates. Fire history remains **NO_VALID_SUPPORT**, not no fire. No quality threshold was relaxed.
- OSM: deterministic historical 2025-03-31 Overpass road queries, bounded 1 km halo and maximum 1,000 ways. All three returned HTTP 406. No road distances were fabricated; the reproducible method is implemented but road acquisition is unavailable. Mapping presence/history would not establish construction date or completeness.

Three newly populated families raise the available-domain count from four to seven everywhere; partial JRC support gives eight in 88:556. Geology, mining context and roads remain unavailable; fire is unsupported. These are context stacks, not reference datasets.

## Exact scene identity: recovery versus certification

Local reviewer-chip receipts first yielded **332 S2 identity associations** across site/season records, covering smaller overlapping chips rather than complete AOI composites. They are retained privately as partial candidate provenance, not substituted into the legacy exporter receipt.

The single current query then recovered **24 unique S1 IDs and 214 unique S2 IDs**, with exact acquisition timestamps, plus seasonal CHIRPS/MODIS asset IDs and native projections. Duplicate associations between AOIs are not independent acquisitions.

| AOI | BEFORE S1 / S2 items | AFTER S1 / S2 items |
|---|---:|---:|
| 86:561 | 13 / 52 | 11 / 58 |
| 88:556 | 13 / 47 | 11 / 57 |
| 89:557 | 13 / 47 | 11 / 57 |

All six current S2 timestamp multisets match legacy metadata, and all six S1 counts match. This corroborates the reconstructed query, but **does not retrospectively certify original S1 identities or original composite membership**. Exact follow-up source identities also remain incomplete. The old caches and their provenance were not rewritten.

## Rights, preservation and local artifacts

Official source documentation: [SRTM](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003), [WorldCover](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200), [CHIRPS](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY), [JRC](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater), [MODIS](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD64A1), [OSM copyright](https://www.openstreetmap.org/copyright), [Overpass historical queries](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL).

WorldCover requires CC-BY-4.0 attribution; CHIRPS is public domain with citation; JRC requires EC JRC/Google attribution and applicable Copernicus terms; NASA/USGS SRTM and unrestricted LP DAAC MODIS products require appropriate source citation. OSM ODbL attribution and database share-alike obligations must be assessed before any future distribution. No raster/geodata redistribution is authorized here. GSI geology/export access and exact product rights remain unresolved; Bhuvan display access is not an extraction grant; Bhoonidhi products/orders are permission-specific. No scraping, private orders, restricted imagery or substitute geology was used.

Private root: `outputs/phase25/datasets/25b1-v1/`. It contains local source recovery, current query receipt, HTTP ledger/session fingerprints and three per-AOI context downloads plus `integrated/{features.tif,validity.tif,context_diagnostics.tif,receipt.json}`. All payloads remain ignored. Essential backup receipt: `outputs/phase25/receipts/25b1-backup-verification-v1.json`.

All four original Phase25B pseudo-state hashes were rechecked unchanged. Original results remain 36 potential-disturbance cells, 4,837 potentially stable and 11,511 uncertain cells. New context was **not** used to rerun rules, recalibrate cutoffs or alter human review. Labels admitted: zero; training: none; mining attribution UNKNOWN; operational alerts zero. No dashboard, river, checkpoint or frozen experiment changed.

## Validation and next gate

Seven new focused tests cover request/byte limits, interrupted reservation, oversized/unknown streams, secret-free ledger, endpoint allowlist, altered receipts, missing OSM support and offline context graphs. Together with nine Phase25B tests, 16 focused tests passed. Full offline regression: **389 passed in 60.03 seconds**, using a fresh isolated Phase25 QA directory. Software fixtures are not research training or synthetic evidence substitution.

Remaining blockers: original-cache/follow-up identity certification; unsupported fire and sparse historical water coverage; unavailable roads/geology/mining context; coarse and temporally mismatched context; independent human reference admission. A future approved task may address these exact gaps or specify Phase25C. No training, public dataset release, further acquisition or Phase25C is authorized by this completion.

Staged publication/privacy audit passed; only source, tests, preregistration and sanitized documentation are included. No local source receipts, imagery, derivatives, credentials or datasets are staged.
