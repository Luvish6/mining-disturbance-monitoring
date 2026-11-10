> Text-only publication copy prepared 11 November 2026 from `outputs/phase3c_bhoonidhi_inspection/REPORT.md`. Private paths/session URL fragments sanitized. Referenced local imagery and licensed assets deliberately excluded. Findings preserved; publication does not admit reference labels.

# Bhoonidhi Resourcesat-2 LISS-IV inspection — 10 November 2026

**Decision: NOT SUITABLE at the supplied KORPET coordinates; NOT READY for before-season comparison there.** KORPET lies within the rectangular GeoTIFF bounds but outside the recorded image signal. No mining labels or model training were performed.

## Verified archive and acquisition

- Source: `data/R2F19NOV2024070502011000054SSANSTUC00GTDB.zip` (589,165,148 bytes).
- ZIP directory inspected, every member CRC verified, and original SHA-256 unchanged before/after: `74cc0daf0cd0b6fb042eabd20cf4ab7e9a92b6451f691f2349e026915ae65d9a`. Modification time also unchanged. Imagery was read directly through GDAL /vsizip; full source rasters were not extracted or edited.
- Actual rasters: `BAND2.tif`, `BAND3.tif`, `BAND4.tif`, one uint16 band per file, 18,348 columns × 16,265 rows. Metadata declares 10-bit values, TIFF range 0–1023.
- Metadata: product `.meta`, `BAND_META.txt`, `ACC_REP.txt`, JPEG quicklook and JPEG auxiliary XML. No cloud/shadow QA raster is included.
- Satellite/sensor: IRS-R2 / L4FX, SubScene B. Acquisition 19 November 2024; orbit 070502, path 110, row 054, matching supplied scene identifier components. Scene centre time 03:58:22.993350 as stored; metadata does not explicitly identify the time zone. Scene start/end 03:58:16.512625782 / 03:58:27.051938952.
- Product is GEOREF / STD, DEMCorrection=YES, cubic-convolution resampling (`CC`). It is not declared surface reflectance; values inspected and exported here remain original digital numbers. Radiance calibration limits are supplied, but no atmospheric correction was applied.
- Provenance discrepancy to retain: product `.meta` and accuracy report use ProductID **24105359161**, whereas `BAND_META.txt` says **2630552841**. The OTS product identifier and acquisition agree. This discrepancy should be clarified with the provider before formal reference provenance admission.

## Bands and geometry

| File | Spectral interpretation | Nominal wavelength | Observed full-scene nonzero DN range |
|---|---|---|---|
| BAND2.tif | Green | 0.52–0.59 µm | 9–599 |
| BAND3.tif | Red | 0.62–0.68 µm | 3–580 |
| BAND4.tif | Near infrared | approximately 0.77–0.86 µm | 30–823 |

The archive confirms band numbers 234; the spectral interpretation follows the official LISS-IV specification. There is **no blue band**, so a true-colour RGB product cannot be made. False colour uses display R=B4/NIR, G=B3/red, B=B2/green. These band numbers are not Sentinel-2 band meanings.

CRS: **WGS 84 / UTM zone 46N, EPSG:32646**. Identical grid/shape in all three source rasters. Actual output pixel spacing **5 × 5 m**; metadata input/native resolution **5.8 m**. The 5 m resampling does not create 5 m native resolving power. Raster bounds: easting 321063.94308370305–412803.94308370305 m; northing 2754687.5–2836012.5 m. Rasterio's transform correctly handles the source `AREA_OR_POINT=Point` tag; metadata corner centre coordinates differ by half a pixel, as expected.

