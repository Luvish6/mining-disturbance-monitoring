> Text-only publication copy prepared 11 November 2026 from `outputs/phase3c_reference_quality_review/REPORT.md`. Private paths/session URL fragments sanitized. Referenced local imagery and licensed assets deliberately excluded. Findings preserved; publication does not admit reference labels.

# Phase 3C reference quality review — 17 March / 12 November 2024

## Recommendation

**Human quality review is ready; final mining/non-mining reference annotation should not begin yet.** KORPET and Sumon Pohduna remain **NEEDS FURTHER REVIEW**. Both have complete common signal and visible context, but radiometric comparability, March low contrast, local shadow effects, reference positional accuracy and metadata provenance remain unresolved. Reviewers may begin independent descriptive notes and quality assessment using this package. No mining-related change has been confirmed or labeled.

Inputs: previously inspected Resourcesat-2A LISS-IV scenes **037752_111_54 (17 March 2024)** and **041162_111_54 (12 November 2024)**, with original-DN crops and reports under `outputs/phase3c_bhoonidhi_pair_review_17mar2024_12nov2024/`. Both dates are within the defined seasons, but March and November represent different seasonal states, not season-long composites.

| Site | Original project anchor (latitude N, longitude E) | Common three-band signal within saved polygon |
|---|---|---|
| KORPET | 25.21552876312328, 92.07169655129559 | 634/634 pixels, 100% |
| Sumon Pohduna | 25.21908290812763, 92.0732783689618 | 1,593/1,593 pixels, 100% |

Anchors are original application KML vertices, not mine centres. Decimal precision is not positional accuracy. Application outlines are not observed mining boundaries. Source quality protocol and the existing <=30 m positional-error admission requirement remain unchanged. Lumshnong was rejected in the previous pair review for all-zero signal and is not promoted by this package.

## Radiometric comparability and NDVI decision

**These are DN products, not calibrated reflectance.** Metadata states GEOREF/STD, DEMCorrection=YES, cubic-convolution resampling and 10-bit data stored in uint16. B2=green, B3=red and B4=near infrared; output grid spacing is 5 m, input/native sensor resolution 5.8 m. No blue band exists. DEMCorrection describes geometric processing, not surface-reflectance or topographic illumination correction.

Before/after metadata contains the same Lmin=0 and Lmax values (green 52, red 47, NIR 31.5). These are radiance-scaling metadata, not proof that pixel values are reflectance, that atmospheric effects are removed, or that scenes are radiometrically interchangeable. Red and NIR scaling differs. A normalized ratio cancels only a common multiplicative scale, not arbitrary band gains or additive atmospheric offsets. No verified full per-product DN-to-reflectance procedure, solar-irradiance calibration, aerosol correction or BRDF/topographic normalization was applied here. Such processing may be possible with provider documentation, but cannot be silently assumed.

