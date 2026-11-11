# Phase 6B — Real multi-tile feature acquisition

Six 64 × 64 tiles were acquired serially from Earth Engine on a common 30 m EPSG:32646 lattice anchored at (0, 0). The study geometry came from GAUL 2025. The roster was frozen before any raster download. The first tile passed its checks before the other five were requested. No Drive or asset export was submitted.

The [Phase 6A plan](phase6a-multitile-plan.md) was implemented with the hash key `phase6a-multitile-v1:<block-id>`. Up to three candidates per district and split were screened using median slope, baseline NDVI and the lower of the two seasonal median optical observation counts. Each choice used its prescribed within-slot rank. Candidate screening used an aligned 120 m reduction. Earth Engine reported 289 nonmasked optical-count samples per candidate, including intersecting boundary cells. These coarse screening statistics are separate from the 4,096-cell raster QA denominator. The local roster records 373 excluded extents with reasons and no missing slots.

The first preflight request exceeded Earth Engine's reducer pixel estimate cap. Raising the guard from 400 to 2,048 on the same 120 m grid and unchanged tile bounds resolved the request. The failed request is retained locally. No raster downloads failed. The six raw responses totaled 1,405,410 bytes. Per-tile acquisition and checks took 7.72–14.25 seconds, excluding preflight.

| Tile | Frozen partition | Optical observations per cell, before / after | Common support |
| --- | --- | --- | ---: |
| east-94-559 | Train | 4–38 / 6–52 | 4,096/4,096 |
| east-90-562 | Validation | 5–46 / 6–47 | 4,096/4,096 |
| east-91-561 | Test | 27–42 / 33–51 | 4,096/4,096 |
| west-82-563 | Train | 4–19 / 2–23 | 4,096/4,096 |
| west-85-563 | Validation | 12–37 / 22–49 | 4,096/4,096 |
| west-81-557 | Test | 3–42 / 7–46 | 4,096/4,096 |

SAR observation counts were 13 before and 11 after in every cell. All six tiles met the two-observation threshold in each sensor-season, with no cells missing from the common mask. These values describe preprocessing support on selected tile footprints. They do not quantify cloud-free scene availability, district coverage, positional accuracy or reference suitability.

## Verification

- The paired graph produced the exact 14 feature bands and nine aligned diagnostic bands. Local GeoTIFFs round-tripped with the expected affine, band descriptions and explicit −9999 NoData. Count limits, threshold masks, all-band intersection and after-minus-before values were checked numerically. SRTM elevation and slope retained the source conventions of metres and degrees. Returned slope values were checked against 0–90 degrees.
- Frozen 5 km block assignments, the 120 m buffer and global 30 m lattice were checked for every tile. A separate Earth Engine containment query verified that each footprint was contained in exactly its assigned original GAUL district.
- The source receipt records Sentinel-1, Sentinel-2 and matching cloud-probability scene indices and UTC acquisition times. Scene timestamps were checked against both seasonal windows. Raw and derived raster hashes and receipt hashes were verified after reopening the files.
- A limited relative alignment screen matched textured 12 × 12 VV windows over a ±2-cell search in each axis. Across the six tiles, 53 windows met the correlation threshold of 0.75, and each of those had its best match at zero integer-cell shift. The first tile's before/after VV panels also showed a similar curved boundary in the lower right. This compares repeated radar texture on the delivered grid. It supplies no independent landmarks, subpixel registration, optical alignment assessment or absolute positional accuracy.
- The targeted selection, mask, raster and satellite regression tests passed (23 tests). The full suite passed (114 tests).

## Local outputs and reproduction

The frozen roster, rejected extents, original district snapshot, per-tile raw responses, 14-band feature rasters, diagnostic rasters, previews and receipts are local under `outputs/phase6b_multitile/`. Each completed tile directory contains `features.tif`, `diagnostics.tif`, `source.tif`, `exploratory.png`, `sources.json`, `alignment.json`, `structural_checks.json` and `quality.json`. The separate check is recorded in `verified_summary.json`.

Run with the existing environment and authorized Earth Engine project. Choose a new output path for a new run.

```powershell
python -B -m scripts.phase6b_multitile --output outputs/phase6b_multitile_reproduction
python -B -m scripts.phase6b_multitile --output outputs/phase6b_multitile_reproduction --first
python -B -m scripts.phase6b_multitile --output outputs/phase6b_multitile_reproduction --remaining
```

The feature rasters match the model band schema. No matching successful district coverage receipt was used, so the run remains exploratory and does not satisfy supervised raster registration. Independent references and multi-source manifest checks still gate model fitting and held-out evaluation. See the [reference admission protocol](../reference/REAL_REFERENCE_PROTOCOL.md) and [model-readiness audit](phase6a-model-readiness.md).
