# Phase 3D — Resourcesat-2A provenance reconciliation

Review date 2026-11-11. Metadata was read directly from each original ZIP. SHA-256 was recomputed and matched the previous inspection receipts. The March corner comparison was recomputed from the archived B2 raster without rerunning image-quality diagnostics.

| Field | Before | After |
| --- | --- | --- |
| Date of pass | 2024-03-17 | 2024-11-12 |
| Scene (imaging orbit / path / row, subscene) | 037752 / 111 / 054, A | 041162 / 111 / 054, A |
| OTSProductID and archive stem | RAF17MAR2024037752011100054SSANSTUC00GTDA | RAF12NOV2024041162011100054SSANSTUC00GTDA |
| ProductID in primary .meta and ACC_REP | 2437198211 | 2410398791 |
| ProductID in BAND_META | 25307537831 | 2630507321 |
| Archive SHA-256 | 597b9ea8e442c56eb92cfab5b5c4407150d4bbbfaed70248db935005f21b16e9 | 01e9892ee7ac98ee1c424f313c9aa60485377f75e102735c89d98d50426a7b82 |
| Primary generation timestamp, timezone unspecified | 18-MAR-2024 05:16:32 | 12-NOV-2024 14:57:57 |
| Archived raster dimensions, rows × columns | 16,427 × 18,146 | 16,429 × 18,140 |

Both archives identify IRS-R2A / L4FX, bands B2 green, B3 red and B4 near infrared, 10-bit DN in uint16, GEOREF/STD, and DEM geometric correction with cubic-convolution resampling by the provider. Primary metadata uses product code STUC00GTD and BAND_META uses STUC00GT. Source rasters are north-up 5 m, pixel-is-point, WGS 84 / UTM zone 46N with EPSG:32646 authority in embedded WKT. The custom ellipsoid serialization and its submillimetre crop normalization are documented in the [interpretability assessment](phase3c-interpretability-assessment.md). Reported sensor sampling is 5.8 m. Neither archive declares TIFF NoData. All-valid TIFF masks do not distinguish zero-filled margins. No surface reflectance calibration is established. The [ISRO mission description](https://www.isro.gov.in/RESOURCESAT_2A.html) and [NRSC LISS-IV handbook](https://bhoonidhi.nrsc.gov.in/bhoonidhi_resources/help/docs/R2_data_user_handbook.pdf) corroborate sensor and band context.

## March catalog footprint

Both catalog polygons are user transcriptions of two previously displayed screenshots. The original screenshots and authenticated catalog records were unavailable. The comparison below uses WGS84 geodesic distance between the transcribed vertices and matching archived raster corner pixel centres in TL, TR, BR, BL order.

| Corner | Raster centre (lon, lat) | First transcription (lon, lat) | First offset | Second transcription (lon, lat) | Second offset |
| --- | --- | --- | ---: | --- | ---: |
| TL | 91.56079350, 25.76809185 | 91.4113, 25.171029 | 67.830 km | 91.5608, 25.768092 | 0.65 m |
| TR | 92.46545290, 25.77422685 | 92.3118, 25.177956 | 67.838 km | 92.4655, 25.774227 | 4.72 m |
| BR | 92.46871114, 25.03257599 | 92.3159, 24.436583 | 67.803 km | 92.4687, 25.032576 | 1.12 m |
| BL | 91.56956280, 25.02664174 | 91.4207, 24.429886 | 67.796 km | 91.5696, 25.026642 | 3.76 m |

The first transcription excludes the KORPET and Sumon anchors and is inconsistent with this archive. The second agrees with the downloaded product rectangle at its reported coordinate precision and includes both anchors. The rectangular product envelope, slanted image swath and usable ground pixels describe different extents. The earlier [pair review](bhoonidhi-pair-review.md) documents the swath and actual signal checks. The discrepancy's cause remains unknown.

## Questions for NRSC/Bhoonidhi

1. Provide authoritative item IDs and version lineage for both OTS products, reconcile the ProductID and ProdCode fields, and identify which metadata keys are intended for citation.
2. Provide the original March catalog item record and any distinct rectangle, image swath and validity geometry, with corner conventions. Confirm what product or field each transcribed coordinate set represents if it can be identified.
3. Confirm product processing, geometric model, actual CRS parameters, zero-fill convention, accuracy-report scope and any independently assessed positional uncertainty at these locations. Internal tie points alone cannot satisfy the reference positional rule.
4. Provide applicable radiometric metadata and calibration guidance if quantitative radiometry is later needed, and confirm the acquisition-specific quality and permitted research/redistribution terms.

The [Bhoonidhi portal](https://bhoonidhi.nrsc.gov.in/bhoonidhi/home.html) and [provider FAQ](https://bhoonidhi.nrsc.gov.in/bhoonidhi/htmls/FAQ2.html) identify catalog and data-use channels. Archive-specific responses remain pending.
