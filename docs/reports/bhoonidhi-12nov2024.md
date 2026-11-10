> Text-only publication copy prepared 11 November 2026 from `outputs/phase3c_bhoonidhi_inspection_12nov2024/REPORT.md`. Private paths/session URL fragments sanitized. Referenced local imagery and licensed assets deliberately excluded. Findings preserved; publication does not admit reference labels.

# Resourcesat-2A LISS-IV — 12 November 2024 inspection

## Decision

| Candidate | Anchor B2 / B3 / B4 DN | Actual three-band signal in saved polygon | Overall decision |
|---|---|---|---|
| KORPET | 52 / 29 / 229 | **634 / 634 pixels (100%)** | **NEEDS FURTHER REVIEW** — coverage passes, visually promising after image |
| Sumon Pohduna | 78 / 77 / 144 | **1,593 / 1,593 (100%)** | **NEEDS FURTHER REVIEW** — coverage passes, visually promising after image |
| Lumshnong (70 ha) | 0 / 0 / 0 | **0 / 27,410 (0%)** | **REJECTED** — all-zero signal |

“NEEDS FURTHER REVIEW” does not mean missing signal: the KORPET/Sumon coverage check passes. It means final admission as independent reference evidence remains pending site-specific quality/geolocation/provenance review. No before-season pair, second review, mining labels or classifier were created. Exposed/bright soil alone is not proof of mining or illegality.

## Archive and actual metadata

Source: `<PROJECT_PARENT>/RAF12NOV2024041162011100054SSANSTUC00GTDA.zip`, **684,064,111 bytes**. ZIP exists; contents comprise BAND2.tif, BAND3.tif, BAND4.tif, the product .meta, BAND_META.txt, ACC_REP.txt, JPEG and JPEG auxiliary XML (plus directory entry). All member CRCs passed. SHA-256 before and after is identical:

`01e9892ee7ac98ee1c424f313c9aa60485377f75e102735c89d98d50426a7b82`

Original modification time also unchanged. Source GeoTIFFs were read directly inside the ZIP; no source archive copy, edit, Git staging or upload was made. The old 19 November ZIP and report were only read and remain unchanged.

- Primary metadata: IRS-R2A / L4FX, SubScene A, orbit **041162**, path **111**, row **054**, date **12-NOV-2024**. Scene centre time 04:30:05.809012 as stored (timezone not explicitly supplied); acquisition start/end 04:29:59.505697246 / 04:30:10.045010416.
- Three single-band **uint16** GeoTIFFs, **18,140 × 16,429** pixels, 10-bit metadata. B2=green, B3=red, B4=near infrared. No blue channel; previews are **false colour B4/B3/B2**, not true RGB. Band meanings differ from Sentinel-2 numbering.
- Identical native affine grids across bands: 5 m output spacing, top-left outer corner E=354078.94308370305 m, N=2850817.5 m; north-up. Metadata input/native resolution is **5.8 m**; cubic-convolution 5 m resampling does not create additional native detail.
- Declared WGS84 / UTM zone 46N (EPSG:32646 in source WKT). Source inverse flattening is slightly rounded (298.25722293287); strict CRS recognition returns no EPSG, whereas GDAL-written derivatives normalize it to canonical EPSG:32646. Identical affine grids and coordinate-equivalence at each anchor were verified: normalization shift <**0.000037 m**. This is serialization rounding, not a measured positional accuracy or independent geolocation check. Source WKT and transform are preserved in inspection.json.
- Product type GEOREF, level STD, DEMCorrection=YES, resampling CC. Inspected values are original **DN**, not calibrated surface reflectance. No atmospheric correction or classifier-feature calculation performed.
- **Provenance discrepancy:** primary .meta and ACC_REP ProductID **2410398791**, BAND_META ProductID **2630507321**. OTS ID/date/sensor agree. Retain both and clarify the identifier relationship before formal reference admission.

## Actual candidate coverage and nodata

Used original verified project application polygons and map anchors in `outputs/phase3c_20261108_01/PHASE3C_VERIFIED_MINING_CANDIDATES.geojson`. They are geographic application boundaries, not observed disturbed masks. Anchor coordinates (longitude, latitude):

- KORPET: (92.07169655129559, 25.21552876312328), matching the supplied rounded coordinate at the same pixel.
- Sumon: (92.0732783689618, 25.21908290812763).
- Lumshnong: (92.36492230074244, 25.16639280941408).

Each full polygon was checked to fit inside its own 801×801 crop. Pixel-centre rasterization defines denominators; pixel counts are not independent labeled samples or surveyed areas. Native nodata is **undeclared**, and GDAL masks report all-valid even in the margins. Inspection therefore uses source-mask-valid, finite, **all three DN > 0** as an explicit signal-support proxy. This is not a validated clear-sky mask; zero-fill interpretation is supported by the geometric swath margins and contiguous all-zero areas.

KORPET and Sumon both have no zero-valued pixels in any band across their full polygons. Their 200 m, 1 km, 2 km and 4 km square context windows all have **100% common signal support**. Lumshnong's full polygon and every context window are **all zero in all three bands**, including the entire 4 km crop, despite being inside the product rectangle. Pixel-centred inclusive windows are 5 m wider than the nominal sizes; the largest is 4005×4005 m.

