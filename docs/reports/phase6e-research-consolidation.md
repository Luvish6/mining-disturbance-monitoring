# Phase 6E — Research results and scientific completion assessment

**The project has demonstrated a reproducible satellite feature and observation-quality pipeline. Validated mining classification, early-warning performance, fusion benefit and downstream impact assessment remain open.** The evidence below comes from saved observations and receipts. The dates are seasonal windows, and land composites represent medians of qualifying observations within those windows.

## Real satellite observations

Before is 1 November 2023 through 31 March 2024. After is 1 November 2024 through 31 March 2025. Both exclude the subsequent 1 April. Phase 1 verified the two original GAUL 2025 districts and their combined area of **3,818.32 km²**.

| Scope | Before | After | Meaning |
| --- | --- | --- | --- |
| Phase 1 Sentinel-1 GRD | 52 scenes | 47 scenes | Raw inventory over the district geometry |
| Phase 1 Sentinel-2 harmonized SR | 178 scenes | 186 scenes | Raw optical inventory |
| Phase 1 Sentinel-2 cloud probability | 209 scenes | 215 scenes | Raw cloud-probability inventory |
| Phase 2 district Sentinel-1 | 26 scenes | 23 scenes | Descending IW VV/VH, relative orbit 77 |
| Phase 2 district Sentinel-2 | 144 joined scenes | 174 joined scenes | SR and cloud-probability inputs matched by scene index |
| Phase 3G demonstration tile | 13 SAR and 52 joined optical scenes | 11 SAR and 58 joined optical scenes | Source lists for one 960 m tile |

The raw inventory and filtered lists have different selection rules. The same source scene can cover several tiles. Exact scene IDs and UTC acquisition times are retained in the existing receipts and consolidated in the local source table. Sentinel-1 seasonal counts are per cell after source-mask screening. Sentinel-2 uses harmonized surface reflectance scaled by 1/10000, matched cloud probability below 40, scene cloud at most 80%, SCL 4/5/6, edge and joint index masks. The existing default requires at least two valid observations per sensor-season. SAR smoothing uses a 20 m radius in linear power before the seasonal median and dB conversion.

| District | Coarse reducer area (km²) | SAR support before / after | Optical support before / after | Common support |
| --- | ---: | --- | --- | ---: |
| East Jaintia Hills | 2,012.16 | 99.906% / 99.900% | 99.950% / 99.963% | 99.938% |
| West Jaintia Hills | 1,798.22 | 99.900% / 99.895% | 100% / 100% | 100% |

The existing 500 m district coverage gate passed with the original 90% seasonal SAR and 70% common thresholds. These are coarse area-weighted diagnostic values. The separate fixed-grid binary-mask check reproduced both common fractions and returned 100% seasonal SAR support at its checked grid. In the original reducer, West's reported common fraction exceeds its separately reduced SAR fractions. Both receipts are retained, and the gate decision agrees under both checks. Neither establishes district-wide interpretability at 30 m. [Phase 6D coverage report](phase6d-reference-readiness.md)

| Bounded product | Footprint | Common valid cells | Optical count range before / after |
| --- | --- | ---: | --- |
| Phase 3G viewer | One 960 m square, 32 × 32 | 1,024 / 1,024 | 19–36 / 25–44 |
| Phase 6B East train | 1.92 km square, 64 × 64 | 4,096 / 4,096 | 4–38 / 6–52 |
| Phase 6B East validation | 1.92 km square, 64 × 64 | 4,096 / 4,096 | 5–46 / 6–47 |
| Phase 6B East test | 1.92 km square, 64 × 64 | 4,096 / 4,096 | 27–42 / 33–51 |
| Phase 6B West train | 1.92 km square, 64 × 64 | 4,096 / 4,096 | 4–19 / 2–23 |
| Phase 6B West validation | 1.92 km square, 64 × 64 | 4,096 / 4,096 | 12–37 / 22–49 |
| Phase 6B West test | 1.92 km square, 64 × 64 | 4,096 / 4,096 | 3–42 / 7–46 |

The Phase 6B sample covers approximately 22.12 km². All 24,576 sampled cells passed the complete-case preprocessing mask. Both bounded products have 13 before and 11 after valid SAR observations per cell. The six Phase 6B rasters passed grid, band, mask, NoData and change-arithmetic checks, with a limited relative VV texture check. The tiles were selected for terrain, baseline vegetation and observation support, so their results do not estimate a district distribution. The Phase 3G 27-band viewer raster has 23 display layers and a separate schema. The Phase 6B 14-band feature rasters remain exploratory and unregistered for supervision. [Phase 3G viewer](phase3g-visualization.md) · [Phase 6B acquisition](phase6b-multitile-acquisition.md)

