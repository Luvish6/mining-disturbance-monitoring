# Claude → Codex handoff (2026-11-20)

- **Branch:** `phase22-label-sources` (upstream `origin/phase22-label-sources`).
- **Starting HEAD:** `36519b8497d6e5400bd08811365b91b80fcc9d2c`. The working tree was clean apart from a pre-existing untracked `results/phase22/feasibility.json` (Phase 22A). I left that file untouched and uncommitted.
- **Ending HEAD:** this handoff commit. It sits on top of the commits listed below; run `git log -5` to see them.

## Commits

| SHA | Purpose |
|---|---|
| `2a7a5bd` | Phase 22O preregistration: offline TEST guards and the JRC pre-screen, committed before any imagery request |
| `b809058` | Phase 22O river NDTI pilot results |
| `d7f242b` | Phase 22P preregistration, committed before the Sentinel-1 request |
| `d9a8414` | Phase 22P Sentinel-1 corroboration results |
| (this) | This handoff |

## Files changed (all new)

- `scripts/phase22o_river.py`, `tests/test_phase22o_river.py`, `docs/reports/phase22o-preregistration.json`, `docs/reports/phase22o-summary.json`, `docs/reports/phase22o-river-ndti.md`
- `scripts/phase22p_sar_corroboration.py`, `tests/test_phase22p_sar.py`, `docs/reports/phase22p-preregistration.json`, `docs/reports/phase22p-summary.json`, `docs/reports/phase22p-sar-corroboration.md`
- `docs/reports/claude-handoff-to-codex.md`
- Local only (gitignored): `outputs/phase22o_river/` (cache, per-granule CSVs with scene IDs, budget ledger) and `outputs/phase22p_sar/` (SAR cache and receipt).

No existing file was modified. Frozen TEST data, spatial blocks, buffers, seed and thresholds are unchanged.

## Commands executed (from the checkout root, with the venv at `..\.venv`)

```
python -B -m scripts.phase22o_river --preregister
python -B -m scripts.phase22o_river --acquire
python -B -m scripts.phase22o_river --refetch-lines   # repair, see below
python -B -m scripts.phase22o_river --analyze
python -B -m scripts.phase22p_sar_corroboration --preregister
python -B -m scripts.phase22p_sar_corroboration --acquire
python -B -m scripts.phase22p_sar_corroboration --analyze
python -B -m pytest -q -p no:cacheprovider tests/test_phase22o_river.py tests/test_phase22p_sar.py tests/test_phase22n_temporal.py tests/test_phase22l_temporal.py
```

**Tests:** 17 passed (7 for 22O, 3 for 22P, plus the existing 22N and 22L tests). The full suite was not run, because no existing code was changed. The publication audit passed on every commit through the pre-commit hook.

## Measured results

### Phase 22O — relative NDTI river pilot

Full report: [phase22o-river-ndti.md](phase22o-river-ndti.md).

**Geometry guards.** All four CPCB station windows (720 m) are district-contained and lie 4.2–5.3 km from any buffered TEST block.

| Reach | Usable dates (before / after) | Median NDTI before → after | After − before [95% CI] | Status |
|---|---|---|---|---|
| Khaddum | 19 / 24 | −0.041 → −0.020 | +0.021 [−0.033, 0.076] | Passes the screen, but the post-hoc check found **0% SCL water** and B3 ≈ 0.17. Water identity is doubtful, so do not interpret. |
| Sunapur | 4 / 0 | — | — | INSUFFICIENT_DATES / UNRESOLVED |
| Mihmyntdu | — | — | — | UNRESOLVED before acquisition: at most 1 eroded JRC pixel |
| Leshka | 15 / 13 | −0.530 → −0.505 | +0.025 [−0.105, 0.130] | Supported, but potentially impounded water. **No change detected.** |

- **Flow topology:** HydroSHEDS NDOID supports Khaddum → Sunapur (14 hops) and Mihmyntdu → Leshka (18 hops). Still, **no upstream–downstream contrast is possible**, because on each river one member of the pair lacks data.
- **Rainfall:** CHIRPS seasonal totals were roughly 45% lower in the after season at every station.
- **Overall:** a negative feasibility result. 10 m Sentinel-2 cannot resolve the narrow channels.

### Phase 22P — Sentinel-1 corroboration of the 9 Phase 22L candidates

Full report: [phase22p-sar-corroboration.md](phase22p-sar-corroboration.md).

