# Phase 6D — District coverage and real-reference readiness

**Decision.** The matching Phase 2 district coverage gate passed. The six Phase 6B tiles are structurally compatible feature rasters. None is registered for supervised use. No candidate reviewed here has an admissible paired reference, verified reference positional error ≤30 m or independent second review. Real fitting and held-out evaluation remain blocked.

## District coverage and provenance

The live run used both original GAUL 2025 districts, descending Sentinel-1 relative orbit 77, the original seasonal windows [2023-11-01, 2024-04-01) and [2024-11-01, 2025-04-01), the original 20 m SAR smoothing, Sentinel-2 scene cloud ceiling of 80%, cloud probability below 40, the existing SCL and edge masks, and at least two valid observations. The coverage calculation uses EPSG:32646 at 500 m. The thresholds remain 90% for each SAR season and 70% for common support in each district.

Two reducer requests failed with Earth Engine pixel-estimate limits at 100,000 and 150,000. A bounded cap of 300,000 completed the same computation. Grid, thresholds, masks and reducers were preserved. No district raster export was submitted.

| District | Coarse area (km²) | SAR before / after | Optical before / after | Reported common | Gate |
| --- | ---: | --- | --- | ---: | --- |
| East Jaintia Hills | 2,012.16 | 99.906% / 99.900% | 99.950% / 99.963% | 99.938% | Pass |
| West Jaintia Hills | 1,798.22 | 99.900% / 99.895% | 100% / 100% | 100% | Pass |

The native report retains all coarse p5/p50/p95 and count diagnostics, including seasonal SAR median counts of 13/11 and optical medians of 33/41 (East) and 27/35 (West). These are coverage-screen statistics. The West common value exceeds the two separately reduced SAR values. A supplemental check wrote each mask into a fully valid binary image on the same 500 m grid before area reduction. It returned 100% SAR support in both districts and reproduced the reported common fractions of 99.938% East and 100% West as explicit intersections of the checked masks. The native and supplemental receipts are retained separately. They do not establish complete coverage at 30 m, local surface interpretability or mining observation quality.

The district collection receipt lists every source scene index and UTC acquisition time: 26/23 Sentinel-1 orbit-77 scenes, and 144/174 joined Sentinel-2 scenes with matching cloud-probability indices. Inputs are `COPERNICUS/S1_GRD`, `COPERNICUS/S2_SR_HARMONIZED`, `COPERNICUS/S2_CLOUD_PROBABILITY`, `USGS/SRTMGL1_003` and `FAO/GAUL/2025/level2`. Coverage receipt SHA-256 is `4122792e3bd52771a55bb95e720f70ccff0c10136a77ceee1e43d4365c007d23`. Full reports, source metadata and hashes are local.

## Phase 6B registration status

| Tile | Split | 14-band grid and receipt hashes verified | Matching district gate now | Supervised registration | Full-tile Landsat QA scenes before / after, out of 8 each |
| --- | --- | --- | --- | --- | --- |
| east-94-559 | Train | Yes | Pass | Unregistered | 5 / 5 |
| east-90-562 | Validation | Yes | Pass | Unregistered | 6 / 5 |
| east-91-561 | Test | Yes | Pass | Unregistered | 4 / 6 |
| west-82-563 | Train | Yes | Pass | Unregistered | 4 / 8 |
| west-85-563 | Validation | Yes | Pass | Unregistered | 6 / 4 |
| west-81-557 | Test | Yes | Pass | Unregistered | 6 / 4 |

Each original feature file has 4,096 common-support cells, exact band order, a 30 m lattice, explicit −9999 NoData and a matching original tile receipt hash. Original receipts identify terrain units. The feature files lack registered provenance and explicit band-unit tags. Their original exploratory acquisition never used the newly passed receipt. The original raw responses carry 23 bands, including diagnostics, and the 14-band feature files are derived copies. No historical provenance was amended. For supervised inputs, produce new bounded paired exports against the passing receipt and register separate copies under the [existing protocol](../reference/REAL_REFERENCE_PROTOCOL.md). The [Phase 6C structural review](phase6c-multitile-integration.md) documents the remaining schema gate.

## Independent evidence

No Phase 3E point falls in a Phase 6B footprint or even in its six blocks. The 27 leads occupy nine distinct frozen blocks, three per partition. The recorded KORPET and Sumon application points are in the same test block as west-81-557 but outside the sampled footprint. The recorded Lumshnong application point is also outside all six tiles. These are point comparisons. Application coordinates cannot define the disturbance interior.