| Feature | Definition and unit | Source and grid |
| --- | --- | --- |
| VV, VH | Sentinel-1 co- and cross-polarized seasonal backscatter, dB | IW GRD, 10 m nominal source spacing |
| NDVI | (B8 − B4)/(B8 + B4), unitless | Sentinel-2 B8 NIR and B4 red, native 10 m |
| NDTI | (B4 − B3)/(B4 + B3), unitless | Sentinel-2 B4 red and B3 green, native 10 m |
| dVV, dVH, dNDVI, dNDTI | After minus before in each feature's units | Seasonal medians, common analysis lattice |
| Elevation, slope | SRTM elevation in metres, slope in degrees derived at DEM projection | SRTM nominal 30 m |
| Support | Observation counts, seasonal masks and all-feature intersection | Derived diagnostics on 30 m EPSG:32646. Feature NoData is −9999. |

The 14-band order is before VV/VH/NDVI/NDTI, after VV/VH/NDVI/NDTI, four signed differences, elevation and slope. A valid cell can still be influenced by vegetation, moisture, terrain, illumination, mixed cover, acquisition imbalance or residual cloud/shadow. Continuous change can guide inspection. No reference class, disturbance attribution or calibrated probability follows from these patterns.

## Model software and independent reference status

| Component | Software evidence | Real result |
| --- | --- | --- |
| Random Forest | Seeded 100-tree SAR, optical, fused and fused-plus-terrain ablations on one common supervised footprint. Model selection uses validation only. | No real fit, held-out scores or validated fusion benefit. |
| Siamese U-Net | Shared temporal encoder, standardized paired inputs with validity flags, masked weighted BCE and validation-based checkpointing. Tested on synthetic fixtures. Absolute feature differences make predictions invariant to swapping the two dates, limiting direction discrimination. | No real fit or empirical model comparison. |
| Multi-source ingestion and evaluation | Schema 2 reconstructs source patches and masks, rejects overlap and cross-partition evidence groups, and checks ordered RF/Siamese test IDs, labels, blocks, tiles and mask agreement. | The six exploratory rasters passed structural inspection. Supervised raster registration and reference admission remain pending. |

The [model audit](phase6a-model-readiness.md) and [integration report](phase6c-multitile-integration.md) document the exact contracts. Synthetic tests establish software behavior. Dense pixels within one block do not provide independent replication.

All **27 discovery leads are UNKNOWN**, with nine leads in three blocks per frozen partition. None falls in a Phase 6B footprint. The archive follow-up found two-window Landsat QA context, five before-only and nine after-only high-resolution metadata leads, and 13 points with no in-window hit in the checked Wayback releases. No admissible pair was verified. The Resourcesat March/November pair has unresolved DN interpretability, illumination, provenance and alignment. IBM Lumshnong inspection dates span both seasons, while the reported footprint dates and geometry do not establish target-aligned change. Application geometry is location evidence. There are zero admitted positives and negatives across the three splits. [Independent evidence inventory](phase3d-reference-evidence.md) · [Phase 3F public-data pilot](phase3f-public-data.md) · [Phase 6D readiness audit](phase6d-reference-readiness.md)

## River observations

| Station | Joined dates before / after | Valid corridor dates | Screened water dates | Screened interior dates |
| --- | --- | --- | --- | --- |
| Lukha Khaddum | 52 / 57 | 39 / 45 | 0 / 0 | 0 / 0 |
| Lukha Sunapur | 47 / 56 | 33 / 43 | 5 / 7 | 1 / 0 |
| Myntdu Mihmyntdu | 24 / 28 | 16 / 21 | 3 / 4 | 0 / 0 |
| Myntdu Leshka | 43 / 52 | 19 / 16 | 12 / 8 | 11 / 6 |

