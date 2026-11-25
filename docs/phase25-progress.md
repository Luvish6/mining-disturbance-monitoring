# Phase 25 — MineChange-India progress

| Phase | Actual status | Evidence / next gate |
|---|---|---|
| 25A | Complete: focused implementation inventory, verified literature, model/input/rights and hardware feasibility | [Report](reports/phase25a-feasibility.md), [evidence](reports/phase25a-evidence.json); 35 offline tests passed |
| 25B | COMPLETE, cached-only engineering | [Report](reports/phase25b-cached-features.md); four development AOIs, 36 potential-disturbance cells; eight unavailable layer families; no reference labels or accuracy |
| 25C | COMPLETE: private offline pilot | [Report](reports/phase25c-private-pilot.md);16 patches,29 slots, preserved pseudo states; no admitted references or release |
| 25D | NOT STARTED | U-Net/modern comparison requires data and approved isolated TerraMind smoke test; no historical RF deletion |
| 25E | NOT STARTED | Preserve existing portal; analyzer changes await approval |
| 25F | NOT STARTED | No public dataset, DOI reservation or upload authorized |
| 25G | NOT STARTED | Integration after preceding gates; no current result replaced |

Initial Phase 25A record (before cached-only 25B authorization), 2026-11-25, baseline 08604dea. No Earth Engine request, image/weight acquisition, research training, TEST payload access or new label in 25A. Pseudo-labels are not independent mining ground truth. Indian verified supervised training remains NO-GO, attribution UNKNOWN and operational alerts zero. Stop at this boundary for approval.

## Mandatory backup gate — VERIFIED 2026-11-25

Stable tag `pre-minechange-india` is pushed at 08604dea. Existing `phase22-label-sources` is preserved; development is isolated on `phase25-minechange-india`. The full private project-parent snapshot passed size, inventory and SHA-256 verification for 72,005 files (7,918,850,848 bytes), zero mismatches. See [rollback instructions](reports/phase25-backup-rollback.md). At the backup snapshot, separate ignored Phase 25 directories were reserved and 25B was NOT STARTED; its subsequent cached-only completion is recorded below. No merge, acquisition or training approval is implied.

## Phase 25B boundary

User authorized cached-only work after safeguards. Essential backup recheck passed for 8,765 files / 6,058,419,596 bytes. Four AOIs processed with no acquisition or research fitting; 19 focused and 382 full regression tests passed. Current twelve-slot stack has four populated domains and eight explicit gaps. Stop after 25B: await approval for missing-source/provenance recovery or 25C planning. No acquisition, training or public dataset release is authorized.

## Phase 25B.1 boundary

The separately authorized, preregistered recovery pilot is complete: [report](reports/phase25b1-recovery.md). Three existing TRAIN AOIs, 14 metered HTTP requests / 1,069,012 body bytes. Elevation/land-cover/rainfall added; sparse JRC support, no qualified fire support and OSM HTTP406 remain explicit. Current query scene IDs recovered without rewriting legacy provenance. Old pseudo-states unchanged. Stop before further acquisition or 25C; independent supervised training and public release remain NO-GO.

## Phase25C boundary

User-authorized offline packaging completed from5b360da. Four guarded parent AOIs produced12 TRAIN /4 VAL non-overlapping crops,52 source hashes rechecked unchanged, zero TEST payload access or acquisition. Labels remain retrospective shared-source pseudo states. VAL has no potential-disturbance support; independent Indian training and release remain NO-GO. Stop after the private pilot; no25D or training authorization.

## Phase25C.1 boundary

[Metadata-only readiness plan](reports/phase25c1-expansion-readiness.md):20 existing guarded development caches, target68 TRAIN/12 VAL crops (not built);17 missing core-context AOIs. Original30-sheet import stays pending with no admitted mining labels. No imagery/mask decoding, acquisition, fitting or TEST payload access. Stop before the proposed acquisition/replay pending explicit approval.

## Phase25C.2 boundary

[Completed private expansion](reports/phase25c2-context-expansion.md):80 patches from all20 frozen development AOIs,17 context downloads/3 reused,48 requests/1,528,746 body bytes.168 total potential-disturbance cells remain UNKNOWN pseudo states; independent references0,operational alerts0. Old25C and review materials preserved. No future acquisition,training or public release authorized. Stop after25C.2.

## Phase25D.1 boundary

[Readiness](reports/phase25d1-model-readiness.md) complete: shared5-channel paired adapters,masked loss/evaluation frame and synthetic-only checks.67 TRAIN/12 VAL usable under common token mask;81/60 pseudo-positives,zero independent labels. Tiny is conditional on isolated CUDA runtime,verified211.9MB checkpoint and32×32/native30m smoke;no weights loaded or fitting. Stop for setup/smoke approval before any installation/download/training.

## Phase25D.2 resource boundary

[STOPPED at RAM gate](reports/phase25d2-cuda-smoke.md):3.474GiB available versus8GiB required. No setup,resolution,transfer,checkpoint load or GPU smoke. Existing settings/data/environments unchanged. Resume after user frees RAM and all gates pass;no further phase started.

## Phase25D.2 partial setup boundary

[Progress](reports/phase25d2-setup-progress.md):RAM initially passed,empty isolated3.11 environment created;official dependency constraints require3.12. Resolution failed,no installs;nextRAM gate7.856GiB stopped before3.12 acquisition. Preserve D: cache/ledger44.40MB charged;model0,smoke unrun. Resume after RAM gate with corrected interpreter,never reset budgets.

## Phase25D.2 Python3.12 compatibility boundary

[Existing venv reused](reports/phase25d2-python312-progress.md);RAM gates passed. Wheel-only dependency resolution stops on official antlr4-python3-runtime4.9.* source-only release. No installs/model/smoke. Preserve cumulative transfer ledger;request narrowly scoped source-to-wheel approval rather than silently relaxing policy.
