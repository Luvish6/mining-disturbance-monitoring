# Day 4 — Dashboard integration and Planet preparation

The Satellite Change Explorer has a Phase 7 tab alongside the original Phase 3G viewer. District and tile selectors route to the six existing Day 2 panels with signed VV, VH, NDVI and NDTI and fixed legends. The page reads Day 1 distributions and observation support and charts Day 2 Jaccard overlap for the directional unions and four absolute pair comparisons. Tables retain threshold disagreement counts and joint component sizes. Calculations remain in the original offline scripts. River, Leshka and methodology pages remain available. The displayed signals are exploratory.

## PlanetScope local preflight

Requested items are 20240325_043545_49_24dd and 20250326_044548_96_2521. No matching imagery was found in the project checkout. Actual footprint, cloud and shadow support, registration and interpretability remain unverified.

Place the authorized assets in a private local folder. For each item supply its original item GeoJSON as SCENE_ID.json, and the corresponding SCENE_ID_3B_AnalyticMS_SR_8b.tif and SCENE_ID_3B_udm2.tif files. The CLI accepts the asset directory, a local JSON review plan and a new local output directory.

```powershell
python -B -m scripts.phase7_planet_reference LOCAL_ASSET_DIR LOCAL_PLAN_JSON outputs/phase7_day4_planet_review
```

The plan requires projected `crs` and `bounds` in that CRS (xmin, ymin, xmax, ymax), `local_review_permitted` set to true, a `usage_document` identifying the authorization, `control_source` and `control_error_m` for independent positional control, and `controls`. Provide at least three non-collinear stable landmarks with `reference_xy`, `before_xy` and `after_xy` for each. Use documented and spatially distributed control. Keep the plan and the generated package private.

The command checks item identity and UTC time, provider footprints, projected metre units, raster dimensions and alignment within each SR/UDM pair, positive source values and UDM flags. It checks any embedded SR band descriptions against the provider order. If descriptions are absent, band order is sourced from the standard named asset and provider specification. Clear support uses band 1, excludes snow, cloud shadow, haze, cloud and any band 8 unusable bit. Valid common support is sampled at clear before-cell centres within the requested area. Relative and independent-control offsets are measured in metres, with a conservative screen of documented control error plus maximum observed residual at most 30 m. This is a local screening check. Independent visual review and defensible polygon-scale error are still required.

The output, when inputs pass, is a local side-by-side fixed-stretch RGB comparison and a receipt with hashes, UTC dates, cloud and shadow counts and control residuals. Source rasters are read-only. The display uses native crops and neither warps nor writes the originals. Terrain shadows and residual obscuration require human inspection. The output is for independent interpretation and contains no model scores, split labels or automatic mining labels.

[PlanetScope bands and product naming](https://docs.planet.com/data/imagery/planetscope/) · [Planet UDM specification](https://docs.planet.com/data/imagery/udm/) · [Project reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md)
