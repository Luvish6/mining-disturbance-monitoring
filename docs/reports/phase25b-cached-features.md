# Phase 25B — Cached-only multi-source features and exploratory pseudo-states

2026-11-25. Continued on `phase25-minechange-india` from the verified safeguard commit 3e3f5fb, preserving requested Phase 25A baseline d0b6dd1 and stable tag `pre-minechange-india` at 08604dea. No history reset or branch/tag recreation was necessary. Phase 25B is complete as bounded engineering work; a fully populated twelve-domain dataset and verified mining model are **not** established.

## Safeguards and implementation

The frozen backup manifest fingerprint was verified, then **8,765 essential backup files / 6,058,419,596 bytes** were rehashed successfully. This covered data/results, caches, checkpoints, review packages, delivery files and imagery archives. Only backup bytes were read for this recheck, not original frozen TEST imagery. Disk gates passed. The full 72,005-file backup remains private and unchanged; [rollback instructions](phase25-backup-rollback.md) still apply. The old branch/tag were preserved.

New isolated code:

- `src/phase25/features.py`: bounded projected-grid contract, per-source affine/CRS/shape checks, explicit alignment, per-layer validity and three-state rules. Default rejects resampling. Explicit opt-in uses bilinear for continuous fields and nearest neighbor for classes/counts/masks. Coarse native support remains documented; no new detail is implied.
- `scripts/phase25b_cached.py`: offline-only CLI, immutable new run directory, backup/storage gates, content-hash validation against the backup, metadata-only selection and full spatial guards **before any AOI payload read**. No request/download/train interface exists.
- `config/phase25b_v1.json`: twelve source-domain slots, units/native support/rights/roles, frozen seasons, rule settings, sensitivity variants and uncalibrated status.
- `tests/test_phase25b_cached.py`: nine new synthetic contract tests. Synthetic fixtures are software checks, not scientific evidence.

No historical module, cache, checkpoint, dashboard, river result or reference protocol was modified. NDTI remains in the historical water-observability pipeline; it is not a land-mining label feature.

## Multi-source feasibility and availability

These are complementary **domains**, not twelve redundant optical indices. Official catalog/portal documentation was checked only; no data API calls or payload downloads occurred. Product existence is distinct from a licensed, dated, aligned local cache.

