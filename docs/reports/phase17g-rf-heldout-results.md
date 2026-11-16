# Phase 17G — Frozen RF held-out TEST results

The exact preregistered command ran on the pinned archive and original Phase 17D 100-tree RF at cutoff **0.65**. Offline preflight verified the receipt seal, checkpoint hash, training contract, prior access audit, selected rows and aggregate cap. The evaluator checked archive identity and authorized chunk ranges before reading image or mask chunks. It decoded and scored only the 60 preregistered patches from 15 previously untouched official TEST mines under the available access audit. Whole compressed column chunks were required for those rows. No further TEST rows were inspected after scoring.

## Results

All 3,932,160 labeled pixels were included. Foreground support was 421,918 pixels (10.73%), with 11 of 15 mines containing any sampled change. There were 20 change-present patches and 40 zero-change patches. The worst-mine false-positive rate was **24.16%**. Recall is undefined where ground truth has no positive pixels. A dash denotes an undefined ratio.

| Group | Changed pixels | Precision | Recall | F1 | IoU | FPR | Confusion `[[TN, FP], [FN, TP]]` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Pooled | 421,918 | 0.2374 | 0.2554 | 0.2461 | 0.1403 | 0.0986 | `[[3164101, 346141], [314144, 107774]]` |
| Change-present patches | 421,918 | 0.4978 | 0.2554 | 0.3376 | 0.2031 | 0.1223 | `[[780068, 108734], [314144, 107774]]` |
| Zero-change patches | 0 | 0.0000 | — | 0.0000 | 0.0000 | 0.0906 | `[[2384033, 237407], [0, 0]]` |
| Germany_03 | 0 | 0.0000 | — | 0.0000 | 0.0000 | 0.0093 | `[[259714, 2430], [0, 0]]` |
| Ghana_01 | 0 | 0.0000 | — | 0.0000 | 0.0000 | 0.0820 | `[[240655, 21489], [0, 0]]` |
| Hungary_02 | 26,942 | 0.5449 | 0.6350 | 0.5865 | 0.4149 | 0.0607 | `[[220914, 14288], [9834, 17108]]` |
| Hungary_03 | 9,446 | 0.0519 | 0.1373 | 0.0753 | 0.0391 | 0.0937 | `[[229011, 23687], [8149, 1297]]` |
| Hungary_06 | 53 | 0.0017 | 0.8113 | 0.0035 | 0.0017 | 0.0939 | `[[237484, 24607], [10, 43]]` |
| India_06 | 65,536 | 0.2079 | 0.1243 | 0.1556 | 0.0844 | 0.1579 | `[[165567, 31041], [57388, 8148]]` |
| Indonesia_02 | 86,215 | 0.3176 | 0.2171 | 0.2579 | 0.1480 | 0.2285 | `[[135721, 40208], [67502, 18713]]` |
| Ireland_01 | 18,259 | 0.2581 | 0.4370 | 0.3245 | 0.1937 | 0.0941 | `[[220946, 22939], [10279, 7980]]` |
| Kazakhstan_06 | 35,432 | 0.2546 | 0.2938 | 0.2728 | 0.1580 | 0.1344 | `[[196233, 30479], [25021, 10411]]` |
| Myanmar_02 | 0 | 0.0000 | — | 0.0000 | 0.0000 | 0.1541 | `[[221736, 40408], [0, 0]]` |
| NewZealand_01 | 45,954 | 0.5372 | 0.5070 | 0.5217 | 0.3529 | 0.0928 | `[[196122, 20068], [22657, 23297]]` |
| Russia_01 | 65,536 | 0.4546 | 0.0453 | 0.0824 | 0.0430 | 0.0181 | `[[193044, 3564], [62565, 2971]]` |
| SouthAfrica_06 | 0 | 0.0000 | — | 0.0000 | 0.0000 | 0.0263 | `[[255243, 6901], [0, 0]]` |
| SouthAfrica_13 | 65,536 | 0.2639 | 0.2599 | 0.2619 | 0.1507 | 0.2416 | `[[149105, 47503], [48502, 17034]]` |
| Zambia_01 | 3,009 | 0.0446 | 0.2566 | 0.0760 | 0.0395 | 0.0638 | `[[242606, 16529], [2237, 772]]` |

The benchmark covers a small label-blind sample of the official TEST mines outside the quarantined shard. The cropped release lacks verified patch footprints, so spatial overlap within mines remains unknown. Results apply to external RGB change screening. Indian supervised training remains NO-GO, candidates UNKNOWN and operational alerts zero.

## Transfer and receipts

The run acquired **160,102,149 bytes**, exactly the preregistered estimate. The Phase 17 aggregate including earlier development and TEST metadata traffic was **460,188,400 bytes** out of **536,870,912**. There were no execution failures. The output directory contains the verified range journal and metrics receipt with row identities and original source hashes. No checkpoint, payload or local receipt is published in Git.

Preregistration SHA-256: `9ce7467b5bd6dab615988bf1bd0a63956586b933774da8c8616c4d1df0065922`

Local metrics file SHA-256: `3d4208045b5f8fa3f3586dcc1ee429f30f17e22826f75fc74a8229d0ebade1aa`

Ten targeted tests passed. See the [preregistration](phase17f-rf-preregistration.md) for the frozen command and sampling rules.
