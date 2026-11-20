# Phase 22W — Sentinel-1 vs Sentinel-2 vs fusion Random Forest ablation (Maus v2 weak labels)

The preregistration was committed as `28e6204` before acquisition ([phase22w-preregistration.json](phase22w-preregistration.json)). The acquisition-guard fix and incident record are in `418b0bc`. Metrics are in [phase22w-metrics.json](phase22w-metrics.json). Code is in `scripts/phase22w_ablation.py`, with tests in `tests/test_phase22w_ablation.py`.

**What this measures.** It measures **agreement with Maus v2 weak static mining-footprint labels**: 2019, peninsular India, Odisha VAL.
- It is **not** independent ground-truth accuracy.
- It is **not** temporal change detection.
- It says **nothing** about Meghalaya, mining legality or river pollution.

TEST stayed sealed.

## Acquisition incident (not concealed)

| Item | Value |
|---|---|
| Approved caps | 300 Earth Engine requests, 40 MB |
| **Actual usage** (shared on-disk ledger) | **490 requests** (245 URL plus 245 downloads), **47,872,790 bytes** |
| Cause | Two Claude sessions (the original handoff session and its fork) each ran `--acquire` concurrently on the same cache. Each enforced the cap on its own in-memory count. Their processes reported 280 requests / 27.3 MB and 271 requests / 26.3 MB respectively; both counts included the 57 earlier shared ledger entries. |
| Effect | 104 of 141 patches were downloaded twice. Every duplicate download had an identical byte size, and no patch was replaced. |
| Fix (`418b0bc`) | An exclusive lock file blocks a second writer, and the budget is computed from the shared on-disk ledger before every patch. Four unit tests pass. |
| After the incident | Training used **only the cached data**, with **zero additional Earth Engine requests**. The user approved this explicitly after the breach was reported. |

## Pre-training verification

- All **141/141** cached patches match the frozen cohort: **108 TRAIN + 33 VAL**. The 12 Goa TRAIN patches have no Q1-2019 Sentinel-1 coverage and are excluded from every arm.
- The manifest hashes are unchanged, and every patch's split equals its frozen assignment.
- Each patch has 5 bands on its exact optical grid. The grid was verified at download (EPSG, affine, 128 × 128).
- The 3 reused Phase 22V pilot SAR patches are byte-identical to the pilot cache.
- SAR-valid and terrain-finite fractions are 1.0 on every patch, so no post-fetch gate failed.
- The cache hashes are recorded locally in `outputs/phase22w_ablation/cache_manifest.json`.

## Fixed protocol (as preregistered)

- **Data.** A shared set of 100,000 balanced TRAIN pixels (50,000 per class, seed 42), drawn once from 1,491,271 common-support TRAIN pixels.
- **Model.** RF with 100 trees, max depth 16, min_samples_leaf 2, sqrt features, seed 42 and no class weights. The cutoff is fixed at 0.50.
- **Baseline.** Phase 22K Rule A (NDVI < 0.10), applied unchanged.
- **Scoring.** All 450,403 VAL pixels in 11 groups.
- **Uncertainty.** A group bootstrap (10,000 resamples of the 11 VAL groups), with paired differences computed on the same resamples. Resampling whole groups accounts for patch and pixel dependence.
- **Not done.** No tuning, feature selection or threshold search.

## Results (VAL, weak labels)

| Arm | Features | Precision | Recall | F1 [group 95% CI] | IoU [CI] | FPR | Confusion `[[TN, FP], [FN, TP]]` | Background F1 |
|---|---|---|---|---|---|---|---|---|
| A — SAR-only | VV, VH | 0.301 | 0.507 | **0.378** [0.239, 0.480] | 0.233 [0.136, 0.316] | 0.294 | [[254547, 105898], [44353, 45605]] | 0.772 |
| B — Optical-only | B3, B4, B8 | 0.479 | 0.602 | **0.533** [0.354, 0.637] | 0.364 [0.215, 0.467] | 0.163 | [[301537, 58908], [35810, 54148]] | 0.864 |
| C — Fusion | VV, VH, B3, B4, B8 | 0.452 | 0.667 | **0.539** [0.386, 0.628] | 0.369 [0.239, 0.458] | 0.201 | [[287845, 72600], [29976, 59982]] | 0.849 |
| D — Fusion + terrain | C + elevation, slope | 0.362 | 0.645 | **0.463** [0.290, 0.583] | 0.302 [0.169, 0.412] | 0.284 | [[257920, 102525], [31921, 58037]] | 0.793 |
| R — Rule baseline | NDVI < 0.10 | 0.634 | 0.333 | **0.437** [0.199, 0.637] | 0.280 [0.110, 0.467] | 0.048 | [[343172, 17273], [59984, 29974]] | 0.899 |

