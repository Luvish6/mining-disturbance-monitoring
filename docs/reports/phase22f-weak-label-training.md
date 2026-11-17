# Phase 22F — Indian 2019 static weak-label training

The original offline run completed both RF fits, all three U-Net stability attempts and both gated U-Net fits. Recovery used the saved results and verified checkpoint hashes. No fit was restarted. The [preregistration](../preregistration-phase22f-v1.md) was committed before fitting at `b45f812bdabe2b92c4150fd4ef9ead1806700545`.

The same 24 TRAIN and 15 validation patches passed raster, scene-band contract, provenance, mask and checksum checks. TRAIN-only normalization replay matched exactly. Evaluation used 196,036 labeled valid validation cells, of which 32,199 are weak positives and 163,837 are weak background. Unknown and invalid cells and the optical observation-count band were excluded. NDVI required a finite nonzero denominator and excluded zero additional cells. RF arms used the same 100,000 TRAIN cells, 50,000 per class. TEST stayed sealed. No Earth Engine or download operations ran.

> Thresholds and early stopping were selected using the same 15 weak-labelled VAL patches from five groups in Odisha. These scores are selection-biased weak-label agreement estimates, not independent accuracy.

## Pooled validation

Confusion order is TN / FP / FN / TP. All negative evaluation cells are in the background-only windows, so the false positives shown also provide that subset count and FPR.

| Model and features | Threshold | Precision | Recall | F1 | IoU | FPR | Confusion | CPU / wall s |
|---|---:|---:|---:|---:|---:|---:|---|---|
| RF-A, B3/B4/B8 | 0.75 | 0.7382 | 0.3731 | 0.4956 | 0.3295 | 0.0260 | 159577 / 4260 / 20187 / 12012 | 19.0 / 19.2 |
| RF-B, B3/B4/B8 + NDVI | 0.75 | 0.7632 | 0.3646 | 0.4934 | 0.3275 | 0.0222 | 160195 / 3642 / 20460 / 11739 | 32.6 / 33.0 |
| U-Net seed 42, B3/B4/B8 | 0.25 | 0.2194 | 0.6119 | 0.3230 | 0.1926 | 0.4278 | 93754 / 70083 / 12497 / 19702 | 84.2 / 43.1 |
| U-Net seed 43, B3/B4/B8 | 0.25 | 0.1845 | 0.9155 | 0.3071 | 0.1814 | 0.7954 | 33521 / 130316 / 2722 / 29477 | 35.3 / 18.0 |

| Validation group (hashed) | RF-A F1 | RF-B F1 | U-Net 42 F1 | U-Net 43 F1 |
|---|---:|---:|---:|---:|
| 617c0407394a | 0.301 | 0.343 | 0.114 | 0.200 |
| 6f1f04f0186a | 0.807 | 0.779 | 0.356 | 0.473 |
| b058a970af58 | 0.237 | 0.257 | 0.367 | 0.208 |
| ddc26d250831 | 0.070 | 0.056 | 0.174 | 0.114 |
| f35c8ae0451a | 0.254 | 0.273 | 0.545 | 0.406 |

Full per-group precision, recall, F1, IoU, FPR and confusion counts are in the [sanitized metrics](phase22f-weak-label-metrics.json). RF-B trades 618 fewer weak-background false positives for 273 fewer true positives under the selected cutoffs. The RF F1 difference is 0.0022 and group results vary markedly, so the two arms are indistinguishable for an overall ranking on this experiment. RF seed variation is unmeasured. The U-Net F1 spread is 0.0160, IoU spread 0.0112 and FPR spread 0.3676. Both RF arms show greater pooled weak-label agreement and lower FPR on these selected validation samples. The five groups, reused for selection, cannot establish independent superiority.

## U-Net recovery and stability

The original stability process continued after the client error. Adam at 0.0003, batch size one, GroupNorm and no clipping passed the first configuration on seeds 42, 43 and 44. Each completed 1,000 updates. Every checkpoint from steps 900 through 1,000 had masked IoU 1.0 on the eight diagnostic TRAIN patches. Final masked BCE was 0.00418, 0.00181 and 0.00666 respectively. No invalid update was logged. The combined budget used 462.0 CPU seconds and 235.9 wall seconds. No clipping, batch size four, full batch or normalization variant was needed. GroupNorm was already present in the earlier unstable run, excluding BatchNorm running-state behavior as an explanation. The late rebound is consistent with overshooting during sequential optimization at 0.001. The longer diagnostic and lower learning rate do not isolate its cause.

Fresh seeds 42 and 43 ran 20 and 8 epochs, selecting epochs 15 and 3, then stopped on the preregistered patience rule. No training or runtime failures were recorded. Diagnostic memorization did not carry over to clean separation on the weak validation patches.

## Scale-up proposal only

The local proposed group manifest reserves 42 TRAIN groups and 12 Odisha validation groups. Keep the 39 verified patches. For each of Andhra Pradesh, Chhattisgarh, Goa, Gujarat, Karnataka, Madhya Pradesh, Maharashtra, Rajasthan, Telangana and West Bengal target four TRAIN groups and 12 patches, with one existing group each in Bihar and Haryana (three patches per state). Target 36 validation patches across 12 Odisha groups. Total ceiling is 162 patches, with one positive-bearing and two sampled background patches per group. Group choices use frozen assignments, cached groups first and stable hash ordering. New geometries are unassessed.

There are at most 41 new group-screening work units and 123 new direct TIFF responses, with at most 257,949,696 image-response bytes at 2 MiB per TIFF. Budget approximately 574 application requests before retries, allowing two metadata/proxy calls per new group and four calls per new export. The actual plan needs a separately reviewed resource estimate. Reapply the full-footprint state and 2,050 m cross-split buffer screens, all-polygon background exclusions and overlap checks. Retain arity caps and log empty slots. Odisha remains the only validation state under the frozen split. The proposal ran no acquisitions. Verified evaluation still needs independently dated, positioned and adjudicated references.

Local outputs and model checkpoints are under `outputs/phase22f_maus/`. Checkpoint digests are in the metrics ledger. Publication excludes weights and imagery under project policy. Reproduce offline by running `python -B -m scripts.phase22f_maus preflight`, then the `rf` and `unet` actions in a fresh output directory. Phase 22F is a separate historical footprint engineering experiment. Verified Indian temporal model training remains NO-GO.
