# Phase 22L — Meghalaya temporal optical pilot

The existing East Jaintia Hills TRAIN lead east-94-559-c74, block 94:559, supplied the reproducible anchor at 92.71783660 E, 25.29193341 N. The 1.92 × 1.92 km AOI was verified wholly inside the original GAUL 2025 East/West Jaintia Hills geometry before downloading. It is a 64 × 64, 30 m north-up EPSG:32646 grid. This is an exploratory land-disturbance pilot. Reference status remains UNKNOWN.

## Actual observations

Before is 1 November 2023 through 31 March 2024; after is 1 November 2024 through 31 March 2025. The existing Phase 2 Sentinel-2 SR harmonized and cloud-probability join was reused with scene cloud ≤80% and cloud probability <40. The land screen retains SCL 4/5, masks native edge and required-band NoData, rejects NDWI ≥0 and mean green/red/NIR reflectance below 0.04. This adds conservative water and very-dark-surface exclusion. SCL cloud/shadow flags cannot certify complete removal of terrain or cast shadows.

The before collection supplied 52 joined image assets over 28 unique UTC capture days; after supplied 59 over 29 days. Assets include overlapping granules and duplicate processing timestamps, so counts do not represent independent acquisition dates. Per-cell count ranges after screening were 13–38 and 23–55. All 4,096 cells passed the minimum two-observation requirement in both periods, providing 3.6864 km² of common eligible land. Counts measure accepted scene samples. Residual haze, illumination and incomplete quality masks remain possible.

NDVI and bare-soil index were computed per accepted scene and then seasonally median-composited. BSI is ((B11+B4)−(B8+B2))/((B11+B4)+(B8+B2)). SWIR B11 has native 20 m support and all values are sampled on the 30 m export grid. Seasonal median NDWI remains a final water exclusion. The exploratory rule was fixed before processing as delta NDVI ≤−0.30 and delta BSI >+0.10 on common valid land. The BSI increment and dark-surface threshold were implementation choices for this pilot. They are unvalidated and were not optimized against mining labels.

## Candidates and interpretation

The rule selected nine cells in six 8-connected components, totaling 8,100 m² (0.81 ha), about 0.22% of eligible AOI area. Component sizes were 3, 1, 1, 2, 1 and 1 cells. Candidate delta NDVI ranged from −0.406 to −0.302 and delta BSI from +0.151 to +0.497. The context slope ranged from 7.20° to 20.75°. SRTM slope was not used to select or exclude candidates.

The consistent-stretch RGB panels show scattered small spectral differences within a largely vegetated context. The selected cells provide evidence of seasonal spectral change. Their coarse, small clusters do not resolve excavations or establish mining. Seasonal vegetation, forestry, road/construction clearance, erosion, terrain illumination and registration artifacts remain competing explanations. Visual review cannot distinguish these explanations at this output scale. The protocol used whole seasonal composites, with unequal sampling and no independent positional control or field review. A matched-date or month-level inspection and independently dated higher-resolution evidence are needed before interpreting a disturbance mechanism.

## Products and verification

One 199,682-byte satellite response produced the local georeferenced seasonal stack, change stack, six candidate polygons and compact before/after/NDVI map under outputs/phase22l_temporal_pilot/. The receipt retains all scene IDs, acquisition times, source collections, raster hashes, grid and rules. Image stretch was a common 0–0.30 reflectance range. Candidate polygons use exact grid-cell outlines transformed to WGS84; they retain EXPLORATORY_REVIEW_REQUIRED and UNKNOWN.

The map extent order and contour row orientation were corrected from cached data and visually inspected. No second satellite export was needed. The [sanitized summary](phase22l-temporal-summary.json) records empirical coverage and component counts. Raw satellite products, derived maps and exact candidate geodata remain local under publication rules. Reproduce with python -B -m scripts.phase22l_temporal in a fresh output directory. Two focused tests verify masks, count handling and preservation of steep-slope candidates. Area and component counts were checked against the grid denominator.

River NDTI requires a separate water-mask and rainfall-context analysis. No river pollution, mining causality, mining labels or model performance was inferred.
