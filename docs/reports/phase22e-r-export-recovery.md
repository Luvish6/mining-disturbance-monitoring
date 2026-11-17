# Phase 22E-R — Frozen Maus optical export recovery

**DATASET GO for weak-label engineering only.** All 39 frozen 2019 Q1 Sentinel-2 optical patches passed acquisition and QA. No fit beyond the preregistered eight-patch diagnostic ran. Verified reference counts remain zero, and validation masks remain weak annotations.

The original and recovery acquisition plans are byte-identical (SHA-256 `b3aecfd62e4e7d838430b4ca60f15c11e3b71ce7add8db0c2a4287e43f04b459`). The original split is unchanged at `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`. The geometric checks reran against the authenticated Maus inventory, administrative boundaries, and original candidate exclusions for this plan. They found no overlapping windows or cross-split buffer violations. Only development rasters were requested, and TEST imagery, masks and metrics stayed sealed.

## Live smoke and acquisition

The first frozen TRAIN entry passed before batch acquisition. The 128 × 128 image and weak mask shared identical numerical bounds, a 10 m north-up affine, and EPSG:32643. Band order was B3, B4, B8, optical count. The image had 16,298 of 16,384 valid cells (99.48%). The mask matched fresh pixel-center rasterization with invalid cells excluded. The 140,295-byte raw response has SHA-256 `f5634dcdb030d96a287cc38bf8b44c834beae1287bafd3a47e92728408f0f331`.

The smoke cache was reused for the batch, with up to three concurrent workers. The recovery used 39 TIFF responses and 5,712,131 response-body bytes, within the 45-response and 2 MiB-per-response limits. Zero patches were rejected. Phase 22E's original 64 × 64 response and rejection receipts remain preserved in their original directory.

| Split | Accepted patches | Weak foreground patches / groups | Weak background patches | States | Valid pixels | Foreground pixels | Background pixels |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 24 | 8 / 8 | 16 | 8 | 393,080 | 53,043 | 262,103 |
| Validation | 15 | 5 / 5 | 10 | 1 | 245,704 | 32,199 | 163,837 |

The positive-bearing TRAIN states are Andhra Pradesh, Bihar, Goa, Haryana, Madhya Pradesh, Maharashtra, Rajasthan and Telangana. All validation groups are in Odisha. Minimum valid-cell fractions were 99.48% for TRAIN and 99.74% for validation. Each image/mask pair passed CRS, affine, band, NoData, validity and checksum checks. Unknown pixels in positive-bearing patches remain excluded from scoring.

Twenty TRAIN and ten validation overlays are marked HUMAN REVIEW PENDING. A separate normalization replay matched bit-for-bit when using the recorded stable patch-hash order. TRAIN valid-pixel means were [0.09549080, 0.11283492, 0.22933868]. Population standard deviations were [0.03479730, 0.04963028, 0.05970092], in B3, B4, B8 order. Background may include unmapped mining.

## Eight-patch diagnostic

The CPU U-Net diagnostic completed 200 updates in 16.9 seconds. All scores below are on the same eight weakly annotated TRAIN patches used for fitting. No validation score or checkpoint selection was made.

| Step | Mean masked BCE | Weak-mask IoU at 0.50 |
|---:|---:|---:|
| 0 | 0.7098 | 0.0363 |
| 25 | 0.5700 | 0.3429 |
| 50 | 0.5304 | 0.5198 |
| 75 | 0.3637 | 0.6110 |
| 100 | 0.2528 | 0.6664 |
| 125 | 0.1799 | 0.7669 |
| 150 | 0.1946 | 0.7484 |
| 175 | 0.1487 | 0.8173 |
| 200 | 0.5732 | 0.3469 |

The diagnostic passed the final-loss improvement criterion. Loss rebounded at step 200 and IoU fell from its step-175 peak. This instability limits interpretation to a check of the fit and loss wiring on weak TRAIN masks. These values establish no independent accuracy or broader model readiness. No operational model weights were produced.

Local outputs are under `outputs/phase22e_r_maus/`. The smoke, plan, per-patch receipts, manifests, summary, normalization, diagnostic and overlays are kept local. Commands from the existing Python environment, in order on a fresh recovery output directory:

```powershell
python -B -m scripts.phase22e_r_maus smoke
python -B -m scripts.phase22e_r_maus batch
python -B -m scripts.phase22e_r_maus debug
```

The diagnostic requires DATASET GO. All 21 focused tests passed.
