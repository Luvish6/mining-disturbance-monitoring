# Phase 22H — Expanded static weak-label training

Agreement with unverified Maus v2 weak labels - NOT independently verified Indian accuracy.

## Acquisition and QA

The [dated preregistration](../preregistration-phase22h-v1.md) was committed before acquisition at `1f9449d32ab4278f7869003c4b67c3046bdd822f`. The approved manifest SHA-256 stayed `00f87cbbe5f26a5166165582bacff8492f89f928d13750b5f991d01bbcc503ea`. The frozen split stayed `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`. TEST imagery and labels stayed sealed. The earlier 39 patch files and checkpoints were preserved.

The new smoke patch passed the 128 × 128 north-up 10 m image/mask grid, CRS, affine, band order, exact rasterization and validity checks. It had 16,371/16,384 valid cells. The remaining acquisitions used the same frozen windows. An Earth Engine metadata memory error paused the initial batch at 20 verified results. Acquisition resumed with two workers and the existing request ledger. The accepted 114 TIFF responses used 16,511,122 body bytes and 344 metadata calls, within both caps. There were zero rejected patches. A Windows console encoding error occurred after final QA receipts were written. The status print was corrected and completed artifacts were revalidated without additional downloads.

| Split | Patches | Groups | States | Positive / background patches | Weak positive / background cells | Min valid fraction |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 120 | 40 | 12 | 40 / 80 | 342,469 / 1,308,268 | 91.39% |
| Validation | 33 | 11 | 1 | 11 / 22 | 89,958 / 360,445 | 99.74% |

The TRAIN states were Andhra Pradesh, Bihar, Chhattisgarh, Goa, Gujarat, Haryana, Karnataka, Madhya Pradesh, Maharashtra, Rajasthan, Telangana and West Bengal. Odisha provided all 33 validation patches and 11 validation groups. All 51 group triples remained complete. Exact joint footprint, state, group, overlap, buffer and candidate exclusions were rechecked. The [sanitized manifest](phase22h-expanded-manifest.json) contains state counts and patch hashes. Unknown and invalid cells did not enter loss or scoring.

Twenty seed-selected new overlays had zero automated geometry flags. Visual inspection showed no common translation but identified weak outline concerns around mixed roads, industrial-looking blocks, ponds and vegetated terrain. Background windows include varied bare, bright and built-looking surfaces. This is HUMAN REVIEW PENDING. No label error was certified. TRAIN-only normalization reproduced exactly. The archived Phase 22F statistics file SHA-256 is `5c51f938b3ffef5d6f7d1c810066165c0a71fc70c67d6717a63cffbe80a3f9df`.

## Model results

Both RF models fit the same 100,000 balanced unique TRAIN pixels, using 100 trees and seed 42. NDVI excluded no extra labeled pixels. RF CPU times were 22.0 and 33.5 seconds for A and B. The U-Net used 40 positive and 80 unique background patch exposures per complete epoch. The maximum available unique ratio was 1:2. No extra background was exported or repeated within an epoch. All three seeds completed before the cap, using 629.5 CPU seconds combined. Seed 42, 43 and 44 each used 9, 14 and 15 epochs, retaining epochs 4, 9 and 10. No fitting failure occurred.

