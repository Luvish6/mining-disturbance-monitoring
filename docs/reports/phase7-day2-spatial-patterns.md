# Day 2 — Spatial multi-sensor change patterns

## Analysis specification

Use the original six Phase 6B common-valid footprints on their 30 m EPSG:32646 grids. The before window is November 2023–March 2024 and the after window is November 2024–March 2025. Changes are after minus before.

Apply three nested descriptive levels. A cell qualifies at or beyond the stated magnitude.

| Level | Absolute radar change in either polarization | Absolute optical index change |
| --- | ---: | ---: |
| Low | 1 dB | 0.03 |
| Middle | 2 dB | 0.06 |
| High | 3 dB | 0.09 |

Map and tabulate both directions of each of the four bands. For a directional overlap comparison, define the radar mask as VV decrease OR VH decrease and the optical mask as NDVI decrease OR NDTI increase. These directions describe the dominant pooled signs observed on Day 1 and are used to compare patterns, with no assumption that they indicate a class. Also report all four cross-sensor band pairs using absolute magnitudes as a direction-agnostic comparison. Report intersection, union, radar-only, optical-only, neither, Jaccard, and the two conditional overlap fractions. Empty denominators are undefined.

Use four-neighbour connectivity for every signed band, both directional sensor masks and their intersection. Count all components, including isolated cells. Component area is cell count × 900 m². Perimeter is 30 m × exposed cell edges, including holes and tile-boundary edges. Record centroid in EPSG:32646, tile-edge contact, elevation, slope and minimum seasonal optical count. A tile-edge component may continue outside the footprint. No cross-tile stitching is used.

Track every low-level component through nested middle and high masks by exact cell membership. Report total surviving cells, number of fragments and largest surviving fragment. Classify only low components of at least four cells for persistence. A component is persistent by this rule when its largest connected high fragment has at least four cells and retains at least 25% of the original low component. Other eligible components are threshold-sensitive. Four cells and 25% are descriptive criteria for this analysis. For annotated examples choose the largest low joint component meeting the persistence rule and the largest eligible low joint component failing it, across the frozen roster. Ties use tile ID and component number. Keep examples separate from independent reference material.

## Results

All six original raster pairs passed source-hash, grid, mask and change-arithmetic verification. Each tile contributed 4,096 common-valid cells, for 24,576 cells in total. The component ledger contains 24,885 rows across patterns and levels. These rows include repeated and overlapping observations by design.

| Directional threshold | Both | Radar only | Optical only | Neither | Both / union (Jaccard) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Low | 8,254 | 5,428 | 5,195 | 5,699 | 0.437 |
| Middle | 2,541 | 2,938 | 4,256 | 14,841 | 0.261 |
| High | 728 | 1,013 | 2,983 | 19,852 | 0.154 |

Joint support shrank from 33.59% to 2.96% of the sampled footprint. At the high level, 728/1,741 radar cells also met the optical rule (41.8%), and 728/3,711 optical cells also met the radar rule (19.6%). The absolute-magnitude checks showed the same threshold dependence. Their pooled Jaccard values ranged from 0.283–0.387 at low and 0.046–0.133 at high. dVH–dNDVI had the highest absolute-magnitude overlap at each level (0.387, 0.224, 0.133). The absolute and directional masks have different definitions and denominators.

| Tile | Frozen split | Joint cells low / middle / high | Directional Jaccard low / middle / high | Eligible low joint components persistent / sensitive |
| --- | --- | --- | --- | --- |
| east-94-559 | Train | 1,512 / 657 / 253 | 0.501 / 0.385 / 0.281 | 1 / 33 |
| east-90-562 | Validation | 1,295 / 409 / 100 | 0.418 / 0.258 / 0.130 | 0 / 59 |
| east-91-561 | Test | 1,931 / 710 / 233 | 0.564 / 0.340 / 0.204 | 0 / 58 |
| west-82-563 | Train | 1,670 / 453 / 82 | 0.479 / 0.211 / 0.075 | 0 / 66 |
| west-85-563 | Validation | 1,160 / 274 / 54 | 0.372 / 0.166 / 0.075 | 0 / 70 |
| west-81-557 | Test | 686 / 38 / 6 | 0.251 / 0.068 / 0.058 | 0 / 42 |

