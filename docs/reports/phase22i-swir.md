# Phase 22I-LEAN — Sentinel-2 additional-band ablation

Agreement with unverified Maus v2 weak labels - NOT independently verified Indian accuracy.

**Stop rule triggered.** RF-F2 improved expanded-validation F1 and increased FPR. U-Net F2 lowered F1 and raised FPR on both completed paired seeds. No further tuning ran.

## Frozen inputs, transfer and common support

The [protocol](../preregistration-phase22i-v1.md) was committed before acquisition at `55ae6b524eaf377ade716ea177bb8d6d1dedf927`. The frozen split SHA-256 is `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`, and manifest SHA-256 is `00f87cbbe5f26a5166165582bacff8492f89f928d13750b5f991d01bbcc503ea`. All 120 TRAIN and 33 Odisha validation windows, their assignments and original weak masks were preserved. TEST stayed sealed.

Only B2/B11/B12 were exported. B2 is native 10 m. The existing 10 m UTM grid received bilinearly sampled native 20 m B11/B12 per masked scene before the seasonal median. Resampling creates no new SWIR detail. The smoke tile passed all 128 × 128 grid, order and support checks with 16,384 common valid cells. All 153 acquisitions passed. Total 153 TIFF responses and 20,161,413 response-body bytes, no TIFF retries. Source IDs and dates were inherited from the authenticated Q1 2019 joined scene rosters.

The intersection removed four valid TRAIN cells (three known targets) and five valid validation cells (five known targets). Four patch masks lost optical support. The known-cell comparison used 1,650,734 TRAIN cells, 450,398 expanded validation cells and 196,031 original-subset cells. F1 was refitted on the same support as F2. Both RF arms sampled the exact same 100,000 unique balanced TRAIN cells. Each U-Net arm's normalization was computed on common TRAIN cells only. Original Phase 22H results and rasters remain unchanged.

F1 features are B3/B4/B8. F2 features are B2/B3/B4/B8/B11/B12. There is no SAR, DEM, NDVI or other feature in the comparison.

## Paired weak-label metrics

| Expanded validation (33 patches, 11 Odisha groups) | Feature arm | F1 | IoU | FPR |
|---|---|---:|---:|---:|
| RF, cutoff 0.50 | F1 | 0.5788 | 0.4073 | 0.1318 |
| RF, cutoff 0.50 | F2 | 0.5875 | 0.4159 | 0.1349 |
| U-Net, seeds 42/43 mean ± sample SD | F1 | 0.6959 ± 0.0948 | 0.5377 ± 0.1118 | 0.0898 ± 0.0568 |
| U-Net, seeds 42/43 mean ± sample SD | F2 | 0.4679 ± 0.0034 | 0.3054 ± 0.0029 | 0.2111 ± 0.0309 |

| Original 15 validation patches, no subset retuning | Feature arm | F1 | IoU | FPR |
|---|---|---:|---:|---:|
| RF | F1 | 0.4474 | 0.2881 | 0.1923 |
| RF | F2 | 0.4439 | 0.2853 | 0.1752 |
| U-Net, paired mean ± sample SD | F1 | 0.4443 ± 0.0120 | 0.2856 ± 0.0099 | 0.1854 ± 0.1076 |
| U-Net, paired mean ± sample SD | F2 | 0.3888 ± 0.0310 | 0.2415 ± 0.0239 | 0.3644 ± 0.0564 |

Per-group and Odisha state metrics, cutoff selection, confusion counts, precision/recall and checkpoint digests are in the [sanitized metrics](phase22i-swir-metrics.json). Expanded validation was reused for selection. The original 15 are a subset of expanded validation. Neither table is an independent test. The RF's small expanded F1 gain came with 1,132 more false positives. The U-Net difference is consistent across paired seeds 42 and 43. This comparison adds blue and SWIR together, so it cannot isolate the contribution of SWIR alone. Resampled SWIR can mix narrow excavation edges, water, bare terrain and infrastructure within the same native cell. Background may include unmapped mining and outlines remain weak. The results do not verify causes for individual false positives or label errors.

## Execution recovery and CPU accounting

An undefined summary variable interrupted RF result serialization after both models had fitted. The first recovery-dispatch attempt incorrectly entered U-Net and duplicated the F1 seed-42 fit before an existing-receipt guard stopped it. The original seed-42 receipt and its checkpoint still match byte-for-byte by SHA-256. The dispatch and support-receipt defects were fixed and covered by regression tests. RF scores were reassembled from the two fitted checkpoints, and U-Net scores from the existing arm receipts. Recovery performed no additional fitting after the dispatch fix.

The original U-Net process was halted at 950.75 measured process CPU seconds, reserving approximately 250 seconds of the 1,200-second budget for the duplicate attempt. The duplicate did not leave a CPU-time receipt, so the exact combined CPU usage cannot be certified. Seeds 42 and 43 have complete pairs. Seed 44 has a complete F1 receipt and a partial F2 checkpoint without a final paired receipt, so it is excluded from paired means and SDs. No job was restarted to fill the gap. The trained-model artifacts and transfer ledger remain local under `outputs/phase22i_maus/`.

Six focused tests passed.
