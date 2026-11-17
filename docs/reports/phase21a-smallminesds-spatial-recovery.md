# Phase 21A — SmallMinesDS spatial recovery

**NO-GO for independent TEST evaluation and training.** Header recovery is technically feasible, but the bounded probe found publisher TRAIN/TEST buffer conflicts. A complete buffered split and grouped support remain uncertified. The optical-only design is specified below. SAR and fusion are blocked independently by the delivered-unit discrepancy.

## Header-only evidence

The revision-pinned ZIP central directory identified 2,135 2022 image TIFFs, all individually deflated. ZIP directory and prefix requests consumed 1,075,619 response-body bytes under a 2 MiB cap, plus 76,352 bytes for the publisher split CSV. Coverage was eight of 2,135 footprints (two of 1,491 TRAIN and six of 644 TEST). TEST IDs were the first six lexical IDs in the publisher TEST membership list. Only image metadata was opened. No raster band or mask was read. Compressed prefixes can include data beyond the TIFF tags, so the byte limit governs transport and the metadata-only reader governs inspection. Partial reads do not certify member CRC or raster integrity. [Pinned dataset release](https://huggingface.co/datasets/ellaampy/SmallMinesDS/tree/0cb168b807206d9d34c0d1bd3c81097e69bb889b)

TEST IDs 0001 and 0007 each had zero edge distance to at least one sampled TRAIN footprint, which establishes contact or overlap. TEST 0017 was exactly 1,280 m from its nearest sampled TRAIN footprint. The other three nearest sampled distances were 3,840 m, approximately 1,810 m and 4,048 m. These are distances to the two sampled TRAIN footprints only. The existing TRAIN samples have verified image/mask grids. Full footprint enumeration and post-quarantine class support were not established.

Reproduce the metadata probe from the repository root:

```powershell
python -B -m scripts.smallminesds_spatial 0002 0068 0001 0007 0011 0017 0018 0020
```

## Geographic protocol

The split function requires complete verified EPSG:32630 bounds and disjoint publisher rosters. Merge footprints linked by an edge distance of 1,280 m or less, including overlaps and touches. Transitive grouping may join many fishnet cells and is deliberately conservative. Quarantine all publisher TRAIN patches in groups containing any publisher TEST patch. Keep TEST membership unchanged. Allocate remaining groups by SHA-256 over sorted patch IDs and seed 42, assigning validation when the first hash byte is below 51. Fail on incomplete footprint coverage or an empty partition. These are reconstructed spatial groups, with mine-complex identity unverified. Before fitting, certify viable independent groups and both classes across geographically separate development groups. The current partial roster cannot be frozen as a split.

## Radar and conditional optical pilot

The paper describes Planetary Computer Sentinel-1 RTC input, a circular 3 × 3 mean filter and conversion to dB. The public code tree contains model training scripts and no identified generator for the released SAR derivatives. The source collection identifies RTC imagery derived from Sentinel-1 GRD. It does not identify which acquisitions or export transformation produced the released 2022 pixels. The positive fractional values in both sampled 2022 images conflict with the stated conversion and do not independently establish linear power. No real SAR conversion was applied. [Publisher paper](https://elib.dlr.de/221107/) · [Publisher code](https://github.com/DLR-MF-DAS/SmallMinesDS) · [RTC catalog](https://planetarycomputer.microsoft.com/dataset/group/sentinel-1)

Conditional 2022 optical-only pilot uses B02/B03/B04/B05/B06/B07/B08/B8A/B11/B12 without DEM, a 100-tree RF and a small single-date U-Net. Fit per-band mean and standard deviation on finite common-valid TRAIN cells only, with unit divisor for zero variance. Keep mask NoData excluded. Freeze seed 42 and a combined 30-minute CPU wall budget. Select thresholds on validation from 0.25, 0.50 and 0.75 by highest pooled IoU, breaking ties in favor of the higher threshold. Evaluate the frozen pair once on publisher TEST only if independence is certified. Report pooled and per-group confusion matrices, precision, recall, IoU, false-positive rate and class support, including undefined denominators. No assignment manifest or scientific result was frozen. The smallest remaining input is a complete authenticated footprint roster to apply quarantine and certify development support. Indian supervised training remains NO-GO.
