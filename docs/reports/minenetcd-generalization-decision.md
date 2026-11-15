# MineNetCD generalization and training decision

**NO-GO for another fit on the current sample.** The reproduction and diagnostics below use frozen validation results only. No previously accessed test-site assets, results or labels were needed in this audit. The Indian 14-band supervised workflow remains NO-GO.

## Geometry checked

The local development and validation manifests contain site, shard, row group, row index and asset hashes. They lack patch footprints, offsets and CRS. The [publisher's cropped schema](https://huggingface.co/datasets/HZDR-FWGEL/MineNetCD256/blob/73c771bda9e5c5a1aed755077b1e61596e613161/README.md) lists paired images, label and domain. A 125,993-byte range read of only the domain and image/mask path columns across the pinned validation shard showed numbered image and mask names. No crop window or map transform was present in the schema. A bounded read of the [original RODARE ZIP](https://rodare.hzdr.de/record/3251) confirmed the site JPEG and PNG layout. Its summary20240127.csv contains whole-site extent fields (left/right/top/bottom), dates T1/T2 and task names. The metadata read consumed 30,693 bytes after a 26,477-byte initial index probe. The site bounds offer regional context. The CSV and published preparation method do not provide a verified patch-ID-to-crop-window mapping or a patch CRS/transform. No image payloads were downloaded.

If an author crosswalk becomes available, require source image IDs, per-patch offsets or polygons, CRS and an independently checked mapping to the published rows. Freeze a label-blind validation roster and take at most four nonoverlapping footprints per official validation mine. Use a prespecified positive buffer justified by verified source resolution. If original imagery alignment and dimensions can be verified, freshly cut disjoint source windows using native image coordinates, leaving a 256-source-pixel gap, and label this a pixel-space evaluation unless a geographic transform is established. Keep training, validation and unused test sites disjoint. Do not infer spacing from numeric filenames.

## Training and matched validation findings

The U-Net saw 30 patches from six sites (five America-series sites and Australia_01), with 947,631/1,966,080 foreground pixels (48.20%). RF used 36 candidate patches across eight sites after adding Australia_03 and Austria_01. They contained 1,004,737/2,359,296 foreground pixels (42.59%), and the fitted sampler selected 50,000 positives and 50,000 negatives. The label-blind frozen validation sample has 7.91% foreground and six sites with no positive pixels. The prevalence difference and geographically narrow training sample can contribute to unstable operating points. They do not causally explain individual false positives. The U-Net's narrow score range in the existing threshold sweep is consistent with limited discrimination and poor calibration. Signed RGB differences alone give RF no spatial context for separating mining from other appearance changes.

Both baselines below used the same 40 validation patches and original frozen thresholds (.50 U-Net and .75 RF). See the [prior report](minenetcd-representative-validation.md) for precision, F1, IoU, calibration and per-site counts.

| Mine | U-Net recall / FPR | RF recall / FPR |
| --- | ---: | ---: |
| Brazil_01 | — / 8.57% | — / 33.67% |
| Chile_01 | 0.00% / 2.32% | 44.38% / 12.45% |
| Congo_01 | 13.55% / 3.45% | 4.18% / 13.97% |
| Germany_05 | 6.26% / 2.91% | 27.29% / 35.25% |
| Russia_08 | — / 2.87% | — / 6.96% |
| Serbia_01 | — / 2.89% | — / 6.80% |
| SouthAfrica_05 | — / 4.34% | — / 12.42% |
| SouthAfrica_08 | 6.21% / 2.82% | 29.24% / 54.93% |
| SouthAfrica_11 | — / 6.44% | — / 0.52% |
| Tanzania_01 | — / 2.95% | — / 10.78% |

The U-Net therefore misses most positives even on its strongest positive-support site. The RF catches more foreground overall, with much higher and more variable false alarm rates. No change was selected and no new fit was justified without an evaluation that can distinguish sample clustering from improved cross-site transfer.

## Conditional next experiment

Use one low-cost change after recovering geometry and freezing a more geographically varied validation sample. Add a capped set of equal-budget, label-blind windows from geographically distinct official TRAIN mines, retaining unchanged mine surfaces and no-change patches. Keep the U-Net architecture, loss and schedule fixed so the sampling change is isolated. Compare both checkpoints on exactly the same spaced validation pixels. Before scoring, agree on an application-specific maximum per-site false-positive rate and minimum median recall on positive-support sites. Select threshold and configuration on validation only, minimizing worst-site FPR among models meeting the recall floor. If none qualify, retain the research-only status. No threshold alteration or previously accessed test reuse.
