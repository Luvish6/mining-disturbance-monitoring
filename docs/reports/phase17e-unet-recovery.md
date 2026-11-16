# Phase 17E — RGB Siamese U-Net class-imbalance recovery

## Diagnosis before fitting

Phase 17D validation reproduced exactly from its frozen best checkpoint, on the same 80 patches and their full binary masks. The loader verified all 320 acquired patches. The source masks encode 0 unchanged and 255 changed. The loader converts those values to binary targets. The head emits logits, the existing BCE-with-logits applies the valid mask, and evaluation applies sigmoid once before comparing with inclusive thresholds. The focused tests confirmed weighted gradient signs, exclusion of invalid pixels and threshold direction. No implementation defect was found.

TRAIN foreground prevalence was 9.78%. Unweighted BCE assigns background roughly nine times the aggregate pixel count. Low raw scores and overlapping class distributions are consistent with foreground suppression under imbalance. The acquisition does not isolate imbalance from weak visual discrimination or between-mine shifts. Pixel-pooled calibration summaries can look modest even with very poor foreground recall.

| Phase 17D split | Prevalence | Mean score | Change median | Unchanged median | Change P05–P95 | Unchanged P05–P95 | Brier | Ten-bin ECE | Positive / negative recall at .25 |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| train | 0.0978 | 0.0941 | 0.1085 | 0.0787 | 0.0509–0.2581 | 0.0504–0.1692 | 0.0839 | 0.0169 | 0.0627 / 0.9901 |
| val | 0.1021 | 0.0925 | 0.0956 | 0.0793 | 0.0470–0.2038 | 0.0530–0.1676 | 0.0910 | 0.0121 | 0.0209 / 0.9908 |

A 32 × 32 TRAIN-derived crop and mask supplied a synthetic contrast cue. The synthetic pair never entered the real run. After 150 updates its loss fell from 0.70875 to 0.00394, with 100.0% change recall and 100.0% specificity at .50. This checks learnability of a simple cue.

## Controlled recovery

The sole fitting change was weighted valid-mask BCE, with positive weight min(10, 14,189,749 / 1,538,891) = **9.22076287404371**. Initialization, TRAIN order, per-date RGB scaling, architecture, Adam learning rate, batch size and five CPU epochs follow Phase 17D. The same weighted loss selects the lowest-loss validation epoch. Weighted losses and raw scores have a different objective from the unweighted baseline; the recovery sigmoid is an operating score with no probability calibration claim. The prespecified .20 median-mine recall floor, threshold grid and worst-mine FPR selection rule were reused. No official TEST was accessed.

| Epoch | Weighted TRAIN loss | Weighted validation loss | Wall seconds |
| --- | ---: | ---: | ---: |
| 1 | 1.27813 | 1.27915 | 99.5 |
| 2 | 1.25244 | 1.27766 | 100.7 |
| 3 | 1.25200 | 1.27742 | 95.5 |
| 4 | 1.25202 | 1.27718 | 98.5 |
| 5 | 1.25192 | 1.27700 | 97.9 |

Selected epoch: **5**. Recovery used 509.6 wall seconds and 998.3 process CPU seconds. Validation uses identical rows and masks throughout.

| Model and score cutoff | Precision | Recall | F1 | IoU | FPR | Worst-mine FPR | Median-mine recall | Confusion [[TN, FP], [FN, TP]] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Phase 17D U-Net 0.25 | 0.2055 | 0.0209 | 0.0379 | 0.0193 | 0.0092 | 0.0253 | 0.0040 | `[[4664120, 43226], [524355, 11179]]` |
| Frozen RF 0.65 | 0.2261 | 0.2392 | 0.2325 | 0.1315 | 0.0931 | 0.2052 | 0.2018 | `[[4269026, 438320], [407445, 128089]]` |
| Weighted U-Net 0.25 | 0.1021 | 1.0000 | 0.1854 | 0.1021 | 1.0000 | 1.0000 | 1.0000 | `[[0, 4707346], [0, 535534]]` |
| Weighted U-Net (operating) 0.35 | 0.1021 | 1.0000 | 0.1854 | 0.1021 | 1.0000 | 1.0000 | 1.0000 | `[[0, 4707346], [0, 535534]]` |
| Weighted U-Net 0.50 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| Weighted U-Net 0.65 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| Weighted U-Net 0.75 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| Weighted U-Net 0.90 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |
| Weighted U-Net 0.95 | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `[[4707346, 0], [535534, 0]]` |

