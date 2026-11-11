# Phase 3F — Archive availability and acquisition pilot

Pilot run 2026-11-11. Six existing Phase 3E locations were checked at their saved coordinates in both frozen seasonal windows. Site selection and routing details are in the private inventory. The reviewer handoff contains neutral IDs, locations, available imagery and source provenance.

## Pilot decisions

**Zero of six sites have a verified usable before/after pair for reference interpretation.** Three have native two-date Resourcesat signal and local descriptive-review packages. This pilot required interpretable corresponding ground detail at the candidate and its immediate surroundings on both dates before marking a pair usable. No independent positional error or reviewer agreement was established.

| Site | Decision | Resourcesat archive check | Landsat footprint hits, before / after |
| --- | --- | --- | ---: |
| R003 | ACCESS OR QUALITY UNVERIFIED | Both dates 3,721/3,721 three-band signal pixels. Pale March detail and dark November pixels at or near the location limit fine interpretation. | 41 / 38 |
| R005 | ACCESS OR QUALITY UNVERIFIED | Both dates 3,721/3,721. A broad central feature can be inspected descriptively, but March contrast and November dark margins leave fine boundaries uncertain. | 41 / 38 |
| R008 | ACCESS OR QUALITY UNVERIFIED | Both dates 3,721/3,721. Diffuse March detail and stronger November tonal differences leave reliable local correspondence unresolved. | 20 / 19 |
| R013 | NO SUITABLE IMAGERY FOUND IN SEARCHED SOURCES | Both windows lie within the product rectangles and have zero three-band signal. | 41 / 38 |
| R021 | NO SUITABLE IMAGERY FOUND IN SEARCHED SOURCES | Both windows lie within the product rectangles and have zero three-band signal. | 21 / 19 |
| R022 | NO SUITABLE IMAGERY FOUND IN SEARCHED SOURCES | The candidate neighbourhood is outside both raster rectangles. | 38 / 38 |

Signal counts refer to 61 × 61 native-pixel windows (305 m across) centred on the source pixel containing the inventory coordinate. A signal pixel has positive DN and a valid source mask in all three bands. There is no validated clear-sky fraction for these windows. Visual notes are descriptive and may reflect atmospheric veiling, season or illumination. The last three decisions apply to the products and public collections actually checked. Unsearched authenticated archive inventory remains unknown.

## Sources and limits

| Source | Pilot result | Access and cost |
| --- | --- | --- |
| Local NRSC/Bhoonidhi Resourcesat-2A LISS-IV | Original 17 March and 12 November 2024 products checked at every site. Source scene centres are reported as 04:36:06.165199 and 04:30:05.809012 respectively; metadata excerpts retained as supplied, without inferring a timezone. GEOREF/STD, 5 m product grid, 5.8 m sensor sampling, B2/B3/B4 DN. CloudPercent unavailable and internal geometry reports do not establish candidate-level absolute error. | Existing legitimately held products, no pilot charge. Local source and derivative retention. New archive access follows the [Bhoonidhi API and account process](https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/) and [product terms](https://bhoonidhi.nrsc.gov.in/bhoonidhi/htmls/FAQ2.html). No authorized catalog login was used in this pilot. |
| Copernicus Data Space contributing missions, ccm-optical | Twelve public searches returned HTTP 200 and zero footprint hits at the six coordinates in the two windows. That result is limited to the searched public collection. | Public metadata. No matching products or corresponding asset terms/cost to evaluate. [Copernicus Data Space](https://dataspace.copernicus.eu/explore-data) |
| USGS LandsatLook, landsat-c2l2-sr | Public searches checked actual item footprint geometries against the exact points. Returned records retain exact item IDs, acquisition timestamps, footprint, cloud and geometric properties where supplied. The 30 m products are supplementary context. The [Phase 3E assessment](phase3e-candidate-discovery.md) separately checked QA-pass pixels at each point. Neither check establishes fine-scale suitability. | Public catalog; no Landsat imagery purchased or exported. [USGS STAC documentation](https://www.usgs.gov/landsat-missions/spatiotemporal-asset-catalog-stac) |
| PlanetScope | The provider STAC/Data API requires authenticated access. Candidate-specific IDs, availability, quality, positional documentation and product cost could not be determined without entitlement. | No authorized account used or restricted search attempted. University-affiliated applicants may seek limited noncommercial access, subject to approval and terms. [Planet STAC authentication](https://docs.planet.com/develop/apis/data/stac/) · [Academic program](https://www.planet.com/industries/education-and-research/) |

The local Resourcesat identifiers, archive hashes, source projection and footprint distinctions are documented in the [provenance reconciliation](phase3d-provenance.md). This pilot recomputed both archive hashes, extracted only bounded integer source windows, and verified reopened GeoTIFF DN, masks, NoData and affine transforms. Output CRS normalization to EPSG:32646 was checked at crop corners to within 1 mm; no pixels were resampled or registered. The display panels use a shared B4/B3/B2 stretch, separate from the original DN GeoTIFFs.

## Expansion decision

Expand to the remaining 21 sites in stages. A bounded local swath and actual-pixel check is worthwhile because half the pilot had two-date signal and three locations showed why a catalog rectangle is insufficient. Defer bulk scene orders and full interpretation until a clearer authorized single-scene pair is found and tested on pilot sites. Prioritize a clearer before scene and corroborating after scene at R005, R003 and R008, and replacement pairs at R013, R021 and R022. Obtain exact capture dates, usable coverage over the proposed interiors, product rights, distributed control or defensible positional uncertainty within 30 m, and independent second review. Follow the [real-reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md).

The pilot admitted no reference labels. The study area, frozen partitions and methodology are unchanged.