| Model / exact bands | Expanded validation cutoff | Precision | Recall | F1 | IoU | FPR | TN / FP / FN / TP |
|---|---:|---:|---:|---:|---:|---:|---:|
| RF-A, B3/B4/B8 | 0.50 | 0.5400 | 0.6126 | 0.5740 | 0.4025 | 0.1302 | 313502 / 46943 / 34849 / 55109 |
| RF-B, B3/B4/B8 + NDVI | 0.50 | 0.5359 | 0.6065 | 0.5690 | 0.3976 | 0.1311 | 313189 / 47256 / 35398 / 54560 |
| U-Net 42, B3/B4/B8 | 0.20 | 0.5561 | 0.6884 | 0.6152 | 0.4443 | 0.1371 | 311010 / 49435 / 28032 / 61926 |
| U-Net 43, B3/B4/B8 | 0.40 | 0.7869 | 0.7410 | 0.7633 | 0.6172 | 0.0501 | 342391 / 18054 / 23296 / 66662 |
| U-Net 44, B3/B4/B8 | 0.60 | 0.7504 | 0.7714 | 0.7608 | 0.6139 | 0.0640 | 337367 / 23078 / 20560 / 69398 |
| U-Net mean ± sample SD | | 0.6978 ± 0.1241 | 0.7336 ± 0.0420 | 0.7131 ± 0.0848 | 0.5585 ± 0.0989 | 0.0838 ± 0.0468 | |

Support was 89,958 weak positives and 360,445 weak backgrounds. All false positives are from background-only windows under the weak-label protocol. Full pooled, per-group and per-state results and checkpoint hashes are in the [sanitized metrics ledger](phase22h-expanded-metrics.json). Expanded validation was reused for model/threshold selection and is Odisha-only. The comparison is descriptive and affected by seed variation.

## Original 15 validation patches, using new frozen cutoffs

| Model | Phase 22H F1 / IoU / FPR | Phase 22F F1 / IoU / FPR |
|---|---|---|
| RF-A | 0.4462 / 0.2871 / 0.1926 | 0.4956 / 0.3295 / 0.0260 |
| RF-B | 0.4434 / 0.2849 / 0.1939 | 0.4934 / 0.3275 / 0.0222 |
| U-Net seed 42 | 0.4155 / 0.2622 / 0.2641 | 0.3230 / 0.1926 / 0.4278 |
| U-Net seed 43 | 0.4553 / 0.2948 / 0.1102 | 0.3071 / 0.1814 / 0.7954 |
| U-Net seed 44 | 0.4736 / 0.3103 / 0.1354 | Unavailable |
| U-Net three-seed mean ± sample SD | 0.4482 ± 0.0297 / 0.2891 ± 0.0245 / 0.1699 ± 0.0826 | Two-seed baseline |

The original 15 are part of expanded validation. Thresholds were applied unchanged and this is a common-support comparison, with selection bias. Both RF arms had lower F1 and higher FPR on this subset. The matched U-Net seeds 42/43 improved mean F1 from 0.3150 to 0.4354 and lowered mean FPR from 0.6116 to 0.1871. The preregistered stop condition of no dual improvement did not trigger. No further tuning ran. No statistical or independent accuracy claim follows.

## Deterministic error panels

RF-A is the provisional RF by lowest expanded FPR. The three weakest positive-bearing patches had IoU 0.0755, 0.1710 and 0.2198, missing 4,532, 2,118 and 8,603 weak-positive cells respectively. Only known positive pixels are scored in those windows. The first two masks include angular segments with mixed vegetation, dark ponds or narrow cleared features and very sparse predictions. The third covers mixed disturbed-looking and vegetated texture, with omissions across and within the apparent outline. This is consistent with spectral mixture or ambiguous outline semantics, with label quality unresolved.

The two selected background windows had 13,447 and 6,465 predicted positive cells (82.07% and 39.46% of valid weak background respectively). The former is dominated by a dark water-like response; the latter has patchy vegetation and linear/cleared-looking features. Water, shade, bare ground, infrastructure and unmapped extraction are plausible confounders. No independent observation established a mine or a label error. For the paired groups and full counts see the metrics ledger. The slides and checkpoint files remain private under `outputs/phase22h_maus/`.

Offline reproducibility follows the committed protocol and receipts. The acquisition commands are `python -B -m scripts.phase22h_maus_acquire smoke` then `batch`, with the explicit overlay inspection gate. The model commands are `python -B -m scripts.phase22h_maus_train rf` and `unet`. No results were applied to the frozen Indian temporal experiment.
