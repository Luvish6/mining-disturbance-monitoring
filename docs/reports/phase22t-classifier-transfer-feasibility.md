# Phase 22T — Maus-trained U-Net transfer feasibility to Meghalaya

This audit starts from commit `a9e834f`.

**Constraints:** no Earth Engine requests, no inference, no retraining, no threshold changes and no TEST access.

**Sources:** [Phase 22H](phase22h-expanded-training.md), [Phase 22J model registry](phase22j-model-registry.json) and the Phase 22A Maus audit (`results/phase22/feasibility.json`, local and untracked), plus Phase 22L/22N/22Q and the cached output metadata.

## Verdict

**NO-GO for applying the U-Net to Meghalaya now.**

**CONDITIONAL GO** for a separately preregistered, strictly exploratory *agreement* run in the future. That run would report no accuracy, would need about 16 Earth Engine requests and under 3 MB of new 10 m acquisition, and needs your explicit approval first. No existing imagery can be used without violating the frozen input contract.

## 1. Frozen model contract (verified offline)

| Item | Frozen value | Check |
|---|---|---|
| Checkpoints | `unet-42/43/44.pt`: one model per seed, **no ensemble rule frozen** | All three SHA-256 hashes match the registry |
| Selected epochs / thresholds | 4 / 9 / 10 at cutoffs 0.20 / 0.40 / 0.60, each chosen on Odisha VAL | Read only, unchanged |
| Input | float32 NCHW, 3 channels (B3, B4, B8), **128 × 128 at 10 m**, north-up local UTM | — |
| Preprocessing | **2019 Q1 masked median** of harmonized S2 SR ÷ 10,000; ≥ 2 observations; ≥ 70% valid window; invalid cells set to zero after normalization | — |
| Normalization | TRAIN-only mean [0.0958, 0.1164, 0.2164] and SD [0.0384, 0.0544, 0.0632] | The source-file hash matches |
| Status | `PROVISIONAL_WEAK_LABEL_OPTICAL_BASELINE` | — |

## 2. Input compatibility with existing Meghalaya data

| Cached product | Grid | Bands | Dates | Compatible? |
|---|---|---|---|---|
| Phase 6B tiles; Phase 22L/22Q seasonal stacks | 64 × 64 at **30 m** | Seasonal indices; B2/B3/B4 medians (22L) | 2023–24 and 2024–25 seasons | **No.** Upsampling 30 m to 10 m would invent sub-pixel detail. 22L lacks B8; 6B lacks reflectance bands. |
| Phase 22O river cache | 72 × 72 at 10 m | B3, B4 and flags (no B8) | Per-granule, 2023–25 | **No.** No B8, smaller than 128 px, river corridors only. |
| Phase 4A examples | 72 × 72 at 10 m | B2/B3/B4/B8 | Single dates | **No.** Single scene rather than a Q1 median, smaller than 128 px, river windows. |

The scan of non-TEST caches found **no** 128 × 128 10 m Q1 B3/B4/B8 median anywhere in the study area. TEST tile paths were skipped and not opened. Any inference therefore needs **new acquisition**.

## 3. Training geography, label definitions, leakage and domain shift

- **Training geography.** TRAIN covers 120 patches in 40 groups from 12 peninsular and western states. Validation is 33 Odisha patches. **Maus v2 has zero Meghalaya polygons**; its North-East records are Assam (11) and Arunachal (1). The model has never seen Meghalaya terrain, forest, cloud regimes, shifting-cultivation (jhum) fallows or rat-hole coal workings.
- **Label definitions.** Positives are Maus v2 polygons, a 2019 reference year (CC BY-SA 4.0), mostly large open-cast mine footprints. Negatives are *weak* backgrounds that can contain unmapped mines. Meghalaya coal mining is small rat-hole pits plus coal dumps, with limestone quarries near Lumshnong. Their surface signature and scale differ from the training positives.
- **Known failure mode.** Validation groups show background-only FPR up to 0.36 to 0.52 on bright bare, built or industrial surfaces. Jhum fallows, roads and landslides in Meghalaya are plausible false-positive triggers.
- **Leakage.** There is no Maus-label leakage, because Meghalaya has no Maus polygons and Maus TEST stays sealed. The project's TEST blocks are excluded by the existing full-footprint guard. The remaining risk is *selection leakage*: choosing AOIs or thresholds after seeing outputs. The protocol below prevents it.
- **Temporal mismatch.** The model is static and single-season (2019 Q1). It is not a change detector. Differencing two static maps is unvalidated.

