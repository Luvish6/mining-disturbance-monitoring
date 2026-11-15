# External MineNetCD256 held-out RGB experiment

This is an external RGB change benchmark. MineNetCD documents expert interpretation of bitemporal imagery and official site-disjoint splits. The [RODARE release](https://rodare.hzdr.de/record/3251) is CC BY 4.0. The cropped [publisher dataset](https://huggingface.co/datasets/HZDR-FWGEL/MineNetCD256) was range-read at the immutable revision. Original PNG masks were validated and ambiguous values excluded. India and the 14-band Sentinel workflow are separate.

Both models were freshly fitted using 30 frozen training patches from six sites. The CPU Siamese U-Net used seed 42, five epochs, Adam at 0.001, FP32 and batch size one. Epoch three was selected using loss on 15 patches from three validation sites. The RF used 100 trees and signed RGB differences with the existing per-mine and per-class capped sampler. Its 0.50 decision threshold was fixed, as was the U-Net threshold. Model hashes were frozen before the test selection.

The official 60/10/30 site rosters were checked against the pinned-cache rosters. Previously evaluated America_02 was excluded. Source-domain metadata fixed five patches from each of Brazil_02, Brazil_03 and Brunei_01 without consulting test labels. Decoded RGB hash checks found no exact cross-partition epoch duplication in the selected data. The cropped release lacks coordinates needed to independently measure physical separation or near-duplicate overlap. Nearby patches can be correlated.

| Model | Positive precision | Recall | F1 | IoU | Confusion matrix, TN/FP then FN/TP |
| --- | ---: | ---: | ---: | ---: | --- |
| RF | .0143 | .8282 | .0282 | .0143 | 505779/469023 then 1415/6823 |
| Siamese U-Net | .1967 | .5747 | .2931 | .1717 | 955473/19329 then 3504/4734 |

Identical evaluation covered 983,040 pixels, with 8,238 changed pixels, all from Brunei_01. Results characterize this bounded sample. These metrics are not a full benchmark or Indian validation.

An unlabeled diagnostic compared signed R/G channel marginal distances to cached Gevra and Bhubaneswari Sentinel-2 red/green changes. Separate median/MAD scaling still left residual differences between sites. Raw distances use input numeric scale; normalized distances use robust units, so changes between those columns do not quantify transfer improvement. This two-channel check cannot resolve the RGB/reflectance/SAR channel mismatch and did not execute either model on Indian imagery.

Reproduce from the project root with the existing environment and frozen local development caches:

```powershell
python -B -m scripts.minenetcd256_heldout outputs/external_minenetcd256 outputs/external_minenetcd256/new_heldout_run
```

For an interrupted evaluation with frozen artifacts add `--resume` to the same command. The original request reset during a Parquet read. The resumed pass used the same sites, selection and models with smaller byte ranges. Reported range bytes are for the completed attempt. Split manifests, PNG-derived test caches, per-mine metrics and checkpoints remain local. For the unlabeled diagnostic call `domain_probe` with the saved Siamese RGB cache and Phase 11C cache paths.
