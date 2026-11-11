# Phase 3F — No-cost public-data follow-up

Planet academic access and the IBM request can proceed in parallel. The checks below used existing project access, original Resourcesat data and public metadata. None required a purchase or a new approval.

## What can be used now

| Pilot | Landsat in both windows | Local Resourcesat | In-window Wayback source metadata in four checked releases |
| --- | --- | --- | --- |
| R003 | QA-pass context | Two dates, descriptive review only | None |
| R005 | QA-pass context | Two dates, descriptive review only | None |
| R008 | QA-pass context | Two dates, descriptive review only | After, 2025-02-20 (LG02, 0.34 m source) |
| R013 | QA-pass context | Zero signal on both dates | None |
| R021 | QA-pass context | Zero signal on both dates | After, 2025-01-10 (LG01, 0.34 m source) |
| R022 | QA-pass context | Outside both rectangles | Before, 2024-01-12 (WV03, 0.31 m source) |

**Zero of six have an independently verified reference pair.** All remain UNKNOWN. The findings supplement the [original archive pilot](phase3f-archive-pilot.md).

- **Landsat.** Earth Engine evaluated up to eight low scene-cloud Landsat 8/9 Tier 1 Collection 2 Level 2 scenes per point and season. Every site had 7 or 8 scenes per season passing QA at the centre and all sampled pixel centres in a 90 m radius. The check used QA_PIXEL bits 0–5 unset and QA_RADSAT zero. The local receipt records product IDs, timestamps, scene cloud, QA counts and scene geometric model RMSE where available. QA is a data-quality indicator. At 30 m, a valid pixel can mix cover types and cannot resolve small disturbance boundaries or establish cause. The Landsat observations are independent of the Sentinel feature stack and remain coarse context. [USGS QA definitions](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands)
- **ASTER.** NASA CMR exact-point searches returned one before-season AST_L1T v004 granule with a VNIR TIFF link at each point, all from 26 March 2024. After-season hits for five points were thermal-only. R022 had no after hit. No after-season 15 m VNIR asset was returned. Full assets are free with ordinary Earthdata Login. Links and footprints were verified at the catalog level; pixels were not inspected. [NASA AST_L1T v004](https://data.nasa.gov/dataset/aster-level-1t-precision-terrain-corrected-registered-at-sensor-radiance-v004)
- **Historical high resolution.** Esri World Imagery Wayback returned source metadata at all six points for releases 2024_r05, 2024_r13, 2025_r05 and 2025_r12. The three in-window hits above are single-season leads. Older source dates were excluded. The layer reports source accuracy of 5 m for the listed hits, which still requires interpretation of the accuracy metric and local geometry before admission. Capture dates come from source metadata, separate from basemap release dates. Point queries do not establish coverage over a proposed interior, and no tiles were downloaded or visually verified. Google Earth historical viewing remains an optional manual cross-check. No site-level Google Earth dates or screenshots were verified in this follow-up. Check source attribution, acquisition dates or mosaic ranges, product provenance, local positional documentation and permitted uses before relying on either viewer. [Esri Wayback metadata](https://www.esri.com/arcgis-blog/products/arcgis-living-atlas/imagery/wayback-with-world-imagery-metadata) · [Google Earth image dates](https://support.google.com/earth/answer/6327779/how-images-are-collected?hl=en) · [Google imagery use guidelines](https://about.google/brand-resource-center/products-and-services/geo-guidelines/)

## Continue without external approval

1. Use the exact receipt IDs for matched Landsat context and the existing native Resourcesat windows for R003, R005 and R008. For finer follow-up, check the R008 and R021 after hits and R022 before hit in the authorized public viewer and look for complementary dated coverage. Keep source rights and any image reuse decision explicit. Public metadata checks can also be extended to other frozen candidates before spending time on full downloads.
2. Continue real Earth Engine feature construction, coverage checks, bounded exports, raster ingestion and visualization development. Exercise ingestion, masks, split isolation and map presentation with clearly marked synthetic fixtures. This follow-up ran 34 targeted coverage, ingestion, map and candidate-geometry tests. Synthetic output stays outside the accepted-reference workflow.
3. Give independent interpreters neutral IDs, coordinates and independent sources only. Keep Sentinel change values, screening rationale and rankings out of their materials. Retain UNKNOWN when cover type, boundary, timing or disturbance cause is ambiguous. Keep the frozen partitions and existing admission criteria. [Real-reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md)

A public-data-only validation design is defensible **if** it obtains interpretable, independently dated evidence in both windows, documented positional uncertainty at most 30 m, independent second review, and sufficient independent blocks for both classes in every split. The current pilot supports acquisition triage and software verification. It cannot validate real detection performance. Demonstration or synthetic results cannot substitute for admitted references.
