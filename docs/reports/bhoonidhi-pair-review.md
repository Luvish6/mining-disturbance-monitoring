> Text-only publication copy prepared 11 November 2026 from `outputs/phase3c_bhoonidhi_pair_review_17mar2024_12nov2024/REPORT.md`. Private paths/session URL fragments sanitized. Referenced local imagery and licensed assets deliberately excluded. Findings preserved; publication does not admit reference labels.

# Phase 3C: 17 March 2024 / 12 November 2024 LISS-IV pair review

## Decision and geographic coverage

| Site | BEFORE signal | AFTER signal | Common signal on identical grid | Decision |
|---|---|---|---|---|
| KORPET | **634/634 (100%)** | **634/634 (100%)** | **634 pixels, 15,850 m²** | **NEEDS FURTHER REVIEW** |
| Sumon Pohduna | **1,593/1,593 (100%)** | **1,593/1,593 (100%)** | **1,593 pixels, 39,825 m²** | **NEEDS FURTHER REVIEW** |
| Lumshnong (70 ha application) | **0/27,410 (0%)** | **0/27,410 (0%)** | **0** | **REJECTED** |

These are actual original-band signal measurements inside the existing project polygons, not catalog assumptions. All three whole polygons fit within inspected crops. Full 801×801 context windows (4,005 m wide) have complete signal at KORPET and Sumon in both dates and zero signal at Lumshnong. Polygon denominators use pixel-centre rasterization; reported areas are UTM pixel-grid support, not surveyed lease areas or independent sample counts.

**Cloud-free common usable coverage remains unquantified.** Both dates have sufficient signal and visible ground detail for further human pair review at KORPET/Sumon. They are not yet admitted as reference labels. March's low contrast/possible atmospheric veil, local shadows, band-dependent alignment, undocumented absolute positional accuracy and differing product IDs remain unresolved. Lumshnong cannot be interpreted from this pair.

## Archive preservation and acquisition identity

Both ZIPs exist at `<PROJECT_PARENT>/`, outside the inner project. All member CRCs passed for both; before/after SHA-256 and modification times were unchanged. The November hash also agrees with its earlier inspection. No archives were copied into the project/GitHub or edited.

| | BEFORE | AFTER |
|---|---|---|
| ZIP | RAF17MAR2024037752011100054SSANSTUC00GTDA.zip | RAF12NOV2024041162011100054SSANSTUC00GTDA.zip |
| SHA-256 | `597b9ea8e442c56eb92cfab5b5c4407150d4bbbfaed70248db935005f21b16e9` | `01e9892ee7ac98ee1c424f313c9aa60485377f75e102735c89d98d50426a7b82` |
| Acquisition | **17-MAR-2024** | **12-NOV-2024** |
| Scene components | **037752_111_54** | **041162_111_54** |
| Platform / sensor | IRS-R2A / L4FX | IRS-R2A / L4FX |
| Primary .meta and ACC_REP ProductID | 2437198211 | 2410398791 |
| BAND_META ProductID | 25307537831 | 2630507321 |
| Scene centre time as stored | 04:36:06.165199 | 04:30:05.809012 |
| Sun elevation / azimuth | 56.544144° / 139.411118° | 43.877091° / 157.912901° |

The centre-time timezone is not explicitly identified. Dates, orbit/path/row, OTS IDs and sensor agree between archive names and embedded records, and lie in the requested respective seasons. The product-ID differences are explicitly retained; they may represent different processing/catalog identifiers but that explanation is **not verified**. Ask the provider to clarify rather than rewrite them. Generation on 18 March is not acquisition on 18 March. March metadata also repeats 87.304672 for sensor azimuth/elevation; preserve the values without treating them as validated geometry.

Both archives contain three band TIFFs, primary metadata, BAND_META, ACC_REP and JPEG/auxiliary XML. No per-pixel cloud/shadow QA raster is present. `CloudPercent=-NA-`, `Quality=Q`; no undocumented meaning or cloud percentage was assigned.

## Rasters, georeferencing and common grid

B2=green, B3=red, B4=near infrared, uint16 with 10-bit product metadata. There is no blue band; display is false colour **R=B4, G=B3, B=B2**, not true RGB. These are original DN, not calibrated surface reflectance. GEOREF/STD, DEMCorrection=YES and cubic-convolution (`CC`) resampling are recorded.

