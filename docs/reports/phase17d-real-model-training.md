# Phase 17D — Real MineNetCD256 RGB model training

Both models fitted offline after the Phase 17C primary manifest, acquisition receipt and all 320 patch hashes passed read-back. The cache contained 240 TRAIN patches from 20 mines and 80 VALIDATION patches from ten disjoint official mines. The source RGB bytes and original PNG provenance hashes are bound to the frozen acquisition receipt. The loader independently validates decoded arrays and masks, duplicate pairs and cross-split identical RGB observations. No official TEST data were read.

## Fit and validation contract

U-Net uses the existing three-channel width-16 architecture, FP32, fixed RGB division by 255, batch size one, seed 42, Adam at 0.001 and the existing unweighted masked loss. Epoch selection uses minimum validation loss. RF uses 100 trees, depth 16, two samples per leaf minimum, balanced class weights, seed 42, one job and signed RGB differences. Its TRAIN-only sampler draws without replacement under a 5,000-pixel per-mine cap with up to 2,500 pixels per class; shortages stay unfilled. No validation samples enter updates, fit statistics or RF sampling.

Both evaluations share the ordered 80 patch IDs and full 256 × 256 binary masks. They cover 5,242,880 pixels, including 535,534 changed pixels, with change at all ten mines. Twenty-four patches contain change; 56 contain none. Before training the run fixed a 0.20 median recall floor across mines with change. Of the eligible thresholds (.25, .35, .50, .65, .75, .90, .95), selection minimizes worst-site FPR, breaking ties by higher median recall then higher threshold. An empty eligible set has no operating threshold. Undefined recall is recorded as null.

## Results

| Model and cutoff | Precision | Recall | F1 | IoU | FPR | Worst-mine FPR | Median mine recall | Confusion `[[TN, FP], [FN, TP]]` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Siamese U-Net 0.25 | 0.2055 | 0.0209 | 0.0379 | 0.0193 | 0.0092 | 0.0253 | 0.0040 | `[[4664120, 43226], [524355, 11179]]` |
| Siamese U-Net 0.35 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0006 | 0.0042 | 0.0000 | `[[4704463, 2883], [535534, 0]]` |
| Siamese U-Net 0.50 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| Siamese U-Net 0.65 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| Siamese U-Net 0.75 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| Siamese U-Net 0.90 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| Siamese U-Net 0.95 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| RF 0.25 | 0.1230 | 0.6886 | 0.2087 | 0.1165 | 0.5588 | 0.8929 | 0.6559 | `[[2076842, 2630504], [166747, 368787]]` |
| RF 0.35 | 0.1503 | 0.5278 | 0.2339 | 0.1325 | 0.3396 | 0.6219 | 0.5070 | `[[3108782, 1598564], [252862, 282672]]` |
| RF 0.50 | 0.1874 | 0.3626 | 0.2471 | 0.1410 | 0.1788 | 0.3802 | 0.3605 | `[[3865546, 841800], [341361, 194173]]` |
| RF 0.65 (operating) | 0.2261 | 0.2392 | 0.2325 | 0.1315 | 0.0931 | 0.2052 | 0.2018 | `[[4269026, 438320], [407445, 128089]]` |
| RF 0.75 | 0.2557 | 0.1639 | 0.1997 | 0.1110 | 0.0543 | 0.1250 | 0.1423 | `[[4451970, 255376], [447778, 87756]]` |
| RF 0.90 | 0.3028 | 0.0586 | 0.0982 | 0.0517 | 0.0154 | 0.0377 | 0.0562 | `[[4635059, 72287], [504140, 31394]]` |
| RF 0.95 | 0.2925 | 0.0255 | 0.0469 | 0.0240 | 0.0070 | 0.0220 | 0.0162 | `[[4674322, 33024], [521882, 13652]]` |

### Per-mine and patch-stratum behavior

**Siamese U-Net at 0.50** (no operating cutoff qualified; .50 reference).