Full-scene exhaustive scans: **233,720,268** pixels have common three-band signal, **78.42381%** of the rectangle. This is recorded support, not usable/cloud-free coverage. The per-band zero counts, ranges and full-scale counts are in inspection.json. Globally four B3 and one B4 pixels reach DN 1023; no candidate-polygon value reaches this full scale (KORPET maxima B2/B3/B4=75/84/309; Sumon=129/168/288). This does not validate all radiometric quality.

## Cloud, shadows and visual interpretation

Visually reviewed the saved false-colour context/detail panels for all three sites. Each channel has its own 2nd–98th percentile display stretch over common signal; display brightness is not calibrated reflectance.

- **KORPET:** visible textured ground and vegetation inside the outlined polygon. No obvious large opaque cloud obscures the polygon in the preview. Nearby dark ridges/valleys and bright surfaces warrant local illumination/shadow review. No mining identity inferred.
- **Sumon:** distinguishable red/dark interior, bright surrounding surfaces and linear features. No obvious large opaque cloud across the polygon, but nearby dark slopes and brightness contrasts require closer human shadow/land-surface interpretation. Bright patches were not classified as clouds or mining from colour alone.
- **Lumshnong:** no ground interpretation possible. Black indicates absent signal here; it is not a measured cloud or shadow condition.

These are **qualitative visual observations**, not validated masks or cloud percentages. Metadata CloudPercent is `-NA-`; Quality=`Q` is retained without inventing a code meaning. No cloud/shadow QA raster is present. Thin cloud/haze and small shadow-affected pixels cannot be ruled out. Validated cloud and shadow percentages remain **null**. No arbitrary brightness/darkness threshold was used to manufacture a percentage.

Sun elevation is 43.877091 degrees, azimuth 157.912901 degrees; hilly terrain can produce strong illumination differences. Provider tiepoint residual standard deviations are 5.46772 m and 3.99144 m along the reported pixel/scan directions. These are internal matching residuals, **not independently established absolute positional uncertainty**. Zero-valued across/along-track accuracy fields do not establish perfect geolocation. Existing source-boundary positional accuracy remains undocumented.

## Comparison with rejected 19 November 2024 image

| Candidate | 19 Nov Resourcesat-2, 070502_110_54 | 12 Nov Resourcesat-2A, 041162_111_54 |
|---|---|---|
| KORPET | 0/634 polygon support; ~5 km neighbourhood zero; nearest signal 5.08 km away | 634/634; anchor and 4 km context recorded |
| Sumon | 0/1,593 polygon support in saved actual crop | 1,593/1,593; anchor and 4 km context recorded |
| Lumshnong | Outside old scene rectangle | Inside new rectangle, but 0/27,410 and 4 km context zero |

This is a spatial-support comparison, not a land-change analysis. Different dates/platforms/illumination and separate display stretches prevent interpreting appearance differences as disturbance. The new actual KORPET/Sumon signal supersedes earlier catalog-only uncertainty for this specific scene; Lumshnong remains unsuitable.

## Outputs and remaining actions

All new outputs are under `outputs/phase3c_bhoonidhi_inspection_12nov2024/`:

- `inspection.json`: archive inventory, acquisition/CRS metadata, checksums, exact per-band and per-site statistics, visual notes and comparison.
- `coverage.csv`: polygon signal fractions, missing-signal counts, quality uncertainty and decisions.
- Source metadata/accuracy files copied without changes; `inspection_script.py` records one-off scanning/crop generation (choose a fresh output folder before reproducing). Final visual notes/report were added after reviewing its outputs.
- Per candidate: `context_dn_B2_B3_B4.tif` (original DN, 5 m grid), `common_signal_support.tif` (0/1 support proxy), `false_color_B4_B3_B2.tif` (georeferenced stretched display; derived nodata=0), `false_color_preview.png` (context/detail with application outlines). Lumshnong's blank display is included as rejection evidence, not usable imagery.
- `scene_overview.png`: 100 m nearest-sampled context only; exact counts were calculated independently at native output spacing.

Derived DN crops were reopened to check shape, affine transform, CRS coordinate effect and exact anchor DN round-trip. The initial literal CRS-string check was corrected after identifying vendor rounding; no source or production code was edited. Archive CRC/hash checks completed after successful crop generation. No dependencies installed, production changes, test changes, tests, model training or label creation. The prior 103-test result is historical and was not rerun for this inspection-only task.

**Next priority:** keep this as the promising after-season source for the KORPET–Sumon cluster. Review original-scale crops with the second reviewer; establish adequate positional accuracy/registration and clarify product provenance. Obtain a genuine November 2023–March 2024 image covering the same polygons, preferably comparable seasonal timing, inspect its actual pixels independently, and compare only shared interpretable ground. No two-season pair is accepted yet. For Lumshnong obtain a different swath with verified full-polygon signal. Formal reference labels remain blocked pending these checks; do not treat either application outline or bright soil as a mining label.
