# Phase 3C preliminary visual review — 2026-11-11

The project supplied these non-independent reviewer notes from exported screenshots of matched March and November Resourcesat-2A LISS-IV imagery. The date records entry of the notes. The scenes were acquired on 17 March and 12 November 2024. See the [existing pair review](bhoonidhi-pair-review.md) for coverage and registration diagnostics.

| Site | Screenshot observations | Uncertainty and review status |
| --- | --- | --- |
| KORPET | A large cyan, exposed-looking feature is visible in both images. March appears pale and low contrast. November shows stronger vegetation contrast and pronounced dark areas. | Mining-related change remains unconfirmed. |
| Sumon Pohduna | A large cyan, exposed-looking feature is visible in both images with broadly similar outlines. March appears pale and low contrast. November shows stronger contrast and darker surrounding areas. | The screenshots do not support confident interpretation of smaller differences. Mining-related change remains unconfirmed. |

The cyan appearance is a display observation. Surface material, activity, and the cause of any apparent difference remain unverified. Source imagery contains digital numbers (DN), with surface reflectance calibration unconfirmed. March atmospheric veiling or haze is possible. Terrain shadow and illumination differences remain unresolved. The sites share overlapping image context and constitute a single evidence context. Application polygons define areas for review and carry no mining class. The mismatch between the scene pair and the seasonal-composite research design remains unresolved.

## Local native-pixel comparisons

For each site, the local comparison uses the application bounds plus a 250 m margin, rounded outward to native 5 m pixel boundaries. The March and November windows share the same map extent within georeferencing precision. The lossless single-band GeoTIFFs preserve the B2, B3 and B4 DN arrays, data types, NoData and validity masks. Reopened files were checked against the archived source windows. GeoTIFF CRS normalization to EPSG:32646 changed mapped crop-corner positions by less than 1 mm in the verification check. No resampling or registration correction was applied. Existing broader context outputs remain available. Use the separate application boundary overlay and synchronized nearest-neighbor display with a shared B4/B3/B2 stretch for visual comparison.

## Reviewer checklist

- [ ] Check coverage, validity masks, haze, saturation, and whether the polygon interior and surroundings are interpretable on both dates.
- [ ] Check dark areas against slope, aspect, illumination geometry, and visible cast-shadow boundaries. Flag obscured areas as uncertain.
- [ ] Compare stable features distributed around the polygon for registration offsets and scene-wide tonal differences.
- [ ] Record any apparent boundary or texture differences with location, date, visibility, and confidence. Document alternative explanations and keep disturbance interpretations unverified pending corroboration.
- [ ] Record overlap between sites and count shared evidence once.

## Before reference labeling

Verify scene provenance, processing level, polygon placement, native grid alignment, and review-window integrity. Establish interpretability after assessing haze and shadow. Obtain admissible independent evidence for the relevant periods, reconcile the scene dates with the seasonal-composite design, and apply the existing reference protocol and admission criteria.