- **Reproduction check:** the new fetch matches the cached Phase 6B tile on 1,938 shared cells (max error 1.8×10⁻⁶ dB).
- **dVH:** the candidate median is −2.75 dB against a background median of −1.06 dB. Cell-level permutation p = 0.004 and cluster-level p = 0.031. Both are descriptive only, because the cells are spatially autocorrelated.
- **dVV:** not distinct from background (p = 0.17).
- **Outside the background 5–95% range:** 4 of 9 candidates, against at most 1.8 expected by chance.
- **Meaning:** this is the first measured S1–S2 agreement on real temporal candidates. It is not mining validation.

## Cloud usage

| Task | Requests | Response bytes | Caps |
|---|---|---|---|
| 22O | 22 (including 1 repair request) | 7,323,424 | 40 / 50 MB |
| 22P | 3 | 68,234 | 8 / 2 MB |

GEE initialization calls are not counted. getInfo byte counts are serialized JSON sizes; download byte counts are exact.

## Blockers, incidents and unresolved issues

1. **22O fetch bug.** The first acquisition saved HydroSHEDS *collection metadata* instead of the window lines, because `ee.Dictionary` of FeatureCollections does not expand to features. I fixed it with `fetch_lines()` and a one-off `--refetch-lines` repair request, which is recorded in the ledger. No analysis rule changed. A fresh `--acquire` now uses the fixed path.
2. **22O screen weakness.** At Khaddum, JRC occurrence ≥50% plus MNDWI > 0 admits pixels that are probably not open water. Any revised water screen must be a *new* preregistration, for example one requiring SCL 6 or NDWI > 0 as well. Do not edit 22O.
3. **Unchanged blockers:**
   - There are still zero independently verified mining-change reference labels.
   - There is no admissible Meghalaya reference pair (Phase 7 Day 3 NO-GO).
   - The KORPET/Sumon pair is still under quality review.
   - The U-Net remains incompatible with 30 m change stacks.

## Paper-readiness gaps, highest priority first

1. **Independent reference labels for Meghalaya mining change.** This is the main blocker for any accuracy claim. A realistic route: run the existing Phase 22J two-reviewer blind protocol on dated very-high-resolution imagery (Planet or Google Earth historical) for the 6 Phase 22L clusters plus matched random background cells, recording excavation / other / uncertain verdicts.
2. **Spatially independent multi-AOI replication of the temporal rule.** Only 1 AOI has been processed. Select ≥3 further TRAIN/VAL AOIs with full-footprint guards (as in 22N), fixed in advance. Do not search for detections.
3. **Supervised S1 vs S2 vs fusion ablation on real labels.** This has never been run in Meghalaya because labels are missing. Phase 22P gives the first descriptive S1–S2 agreement. A labelled ablation needs gap 1 first. Until then, a defensible substitute is a *label-free* agreement analysis: SAR co-change rates for optical candidates against random cells across several AOIs, under the 22P protocol.
4. **Control AOIs.** None is eligible yet. The proposed forest control was rejected because it intersects TEST.
5. **River evidence.** This is a negative feasibility result at 10 m, and there is no field turbidity data. Options:
   - field NTU sampling at Leshka or Khaddum, matched to Sentinel-2 overpass dates;
   - wider downstream Lukha reaches toward the Bangladesh plains, which would need a new guarded preregistration;
   - PlanetScope 3 m imagery.
   Describe the river component in the paper as a feasibility study only.
6. **Model results to keep separate.** The MineNetCD held-out RF (Phase 17G, pooled F1 0.246) and the Maus weak-label U-Net (VAL F1 0.713 ± 0.085) are benchmark and weak-label results. They are not Meghalaya accuracy.

## Recommended next Codex task

Extend Phase 22P to ≥3 new preregistered, guard-passing TRAIN/VAL AOIs, which addresses gaps 2 and 3:
1. Preregister the AOI roster with the Phase 22N full-footprint `check()`.
2. Fetch the S2 seasonal stack (using the Phase 22L graph) and S1 orbit 77 for each AOI.
3. Apply the unchanged 22L rule and the 22P statistics.
4. Report the per-AOI candidate count and the dVH agreement.

Expected cost: about 4 requests and under 1 MB per AOI. In parallel, the user could start the gap 1 blind review of the 6 existing clusters.

## Uncommitted or unpushed state

- `results/phase22/feasibility.json` is pre-existing, untracked and was left alone.
- Local outputs listed above are gitignored by design.
- Push status is reported in the final chat summary. Verify with `git ls-remote origin phase22-label-sources`.
