# Phase 15C — Unsupervised Indian change screening

The two 32×32 windows use the saved Phase 11C observations on their native 30 m UTM grids and canonical Phase 16A features. Bhubaneswari required one bounded SRTM terrain request. No Sentinel imagery was fetched again. Preserve the two frozen seasonal windows and source receipts.

For each eligible tile cell, take absolute feature departures from the tile median, scaled by 1.4826 × MAD and floored at 0.5 dB for dVV/dVH and 0.015 for dNDVI/dNDTI. Take the larger standardized departure within each sensor and the smaller between sensors. Clip at six and divide by six to obtain a unitless anomaly score. Require a departure of at least 2.5 in both sensors. Eligibility uses all 14 valid features, at least two observations for each sensor/season and slope ≤25°. Require four-connected components of at least four cells (3,600 m²). These fixed descriptive choices are not calibrated or optimized against labels.

| Site | Eligible / total | Score-screen cells | Retained polygons |
| --- | ---: | ---: | ---: |
| Gevra | 1,021 / 1,024 | 32 | 3 |
| Bhubaneswari | 1,024 / 1,024 | 4 | 0 |

Gevra WGS84 centroids (longitude, latitude) are (82.599244, 22.332935), (82.600131, 22.327710), and (82.599393, 22.326850), respectively 3,600, 7,200 and 4,500 m². The first has positive median VV/VH and NDTI changes. The other two have negative median VV/VH, NDVI and NDTI changes. They lie inside the Phase 11C published project-envelope rectangle, which locates the mining project. The Phase 15B composites reuse the feature source and carry no independent temporal attribution. There is no admitted before/after reference pair. Terrain layover, mask bias, seasonal differences and other disturbance remain unresolved. A zero count is specific to the screened window and thresholds.

From the project root with its Python environment active:

```powershell
python -B -m scripts.phase15c_screen outputs/phase16a_gevra/features.tif outputs/phase16a_gevra/receipt.json outputs/phase11c_india_discovery/gevra/tile.tif outputs/phase15c_gevra
```

For Bhubaneswari substitute bhubaneswari for gevra. Use new ignored output directories. The command writes anomaly.tif, receipts, and Phase 14B GeoJSON, CSV and JSON. The `exploratory` data kind uses the `anomaly_score` band and always enters review-only handling with UNKNOWN evidence. It cannot enter operational validation. Date fields use the last included day of each composite window and are not single-scene acquisitions. Review GeoJSON against independently dated actual-work maps or licensed imagery before attributing change.
