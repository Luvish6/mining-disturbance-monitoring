# Phase 22W — Sentinel-1/Sentinel-2 RF ablation: status STOPPED BEFORE TRAINING (budget breach)

The preregistration was committed as `28e6204` before acquisition: [phase22w-preregistration.json](phase22w-preregistration.json).

The cohort was frozen at **108 TRAIN + 33 VAL** patches. All 12 Goa TRAIN patches were excluded from every arm because they have no Q1 2019 Sentinel-1 coverage. TEST stayed sealed.

The labels are Maus v2 **weak static footprint** labels. They are not verified, not change labels and not Meghalaya labels.

## Acquisition outcome

| Item | Value |
|---|---|
| Patches cached | 141 / 141 (5 bands: VV, VH, count, elevation, slope), each on its exact optical grid |
| Pilot SAR reused | Yes, the 3 valid Phase 22V patches. Only their terrain was fetched. |
| Earth Engine requests | **490** (cap 300) |
| Response bytes | **47,872,790** (cap 40,000,000) |
| Duplicate patch fetches | 104 patches downloaded twice. Every duplicate download had an identical byte size. |

**Incident.** The on-disk ledger shows two acquisition writers interleaving. Each process enforced the cap against its own in-memory request count, so neither one stopped. The process that reported back counted 280 requests and 27.3 MB. The second writer's origin is unconfirmed: only one run was launched intentionally.

**Actual usage exceeded both preregistered caps.** Following the task's stop rule, **no models were trained and no VAL data was scored.**

## Fix (tested)

`scripts/phase22w_ablation.py` now:
- takes an exclusive lock file, so a second concurrent `--acquire` exits;
- computes the budget from the shared on-disk ledger before every patch.

`tests/test_phase22w_ablation.py` includes a test for both behaviours (4 tests pass).

The cached data needs **no further requests**. Rerunning `--acquire` skips all 141 cached patches.

## Decision needed

The cached inputs are complete, but they were obtained above the approved budget. Training and evaluation (`--run`) are offline and unchanged from the preregistration. They will proceed only on an explicit user decision. No results exist yet.
