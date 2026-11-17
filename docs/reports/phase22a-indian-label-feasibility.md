# Phase 22A — Indian mining label source verification

**Decision: NO-GO for Indian supervised fitting today.** Maus v2 is the strongest candidate for a separate historical static-footprint experiment. Admitted Indian positives and negatives remain zero for both static and temporal tasks. Counts below describe source features or published study rosters. The [current admission decision](indian-training-data-decision.md) and frozen 2023–24 / 2024–25 change design remain in force.

## A. Maus v2 — CONDITIONAL for historical static positives

The [PANGAEA v2 record](https://doi.pangaea.de/10.1594/PANGAEA.942325) was published in 2022 under CC BY-SA 4.0. The [official GeoPackage](https://download.pangaea.de/dataset/942325/files/global_mining_polygons_v2.gpkg) was read in memory (24,657,920 bytes). It contains 1,204 India-coded WGS84 geometries, all valid under Shapely, matching the [publisher country summary](https://download.pangaea.de/dataset/942325/files/global_mining_area_per_country_v2.csv), which reports 2,293.41 km². These are polygon features, so one mine complex may contribute more than one.

State counts use one representative interior point per polygon with the [pinned simplified geoBoundaries ADM1 layer](https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbOpen/IND/ADM1/geoBoundaries-IND-ADM1_simplified.geojson), ID IND-ADM1-1811400 (represented year 2011 according to the API). All points matched exactly one state. Eighteen polygons intersected two state geometries. These counts depend on the stated boundary release and counting method.

| State | Features | State | Features |
|---|---:|---|---:|
| Andhra Pradesh | 44 | Arunachal Pradesh | 1 |
| Assam | 11 | Bihar | 2 |
| Chhattisgarh | 59 | Goa | 81 |
| Gujarat | 38 | Haryana | 7 |
| Jharkhand | 245 | Karnataka | 95 |
| Kerala | 3 | Madhya Pradesh | 62 |
| Maharashtra | 49 | Odisha | 218 |
| Rajasthan | 141 | Tamil Nadu | 17 |
| Telangana | 76 | Uttar Pradesh | 8 |
| West Bengal | 47 | | |

The polygons were visually delineated using the 2019 10 m Sentinel-2 cloudless mosaic with supplementary basemap interpretation. The public schema has no polygon-specific date or scene list. The 10 km inventory search envelope and reported global validation (78.9% mine producer accuracy) do not establish complete mine coverage in India. The target includes pits, waste, tailings, ponds and related infrastructure. Background beyond polygons is unlabeled. Rasterization on a 10 m grid is technically possible. Reference dates, boundary accuracy and inclusion rules need checking before evaluation. Sampling 2019 Sentinel-2 as input risks shared-source bias. A separately reviewed 2019 static experiment can reuse Sentinel-1/2 preprocessing and DEM with a single-date feature contract. There is no paired change target or direct fit to the 14-band temporal runner. Multiple geographically separate mine complexes appear feasible to sample, but no independent partition or negative support has been certified.

## B. Indian Surface Mining Dataset — UNVERIFIED as a downloadable standalone release

Shivani A Mehta, Ashish, Mayur Solanki and Aaditeshwar Seth authored the verified [ACM paper, DOI 10.1145/3624774](https://doi.org/10.1145/3624774). Its [author copy, Sections 3 and 5.1](https://www.cse.iitd.ac.in/~aseth/mining-characterization.pdf) reports 781 India polygons from Maus v1 clustered into 170 areas by k-means on polygon centroids, with 2019 Sentinel-2 imagery at 10 m. This verifies the reported study counts, without independently reproducing its roster. The paper also describes manual Google Earth interpretation for ten out-of-sample mines across six states. The 2018/2022 delineations are classifier outputs. No downloadable cluster crosswalk, independent masks, per-feature imagery dates, positional evidence, archive size or artifact license was authenticated. The v1 source is [separately available](https://doi.pangaea.de/10.1594/PANGAEA.910894). The published clusters could guide a static optical experiment, subject to overlap review and dated independent controls. They supply no admitted S1/S2/DEM training labels or temporal change masks.

## C. Bhuvan/NRSC — CONDITIONAL for coarse historical static review

NRSC lists purpose-declared AOI/district shapefile requests for 2005–06, 2011–12 and 2015–16 at 1:50,000. This is map scale, not delivered pixel size. The thematic legend includes active mining, abandoned mining and quarry, with the parent class also covering pits and brick kilns. A received vector layer could be filtered by its verified class codes. The [official WMS example](https://www.iirs.gov.in/iirs/sites/default/files/pdf/GTA_Practicals.pdf) documents display access, which does not establish feature download or export rights. [Bhuvan general terms](https://bhuvan.nrsc.gov.in/bhuvan_links.html) grant limited access. Product-specific research and redistribution rights, response size, delivered class fields, source dates and positional suitability were not verified. The latest cited 50K cycle may overlap Sentinel acquisitions, but per-feature matches are unverified. Earlier cycles predate the full S1/S2 pairing. A separate static experiment might support regional grouping after export and review. Differencing these broad classes would not establish the project's dated change labels. [NRSC release notice](https://bhuvan.nrsc.gov.in/updates/bhuvan_apr2026.html) · [NRSC class manual](https://bhuvan-app1.nrsc.gov.in/2dresources/thematic/LULC503/lulc.pdf)

## D. OpenStreetMap — NO-GO for masks, candidate locations only

Count-only Overpass queries targeted closed ways and multipolygon relations with `landuse=quarry` or `industrial=mine`, using four WGS84 boxes (south, west, north, east): Korba (21.95,82.35,22.55,82.95), Talcher (20.75,84.85,21.25,85.45), Jharia (23.5,86.15,24,86.65) and Singrauli (24,82.35,24.45,83). Valid India counts and distribution were not established. Global endpoints returned capacity errors, rate limits or timeouts. The Switzerland-only instance was excluded. No polygon export size was measured. OSM element edit times are editing dates and do not date source imagery or extraction. Tags can distinguish some inactive sites, but completeness and boundary semantics vary. A future geographic split would require geometry deduplication and independently verified mine complexes before any label use. Rasterizable boundaries would remain candidate annotations until independently dated and validated. Neither static nor temporal masks are admitted. [Quarry tagging](https://wiki.openstreetmap.org/wiki/Tag:landuse%3Dquarry) · [OpenStreetMap ODbL terms](https://www.openstreetmap.org/copyright)

## E. Global Energy Monitor — NO-GO for masks, site reference only

The [August 2026 tracker](https://globalenergymonitor.org/projects/global-coal-mine-tracker) reports coal asset locations, status and source-linked wiki entries, with exact or approximate location flags. The primary geometry is a point. Status and update dates are useful for screening possible matches but do not date footprint observations. GEM provides [CC BY 4.0 terms](https://globalenergymonitor.org/creative-commons-license). The tracker advertises a distinct [February 2026 boundary supplement](https://www.gem.wiki/Coal_Mine_Boundaries_and_Methane_Sources) for methane attribution. The form-gated files were not acquired. Indian workbook counts, file sizes, supplement-specific terms, Indian polygon coverage and imagery dates remain unverified. Even where delineated, proposed, lease or methane attribution areas require excavation-specific verification. Points can help group or identify coal sites for review. They supply neither pixel masks nor an independent static or temporal partition.

## Next experiment

Pre-register a bounded 2019 static feasibility sample across spatially separated mine complexes, starting from Maus v2. Use independently dated reference imagery to vet conservative mining interiors and hard-negative controls, including nearby bare land, industrial surfaces and quarries where relevant to the target. Keep contiguous and buffered complexes within one split and seal TEST before model selection. Confirm rights, positioning and valid coincident S1/S2 before generating any training manifest. Keep the existing temporal 14-band experiment separate.
