# Day 1 — Real multi-sensor change analysis

## Analysis specification

Use the six frozen Phase 6B tiles and no additional observations. Analyze the signed after-minus-before dVV, dVH, dNDVI and dNDTI over the intersection of the 14 feature bands and the stored common-valid mask. Report per-band missingness and the complete-case denominator against the full footprint. Compare November 2023–March 2024 with November 2024–March 2025. Treat the results as descriptive for these 30 m cells, with each tile assigned to its existing district and split.

For each tile, district, split and the combined sample, report counts, mean, sample standard deviation, median, linear 5th/25th/75th/95th percentiles, extrema and negative/zero/positive counts. For each of the four SAR–optical pairs, report Pearson correlation, Pearson after subtracting the respective tile means, and Spearman rank correlation with average ties. Report the four sign quadrants, the number excluded from sign comparison because either value equals exactly zero, same-sign fraction and its difference from the expected fraction calculated from the two marginal sign proportions. Same sign describes the direction of two different measured quantities. It has no physical equivalence or classification threshold attached.

For each signed change and its absolute magnitude, report descriptive Pearson correlations with elevation, slope, and optical observation counts in each season, their minimum and their after-minus-before difference. Include SAR counts as a constant-variable check. Report correlations on raw and tile-centred values. Return undefined correlations for constant or insufficient data. Centre within each tile using the cells in the relevant group. No significance tests or pixel-level confidence intervals are used. Spatial dependence, unequal observation quality and tile selection limit interpretation. No causal or predictive comparison is implied.

## Results

All six original feature and diagnostic raster pairs passed hash, grid, band-order, NoData, mask and difference-arithmetic checks. The sample contains **24,576 of 24,576 common-valid cells**, with zero exclusions for any of the 14 feature bands or the complete-case footprint. Each tile contributes 4,096 cells, each district 12,288 and each split 8,192. These are sampled 30 m grid cells, with spatial dependence within tiles. The six footprints cover about 22.12 km².

| Change | Mean | Sample SD | Median | 5th–95th percentile | Negative / zero / positive |
| --- | ---: | ---: | ---: | --- | --- |
| dVV (dB) | −0.626 | 1.136 | −0.574 | −2.556 to +1.131 | 17,535 / 0 / 7,041 |
| dVH (dB) | −0.805 | 1.288 | −0.707 | −3.062 to +1.094 | 17,974 / 0 / 6,602 |
| dNDVI | −0.0295 | 0.0626 | −0.0196 | −0.1490 to +0.0497 | 17,027 / 0 / 7,549 |
| dNDTI | +0.0248 | 0.0379 | +0.0226 | −0.0291 to +0.0862 | 5,385 / 2 / 19,189 |

VV and VH medians were negative in all six tiles. NDTI medians were positive in all six. NDVI medians were negative in five, with east-94-559 close to zero at +0.0005. The East sample had larger median SAR decreases, while the West sample had a larger median NDVI decrease. This is a contrast between three sampled tiles per district.

| Group | Cells | Median dVV (dB) | Median dVH (dB) | Median dNDVI | Median dNDTI |
| --- | ---: | ---: | ---: | ---: | ---: |
| East Jaintia Hills | 12,288 | −0.7591 | −0.9875 | −0.0088 | +0.0216 |
| West Jaintia Hills | 12,288 | −0.3967 | −0.4507 | −0.0243 | +0.0234 |
| Train | 8,192 | −0.6390 | −0.8135 | −0.0230 | +0.0269 |
| Validation | 8,192 | −0.6297 | −0.8462 | −0.0120 | +0.0111 |
| Test | 8,192 | −0.4657 | −0.4904 | −0.0221 | +0.0321 |
| east-94-559 | 4,096 | −0.7521 | −1.0042 | +0.0005 | +0.0198 |
| east-90-562 | 4,096 | −0.6886 | −0.9601 | −0.0028 | +0.0135 |
| east-91-561 | 4,096 | −0.8236 | −0.9929 | −0.0329 | +0.0345 |
| west-82-563 | 4,096 | −0.5142 | −0.6448 | −0.0424 | +0.0320 |
| west-85-563 | 4,096 | −0.5702 | −0.7190 | −0.0195 | +0.0086 |
| west-81-557 | 4,096 | −0.1648 | −0.1018 | −0.0195 | +0.0303 |

