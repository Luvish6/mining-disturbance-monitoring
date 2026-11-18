# Phase 22K — Static optical index-rule baseline

Agreement with unverified Maus v2 weak labels - NOT independently verified Indian accuracy.

The preregistration was committed before threshold fitting at 4d156c9. The original Phase 22H mask support was preserved: 120 TRAIN patches in 40 groups and 12 states, and 33 validation patches in 11 Odisha groups. The known weak-label support was 1,650,737 TRAIN cells and 450,403 validation cells. No index denominator was zero on that support. Existing cache/hash/grid checks passed, and TEST remained sealed.

Raw B3/B4/B8 reflectances supply NDVI=(B8−B4)/(B8+B4), NDWI=(B3−B8)/(B3+B8) and brightness=(B3+B4+B8)/3. Grids were t1 −0.20 to 0.80 every 0.10; t2 0.02 to 0.30 every 0.02; t3 −0.60 to 0.40 every 0.10. The histogram search uses strict inequality semantics, all eligible TRAIN pixels and the first ascending-grid combination on an exact TRAIN F1 tie. Unknown/invalid pixels are excluded. There was no component filtering. The selected thresholds were saved before the sole validation reporting pass.

Rule A selects NDVI <0.10. Rule B additionally requires brightness >0.02. Rule C additionally requires NDWI <0.40. Brightness selected the grid's lowest bound and provided no validation change. The water exclusion removes some predicted positives at a recall cost. Grid-edge choices were retained without expanding the search.

| Rule/model | Support | Precision | Recall | F1 | IoU | FPR |
|---|---|---:|---:|---:|---:|---:|
| A | train | 0.6875 | 0.4283 | 0.5278 | 0.3585 | 0.0510 |
| A | validation | 0.6344 | 0.3332 | 0.4369 | 0.2795 | 0.0479 |
| B | train | 0.6837 | 0.4207 | 0.5209 | 0.3522 | 0.0510 |
| B | validation | 0.6344 | 0.3332 | 0.4369 | 0.2795 | 0.0479 |
| C | train | 0.7066 | 0.3939 | 0.5058 | 0.3385 | 0.0428 |
| C | validation | 0.6723 | 0.3263 | 0.4394 | 0.2816 | 0.0397 |
| Frozen Phase 22H RF-A, B3/B4/B8 | validation | 0.5400 | 0.6126 | 0.5740 | 0.4025 | 0.1302 |
| Frozen Phase 22H RF-B, B3/B4/B8/NDVI | validation | 0.5359 | 0.6065 | 0.5690 | 0.3976 | 0.1311 |
| Frozen Phase 22H U-Net, B3/B4/B8, mean ± sample SD | validation | 0.6978 ± 0.1241 | 0.7336 ± 0.0420 | 0.7131 ± 0.0848 | 0.5585 ± 0.0989 | 0.0838 ± 0.0468 |

All metrics in this table are agreement with unverified Maus v2 weak labels - NOT independently verified Indian accuracy. Phase 22H models used validation for selection; the three rules used TRAIN only. The comparison has different selection procedures and is descriptive. Differences within the U-Net seed spread do not support a significance claim.

| Rule | TRAIN TN / FP / FN / TP | Validation TN / FP / FN / TP |
|---|---|---|
| A | 1241603 / 66665 / 195803 / 146666 | 343172 / 17273 / 59984 / 29974 |
| B | 1241603 / 66665 / 198392 / 144077 | 343172 / 17273 / 59984 / 29974 |
| C | 1252249 / 56019 / 207565 / 134904 | 346138 / 14307 / 60601 / 29357 |

Every negative scored cell is in a weak background-only window. Thus the FP counts above also describe background-only false positives. The [metrics JSON](phase22k-rule-metrics.json) preserves precision, recall, F1, IoU, FPR, confusion counts and background false positives by group and state on TRAIN and validation, with null undefined denominators.

TRAIN F1 exceeded validation F1 by approximately 0.091, 0.084 and 0.066 for A/B/C. This indicates limited threshold transfer across the observed groups. Low recall is present already on TRAIN, consistent with an under-expressive index rule for heterogeneous footprint annotations. Surface composition, shade, water and unmapped mining in weak backgrounds remain possible sources of disagreement. These scores do not resolve label quality.

This is a single-date static footprint rule. Temporal NDVI-drop and CVA require two seasonal composites and are deferred to the Indian application phase. NDTI cannot be evaluated as a turbidity measure on these land patches; the rule task has no river-water screening or calibration. An algebraic red–green ratio would not supply a validated NDTI evaluation.

Reproduce with the existing environment using python -B -m scripts.phase22k_rules. The runner preserves exclusive frozen threshold and metric receipts. Three focused tests passed, including exact threshold-bin boundaries, direct-search parity and unknown-mask exclusion. No RF/U-Net retraining, imagery request or split change ran.