| Group | Precision | Recall | F1 | IoU | FPR | Confusion |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Change-present patches | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[1037330, 0], [535534, 0]]` |
| Brazil_01 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[412952, 0], [111336, 0]]` |
| Chile_01 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[496870, 0], [27418, 0]]` |
| Congo_01 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[457068, 0], [67220, 0]]` |
| Germany_05 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[490519, 0], [33769, 0]]` |
| Russia_08 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[491090, 0], [33198, 0]]` |
| Serbia_01 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[482311, 0], [41977, 0]]` |
| SouthAfrica_05 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[519698, 0], [4590, 0]]` |
| SouthAfrica_08 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[397766, 0], [126522, 0]]` |
| SouthAfrica_11 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[446049, 0], [78239, 0]]` |
| Tanzania_01 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[513023, 0], [11265, 0]]` |
| Zero-change patches | — | — | — | — | 0.0000 | `[[3670016, 0], [0, 0]]` |

**RF at 0.65**.

| Group | Precision | Recall | F1 | IoU | FPR | Confusion |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Change-present patches | 0.4412 | 0.2392 | 0.3102 | 0.1836 | 0.1564 | `[[875079, 162251], [407445, 128089]]` |
| Brazil_01 | 0.2807 | 0.2970 | 0.2886 | 0.1686 | 0.2052 | `[[328200, 84752], [78267, 33069]]` |
| Chile_01 | 0.1027 | 0.1617 | 0.1257 | 0.0670 | 0.0779 | `[[458148, 38722], [22984, 4434]]` |
| Congo_01 | 0.3354 | 0.1818 | 0.2358 | 0.1337 | 0.0530 | `[[432857, 24211], [55000, 12220]]` |
| Germany_05 | 0.1525 | 0.3683 | 0.2157 | 0.1209 | 0.1409 | `[[421402, 69117], [21332, 12437]]` |
| Russia_08 | 0.0859 | 0.0902 | 0.0880 | 0.0460 | 0.0649 | `[[459199, 31891], [30202, 2996]]` |
| Serbia_01 | 0.1730 | 0.1503 | 0.1609 | 0.0875 | 0.0625 | `[[452149, 30162], [35667, 6310]]` |
| SouthAfrica_05 | 0.0027 | 0.0394 | 0.0050 | 0.0025 | 0.1303 | `[[452002, 67696], [4409, 181]]` |
| SouthAfrica_08 | 0.3770 | 0.2219 | 0.2794 | 0.1624 | 0.1167 | `[[351366, 46400], [98447, 28075]]` |
| SouthAfrica_11 | 0.4745 | 0.2980 | 0.3661 | 0.2240 | 0.0579 | `[[420234, 25815], [54927, 23312]]` |
| Tanzania_01 | 0.2054 | 0.4487 | 0.2818 | 0.1640 | 0.0381 | `[[493469, 19554], [6210, 5055]]` |
| Zero-change patches | 0.0000 | — | 0.0000 | 0.0000 | 0.0752 | `[[3393947, 276069], [0, 0]]` |

## Compute and reproduction

| Epoch | TRAIN loss | Validation loss | Wall seconds | CPU seconds |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.34180 | 0.33410 | 103.9 | 203.5 |
| 2 | 0.32083 | 0.34630 | 107.8 | 211.8 |
| 3 | 0.31742 | 0.33124 | 100.5 | 197.9 |
| 4 | 0.31203 | 0.34339 | 104.9 | 205.2 |
| 5 | 0.31239 | 0.32829 | 101.3 | 199.8 |

Best epoch was **5**. RF used 95,000 unique TRAIN pixels (45,000 changed, 50,000 unchanged) and took 10.5 wall seconds. The combined run took 610.0 wall and 1118.8 process CPU seconds. Peak process working set was 845.3 MiB. The runner checks the 1,800-second wall budget between batches and phases; the single sklearn fit is nonpreemptible. Completed epochs and the fitted RF are reusable on resume.

From the repository root with the existing Python environment:

```powershell
python -B -m scripts.minenetcd256_phase17d outputs/external_minenetcd256/phase17c_plan/primary.json outputs/external_minenetcd256/phase17c_acquired outputs/external_minenetcd256/phase10c.json outputs/external_minenetcd256/phase17d_run
```

Run and artifact receipts are local in `outputs/external_minenetcd256/phase17d_run/`: `run.json`, `metrics.json`, `epoch-1.pt` through `epoch-5.pt`, and `rf.pkl` with `rf.json`. Validation support SHA-256 is `d7a1efc9a563d6c3fd429b010cbc83f847b8dec77031c7e2a17d37260bdc4a75`. All input and checkpoint hashes and per-threshold confusion matrices are in the local receipts.

**Next task:** Freeze the selected checkpoint and operating cutoff of any qualifying model. Audit prior manifest accesses and pre-register a bounded, label-blind evaluation on previously untouched official TEST mines. Report per-mine failure modes and never retune on test. This is site-disjoint external RGB validation with possible within-mine crop correlation. It provides no Indian Sentinel-1/2 accuracy estimate. Indian supervised training remains NO-GO, candidates UNKNOWN and operational alerts zero.

Eight targeted tests passed, including frozen-mask, zero-change metric and class-aware sampling checks.