Counts are distinct UTC dates within screened station corridors. The Phase 4A 10 m masks depend on cloud, water classification, green–NIR NDWI and bank clearance. Missing support leaves water conditions unknown. Leshka was the only station with interior support in both windows. Phase 4B matched **five date pairs across November, December and February**, but found only **12 connected common 10 m cells** against its 25-cell exploratory floor. No complete native 20 m SCL or B11 footprint fit inside the common support. The spectral comparison was withheld. B3/B4 are native 10 m; SCL/B11 are native 20 m. CHIRPS supplied coarse station-cell context. Only two of five pairs were within 5 mm on the exploratory seven-day rainfall comparison. Potential reservoir regulation, lack of contributing-area validation and lack of synchronous field calibration remain. [Phase 4A screening](phase4a-river-feasibility.md) · [Phase 4B Leshka](phase4b-leshka-spectral-pilot.md)

## Assessment against the original objectives

| Objective | Achieved evidence | Required for scientific completion |
| --- | --- | --- |
| Detect new or expanded mining-related surface disturbance early | Real before/after change features and audited reference workflow. | Independently admitted dated interiors, registered feature inputs and held-out evaluation. Separate temporal validation is needed for detection lead time or operational alerts. |
| Use Sentinel-1 and Sentinel-2 jointly | Shared 30 m grid and verified feature arithmetic, with RF ablation and Siamese baseline software. | Compare prespecified models and ablations on identical held-out reference pixels and multiple independent blocks. Report exclusions and uncertainty. |
| Investigate downstream degradation | Four real station screening results and a withheld fixed-footprint pilot. | Adequate fixed water support, comparable dated observations, validated catchment/drainage and exposure, flow or release context, rainfall and synchronous field observations. |
| Visualize risk and evidence | Existing local viewer and dashboard display real observations and feasibility diagnostics. | A validated disturbance layer with explicit coverage and error characterization before risk or alert claims. |

## Publication-safe limitations

The study demonstrates sensor support and a reproducible feature pipeline over a bounded sample. Seasonal medians and observation masks do not identify the cause or date of a surface change. Optical and radar changes can reflect atmosphere, terrain, phenology, moisture or non-mining activity. Relative VV alignment checks lack independent ground control. A 30 m analysis grid or catalog accuracy field does not establish positional error for reference polygons. The observed land-feature patterns establish neither illegal extraction nor early warning. Water indices are relative spectral descriptors. The Leshka support gate prevents a seasonal spectral result, and no NTU, sediment concentration, acidity, contamination, degradation or mining-to-river attribution was estimated. The downstream analysis still requires the inputs and controls in the [Phase 4 contract](../reference/PHASE4_INPUT_CONTRACT.md).

## Conditional follow-up for Planet or IBM evidence

1. If Planet grants access, retain authorized product IDs, exact acquisition timestamps, processing and orthorectification details, coverage geometry, QA, license and original hashes. Screen actual imagery in both frozen windows for clear coverage of the same conservative interiors and documented positional error ≤30 m. If only one window qualifies, log the gap and retain UNKNOWN.
2. If IBM supplies records, request original dated inspection maps, georeferenced photographs or surveys and actual worked-area footprints in both windows. Reconcile mine identity, capture dates, geometry definitions, datum/CRS, control accuracy and permitted use. An inspection date, proposed boundary or activity narrative alone cannot establish a paired reference.
3. When enough evidence is available, provide neutral reviewer packets with date and source provenance, omitting screening scores, candidate rankings and partition assignments. Obtain independent second review. Admit only defensible interiors and retain a rejection ledger. Prioritize missing classes and independent blocks in each frozen split without moving blocks.
4. Only after admission, acquire and register bounded paired feature exports against the successful coverage receipt over the eventual reference footprints. Freeze the manifest, common held-out IDs, validation-only selection and analysis rules. Report per-class support, independent blocks and held-out uncertainty. Keep the final test set out of tuning. [Real-reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md)

## Local reproduction

Phase 6E used existing data only. Local tables, three figures and the rebuild script are under `outputs/phase6e_research_consolidation/`. Run from the checkout root with the existing environment.

```powershell
python -B -c "import runpy; runpy.run_path('outputs/phase6e_research_consolidation/rebuild_local.py')"
```

The targeted coverage, graph, raster and multi-tile suite passed (56 tests). The receipt records the script and source hashes, rendering versions and figure/table hashes. Figures retain native delivered cell values on the respective saved analysis grids. Panels use nearest-neighbour display and common scales for each quantity. Saturated colourbar ends indicate display clipping, with source rasters untouched. The local river figure shows screened dates only. No imagery or site-level receipt is distributed with this report.