**Paired F1 differences** (median, group-bootstrap 95% CI, share of resamples above 0):

| Comparison | ΔF1 | 95% CI | P(Δ > 0) |
|---|---|---|---|
| **Fusion − Optical** (does SAR add value?) | **+0.006** | [−0.039, +0.058] | 0.61 |
| Optical − SAR | +0.152 | [+0.031, +0.261] | 0.99 |
| Fusion − SAR | +0.159 | [+0.086, +0.225] | 1.00 |
| Fusion+terrain − Fusion | −0.072 | [−0.176, +0.006] | 0.04 |
| Fusion+terrain − Optical | −0.064 | [−0.148, +0.012] | 0.05 |
| Rule − Optical | −0.098 | [−0.205, +0.027] | 0.06 |

**Per-group F1.** Results are heterogeneous. Fusion beats optical in 5 of 11 groups. The F1 ranges are 0.04–0.62 (SAR), 0.12–0.71 (optical) and 0.16–0.74 (fusion). One group collapses under terrain (F1 0.07, FPR 0.62). The full per-group confusions are in the metrics JSON.

**Feature importances (impurity-based, descriptive).**
- In fusion, B8 0.39, B3 0.24, B4 0.15, VV 0.12 and VH 0.11.
- In fusion + terrain, elevation is 0.23.

## Interpretation

1. **Sentinel-1 adds no detectable value over Sentinel-2** for static footprint agreement on this dataset. The paired ΔF1 is +0.006, with a CI spanning zero.
   - Fusion shifts the operating point toward higher recall (+0.065) and higher FPR (+0.038). It does not raise F1.
   - This is a **negative result** and is preserved as such.
2. **SAR alone is clearly weaker than optical** (ΔF1 +0.15, CI excludes zero), but it is well above trivial. VV/VH carry some footprint information.
3. **Adding terrain hurts.** Fusion + terrain is lower in 96% of resamples. Elevation's high importance suggests site-level confounding: absolute height learned from the 36 TRAIN groups does not transfer to Odisha.
4. **The rule baseline is precise but low-recall.** It has the lowest FPR (0.048) and the best background-class F1. Its F1 interval overlaps every RF arm.
5. **Context.** Phase 22H RF-A (optical, all 120 TRAIN patches including Goa) reported F1 0.574. The present optical arm uses a different cohort and pixel support, so the two are not directly comparable.

## Limitations

- **Labels.** Maus v2 weak labels: unmapped mines can sit in the backgrounds, and the outlines are approximate.
- **Validation.** VAL is a single state (Odisha, 11 groups), so the CIs are wide.
- **TRAIN coverage.** Goa is excluded because it has no Sentinel-1 coverage.
- **Data.** This is static Q1-2019 imagery. SAR is a 20 m focal-smoothed median with a single orbit per patch.
- **Pixel dependence.** Pixels are dependent within groups. Only the group bootstrap addresses this.
- **Transfer.** Peninsular open-cast mining differs from Meghalaya's rat-hole coal and limestone workings; nothing here transfers to Meghalaya accuracy.
- **Not tested.** Temporal fusion, such as seasonal dVV/dVH change, remains untested on labels.

## Reproduction (offline; cache present)

```powershell
python -B -m scripts.phase22w_ablation --run
python -B -m pytest -q -p no:cacheprovider tests/test_phase22w_ablation.py
```

Do not rerun `--acquire`. It now holds a lock and would skip every cached patch, but it still initializes Earth Engine.
