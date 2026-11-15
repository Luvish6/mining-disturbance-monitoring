# Real mining-change model training readiness

**MineNetCD256: GO for a larger bounded, site-disjoint experiment design; fitting awaits an acquisition preflight and frozen manifests. Indian Sentinel-1/2 supervised training: NO-GO.** No fitting, imagery download or test-label inspection was performed.

## Verified inventory

The saved Phase 10C official domain roster at revision `73c771bda9e5c5a1aed755077b1e61596e613161` has disjoint site IDs. [Publisher cropped dataset](https://huggingface.co/datasets/HZDR-FWGEL/MineNetCD256/blob/73c771bda9e5c5a1aed755077b1e61596e613161/README.md) · [Original release, CC BY 4.0](https://rodare.hzdr.de/record/3251)

| Official split | Mine sites | 256 × 256 patches | Patches per site, min–max |
| --- | ---: | ---: | ---: |
| Train | 60 | 47,743 | 12–4,221 |
| Validation | 10 | 4,613 | 104–1,122 |
| Test | 30 | 19,355 | 15–2,622 |

The original paired development cache and expansion contain 36 train patches across eight mines, all with foreground and 1,004,737 changed / 1,354,559 unchanged pixels. That cache was positive-enriched. The label-blind representative validation cache has 40 patches across all 10 mines, six patches with foreground, and 207,471 changed / 2,413,969 unchanged pixels. The full official class distribution is unknown from domain counts. Count exact 0/255 label values on the frozen selections before fitting and include all-zero patches. Reject nonbinary source masks in this experiment. The viewer JPEG route is unsuitable.

## Bounded next run

- **Freeze 240 TRAIN patches from 20 mines and 80 VALIDATION patches from all ten mines.** Select 20 TRAIN sites from the official roster by seed-42 round-robin over the publisher's site regions where region is documented, with hash ordering within each known group and a separate unknown group. Select 12 TRAIN and eight validation rows per site at equidistant ranks across its ordered official rows, using stable shard order and seed 42 for site ordering. Freeze all selections before reading labels or model outputs. Reuse exact cached rows when hashes and identifiers match. These are targets, with enough rows according to the official roster. Patch georeferencing is unavailable, so use site-disjoint claims and disclose possible intramine crop correlation.
- **Acquisition preflight.** Read only TRAIN/validation footer and domain columns across all three official TRAIN shards and the validation shard. Resolve exact shard/group/row keys, verify the roster totals, and sum required compressed column chunk sizes plus measured metadata traffic. Enforce one aggregate 512 MiB transfer cap before fetching original RGB and PNG payloads. Verify row site, source hashes, dimensions, alignment, binary mask, and decoded input duplication across splits. Report prevalence and positive-support mines per split. Require both classes and foreground at three or more mines in each development split before fitting. If the primary transfer exceeds the cap, preflight the fixed fallback of 120 TRAIN patches (six per same site) and 40 VALIDATION patches (four per site, using the existing label-blind cache). Record the changed validation selection and apply the same support gates. If neither qualifies, retain the current results.
- **Model settings.** Use the same frozen rows for both models. U-Net: RGB divided by 255, shared architecture with channels=3 and width=16, FP32, Adam 0.001, batch size one, seed 42, existing masked loss, up to five epochs, checkpoint each completed epoch. Keep natural patch prevalence with equal site contribution. RF: signed after-minus-before RGB, existing 100 trees, depth 16, leaf minimum 2, seed 42, one job, class weighting, maximum 100,000 unique pixels with equal site caps and class-aware sampling within each mine. Measure pooled and per-site recall/FPR and F1/IoU at the frozen threshold and candidate validation cutoffs .25, .35, .50, .65, .75, .90 and .95. Select U-Net epoch by validation loss. Prespecify an operating recall floor before fitting and then use validation only to minimize worst-site FPR subject to that floor. Preserve undefined recall for zero-positive sites.
- **Test quarantine.** Keep all official TEST assets sealed during development. Exclude America_02, Brazil_02, Brazil_03, Brunei_01, Canada_01 and Canada_02 from any future fresh evaluation, and check every prior manifest for other accesses before claiming a subset is untouched. Freeze models, thresholds, code and validation hashes before any final test, then use a label-blind selection shared by both models.
- **CPU/storage.** Ryzen 7 7840HS, 16 logical processors and a CPU-only PyTorch build. Historic 30/15 runs took 13–15 s per epoch with two threads. Linear scaling suggests roughly 8–12 min for five 240/80 epochs with evaluation overhead. Budget 5–15 min for RF fit and validation scoring, and 30 min for the combined compute run with epoch checkpointing and an explicit wall limit. These are estimates, excluding acquisition. Raw uint8 RGB pairs plus masks for 320 patches occupy 140 MiB. Reserve 2 GiB for cached arrays, manifests, intermediate files and checkpoints. Profile peak RAM before any scale-up.

## Repository fit and next executable step

The pinned reader already enforces range requests and lossless PNG decoding. Existing development acquisition hardcodes the first TRAIN shard and selects only two extra foreground-rich sites. Existing fit and evaluation scripts expect their prior run layout. Do not run those as-is for this plan. The next coding action is an isolated TRAIN/validation roster-to-row preflight that writes a byte estimate and frozen manifest without touching image/mask payloads. Reuse the existing reader, decoder and model functions. First run this existing, offline compatibility check from the project root using the project environment:

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_minenetcd256_adapter.py tests/test_minenetcd256_siamese_data.py tests/test_minenetcd256_siamese_fit.py tests/test_minenetcd256_improve.py tests/test_minenetcd256_validation_audit.py tests/test_phase11a_india_data.py tests/test_phase16a_regional.py
```

The check passed all 15 tests. A 240/80 acquisition command does not exist yet.

## Indian contract

The regional mapper already verifies a north-up 30 m grid, common validity, band order and signed differences. The canonical stack is before VV/VH/NDVI/NDTI, after VV/VH/NDVI/NDTI, dVV/dVH/dNDVI/dNDTI, elevation and slope. U-Net uses four observations plus four validity channels per date with training-only normalization. The symmetric absolute difference fusion is unchanged. RF consumes named changes and optional terrain according to the stored experiment. The regional inference interface requires an approved real run tied to region and artifact hash; the cached Gevra inputs and synthetic interface tests establish compatibility only. Three-channel RGB checkpoint weights cannot populate the eight-channel Indian model. No additional Indian adapter defect was established. The [accepted label count remains zero](indian-training-data-decision.md); independent labels, both classes across frozen splits and registered valid feature support are still required.
