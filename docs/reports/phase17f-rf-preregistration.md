# Phase 17F — RF held-out preregistration

The Phase 17D RF checkpoint independently matched SHA-256 `937c5c8c7165c0e0bc19425a48136a10dbe4ae009067249669c785e443bcf5bc`. The cutoff remains **0.65** on scores from signed after-minus-before RGB in R, G, B order, using the existing 100-tree fit and no probability recalibration. U-Net remains excluded. TEST scoring is a separate phase.

## Exposure audit

Reviewed the available external experiment JSON inventory, prior acquisition code and repository history. The Phase 10C viewer and original lossless RF pilot accessed America_02. The first held-out run accessed Brazil_02, Brazil_03 and Brunei_01. The expanded RF holdout accessed Canada_01 and Canada_02. The local freeze records viewer row IDs, lossless shard and row-group IDs, within-group rows, recorded source hashes, and hashes of the audited receipts. It reconciles earlier test selections with their acquisition manifests. Parquet acquisition read full groups 0, 1, 2 and 4 in the first TEST shard. Since prior requests included whole groups and logs do not prove a finer exposure boundary for every attempt, quarantine **all 15 mines appearing in that shard**. This also excludes Canada_05, Chile_02, Chile_05, China_02, Congo_05, Congo_06, Finland_01, Gabon_01 and Germany_02. The audit establishes exposure within the available project records.

The pinned publisher release contains 30 TEST mines and 19,355 patches. Both shard domain columns reconciled exactly with the saved official roster. The 15 remaining eligible sites, all selected, are Germany_03, Ghana_01, Hungary_02, Hungary_03, Hungary_06, India_06, Indonesia_02, Ireland_01, Kazakhstan_06, Myanmar_02, NewZealand_01, Russia_01, SouthAfrica_06, SouthAfrica_13 and Zambia_01. These site IDs are disjoint from the official development sites. [Publisher release](https://huggingface.co/datasets/HZDR-FWGEL/MineNetCD256)

## Frozen sampling and transfer

Choose group subsets by maximum eligible mine count, then maximum distinct publisher site prefixes, then minimum charged bytes, with seed-42 hash tie-breaking. Select four equally spaced row ranks per mine in the retained groups. The **60 rows in 15 mines** span six row groups in the second official TEST shard. Crops lack verified georeferenced footprints and can cluster within a mine. This sample represents the quarantined archive remainder and cannot establish uniform geographic coverage.

- Charged Phase 17 development transfers through acquisition, including both planning passes: **300,025,306 bytes**.
- Measured TEST metadata reads: **60,945 bytes**. These read headers, exact footers and domain chunks only.
- Expected new acquisition: **160,102,149 bytes** out of **236,784,661 bytes** remaining. The combined estimate is **460,188,400 bytes** under the **536,870,912-byte** cap. Complete physical column chunks and reopened source metadata are included.
- Local receipt: `outputs/external_minenetcd256/phase17f_preregistration.json`. Canonical SHA-256: `9ce7467b5bd6dab615988bf1bd0a63956586b933774da8c8616c4d1df0065922`.

## Evaluation contract

Freeze confusion matrix in TN/FP/FN/TP order, positive-class precision, recall, F1 and IoU, negative-class FPR, per-mine scores, worst-mine FPR and separate change-present/zero-change patch strata. Recall is null for zero positive support; the same denominator rule applies to other undefined ratios. Require the expected seal, unchanged access records, checkpoint and source hashes, frozen sites and rows, original binary PNG masks, shared RGB/mask dimensions and no exact RGB overlap with the Phase 17 development cache. No fitting, calibration, selection or tuning uses TEST.

The next phase can invoke this command from the repository root with the project Python environment. It was not invoked during preregistration.

```powershell
python -B -m scripts.minenetcd256_phase17f evaluate outputs/external_minenetcd256 outputs/external_minenetcd256/phase17f_preregistration.json 9ce7467b5bd6dab615988bf1bd0a63956586b933774da8c8616c4d1df0065922 outputs/external_minenetcd256/phase17g_rf_holdout
```

Indian supervised training remains NO-GO, candidates UNKNOWN and operational alerts zero.