## 4. Can existing TRAIN/VAL imagery support inference?

**No.** Every cached Meghalaya product is 30 m, lacks B8, is too small, is single-date or is a river corridor. Resampling 30 m temporal features to 10 m inputs is rejected because it would be misleading (see Phase 22N).

## 5. Exploratory protocol (only if approved; preregister first)

1. **AOIs.** Use the four existing guarded AOIs (east-94-559-c74, east-90-562, west-82-563, west-85-563), re-checked with the full-footprint guard. No new AOIs and no relocation. Each 1.92 km AOI is fetched as a 192 × 192 10 m grid, then scored as 2 × 2 overlapping 128 × 128 windows. The overlap rule is fixed in advance.
2. **Inputs.** Use the exact contract graph (masked median, ÷10,000, ≥ 2 observations, ≥ 70% valid), restricted to Q1. Q1 2024 (Jan–Mar) lies inside the BEFORE window and Q1 2025 inside the AFTER window. Q1 2019 can be added as an in-contract reference year. The calendar-year shift is a declared domain shift.
3. **Domain-shift gate.** Report the per-band distribution of normalized inputs against TRAIN (median |z| and the fraction beyond ±3 SD). If the preregistered limit is exceeded, report the result as **OUT_OF_DISTRIBUTION** and do not interpret it.
4. **Outputs.**
   - Per-seed probability maps at the frozen cutoffs, with no new threshold.
   - Agreement across the three seeds: cells flagged by all three, by any, or by none.
   - Flagged area per AOI and year.
   - Overlap with the 22L/22Q candidate clusters and the 22P/22Q Sentinel-1 dVH, using the translation permutation from Phase 22R.
5. **Forbidden.** No precision, recall, F1 or accuracy. No retraining, ensembling or threshold tuning. No TEST access. All outputs are labelled **UNKNOWN — exploratory static footprint signal**.
6. **Null outcomes** are reported as measured: zero flagged cells, seed disagreement and OOD failures.

## 6. Prerequisites and cost

| Prerequisite | Status |
|---|---|
| User approval of new 10 m acquisition | **Missing** |
| Committed preregistration (protocol above, OOD limits, overlap rule) | Missing |
| Contract-exact acquisition script for 192 × 192 Q1 windows | Missing; adapt the existing Phase 22H acquisition code without changing the graph |
| Independent Meghalaya reference (DMR/MBDA drone survey, IBM tenements) | Requested ([Phase 22S](phase22s-official-mining-data-audit.md)); without it, results stay agreement-only |

**Estimated cost:** 4 AOIs × 2 years (2024 and 2025) = 8 metadata requests plus 8 downloads, so about 16 requests and roughly 2.5 MB (192 × 192 × 4 int16 bands per window). Adding Q1 2019 raises this to about 24 requests and 3.7 MB. Inference takes CPU seconds; no GPU is needed.

## 7. Bottom line

Even a technically clean run could show only where a model trained on peninsular Indian open-cast mines *responds* in Meghalaya. Without a Meghalaya reference, it cannot show whether those responses are mining. The better uses of effort are:
- securing the [Phase 22S](phase22s-official-mining-data-audit.md) official survey data;
- obtaining the Kalimantan Sentinel-1/Sentinel-2 labels (requested);
- reporting the existing multi-sensor agreement (Phases 22P–22R).

Run the exploratory transfer only if a dashboard or presentation needs an "optical footprint-model response" layer.
