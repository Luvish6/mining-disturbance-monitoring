# Phase 18B — Satellite preview integrity

The Explorer's twelve seasonal PNGs now have deterministic provenance manifests built offline from the frozen Phase 11C GeoTIFFs. The original exporter and offline builder share the existing rendering logic, with B8/B4/B3 false colour at 0–0.35 reflectance, VV grayscale at −25 to 0 dB and VH grayscale at −32 to −5 dB. Linear normalization clips to the display range, and transparent pixels follow the source NoData rule. Native rows and columns are retained without resampling.

Each manifest identifies the site, source raster, SHA-256, preparation receipt and inventory hashes, CRS, affine, dimensions, bounds and NoData. Each PNG entry identifies the layer, season, date window, relevant sensor's source scene IDs and exact UTC timestamps, render settings, band names and PNG SHA-256. The adapter renders independently from the verified raster, compares the manifest and checks the PNG hash and decoded RGBA pixels before publishing. It copies the verified bytes and carries the manifest digest in the site snapshot. A rebuild withdraws prior site snapshots before validation, so an invalid bundle cannot keep a stale source snapshot visible. Rebuild the distributable assets after regenerating these local files.

## Real-data verification

| Site | Previews | Decoded pixel matches to archived PNGs | Encoded byte matches | New manifest SHA-256 |
| --- | ---: | ---: | ---: | --- |
| Gevra | 6 | 6 | 6 | `c1e592e3102922b2f0c62b7a596ac81d1cc9a82be94560623d448241d6838ca4` |
| Bhubaneswari | 6 | 6 | 6 | `7ecb134427621de4f22e25f8329ef5a327553da3c6c87379ce1cca907cede09e` |

All twelve built Explorer PNGs matched the verified bundles byte-for-byte. No source rasters, legacy previews, scientific results, geometry, model checkpoints, alerts or river calculations were changed. The two site snapshots still carry UNKNOWN evidence and zero operational alerts. Indian supervised training remains NO-GO and mining–river attribution remains unverified.

From the repository root, with its Python and Node environments:

```powershell
python -B -m scripts.satellite_previews
python -B -m scripts.prototype_data
npm --prefix frontend run build
```

Keep the bundles under ignored `outputs/phase18b_previews/` and the populated production build local. Use the current Python environment for byte-identical PNG reproduction. Encoder differences can require regenerating both the bundle and snapshot from the same frozen raster. No preview-integrity blocker remains for the verified sites. Fifteen targeted tests passed, covering deterministic output, correct pixels, wrong-site and swapped-season files, pixel alterations, CRS/affine mismatch, missing inputs and stale snapshot handling. The React production build and publication audit passed.
