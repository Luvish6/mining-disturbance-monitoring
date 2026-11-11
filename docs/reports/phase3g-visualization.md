# Phase 3G — Real Earth Engine satellite visualization

The local viewer shows a 960 m square around the previously verified Phase 2 smoke location (92.35° E, 25.35° N). The tile is inside the verified East/West Jaintia Hills study area. This is a demonstration tile, with no claim of statistical representativeness.

The two seasonal windows remain [2023-11-01, 2024-04-01) and [2024-11-01, 2025-04-01). The workflow uses existing Sentinel-1 IW VV/VH preprocessing on descending relative orbit 77, with 20 m linear-power smoothing before seasonal median and conversion to dB. Sentinel-2 harmonized surface reflectance uses the existing cloud-probability join, probability below 40, scene cloud at most 80%, SCL 4/5/6, and existing edge, source and joint index masks. Seasonal layers require at least two valid observations. The display composite uses median B8/B4/B3 reflectance under that same per-image index mask. It is false colour. Index layers use medians of per-observation NDVI and NDTI, and changes are after minus before. Common support also includes the existing SRTM terrain channels.

The standalone viewer has 23 layers, season/date information, display legends and magnification. The local GeoTIFF contains 27 bands on one 32 × 32 north-up EPSG:32646 grid at 30 m. Local receipts record source collections, scene IDs and acquisition times in UTC epoch milliseconds, nominal source spacings, settings, output extent, band definitions, per-season counts and mask totals. The source spacing and output grid are distinct. NoData is -9999 and renders transparent. The graph band order, raster transform, data round-trip, count thresholds, and after-minus-before values were checked.

The viewer shows continuous exploratory changes. No disturbance threshold, reference classes, classifier or performance metrics are included. Cloud, shadow, terrain, seasonal vegetation and moisture can contribute to the signal. Existing reference and spatial gates stay unchanged. See the [real-reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md).

All 1,024 grid cells met common support in this tile. Sentinel-1 counts were 13 before and 11 after per cell. Sentinel-2 counts ranged from 19 to 36 before and 25 to 44 after. These counts describe preprocessing support for this tile. They provide neither a district coverage result nor independent reference evidence.

## Reproduce locally

Use the existing Phase 3 environment, Earth Engine configuration and authorized account from the checkout root. Choose a new output directory if rerunning. The script makes one small synchronous GeoTIFF download using the [Earth Engine download API](https://developers.google.com/earth-engine/apidocs/ee-image-getdownloadurl). It submits no Drive or asset export task.

```powershell
python -B scripts/phase3g_visualization.py --output outputs/phase3g_visualization
```

Open the generated index.html locally. The viewer needs no network connection after generation. All derived image data and receipts remain in the ignored output directory.
