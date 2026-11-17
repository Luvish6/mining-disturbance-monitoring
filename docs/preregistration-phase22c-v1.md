# Phase 22C preregistration amendment v1

This amendment applies only to the 2019 Maus static-footprint pilot. The Phase 22B spatial roster, development sites, reference-review procedure, model settings, seeds, threshold grid and metrics are inherited. The roster SHA-256 is `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`. Coverage decisions attach to tiles and feature configurations. TEST remains sealed throughout Phase 22C.

## Observation amendment

Keep 2019-01-01 inclusive through 2019-04-01 exclusive UTC as the production window. Allow ascending and descending S1 GRD candidates intersecting the window geometry. Keep the IW, 10 m and dual VV/VH filters. Rank direction-orbit combinations by descending scene count, ascending direction before descending on a tie, then smallest relative orbit. Require two scenes for the chosen combination and select only those exact scenes for the composite. Keep the original spatial smoothing, power-domain median and dB output. Report pixel coverage separately from scene intersection. A secondary 2019-10-01 through 2020-01-01 window is permitted for metadata-only diagnosis if Q1 has no eligible orbit combination. Secondary-window scenes cannot substitute for Q1 input or backdate a reference.

| Configuration | Ordered features | Eligibility |
|---|---|---|
| Optical | B3, B4, B8 | At least two jointly cloud/edge-masked S2 observations in at least 70% of cells |
| Optical with DEM | B3, B4, B8, elevation | Same optical rule on cells with finite SRTM elevation |
| Fused with DEM | B3, B4, B8, VV, VH, elevation | Both sensors have at least two observations and DEM is finite on a common footprint covering at least 70% of cells |

Keep Phase 22B S2 L2A reflectance scaling, cloud probability <40, scene cloud ≤80, SCL 4/5/6, B8A/B9 edge masks and shared optical validity. DEM is SRTM GL1 elevation in metres. Compare feature sets only on identical valid support when reporting paired comparisons. Record separate optical and radar counts, use float32 on the frozen 30 m 64 × 64 UTM grid, and mask −9999. No missing sensor is filled with zeros. Scope QA to the same one TRAIN and one validation window. Reuse the cache when selection and provenance match. Allow at most two new direct QA TIFF downloads, each ≤2 MiB.

## Label and claim amendment

Maus candidate polygons in TRAIN may contribute **WEAK, UNVERIFIED positive training interiors** to the provisional pilot after date-context, alignment, quality and mask checks. Rasterize conservative interiors only. Exclude ambiguous boundaries and cells without evidence. Absence from the Maus inventory supplies no negative class. Binary fitting requires explicit admissible negative support and meaningful eligible TRAIN groups. No negative labels are created here.

Separate weak-label agreement from verified evaluation. If unreviewed validation candidate masks are used for debugging or selection, disclose their provenance and coverage and report only weak-label agreement. Verified validation or TEST evaluation requires independently dated, appropriately licensed, position-checked evidence, two independent decisions and documented adjudication. TEST evidence and metrics are inaccessible during model selection. No fitting or evaluation is authorized in Phase 22C.