Native sensor/input resolution is **5.8 m**; delivered spacing **5×5 m**. March dimensions: **18,146 columns × 16,427 rows**. November: **18,140 × 16,429**. Both are north-up in declared WGS84 / UTM46N. Source WKT names EPSG:32646 but includes the slightly rounded inverse flattening noted previously; strict recognition returns None. Derivative CRS serialization to canonical EPSG:32646 was checked numerically to <1 mm at the crop centres; this is not absolute positional accuracy.

March affine outer origin: E=355673.94308370305, N=2850792.5 m. November: E=354078.94308370305, N=2850817.5 m. Their origin difference is an exact integer grid offset (319 columns and 5 rows), so identical geographic windows were extracted **without resampling**. Whole-scene origins differing does not mean the images have a 1,595 m registration error. All band grids within each source agree.

Source nodata is undeclared; GDAL masks say all-valid even over zero-fill. Signal support here requires finite, source-mask-valid values and **DN>0 in B2, B3 and B4 simultaneously**. This is an explicit fill/support proxy, not a cloud mask. Source DN crops retain undeclared nodata; derived display TIFFs mark absent signal as nodata=0. No pixel in either KORPET/Sumon 4 km context reaches DN 1023. Actual anchor B2/B3/B4: KORPET March **96/73/209**, November **52/29/229**; Sumon March **111/102/176**, November **78/77/144**; Lumshnong **0/0/0** both.

## March catalog-footprint discrepancy — resolved for this downloaded raster

The two coordinate sets were supplied by the user as transcriptions of screenshots for the same scene. The screenshot originals were not examined, and the cause of the portal inconsistency is unknown. Both sets are preserved in `catalog_footprint_comparison.json`.

| Catalog set | Agreement with actual product corner pixel centres | Conclusion |
|---|---|---|
| First: TL 25.171029 N, 91.4113 E; TR 25.177956 N, 92.3118 E; BR 24.436583 N, 92.3159 E; BL 24.429886 N, 91.4207 E | Corresponding corners **67.80–67.84 km** away | **Inconsistent with downloaded raster envelope**; KORPET/Sumon anchors excluded |
| Second: TL 25.768092 N, 91.5608 E; TR 25.774227 N, 92.4655 E; BR 25.032576 N, 92.4687 E; BL 25.026642 N, 91.5696 E | **0.65, 4.72, 1.12, 3.76 m** at TL/TR/BR/BL | **Consistent with downloaded product rectangle** and embedded Prod* corners, within transcription rounding |

Actual raster corner pixel centres (lon,lat): TL (91.56079350154846,25.768091853405227), TR (92.46545289942874,25.77422685370951), BR (92.46871114315725,25.032575988184355), BL (91.56956279586839,25.026641739778423). GeoTIFF outer bounds differ by half a pixel, as expected for the source AREA_OR_POINT=Point convention.

**The second set is not a valid-data or clear-sky footprint.** The embedded Image* corners describe a slanted swath inside the product rectangle. The independently read approximately 100 m common-positive support outline agrees with this slanted shape: every sampled signal cell lies inside the second catalog polygon; only 19.71% lie inside the first. This is a coarse descriptive sample, not a native-resolution area estimate or accuracy metric. Lumshnong is inside the second envelope but outside actual recorded signal; exact polygon checks confirm the rejection. KORPET/Sumon actual pixels take precedence over the first catalog set. See `march_catalog_footprint_comparison.png`, sampled-support GeoTIFF and GeoJSON.

## Cloud, haze, shadow and interpretation by date

**March BEFORE:** shared-stretch panels show a pronounced pale/low-contrast appearance over the cluster. Roads, broad bright surfaces and settlement/vegetation texture are still discernible. This appearance is consistent with possible haze/veiling and/or radiometric/seasonal differences; these causes cannot be separated here. No obvious large opaque cloud was identified across either small polygon by visual review, but thin cloud or atmospheric obscuration is not ruled out. Do not call the image cloud-free from the positive pixels.

**November AFTER:** vegetation and ground texture show stronger contrast; dark terrain/valley areas and slope shadows are more pronounced. No obvious large opaque cloud was identified over the polygons in the viewed panels. Small shadow/haze contamination remains possible. The lower sun elevation and different azimuth change illumination; darker November areas are not automatically land disturbance.

**Lumshnong both dates:** no interpretable ground. Zero-fill is not a measured cloud or shadow class. Cloud/shadow percentages and cloud-free common usable fractions remain **null/unknown** for every site. No atmospheric correction, binary brightness-based cloud classification or invented quality metric was produced.