Directional Jaccard fell in every tile. The largest joint component in west-81-557 was 28 cells at low, seven at middle and two at high. In east-91-561 the largest component at each level was 814, 207 and 25 cells. In that tile the total number of joint components rose from 173 to 201 between low and middle even as joint area fell, indicating fragmentation rather than a growth in joint area.

### Which components persisted

Of 1,414 low-level joint components, 1,085 were below the four-cell persistence reporting floor. **One of the 329 eligible joint components persisted**, and 328 were threshold-sensitive under the stated rule. A component can retain high-threshold pixels and still fail the connected-core criterion.

- **east-94-559, low joint component 74.** This was the only persistent joint component. It retained a single connected core from 22 cells at low to 10 at middle and six at high. The high core retained 27.3% of the low footprint. The low component covered 19,800 m² with a 1,080 m grid perimeter, median slope 8.8°, median elevation 1,232.5 m and median minimum optical count 26. It touches a tile edge. This localized cross-sensor pattern warrants interpretation from independent imagery if suitable evidence becomes available. Its cause and continuation outside the tile are unknown.
- **east-91-561, low joint component 62.** The largest eligible sensitive example covered 814 cells or 732,600 m², with a 21,180 m grid perimeter, median slope 3.8°, median elevation 858 m and median minimum optical count 36. It retained 430 middle cells in 60 fragments and 173 high cells in 59 fragments. Its largest high fragment was 25 cells, 3.1% of the original. The low footprint touches the tile edge. Its extent and connectivity depend strongly on the threshold.

| Pattern family | Persistent | Threshold-sensitive |
| --- | ---: | ---: |
| dVV decrease / increase | 2 / 0 | 401 / 44 |
| dVH decrease / increase | 1 / 0 | 370 / 38 |
| dNDVI decrease / increase | 31 / 13 | 213 / 138 |
| dNDTI decrease / increase | 6 / 9 | 63 / 275 |
| Directional radar union | 0 | 267 |
| Directional optical union | 11 | 175 |
| Joint directional intersection | 1 | 328 |

The ledger identifies every qualifying component by tile, pattern and low-level component number, including exact projected centroids, terrain context and middle/high fragmentation. A directional union can connect a much larger low footprint than an individual band, so persistence counts need not agree between a union and its constituent bands.

### Scientific interpretation

Widespread low-level overlap is consistent with broad seasonal changes and the dominant signs measured on Day 1. Its strong contraction under higher cutoffs limits any interpretation of the broad connected patches as coherent disturbance footprints. Small persistent cores are possible land-disturbance leads, with seasonal vegetation, soil moisture, illumination, radar terrain effects, imperfect alignment and residual optical artifacts still plausible. Slope and observation counts provide context. They do not diagnose these mechanisms. The examples are threshold-shape comparisons on seasonal composites. They are separate from the independent [reference admission workflow](../reference/REAL_REFERENCE_PROTOCOL.md).

## Reproduction and local deliverables

Run the offline analysis from the checkout root into a new directory.

```powershell
python -B -m scripts.phase7_day2_spatial --output outputs/phase7_day2_spatial_reproduction
```

The delivered local directory `outputs/phase7_day2_spatial_patterns/` contains six tile maps at original extents, two annotated examples, component and persistence ledgers, per-tile overlap and pattern-size tables, and an exact provenance receipt. The receipt binds the frozen roster, source receipt and raster hashes, source scene identifiers and UTC times, thresholds, analysis versions and artifact hashes. Signed maps use the same zero-centred scale for each band across tiles. Their colourbar extensions indicate display clipping. No source files were changed.

The targeted regression suite passed (18 tests). Two offline runs produced identical hashes. Independent table checks reconciled component and overlap totals.