### SAR–optical agreement

| Pair | Pearson | Tile-centred Pearson | Spearman | Same sign | Same-sign excess (percentage points) | Sign denominator |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dVV–dNDVI | +0.210 | +0.210 | +0.173 | 60.85% | +2.61 | 24,576 |
| dVH–dNDVI | +0.281 | +0.292 | +0.214 | 60.47% | +1.55 | 24,576 |
| dVV–dNDTI | −0.110 | −0.116 | −0.094 | 36.27% | −1.74 | 24,574 |
| dVH–dNDTI | −0.111 | −0.126 | −0.089 | 35.90% | −1.10 | 24,574 |

Correlation denominators are 24,576 for all four pairs. The two exact-zero dNDTI cells were excluded only from the sign comparisons. The roughly 60% SAR–NDVI sign agreement exceeds the marginal-sign benchmark by just 1.55–2.61 points. Most SAR–NDTI opposite-sign cells combined decreasing radar backscatter with increasing NDTI. The dVH–dNDVI Pearson correlation varied from +0.093 to +0.445 across tiles. These patterns describe co-variation between features with different measurement physics and units.

### Terrain and observation support

SAR counts were constant at 13 before and 11 after per cell, so their correlations are undefined. Optical counts ranged from **3–46 before** and **2–52 after** across tiles. All cells passed the existing two-observation minimum. A count measures available observations after preprocessing and cannot rule out residual atmospheric or seasonal differences.

| Change | Signed vs slope, pooled / centred | Absolute vs slope, pooled / centred | Signed vs minimum optical count, pooled / centred |
| --- | --- | --- | --- |
| dVV | +0.164 / +0.117 | −0.164 / −0.112 | −0.048 / −0.109 |
| dVH | +0.189 / +0.133 | −0.176 / −0.127 | −0.044 / −0.135 |
| dNDVI | +0.170 / +0.152 | −0.196 / −0.121 | +0.034 / −0.150 |
| dNDTI | −0.029 / −0.069 | +0.020 / −0.008 | +0.002 / +0.063 |

The dNDVI–minimum optical count association changes sign after tile centring. The signed dVH–optical count difference association shrinks from −0.147 to approximately zero. The absolute dNDVI–elevation association declines from +0.179 to +0.089. These sensitivities show why pooled relationships and within-tile relationships are both reported. The comparisons do not control for terrain, observation count, vegetation, moisture, or other confounding.

## Supervisor conclusion and reproduction

These are quantitative seasonal changes over six selected, spatially dependent footprints. The empirical SAR–NDVI correlations are positive and vary by tile. Sign agreement adds little above the marginal benchmark, and the SAR–NDTI pairs differ in direction. No reference labels, mine boundaries or causal attribution were used. The frozen split summaries describe coverage of the sample. Any future evaluation should keep test labels and model selection separate from this descriptive analysis. The Phase 6B rasters remain exploratory under the [reference readiness audit](phase6d-reference-readiness.md).

The local output includes distributions by tile, district and split, the four sign quadrants and correlations, terrain/count associations, per-band missingness and observation-count summaries. The maps show all four signed changes with north up and common colour scales within each band. Colourbar extensions denote display clipping only. Histograms use 60 equal-width bins per band spanning the full observed range, shared by the two districts. Scatter density uses all paired cells in logarithmically coloured hexagons. No spatial resampling or change classification was applied.

Run the offline analysis from the checkout root into a new directory.

```powershell
python -B -m scripts.phase7_real_change --output outputs/phase7_real_change_reproduction
```

The targeted suite passed (13 tests). Two offline runs produced identical output hashes. The delivered results are under `outputs/phase7_real_change_analysis/`. The local provenance receipt records the exact scene indices and UTC acquisition times inherited from Phase 6B, original hashes, script and methods hashes, software versions, and output hashes. The original [Phase 6B acquisition report](phase6b-multitile-acquisition.md) documents the masks, settings and footprint-selection rationale.