| Domain / output slot | Source, support and dates | Rights / integration verdict | Selected-AOI cache |
|---|---|---|---|
| Vegetation change | S2 SR NDVI, native 10 m, seasonal 2023–24/2024–25, sampled on existing 30 m lattice | Existing Copernicus graph, masks and attribution preserved | AVAILABLE |
| Exposed-ground change | S2 BSI using 10 m visible/NIR and native 20 m SWIR; same seasons | Existing source bands/graph; BSI is spectral context, not mining truth | AVAILABLE |
| SAR change | S1 GRD VH delta, VV corroboration, same seasons; orbit 77, descending, legacy power-domain smoothing then dB median | Copernicus; exact exporter/settings retained, no GRD/RTC interchange | AVAILABLE |
| Slope | [SRTMGL1_003](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003), 30 m, February 2000 terrain, degrees | JPL/USGS policy and source citation; context only, not a flat-slope mining filter | AVAILABLE |
| Elevation | Same SRTM source, metres | Product available, but selected legacy arrays contain slope only; no elevation reconstructed | UNAVAILABLE |
| Land cover | [WorldCover v200](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200), 10 m, 2021, 11 classes | CC BY 4.0. S1/S2-derived model product: historical context, never independent mining truth | UNAVAILABLE |
| Geology | [GSI Bhukosh](https://bhukosh.gsi.gov.in/) | Portal timed out; exact product scale/date/API/rights not authenticated. **REQUIRES PROVIDER CONFIRMATION**; do not guess raster resolution from map scale | UNAVAILABLE |
| Mining context | Existing Maus v2 / independently documented locations, historical footprints | Weak/static context only. Dates, positional suitability and source-specific rights required; cannot become change labels or a target-derived predictor | UNAVAILABLE as aligned layer |
| Roads | [OpenStreetMap](https://www.openstreetmap.org/copyright), vectors with dated history required | ODbL attribution/share-alike assessment. Editing timestamps are not construction dates; do not infer non-mining from no mapped road | UNAVAILABLE |
| Rainfall | [CHIRPS daily](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY), mm/day, 0.05° (~5.6 km), date-matched accumulation required | Public domain/citation. Must not transplant Brahmani station rainfall to these AOIs or imply 30 m independent rainfall measurements | UNAVAILABLE |
| Surface water | [JRC GSW v1.4](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater), Landsat-derived 30 m, 1984–2021 occurrence | Copernicus acknowledgement, EC JRC/Google attribution. Historical occurrence does not prove current water/no-water | UNAVAILABLE |
| Fire history | [MODIS MCD64A1.061](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD64A1), 500 m monthly, burn-date/QA | LP DAAC MODIS use unrestricted with citation. Need exact in-window burn-date support; nondetection is not no fire | UNAVAILABLE |

[Bhuvan](https://bhuvan.nrsc.gov.in/) exposes thematic/infrastructure/hydrology maps and an API link, but no exact dated, redistribution-cleared layer export was authenticated for these AOIs; viewing availability does not authorize extraction. [Bhoonidhi](https://bhoonidhi.nrsc.gov.in/bhoonidhi/home.html) lists open/priced mission products and API access by request. Product resolution, radiometry, dates and rights are order-specific. Existing LISS-IV DN is not calibrated reflectance, and private Planet files are excluded. No portal was logged into, scraped for map tiles or used to order data. Integration is through verified, dated local georeferenced assets with explicit units/masks/rights; no unimplemented provider connector is claimed.

Two additional cached context fields are exported separately: Hansen baseline `treecover2000` (30 m, not a complete land-cover map), and WRI/Google DeepMind 2001–2024 forest-loss drivers (native 1 km, legacy nearest-neighbor sample on the frozen grid). Exact source IDs/hashes are retained in private receipts. Driver classes can suggest agriculture/logging/fire/infrastructure alternatives, but their long-period coarse categories **do not establish causes or dates**. Unknown categories are masked, not converted into evidence of absence. Forest-loss years, hard-commodity probabilities and mining footprints do not determine pseudo-states. These fields never provide independent mining evaluation labels.

**Actual twelve-slot stack: four available, eight unavailable.** Missing layers contain NoData and false per-layer masks, not invented measurements or zero-valued substitutes. Five provider/mission families are represented across core inputs and separate context (S2, S1, SRTM, Hansen, WRI); the source products are not five independent ground-truth sources. Context-only data must not silently become predictive features in a later experiment.

## Selection, alignment and provenance

Selected three TRAIN and one VAL AOIs by SHA-256 ordering of `42:25B:<block_id>` within each frozen split, before opening data and independently of foreground/model outputs. Every 1.92 km rectangle passed the original district containment, 5 km block, 120 m core and expanded TEST exclusion checks; selected rectangles do not overlap. VAL is debugging-only, with no calibration, model selection or independent accuracy computation.

All products are 64 × 64, 30 m north-up EPSG:32646 on the frozen lattice. Legacy NPY caches lack embedded georeferencing: alignment is inherited from their immutable acquisition plan and grid-validated exporter, not a newly measured absolute positional control. Array shape/band order and backup hashes were checked; new GeoTIFF headers, per-layer masks, state counts and output hashes were independently reopened/verified after writing.

Original metadata records S2 acquisition timestamps/counts and S1 scene counts, but omits some exact S1/S2 item IDs and individual follow-up dates. Receipts preserve this **INCOMPLETE scene provenance** explicitly; no scene IDs were invented. This blocks dataset release-quality provenance despite successful cached engineering. Sources/processing versions, file hashes, config hash and software fingerprints are retained privately. The label-input source is shared with the screening features, so evaluating against these masks could measure only pseudo-label agreement.

## Frozen exploratory rules, not calibration

The rule file was written before the first cached replay; SHA-256 `f59a7d08541103f33fb28d8da7815ed13c1e3d1ee41dd3a4b9a9a9a58ac89186` identifies the executed version. It was not fitted to labels, selected using VAL or tuned after results.

- Preserve the 22L quality screen: source cloud/shadow/edge/water/dark masks, minimum two accepted observations per season, common finite optical/slope support; no slope-based mining exclusion.
- Potential disturbance requires delta NDVI ≤−0.30, delta BSI >+0.10, valid SAR with both delta VV and delta VH ≤0 dB, and the same optical change relative to BEFORE in the cached 2025–26 follow-up.
- Potentially stable background requires |delta NDVI| ≤0.10, |delta BSI| ≤0.05 and |delta VV|/|delta VH| ≤1 dB, with valid follow-up similarly close to BEFORE. This is **not** a verified unchanged/non-mining reference.
- All other, missing or conflicting cells are uncertain/ignore. Values: **1 potential disturbance; 0 potentially stable background; 255 uncertain/NoData**. All mining attribution remains UNKNOWN.
- Fixed sensitivity variants change only optical cutoffs: less restrictive −0.25/+0.075, base −0.30/+0.10, more restrictive −0.35/+0.125. Counts are reported descriptively; no best variant was selected.

Calibration is an explicit future TRAIN-only operation; code rejects VAL/TEST calibration and claims of independent evaluation in this contract. Human review/adjudication stays separate and pending. Do not send generated pseudo-masks, threshold rankings or model outputs to independently blinded interpreters. The existing Sentinel-only 30-item reviewer package is unchanged.

Follow-up persistence is **retrospective annotation evidence available after the target interval**, not an earlier model-input channel or an early-warning result. Alternative explanations include seasonal farming, vegetation clearance, roads/construction, fire, erosion, moisture, residual shadow and registration. Coarse context flags are hypotheses; absence/missingness cannot rule them out. No probability, mining precision/recall, illegal-mining claim or river causality is inferred.

## Actual cached results

All AOIs contain 4,096 cells. Common support below means optical+SAR+follow-up quality; optical-only support is separately reported in the [summary](phase25b-summary.json). A zero is measured only where quality permits; missing source layers remain unavailable.

| AOI / split | Common supported cells | Independent S2 BEFORE/AFTER days | Potential disturbance cells / ha | Potentially stable cells | Uncertain cells |
|---|---:|---|---:|---:|---:|
| 88:556 TRAIN | 4,013 | 47 / 56 | 17 / 1.53 | 1,283 | 2,796 |
| 86:561 TRAIN | 4,096 | 51 / 56 | 2 / 0.18 | 776 | 3,318 |
| 89:557 TRAIN | 4,096 | 47 / 56 | 17 / 1.53 | 1,301 | 2,778 |
| 80:559 VAL (debug only) | 4,095 | 24 / 29 | 0 / 0.00 | 1,477 | 2,619 |
| Total | 16,300 | Not pooled as independent days | **36 / 3.24** | **4,837** | **11,511** |

The four rectangles span 14.7456 km²; this is not regional or national coverage. Potential-disturbance counts across less/base/more restrictive variants are **48 / 36 / 28**. VAL retains zero in every variant; this does not establish zero mining activity. Differences reflect rules applied to shared-source observations, not verified accuracy or statistical significance. No ground-truth labels were created.

## Local outputs, checks and next gate

Run once into a new name (never overwrite):

```powershell
$backup = Read-Host 'Verified private backup root'
python -B -m scripts.phase25b_cached --backup $backup --run-id 25b-new-run-id
```

The actual completed run is `outputs/phase25/experiments/25b-v1/`: immutable selection/config receipt, per-AOI 12-band features, per-layer validity, three-state masks, rule evidence, separate context/alternative flags, provenance receipts and summary. An explicit pseudo-state legend and executed-software fingerprints were added during QA without changing rasters. The essential-backup recheck is `outputs/phase25/receipts/25b-backup-verification-v1.json`. These materials remain ignored/private; no raster or dataset release occurred.

**19 focused tests passed**, including nine new grid/affine/NoData/count, state/quality/persistence, metadata selection, TEST-before-payload rejection, context/calibration separation and no-overwrite tests. **Full offline regression: 382 passed in 73.69 s** in a fresh Phase 25 QA directory. Synthetic test fits are software fixtures, not scientific model training. Four actual GeoTIFF grids, masks, band schemas, state counts and hashes passed output verification. Data/weight downloads, Earth Engine requests, new reference labels, research training and operational alerts: **zero**. Only small source-documentation pages were consulted online, not data payloads.

**Blockers / next approval:** eight source families are not locally aligned; GSI/Bhuvan/ISRO export rights/product details need confirmation; exact legacy scene identities remain incomplete; independent human reference admission is pending. Cached-only feature/pseudo-state engineering is complete, but a complete multi-source training/release dataset remains NO-GO. Next approval should cover a specifically budgeted source/provenance recovery plan or Phase 25C specification; no acquisition, environment installation, training, public release or later phase is authorized by this completion. Staged publication/privacy audit passed. Stop after 25B.