Official references: [ISRO Resourcesat-2 mission and 10-bit LISS-IV description](https://www.isro.gov.in/RESOURCESAT_2.html); [ISRO sensor spectral specification](https://www.isro.gov.in/media_isro/pdf/Publications/Diverse_Space_Applications.pdf).

## Actual coverage at KORPET

Input coordinate: longitude **92.07169655**, latitude **25.21552876**. Projected location: E=406486.6150741156 m, N=2789136.040325981 m. Source pixel: row **9375**, column **17084**, zero-based. B2/B3/B4 at this pixel: **0 / 0 / 0**.

| Centred square checked (nominal size) | Raster window | Pixels with all three DN > 0 |
|---|---|---:|
| 200 m | 41 × 41 | 0 / 1,681 |
| 1 km | 201 × 201 | 0 / 40,401 |
| 2 km | 401 × 401 | 0 / 160,801 |
| 5 km | 1001 × 1001 | 0 / 1,002,001 |
| 10 km context | 2001 × 2001 | 77,014 / 4,004,001 (1.9234%) |

Inclusive pixel-centred windows are 5 m wider than their nominal dimensions. All three bands are identically zero throughout the first four windows, not merely missing one channel. The nearest all-three-positive pixel centre in the **entire scene** is approximately **5,075.06 m** away (projected straight-line distance), at lon 92.02248116349305, lat 25.22531569360725. This is recorded-signal proximity, not proximity to clear-sky ground or a mining feature.

Full-scene exhaustive scanning found **233,074,152** common-positive pixels out of 298,430,220: **78.10005%**, approximately **5,826.85 km²** on the UTM grid. The rectangular raster covers 7,460.76 km². This is **nonzero signal support only**, not scientifically usable or cloud-free area. Both black slanted margins and the lack of local signal demonstrate why a rectangular/catalog footprint is insufficient.

The TIFFs declare **no nodata value** and report all-valid GDAL masks, even over zero-filled margins. Accordingly this inspection explicitly derives support from all three DN > 0. The broad all-zero margin and sharp geometric swath edge justify interpreting the KORPET zeros as padding/no recorded scene signal. This support proxy is not a cloud, shadow, water or mining classifier and should not be globally treated as a calibrated validity rule without provider confirmation.

## Quality and independent interpretation

- **KORPET:** no interpretable ground pixels. Cloud/shadow status there is unassessable; missing signal must not be called clear sky, shadow, water, or undisturbed land.
- **Elsewhere in the scene:** the false-colour overview shows textured terrain, vegetation, channels, bright cyan/white areas and dark slope/valley areas. These may include clouds/haze and cloud or terrain shadows; no automated cloud/shadow classification or percentage is defensible from this package. The small recorded strip in the 10 km context lies away from KORPET and does not substitute for coverage at the candidate.
- `CloudPercent` and `Quality` metadata fields are empty. The JPEG auxiliary XML's 100% valid percentage is a quicklook statistic and does not establish valid ground coverage.
- No band reached DN 1023 in the exhaustive scan. This only rules out observed digital full-scale values, not every form of radiometric saturation or poor quality. Provider saturation-radiance values were not converted/applied.
- Sun elevation 38.953298 degrees and hilly terrain make terrain shadows relevant. Supplied tiepoint residual standard deviations (~1.78 m pixel direction, ~1.96 m scan direction) describe provider internal matching, not independently measured absolute positional accuracy. `AcrossTrackAccuracy=0` / `AlongTrackAccuracy=0` are not proof of perfect geolocation.
- At locations actually imaged, 5.8 m native green/red/NIR data can support contextual manual interpretation after local quality review and alignment checks. Spectral brightness/exposed soil alone cannot establish mining. No reference evidence or labels were added to the Phase 3C workflow.

## Outputs and verification

All files are in `outputs/phase3c_bhoonidhi_inspection/`:

- `inspection.json`: archive member inventory, checksums, exact pixel counts, geometry and per-band statistics.
- Copied source metadata/accuracy files, preserving raw bytes.
- `korpet_context_dn_B2_B3_B4.tif`: original-DN ~10 km crop, three bands, 5 m grid, original nodata declaration preserved as absent.
- `korpet_2km_dn_B2_B3_B4.tif`: small georeferenced ~2 km crop, explicitly all zero.
- `korpet_context_common_nonzero_mask.tif`: explicit inferred support, 1=all-three-positive, 0=otherwise. Not a cloud mask.
- `korpet_context_false_color.tif` and `.png`: 2nd–98th percentile per-band DN display stretch, B4/B3/B2. The display TIFF uses zero as derived missing-support nodata; this declaration does not modify source rasters.
- `korpet_2km_nodata.png`: annotated close view explaining the absence of recorded signal.
- `scene_false_color_overview.png`, `scene_nonzero_support_overview.tif`: 100 m nearest-sampled scene context, approximate overview only, not native-resolution quality/area measurements. Full-resolution counts above were computed separately.
- `korpet.geojson`: supplied candidate point, no mining class assigned.
- `inspection_script.py`: reproducible one-off inspection, refuses to replace its output directory. No project implementation or tests were modified.

Reopened native-grid crop outputs to verify EPSG:32646, 5 m spacing, shapes, band counts and all-zero centre values. Reviewed context and scene PNGs visually. No extra dependencies installed. Existing suite: **103 collected, 103 passed, 0 failed, 0 skipped** (37.04 s). Initial restricted TEMP location caused one permission failure (102 passed); setting TEMP/TMP to the permitted workspace resolved it without editing code/tests. Existing synthetic training tests ran as part of the suite; no real model was trained and no labels were created.

## Before-season comparison readiness

**Not ready for KORPET.** First obtain a replacement after-season scene with verified non-padding, interpretable pixels at the exact coordinate and the intended annotation neighbourhood. A before-season scene alone cannot repair this missing after observation. Then obtain an independently suitable November 2023–March 2024 observation covering the same ground; check clouds/shadows, georegistration, native resolving power, seasonal/illumination differences and provenance. The 19 November 2024 date is within the after season, but one date is not the full seasonal composite and cannot alone demonstrate when a disturbance occurred. Neither a before-season image nor cross-date co-registration was inspected in this task.
