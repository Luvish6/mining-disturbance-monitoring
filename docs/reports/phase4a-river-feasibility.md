# Phase 4A — Sentinel-2 river observation feasibility

This stand-alone pilot checks water-pixel support near four named monitoring stations. It does not use model outputs or enable the downstream disturbance analysis defined by the [Phase 4 input contract](../reference/PHASE4_INPUT_CONTRACT.md). It does not delineate the two full catchments or compare upstream and downstream exposure.

## Source inventory and geometry

| Source | Role and limitation |
| --- | --- |
| [CPCB monitoring station register](https://cpcb.nic.in/wqm/WQMN_list.pdf) | Official names and coordinates for Khaddum (4315), Sunapur (3376), Mihmyntdu (4316) and Leshka (3379). Station coordinates identify the search neighbourhood. They are not surveyed banks, widths or satellite matchups. |
| [WWF HydroSHEDS Free Flowing Rivers](https://developers.google.com/earth-engine/datasets/catalog/WWF_HydroSHEDS_v1_FreeFlowingRivers) | Query and clip actual vector reaches. The closest intersecting line is a candidate corridor guide. DEM-derived geometry can miss narrow, moved or impounded channels. The local receipt retains reach topology attributes and station offsets. |
| [JRC Global Surface Water v1.4](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater) | Historical 30 m Landsat occurrence from 1984–2021. Use for independent historical water context. A 10 m display grid adds no resolution. Positive and ≥50% occurrence counts are logged separately. |
| [Sentinel-2 harmonized L2A](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED) and [cloud probability](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_CLOUD_PROBABILITY) | Individual dated observations with harmonized land surface reflectance. B2/B3/B4/B8 have 10 m sampling. SCL and B11 have 20 m sampling. A 10 m export does not improve SCL or SWIR resolution. |
| [CHIRPS daily v2](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY) | Live check of daily availability and point-cell seasonal sums. The nominal 0.05° grid is much coarser than the river reaches. |
| [IMERG V07](https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_V07) and [HydroBASINS](https://developers.google.com/earth-engine/datasets/catalog/WWF_HydroSHEDS_v1_Basins_hybas_12) | Follow-up options for subdaily rainfall timing and nested drainage delineation. Neither was used to fit or infer a rainfall response. Validate outlet snapping and contributing areas before area-weighted rainfall extraction. |

The [MSPCB Myntdu action plan](https://megspcb.gov.in/documents/Revised_Action_Plan_of_Rejuvenation_of_Myntdu_River2020.pdf) identifies Mih Myntdu and Leshka along the river, including hydropower context. Leshka must be checked for reservoir/backwater or regulated-flow influence before pooling with flowing reaches.

## Bounded observation method

Each window is 720 m square on a 10 m EPSG:32646 grid. The screening corridor is the nearest clipped mapped line buffered by 80 m and limited to 260 m around the station. The full window provides neighbours for the interior test. The existing harmonized Sentinel-2 join, scene cloud ≤80%, cloud probability <40%, SCL 4/5/6, edge masks and joint index validity were reused per scene. The seasonal comparison retains the frozen half-open windows [2023-11-01, 2024-04-01) and [2024-11-01, 2025-04-01). No seasonal median is treated as an observation date.

The river screen additionally requires SCL 6 and positive green–NIR NDWI with a positive denominator. A sensitivity screen raises NDWI from >0 to >0.1. An interior candidate is a water pixel centre at least 20 m from the closest failing-mask pixel centre on the 10 m grid. A wider-support sensitivity check uses 30 m clearance. These are raster interior tests. A three-cell-wide aligned strip can pass the 20 m test and a five-cell strip can pass the 30 m test. Neither test measures bank-to-bank width or verifies pure water, and the 30 m test cannot certify a native 20 m SWIR footprint. The screen can miss turbid water that fails NDWI or SCL, and can retain bottom, bank or adjacency effects. Cloud and shadow indicators are logged independently and can overlap.

## Live results

All four windows were fully contained in the verified study districts and intersected actual HydroSHEDS line geometries. The nearest lines were GOID 4103404, 4110349, 4090610 and 4100220 respectively, at 57, 101, 44 and 27 m from the corresponding CPCB coordinates. JRC positive occurrence covered 64/798, 235/749, 18/814 and 491/549 corridor cells respectively on the display grid. The RGB panels show a mapped-line offset at Sunapur and Mihmyntdu. HydroSHEDS is suitable for locating broad river corridors; the pilot did not certify the selected geometries as current centrelines or delineate upstream catchments.

Before / after. Dates are distinct UTC calendar dates. “Valid” means at least one corridor pixel passed existing preprocessing. “Water” additionally requires SCL 6 and NDWI >0. “Interior” further applies the 20 m clearance rule.

| Station | Joined granules | Joined dates | Valid dates | Water dates | Interior dates | 30 m clearance dates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Lukha · Khaddum | 98 / 114 | 52 / 57 | 39 / 45 | 0 / 0 | 0 / 0 | 0 / 0 |
| Lukha · Sunapur | 47 / 57 | 47 / 56 | 33 / 43 | 5 / 7 | 1 / 0 | 0 / 0 |
| Myntdu · Mihmyntdu | 24 / 29 | 24 / 28 | 16 / 21 | 3 / 4 | 0 / 0 | 0 / 0 |
| Myntdu · Leshka | 75 / 87 | 43 / 52 | 19 / 16 | 12 / 8 | 11 / 6 | 11 / 6 |

- **Leshka is the only two-window spectral pilot candidate.** The December 2023 and December 2024 panels show a broad waterbody with a connected interior. Maximum raster clearance was about 149/150 m. This indicates ample screened area at 10 m and potential for native 20 m follow-up after verification. The shape and documented hydropower context warrant separate treatment as potentially impounded water. The stricter NDWI test retained 11/6 dates. Shared calendar months with interior detections were November, December and February, with unequal support. No matched seasonal spectral contrast was estimated.
- **Sunapur is a one-date follow-up lead.** Its single November 2023 interior date also survives the stricter NDWI test, but clearance reaches only about 22 m before and 10 m after. The panel shows a thin curved channel and a visibly offset mapped line. There is no defensible paired interior for a spectral comparison.
- **Mihmyntdu and Khaddum are unsupported for a paired spectral analysis under this screen.** Mihmyntdu returned isolated water cells with at most 10 m clearance, consistent with a narrow or incompletely classified channel. Khaddum has historical water context and general valid land pixels but no screened water in either window. These outcomes cannot distinguish narrow water from mask rejection or geometric misalignment. A true bank-to-bank width remains unverified at all four sites.

Cloud or shadow flags occurred in both windows at each site. For example, at Leshka at least one corridor pixel was flagged as cloud in 26/34 granules and dark/shadow in 22/21 granules. These are overlapping granule counts, with multiple granules on some dates. The local receipt retains per-scene denominators and flags. Counts of retained dates are conditional on cloud, water and interior selection and can bias the seasonal sample toward particular flow or illumination conditions.

CHIRPS supplied 152 and 151 daily images in the two windows. Coarse station-cell seasonal sums were approximately 276/150 mm at Khaddum, 296/181 mm at Sunapur, 212/100 mm at Mihmyntdu and 253/136 mm at Leshka. These point-cell sums establish data availability and show why seasonal comparability needs checking. They are not local gauge, upstream-area rainfall or discharge measurements.

## Spectral feasibility and next steps

If comparable open-water interiors survive independent checks, trial **B4 red surface reflectance** and **(B4 − B3)/(B4 + B3)** as unitless relative spectral indicators. Use positive denominators and compare only matched verified footprints and similar dates/flow conditions. B8 can provide exploratory context at higher sediment loads, where red can saturate, but bottom reflectance, shallow water, glint, terrain shade, aerosols and adjacent banks can change all of these signals. This land L2A product and the pilot mask do not supply water-specific atmospheric correction. Neither proxy measures NTU, suspended-sediment concentration, acidity or contamination without synchronous field matchups and calibration. See the [Vjosa Sentinel-2 and turbidimeter study](https://esurf.copernicus.org/articles/11/881/2023/).

For follow-up, verify reach identity and bank outlines against independently dated finer imagery, prioritise repeated interior pixels and separate reservoir and flowing-water contexts. Match months and hydrological conditions, quantify missing observations and check 1-, 3- and 7-day antecedent catchment rainfall with gauge or IMERG sensitivity where available. Rainfall timing, discharge, regulation and sampling bias can confound a before/after contrast. No degradation or causal conclusion is supported by this pilot.

The local receipt stores coordinates, feature attributes, per-scene counts, acquisition timestamps, widths of the grid and support diagnostics. Local maps show selected dated examples with water and interior-screen overlays. The reproducible script uses the existing virtual environment and Earth Engine account from the checkout root.

```powershell
python -B scripts/phase4a_river.py --output outputs/phase4a_river_feasibility
```
