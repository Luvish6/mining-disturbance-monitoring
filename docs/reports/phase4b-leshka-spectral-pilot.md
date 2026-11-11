# Phase 4B — Myntdu–Leshka fixed-footprint spectral pilot

This pilot reuses the [Phase 4A station window and screening rules](phase4a-river-feasibility.md) at CPCB 3379 and the same clipped HydroSHEDS reach GOID 4100220. The reconstructed corridor matches its earlier 549-cell footprint and 26.78 m station-to-line offset. The 720 m window uses EPSG:32646. The same Sentinel-2 harmonized SR, cloud-probability join, SCL, edge masks and existing seasonal windows were used. No mining feature or reference data enters this analysis.

## Waterbody and matching

The broad branching waterbody in the Phase 4A images is consistent with the Stage I reservoir/backwater near the Myntdu, Lamu and Amshariang confluence. The operator documents a dam with live storage even though the project is described as run-of-river. Its business plan places the dam roughly 0.6 km from the station, outside the bounded window. The pilot treats the sampled water as potentially regulated. No independent reservoir boundary, stage or release record was available. [Dam rehabilitation report](https://meecl.nic.in/wp-content/uploads/2020/12/ESDDReportMyntduLeshkaUpdated_14_10_2020_compressed.pdf) · [MePGCL business plan](https://www.mserc.gov.in/orders/2024-27/MePGCL_BusinessPlan_2024-27.pdf)

All 162 earlier joined granules remain in the observation table with dates, quality diagnostics and exclusion status. The pilot re-fetched the granules with interior support. For duplicate UTC dates it kept the largest screened interior, with a deterministic scene-ID tie break. Matching used dates only. It maximized nonreused same-month pairs within 15 days of the same day-of-month, then minimized total day gaps. The primary analysis required at least two matched months and 25 connected common 10 m cells as an exploratory spatial-support floor. These criteria were chosen for this pilot and carry no implication of statistical independence.

The fixed footprint is the largest four-connected component passing the Phase 4A interior screen and a positive red-plus-green denominator on every matched observation. Sensitivities use subsets of the same footprint surviving NDWI >0.1, a 30 m bank-clearance proxy, or historical JRC occurrence ≥50%. The JRC layer is 30 m historical context sampled on the 10 m grid. Water masks and their intersection show stability under these sampled conditions only. No annual persistence or pure-water certainty is inferred.

B3/B4 are native 10 m Sentinel-2 bands. For SCL and B11 the script checks the actual scene projection and alignment at 20 m and checks that each source cell replicates across its four 10 m display samples. Native support counts only complete 20 m footprints contained in the common mask. B11 is checked for spatial coverage, with no SWIR spectral inference. [Sentinel-2 L2A product](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)

## Live result

The interior screen supplied 11 before and six after dates. Five pairs (ten distinct dates) matched across **November, December and February**. The window has uneven coverage. January and March supplied before-season interior dates only, and one February after date remained unmatched. The full 303-day ledger retains missing dates.

| Month | Eligible before / after dates | Matched pairs |
| --- | ---: | ---: |
| November | 2 / 1 | 1 |
| December | 4 / 3 | 3 |
| January | 3 / 0 | 0 |
| February | 1 / 2 | 1 |
| March | 1 / 0 | 0 |

Only **12 contiguous 10 m cells** (1,200 m² of grid area) passed the fixed support test. The stricter NDWI and historical occurrence checks retained all 12. The 30 m clearance screen retained zero. No whole native 20 m SCL or B11 footprint fell entirely inside the fixed intersection. The map shows this small footprint within the broader waterbody. Leave-one-pair-out support was 12, 94, 12, 78, 12 cells in pair order. This checks sensitivity to date selection and is not a basis for dropping a pair to obtain a result.

The pilot floor of 25 fixed cells was not met. The ten matched dates retain B4, B3 and normalized red–green values in the local table for diagnostic inspection only. No descriptive spectral time-series figure or before/after contrast was produced. The site has open-water potential, but this sampled footprint is insufficient for the proposed comparison.

No matched date lacked rainfall context. Four pairs had zero preceding 1- and 3-day station-cell totals on both dates. The February pair had approximately 3.30 mm after at one day and 4.89 mm after at three days, versus zero before. Only two of five pairs were within 5 mm of each other at seven days, both with zero totals. The other pairs differed by about 6.37 to 15.08 mm. This exploratory rainfall screen further reduces comparable support and does not control rainfall effects.

## Interpretation

The dated statistics use L2A land surface reflectance, scaled by 10,000, and the median of per-pixel (B4 − B3)/(B4 + B3). They are descriptive relative spectral indicators. They are not calibrated NTU, suspended-sediment concentration, acidity, contamination or evidence of a mining impact. Water-specific atmospheric correction, adjacency, glint, bottom effects, reservoir operations, discharge and synchronous field observations remain unresolved. Do not extrapolate to the full Myntdu or Lukha rivers. See the [field-calibrated Sentinel-2 river study](https://esurf.copernicus.org/articles/11/881/2023/).

The CHIRPS daily series is the native coarse station cell. The preceding 1, 3 and 7 complete UTC dates exclude the acquisition day, and any missing day leaves that sum blank. The operator's reported contributing area does not supply validated outlet geometry or a contributing-area polygon for this station. These are point-cell rainfall estimates, with no adjustment for catchment gradients, gauge error, discharge or reservoir operations. [CHIRPS daily](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)

## Reproduction

Run from the checkout root using the existing virtual environment and Earth Engine project, with the local Phase 4A receipt present. The output directory must be new.

```powershell
python -B scripts/phase4b_leshka.py --output outputs/phase4b_leshka_spectral_pilot
```

The local output includes the complete dated diagnostics table, fixed-support mask and preview, provenance receipt, and spectral figures and differences where the screen supports them. Existing mining workflows, results, reference admission and spatial partitions were preserved.
