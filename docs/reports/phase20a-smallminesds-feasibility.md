# Phase 20A — SmallMinesDS feasibility

**Decision: NO-GO for a geographically independent supervised experiment at this stage.** Four TRAIN samples verify that the released imagery and masks share a usable grid. The publisher split does not establish mine or region independence, and the radar encoding differs across the sampled years without an explicit per-band conversion in the GeoTIFF metadata. This review used no TEST raster payloads and fitted no models.

## Release and labels

The [dataset card](https://huggingface.co/datasets/ellaampy/SmallMinesDS) licenses the data under CC BY-SA 4.0 and describes January dry-season observations from 2016 and 2022 in five southwestern Ghana districts. The target is single-date artisanal and small-scale gold mining extent. Background means outside the annotated target, so it does not verify unchanged land or absence of other mining. Annotation lineage and independent verification were not established at patch level. Two dated extent masks are insufficient to certify a change label.

The [revision-pinned ZIP](https://huggingface.co/datasets/ellaampy/SmallMinesDS/resolve/0cb168b807206d9d34c0d1bd3c81097e69bb889b/SmallMinesDS.zip) is 1,650,426,488 bytes. Its year directories contain separate IMAGE and MASK TIFFs. The two [publisher split CSVs](https://huggingface.co/datasets/ellaampy/SmallMinesDS/tree/0cb168b807206d9d34c0d1bd3c81097e69bb889b/data_splits) each list 2,135 patches, reconciling to 4,270 patch-years overall. Their per-row assignments take precedence over the viewer's inferred split labels. The [publisher code](https://github.com/DLR-MF-DAS/SmallMinesDS) provides segmentation examples.

| Year | TRAIN | TRAIN patches with nonzero mask percentage | TEST count from split metadata |
|---|---:|---:|---:|
| 2016 | 1,492 | 688 | 643 |
| 2022 | 1,491 | 980 | 644 |

There is no official validation assignment in these CSVs. Only 1,040 patch IDs are TRAIN in both years. At least 903 IDs occur in TRAIN in one year while absent from the other year's TRAIN list. The two checked repeated IDs have identical grids across years. The official per-year assignments therefore cannot be accepted as a joint geographic split without a full footprint and mine-group check. TEST foreground percentages and raster pixels were excluded from this assessment.

## Bounded TRAIN inspection

ZIP range reads used 2,609,838 response-body bytes under a 12 MiB archive-body cap. The two split CSVs total 152,094 bytes. Eight TIFF members were inspected in memory, comprising two image/mask pairs per year. Two TRAIN IDs shared by both years were picked to exercise both all-background and positive masks. The counts below are diagnostic, not prevalence estimates.

| TRAIN patch ID | Year | Foreground (1) | Background (0) |
|---|---:|---:|---:|
| 0002 | 2016 | 0 | 16,384 |
| 0002 | 2022 | 0 | 16,384 |
| 0068 | 2016 | 3,937 | 12,447 |
| 0068 | 2022 | 5,920 | 10,464 |

Each sampled image and mask matched on dimensions (128 × 128), affine and CRS (EPSG:32630, north-up 10 m grid). The two repeated IDs also matched their own 2016 and 2022 georeferencing exactly. This verifies sampled grid pairing. Dataset-wide pairing and independent registration were not verified. Images were 13-band float32 with NoData −9999. Masks were uint8 with NoData 255, with only 0 and 1 observed. The declared band order is B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12, VV, VH, then Copernicus DEM. The output grid includes resampled optical bands.

The sampled TIFFs had unit scales, zero offsets and no band descriptions. Stored optical values were integer-like (1,013–7,940 across the four images). Sampled VV/VH values were negative in 2016 (−21.42 to −2.71 collectively) and positive fractions in 2022 (0.0084 to 0.599), consistent with different encodings. Confirm physical units, offsets and any log conversion with publisher metadata before comparing or pooling years. Do not assume common radar scaling or infer native resolution from the 10 m output grid.

## Requirements to reopen

Obtain a publisher patch-to-footprint and mine/district index and a sensor/year scaling and label-lineage statement. Use the footprint index to group repeated IDs, overlaps and adjacent patches from the same mine complex under one geographic ID. Freeze nonadjacent district or mine-complex groups for training, validation and testing, with buffers across split boundaries. Verify both classes in each development split before freezing a pilot, and leave TEST pixels sealed. Four TRAIN samples cannot establish release-wide groups or alignment.

If the gates pass, use one verified year for an extent experiment with matched valid pixels for optical-only (ten bands), SAR-only (VV/VH) and fusion (twelve bands). Omit DEM in all three arms. Reuse the 100-tree RF configuration on capped TRAIN pixels, with a small single-date U-Net as the segmentation comparison. The paired Siamese change runner and existing checkpoints have different input and target contracts. Cap all fitting at 30 CPU minutes, use TRAIN-only preprocessing, select settings on validation only, and report pooled and per-group precision, recall, IoU, foreground support and false-positive rate. This is a conditional design. No roster, run or benchmark result was frozen.

This benchmark decision does not alter the Indian supervised NO-GO or existing mining and river results.
