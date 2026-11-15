# MineNetCD256 bounded development expansion

This study uses the [publisher RGB benchmark](https://huggingface.co/datasets/HZDR-FWGEL/MineNetCD256) and [CC BY 4.0 source](https://rodare.hzdr.de/record/3251). We added three original binary PNG change patches per site from official train Australia_03 and Austria_01 and official validation Brazil_01 and SouthAfrica_05. Selection took the first qualifying new sites and rows in the bounded shard scan (at least 64 foreground pixels and both classes). It makes the expanded development sample positive-enriched. The original train/validation patches and frozen test results were preserved. The old test sites America_02, Brazil_02, Brazil_03 and Brunei_01 were excluded from the new holdout. Exact decoded epoch hashes and official site memberships were checked. The release lacks coordinates for an independent near-overlap audit.

The expanded train set has 36 patches, 8 sites, 2,359,296 pixels and 1,004,737 positive pixels. Expanded validation has 21 patches, 5 sites, 1,376,256 pixels and 83,851 positive pixels. Validation positives by site: Chile_01 27,049, Germany_05 4,069, Congo_01 0, Brazil_01 34,922, SouthAfrica_05 17,811. On the original sample, the U-Net had 31,714 false positives (9,556 Chile, 14,103 Germany, 8,055 Congo). The expanded set below was identical for every comparison.

Each configuration tried seven fixed thresholds: 0.25, 0.35, 0.50, 0.65, 0.75, 0.90 and 0.95. Select maximum pooled positive-class validation F1, ties by higher threshold then name. Require >0.005 absolute gain over the same family's original 0.50 configuration before fresh test access. Weighted U-Net loss was 0.7 × masked BCE (positive weight 2) + 0.3 × soft Dice loss. This was a three-epoch CPU run with Adam 0.001, seed 42 and batch size one. RF reused signed RGB differences, 100 trees and 100,000 pixels per configuration. Uniform sampling capped each site equally; balanced sampling capped both classes equally within each site and used the existing class weights.

| Configuration | Best validation threshold | Precision | Recall | F1 | IoU | FP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original U-Net | .50 | .3354 | .3290 | .3322 | .1992 | 54,670 |
| Weighted BCE/Dice epoch 1 | .75 | .3313 | .1953 | .2457 | .1401 | 33,061 |
| Weighted BCE/Dice epoch 2 | .65 | .1533 | .4460 | .2281 | .1288 | 206,637 |
| Weighted BCE/Dice epoch 3 | .50 | .0615 | .9967 | .1159 | .0615 | 1,274,836 |
| Original RF | .50 | .0731 | .7937 | .1338 | .0717 | 844,370 |
| Expanded uniform RF | .75 | .0955 | .4762 | .1590 | .0864 | 378,418 |
| Expanded balanced RF | .75 | .1063 | .4887 | .1747 | .0957 | 344,457 |

Only the balanced RF qualified for new test evaluation. On Canada_01 and Canada_02 (10 patches, 655,360 pixels, 50,959 positives all from Canada_01), pooled precision/recall/F1/IoU was .4490/.5004/.4733/.3100. Confusion matrix was [[573104,31297],[25457,25502]]. Canada_01 F1 was .5585. Canada_02 had no positives and a 5.01% false-positive rate. The fresh subset used site and row order without reading labels for selection. These results cannot establish a controlled test-set gain over the original experiment. The weighted U-Net was not tested on these sites. There was no Indian inference.

The initial CPU pass reached the final U-Net checkpoint in about 61 seconds from run-directory creation. Corrected RF label serialization to integer arrays after an RF sampling error, preserving the completed U-Net checkpoints. Validation replay and RF fitting took 79.8 seconds on the CPU. Successful development-cache reads totaled 63,241,817 bytes, plus a 725,602-byte initial training scan. Fresh test consumed 58,261,541 bytes.

```powershell
$root = "outputs/external_minenetcd256"
python -B -m scripts.minenetcd256_improve acquire $root "$root/new_dev"
python -B -m scripts.minenetcd256_improve fit $root "$root/new_fit" --extra "$root/new_dev"
python -B -m scripts.minenetcd256_improve holdout $root "$root/new_test" --extra "$root/new_dev" --fit-dir "$root/new_fit"
```

These commands reproduce the subset from the pinned source. Treat the resulting test sites as used for any future selection. The local JSON stores all thresholds, per-site results, support, source hashes and the selected checkpoint hashes. Next, validate precision and recall on less selectively positive and more geographically varied development mines while keeping all evaluated test sites sealed.