Reflectance NDVI is `(rho_NIR-rho_red)/(rho_NIR+rho_red)`. The distinction is supported by the [USGS NDVI description](https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index) and [NASA definition](https://science.data.nasa.gov/disasters/data-gallery/landsat-ndvi). These references explain reflectance-based NDVI; they do not supply calibration for these LISS-IV products.

Accordingly **calibrated before/after NDVI and physical NDVI-change products were withheld**. Instead, the package includes explicitly named **uncalibrated DN diagnostics**:

`R_DN = (DN_B4-DN_B3)/(DN_B4+DN_B3)` and `R_DN_after-R_DN_before`.

These maps are NOT reflectance NDVI and must not be interpreted as vegetation loss/gain, physical change, mining evidence or labels. They illustrate apparent spectral differences only. Inputs use finite common-positive three-band support, denominators must exceed 1e-6 DN, and output nodata=-9999. Diagnostics retain the same georeferencing. Their PNGs use fixed display scales and prominent warnings; no threshold classification or disturbance statistics were produced. Even properly derived TOA NDVI would still need atmospheric/seasonal/illumination scrutiny before interpreting cross-date change.

## Matched imagery and quality assessment

Each site has 4,005 m context and 1,505 m detail side-by-side B4/B3/B2 false-colour panels. Both dates share the exact 5 m north-up grid, geographic extent and pooled per-channel 2nd–98th percentile DN display limits. No histogram matching, atmospheric correction or registration correction was applied. The identical display stretch avoids an arbitrary per-date visual rescaling but does not make DN physically comparable. GeoTIFF display crops are supplied for GIS use.

**March BEFORE:** broad pale/veiled low contrast, although structures, road pattern and vegetation texture remain visible. Possible haze/atmospheric veil and radiometric/seasonal effects cannot be separated. No obvious large opaque cloud was identified across the small polygons in visual review. Thin cloud and locally obscured detail are not ruled out. Contrast stretching cannot reconstruct lost information.

**November AFTER:** stronger contrast and vegetation response, with pronounced dark slopes/valleys and local shadows. No obvious large opaque cloud across the polygons in viewed panels, but no validated cloud/shadow mask exists. Do not interpret dark pixels as disturbance or clear signal as guaranteed usable ground.

Both metadata files report CloudPercent=-NA- and Quality=Q. Cloud/shadow percentages and common cloud-free usable area remain **unknown**, not zero. Source nodata is undeclared and source masks say all-valid over zero margins; the prior three-band-positive check measures signal support only.

Sun elevation/azimuth: March **56.544144° / 139.411118°**, November **43.877091° / 157.912901°**. Lower November sun and different direction can change shadows/illumination on the hilly landscape. March-to-November phenology and moisture can also change spectral appearance. No current DEM illumination simulation or validated projected shadow mask was created; visual slope interpretation remains qualitative.

Review-only ambiguity areas are documented in `ambiguity_review_areas.geojson`:

| Area | Location | Alternative explanations to inspect |
|---|---|---|
| A1 | Whole KORPET-centred context, also covering Sumon | Broad March veil/low contrast and spectral contrast; atmosphere, phenology, moisture and radiometry |
| A2 | Northwest ridge, roughly 0.6–1.8 km west and 0.8–1.6 km north of KORPET anchor | Stronger November dark terrain pattern; illumination/terrain shadow versus surface change |
| A3 | Bright-surface context near Sumon, north of KORPET | Bright patterns present both dates; edge/colour differences may reflect illumination, atmospheric veil, season or band misregistration |

These approximate review boxes are not contamination masks, automatically detected changes or ground-truth polygons. Thin boundary-like differences anywhere in the application outlines need alignment and mixed-pixel scrutiny. Broad bright features/roads/settlement patterns are visible in both dates, but no specific new/expanded mining disturbance is confirmed; absence of such confirmation is not proof of no change.

## Landmarks, displacement and uncertainty

Three clearly persistent-looking structural candidates were selected from visual inspection of both dates in the KORPET southern context. L1/L2 are bright roughly rectangular structures; L3 is a narrow road/settlement access bend. These are descriptive image identifications, not verified building ownership/function or surveyed controls. Exact approximate-centre coordinates, common-crop row/column and source map coordinates are saved in `landmark_candidates.csv` and `.geojson`. Inspect `landmark_review_panels.png` before accepting physical persistence.

| Landmark | Latitude N | Longitude E |
|---|---:|---:|
| L1 | 25.207353755 | 92.072749437 |
| L2 | 25.207388391 | 92.063915271 |
| L3 | 25.208145533 | 92.062271725 |

Alignment refinement uses normalized cross correlation of high-pass individual B2/B3/B4 patches. Template widths are 32/48/64 pixels (160/240/320 m), Gaussian high-pass sigma 1.5/3 pixels, search +/-6 pixels (30 m), followed by a local quadratic peak fit when well-conditioned. This is **54 numerical fits on three landmarks**, not 54 independent controls. Templates include surrounding texture and are not exact point measurements. No correction was applied.

Positive east/north values mean apparent AFTER displacement relative to BEFORE. Across all bands/settings/landmarks, fitted displacement ranges from **-1.88 to +2.37 m east** and **-4.11 to -0.36 m north**. Per-landmark median values are:

| Landmark | B2 east / north m | B3 east / north m | B4 east / north m |
|---|---|---|---|
| L1 | -0.76 / -2.23 | -0.99 / -1.00 | +1.47 / -2.14 |
| L2 | -0.74 / -1.02 | -1.29 / -0.61 | +1.70 / -2.01 |
| L3 | -0.90 / -1.35 | -1.15 / -0.89 | +1.30 / -1.87 |

These fitted subpixel numbers show that a zero integer peak does **not** mean zero displacement. Their spread is an **empirical sensitivity envelope**, NOT a confidence interval, absolute accuracy, complete uncertainty bound or evidence of sub-metre resolving power. The interpolation adds numerical precision, not measured spatial information. Low contrast, texture mixture, template size, season, shadows, potential feature changes and per-band PSF/internal alignment affect estimates. Similarity values are diagnostics, not accuracy metrics; full values and peak margins are saved.

The band-dependent east displacement argues against blindly imposing one global shift. The control geometry is limited to a small southern cluster; spatial distortion at KORPET/Sumon boundaries is not established. Independent, distributed, manually verified correspondences and documented positional uncertainty are still needed. Source/provider internal residuals and 5 m output spacing are not a substitute for absolute ground-control accuracy. No resampling or alteration of source imagery was done.

## Human-review readiness and annotation decision

Open `index.html` for the local review gallery. The package contains matched panels and georeferenced false-colour crops, explicit DN-ratio diagnostic rasters/PNGs, application polygons with source URLs, three candidate-landmark coordinates, full registration fits and sensitivity CSV, ambiguity review regions, `REVIEW_CHECKLIST.md`, and a blank `reviewer_observation_template.csv`. Reviewer fields are empty; no mining or non-mining class is prefilled. The first and second reviewers should record evidence independently before adjudication and avoid classifier features/predictions when interpreting independent reference evidence.

**Manual quality assessment and descriptive observations can begin now. Final reference annotation/admission should wait.** Before assigning accepted training labels:

1. Independently verify local March interpretability; seek a clearer/more seasonally matched BEFORE scene if haze/contrast prevents conservative surface-boundary interpretation. Resolve provider calibration if quantitative NDVI comparison is needed.
2. Confirm L1/L2/L3 persistence and add controls distributed around both sites. Quantify repeatable geometric residuals and establish actual image and boundary positional uncertainty under the existing <=30 m gate; apply any validated correction only to a new derivative.
3. Resolve product-ID discrepancies and retain the catalog-footprint evidence. Prior inspection established the second March catalog rectangle matches the raster; that is not a valid-pixel or clear-sky footprint.
4. Obtain independent reviewer agreement on actual target-aligned seasonal surface evidence and conservative interiors. Record uncertainty, source dates and corroborating evidence. Do not automatically label vegetation differences, dark shadows, bright soil or whole application polygons.

No physical NDVI change or specific mining-related disturbance is established here; satellite land disturbance does not establish illegality. Existing Phase 3 methodology and admission gates were preserved.

## Preservation and validation

Only new files under `outputs/phase3c_reference_quality_review/` were created. Source georeferenced crops were hashed before and after processing and stayed identical. Source ZIP hashes are retained from the prior verified pair review; this task did not reread or modify either archive. Previous reports/code/tests were not edited. No models were trained/evaluated, no labels generated, no dependencies installed and no Git operations/uploads performed. Tests were not rerun because production code did not change; 103 passing tests remain the historical result.

Derivative rasters were reopened for finite values, valid ratio range, nodata and pixel-spacing checks. Shared affine grids were checked; landmark and diagnostic PNGs were visually reviewed. Report/gallery local links were checked for missing targets. Scripts record reproducible one-off generation; final narrative/visual assessment was added after inspecting results.