Broad bright surfaces, roads and settlement patterns are visible in both dates. Their existence is an observed visual fact; a specific new/expanded mining disturbance was **not reliably verified** in this inspection. Large red/cyan or brightness differences alone can result from vegetation phenology, moisture, atmosphere, sun geometry or display DN scaling. No claim of absence of all change, mining identity, chemical contamination or illegal activity is made.

## Relative image alignment findings

1. Identical output pixel size, orientation and geographic extents were verified; no reprojection/registration correction applied. Both dates use the **same pooled per-channel 2nd–98th percentile DN limits** within each site's paired panels. This improves display consistency but is not radiometric calibration.
2. Diagnostic normalized cross correlation on high-pass B2/B3/B4 independently used eight 96×96-pixel (480 m) context patches, searching ±12 pixels (60 m). Raw scores, coordinates, peak/secondary peak and boundary flags are saved. No test/model training is involved.
3. Every B2 and B3 patch peaked at **(dy=0, dx=0)** on the integer grid. B4 peaked at (0,+1) in six patches and (+1,0) in two. The visually reviewed settlement/road context_6 and persistent rectangular structure/settlement-edge context_7 also have B2/B3 peaks (0,0) and B4 (+1,0). They are putatively persistent features, **not surveyed control points**; the surrounding texture contributes to each match.
4. NCC peak ranges: B2 **0.466–0.592**, B3 **0.492–0.748**, B4 **0.570–0.728**. These are similarity diagnostics, not registration accuracy. Pattern matching suggests close relative alignment with band-dependent apparent offsets of about one output pixel (5 m). It does **not** establish 5 m accuracy, subpixel precision, absolute geolocation, a confidence interval or a scene-wide distortion model. NIR phenology/illumination and internal band alignment may affect the matches.
5. Sign: dy/dx denotes apparent AFTER feature displacement relative to BEFORE; map east=5×dx m and north=-5×dy m. No correction was applied because band-dependent shifts and unverified controls do not justify one global translation.

The eight contexts are all around KORPET/Sumon; this is not an independent registration check for Lumshnong. Provider ACC_REP internal tiepoint residuals do not replace independent ground controls or establish the positional accuracy of the application boundaries.

## Outputs and next steps before reference labels

New files are confined to `outputs/phase3c_bhoonidhi_pair_review_17mar2024_12nov2024/`: `inspection.json`, `coverage.csv`, `registration_diagnostics.json`, `registration_patch_pairs.png`, catalog comparison JSON/PNG, sampled March support TIFF/GeoJSON, raw metadata copies per date, original-DN and false-colour GeoTIFF crops per date/site, common-signal masks, and matched 4 km/1.5 km side-by-side PNGs per site. One-off scripts are included for reproducibility; their statistics are followed by manual visual review/reporting. Source TIFFs were read directly inside ZIPs. Derivative crops were reopened to verify equal affine transforms, dimensions, CRS, band counts and exact anchor DN values.

- **KORPET/Sumon:** retain the pair for detailed independent review. Seek a clearer or more seasonally comparable before scene if March low contrast prevents conservative boundary interpretation; do not simply increase contrast and assume the atmospheric problem is solved.
- Identify multiple truly stable road intersections/building corners outside possible disturbances; manually verify their correspondence, check each band and estimate residuals/displacements at finer precision if needed. Apply any correction only to a new derivative after validation; preserve source grids.
- Establish documented absolute/reference-boundary positional uncertainty under the existing <=30 m admission policy; pixel size, provider tiepoint residuals and the NCC offsets alone are insufficient.
- Retain both catalog screenshots and ask the provider to clarify the wrong footprint and differing product IDs. This is an unresolved provenance question, not a reason to ignore actual valid KORPET/Sumon pixels.
- First and second reviewers should independently interpret conservative, clearly resolvable interiors using the actual dates and corroborating evidence, adjudicating seasonal/illumination ambiguities. Do not trace an entire application boundary as mining or force a non-mining label where no change can be resolved.
- **Lumshnong:** obtain different imagery with actual valid signal in both seasons; the current pair is rejected there.

No original archive, prior report, production implementation or tests were modified. No dependencies installed, automated labels, classifier training, model evaluation, tests, Git operations or satellite uploads were performed. Existing 103-test success is historical, not a fresh test result. Phase 3C remains incomplete for accepted supervised reference labels.