### Per-mine validation at 0.35

| Mine | Recall | F1 | IoU | FPR | Confusion | Phase 17D U-Net F1 at .25 | Frozen RF F1 at .65 |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Brazil_01 | 1.0000 | 0.3503 | 0.2124 | 1.0000 | `[[0, 412952], [0, 111336]]` | 0.0000 | 0.2886 |
| Chile_01 | 1.0000 | 0.0994 | 0.0523 | 1.0000 | `[[0, 496870], [0, 27418]]` | 0.0000 | 0.1257 |
| Congo_01 | 1.0000 | 0.2273 | 0.1282 | 1.0000 | `[[0, 457068], [0, 67220]]` | 0.1115 | 0.2358 |
| Germany_05 | 1.0000 | 0.1210 | 0.0644 | 1.0000 | `[[0, 490519], [0, 33769]]` | 0.0013 | 0.2157 |
| Russia_08 | 1.0000 | 0.1191 | 0.0633 | 1.0000 | `[[0, 491090], [0, 33198]]` | 0.0000 | 0.0880 |
| Serbia_01 | 1.0000 | 0.1483 | 0.0801 | 1.0000 | `[[0, 482311], [0, 41977]]` | 0.0045 | 0.1609 |
| SouthAfrica_05 | 1.0000 | 0.0174 | 0.0088 | 1.0000 | `[[0, 519698], [0, 4590]]` | 0.0200 | 0.0050 |
| SouthAfrica_08 | 1.0000 | 0.3888 | 0.2413 | 1.0000 | `[[0, 397766], [0, 126522]]` | 0.0826 | 0.2794 |
| SouthAfrica_11 | 1.0000 | 0.2597 | 0.1492 | 1.0000 | `[[0, 446049], [0, 78239]]` | 0.0110 | 0.3661 |
| Tanzania_01 | 1.0000 | 0.0421 | 0.0215 | 1.0000 | `[[0, 513023], [0, 11265]]` | 0.0779 | 0.2818 |

**NO-GO for U-Net promotion.** The frozen rule mechanically selected .35, which predicts change on every valid pixel and has 100% FPR at every mine. At .50 and higher it predicts no change. Validation scores span only .4658–.4894, with the same .4870 median for both classes. The F1 increase over the unweighted baseline reflects an all-change prediction, so the recovery failed to deliver a usable operating point. Preserve this result and freeze only the existing RF at .65 for the next held-out evaluation. Its checkpoint SHA-256 is `937c5c8c7165c0e0bc19425a48136a10dbe4ae009067249669c785e443bcf5bc`.

Before accessing TEST, bind eligible checkpoint SHA-256 values, thresholds, label-blind row-selection rule, budget and previously exposed test-mine exclusion list into a preregistration receipt. Keep the RF checkpoint and threshold unchanged. Do not modify weights or cutoffs after scoring. Indian supervised training remains NO-GO.

From the project root, in the existing Python environment, run diagnosis then recovery in a fresh local output directory:

```powershell
$inputs = @(
  'outputs/external_minenetcd256/phase17c_plan/primary.json',
  'outputs/external_minenetcd256/phase17c_acquired',
  'outputs/external_minenetcd256/phase10c.json',
  'outputs/external_minenetcd256/phase17d_run',
  'outputs/external_minenetcd256/phase17e_run'
)
python -B -m scripts.minenetcd256_phase17e diagnose @inputs
python -B -m scripts.minenetcd256_phase17e recover @inputs
```

Local `diagnosis.json`, `run.json` and `metrics.json` contain the calibration bins, source and checkpoint hashes, loss history and all per-mine confusion matrices. The ordered validation support SHA-256 is `d7a1efc9a563d6c3fd429b010cbc83f847b8dec77031c7e2a17d37260bdc4a75`. Eight targeted tests passed.