| Evidence set | Paired observation evidence | Documented reference positional error ≤30 m | Independent second review | Decision |
| --- | --- | --- | --- | --- |
| Six tile footprints | Paired 30 m Landsat QA context. Three Wayback centre metadata hits after only. | No. Landsat scene RMSE and Wayback source metadata do not establish reference boundary accuracy. | None verified | UNKNOWN |
| 27 Phase 3E leads | Existing two-window Landsat point context. Four Wayback releases yielded 5 before-only leads, 9 after-only and 13 with no in-window hit. No dated high-resolution pair was verified. | No. The Wayback hits report a 5 m source accuracy field without validated local error or complete polygon coverage. | None verified | 27 UNKNOWN |
| KORPET and Sumon Pohduna | Resourcesat scenes dated 2024-03-17 and 2024-11-12. Previous DN review found unresolved haze, illumination and relative alignment. Shared context is one evidence group. | Unknown | Preliminary non-independent review only | UNKNOWN |
| Lumshnong | IBM visits 2023-11-16/17 and 2025-01-22. Reported pit geometry dates or definitions do not establish paired seasonal change. | Unknown pit-grid datum and accuracy | None verified for a paired reference | UNKNOWN |
| Mynkree, Brishyrnot I and Daba Saithad | Mynkree 2024-12-05 only. Brishyrnot inspection 2024-09-10/11 between windows. Daba EAC minutes 2024-11-21/22 record a proposal. | Unknown | None verified | UNKNOWN |

**Landsat.** Up to eight low scene-cloud Landsat 8/9 Tier 1 Collection 2 Level-2 scenes per tile/window were tested over the full 4,096-cell grid. QA_PIXEL bits 0–5, QA_RADSAT and B4 source support were screened. At least four scenes per tile/window passed every sampled cell. The local receipts list exact product IDs, acquisition UTC times, scene geometric-model RMSE and the QA numerator and denominator. The data are publicly reusable with attribution. These tests verify sampled coverage. Mixed pixels and lack of visually verified conservative interiors keep the 30 m evidence at context level. [USGS Level-2 data and citation](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products) · [USGS QA flags](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands) · [USGS geometry](https://www.usgs.gov/landsat-missions/landsat-geometry)

**Historical high resolution.** Four Wayback metadata releases were queried at the six tile centres (24 requests) and the 21 Phase 3E points beyond the six previously queried (84 new requests). Tile-centre source dates were east-94-559 on 2025-03-25 (WV03), and west-82-563 and west-81-557 on 2025-02-20 (LG02). Those are three after-only points. Provider capture dates were used separately from release identifiers. Point metadata establishes neither interior coverage nor visibility. Imagery was not downloaded or redistributed. Viewer access does not establish reuse rights. The existing Phase 3F public archive receipts already record the negative ASTER after-season VNIR search and earlier Resourcesat coverage checks. They were reused. Planet access and restricted archive licensing remain unresolved. [Esri metadata guidance](https://www.esri.com/arcgis-blog/products/arcgis-living-atlas/imagery/wayback-with-world-imagery-metadata) · [Phase 3F archive checks](phase3f-public-data.md)

**Independent records.** The new Daba proposal minutes add administrative context. Ministry oversight proceedings list two East Jaintia clearances dated 2024-12-14 and describe a NESAC drone/GIS restoration survey program. The searched public records did not yield downloadable paired orthomosaics, site-level acquisition and control metadata, or validated seasonal disturbance geometry. Document access alone does not establish imagery reuse permission. Public IBM reports previously checked were carried forward without repeating unsuccessful archive or access requests. [EAC minutes](https://environmentclearance.nic.in/writereaddata/Form-1A/Minutes/0412202489065076Approved36thEACNCMminutes.pdf) · [Oversight proceedings](https://moef.gov.in/uploads/pdf-uploads/pdf_68aeb4ba922604.62239967.pdf) · [Phase 3D evidence inventory](phase3d-reference-evidence.md)

No neutral imagery package met the threshold for release to reviewers. The local acquisition crosswalk remains internal. When a pair is available, use neutral identifiers and source/date/quality information. Omit partition membership, screening ranks, application context and Sentinel changes from the interpretation materials.

## Frozen split readiness

| Split | Phase 3E leads / distinct blocks | Admitted positive / negative references | Blocks with admitted references | Ready |
| --- | ---: | ---: | ---: | --- |
| Train | 9 / 3 | 0 / 0 | 0 | No |
| Validation | 9 / 3 | 0 / 0 | 0 | No |
| Test | 9 / 3 | 0 / 0 | 0 | No |

Before model training, register bounded real paired inputs with documented provenance, secure interpretable independent observations across both seasonal windows with documented usage rights and positional error ≤30 m, obtain independent second review, and retain both classes across several independent blocks per split after exclusions. Match registered extents to eventual admitted interiors. A discovery point outside the existing six tiles requires its own audited feature footprint. Freeze evaluation support and the test comparison before fitting.

The full automated suite passed (134 tests), including coverage graph, registration, reference-admission and multi-tile checks.

Local outputs are under `outputs/phase6d_reference_readiness/`, including `coverage_final/phase2_report.json`, the source-scene inventory, archive responses, the registration readiness table and the private candidate crosswalk. The originals, dashboard and models were preserved.
