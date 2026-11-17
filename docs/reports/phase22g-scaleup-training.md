# Phase 22G — Static weak-label scale-up and retraining decision

**STOP at geometry preflight.** Four preregistered positive windows fail full-footprint containment of the 2,050 m projected guard inside their assigned ADM1. The mandatory windows were left in the rejection ledger. No replacements, Earth Engine metadata or TIFF requests, new QA overlays, fitting or validation scoring occurred.

Agreement with unverified Maus v2 weak labels - NOT independently verified Indian accuracy.

## Frozen inputs and preflight

The [dated amendment](../preregistration-phase22g-v1.md) was committed at `8e5ad27ecb3c74f8e41a191627297d633be0acca` before acquisition. The Phase 22F proposal and original acquisition plan matched their pinned hashes. The original split remained byte-identical at SHA-256 `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`. TEST remained sealed. The source geometries from all splits were used for spatial exclusion only.

All 39 existing imagery and weak-mask pairs passed their stored checksums, patch and label contracts, geometry checks and TRAIN normalization replay. The accepted cache remains 24 TRAIN patches in eight states and 15 validation patches in Odisha. TRAIN states are Andhra Pradesh, Bihar, Goa, Haryana, Madhya Pradesh, Maharashtra, Rajasthan and Telangana. Odisha is the sole validation state under the frozen roster.

| Role | Cached groups | New groups screened | New groups with geometry candidates | Required positive windows blocked |
|---|---:|---:|---:|---:|
| TRAIN | 8 | 34 | 31 | 3 |
| Validation | 5 | 7 | 6 | 1 |

The blocked TRAIN groups are Andhra Pradesh `ccbc1e5e594e4bd7`, Gujarat `5d5b8a0dbfbd36fe` and West Bengal `fea0a4894929f3d9`. The blocked validation group is Odisha `ec8fb774e2a0a3b8`. The failure in all four cases was `ADM1_FULL_FOOTPRINT_BUFFER`. The local unredacted receipt records tested coordinates, CRS, affine and failure reason. Its SHA-256 is `025118c6fc3263f67d72ecbeb063e3311284ee62360d492642fb6013cc3a9b51`.

For the 37 other groups, 724 ring geometries passed initial local screening. Background candidate rejections included 135 Maus or project-candidate intersections, 22 ADM1 containment violations, nine opposing/excluded-group buffer violations and three occupied-window intersections. A geometry could have multiple reasons. These are provisional candidates. No final optical-proxy ranking, cross-window hard-slot recheck or new image coverage/overlay QA was performed. The protocol prevents treating the passing subset as an expanded dataset after required slots fail.

## Frozen Phase 22F comparison

| Existing Phase 22F model | F1 | IoU | FPR |
|---|---:|---:|---:|
| RF-A, B3/B4/B8 | 0.4956 | 0.3295 | 0.0260 |
| RF-B, B3/B4/B8 + NDVI | 0.4934 | 0.3275 | 0.0222 |
| U-Net, B3/B4/B8, two-seed mean ± sample SD | 0.3150 ± 0.0113 | 0.1870 ± 0.0080 | 0.6116 ± 0.2600 |

These frozen Phase 22F results reused the same 15 weak-label validation patches from five Odisha groups for selection and reporting. Phase 22G produced no new FPR trend, seed results or worst-patch interpretation. RF-B is the provisional lower-FPR baseline among the frozen runs. The pooled F1 difference between RF arms does not justify ranking them on agreement. [Frozen Phase 22F report](phase22f-weak-label-training.md)

The next decision is whether to preregister another deterministic anchor rule within the same geographic groups, without relaxing the buffer. Any revised proposal must explicitly resolve the four windows before imagery requests. Independent review is still required for verified evaluation.

Local geometry and normalization receipts are in `outputs/phase22g_maus/`. Run `python -B -m scripts.phase22g_maus_preflight` with the same frozen inputs and a fresh receipt destination to reproduce the geometry checks. Four new focused tests and ten existing focused tests passed.
