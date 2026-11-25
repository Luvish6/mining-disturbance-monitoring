# Phase 25D.2 — Isolated CUDA stack installed; RAM stop before model loading

2026-11-25. Resumed from abde994 on phase25-minechange-india. Reused the supplied Python 3.12.10 venv, audited ANTLR wheel, persistent source cache and cumulative transfer ledger; no source rebuild or environment recreation.

## Verified progress

Initial RAM gate passed at 8.099 GiB, setup entry at 8.118 GiB and pre-installation at 8.076 GiB. GPU free 7,956 MiB of 8,188 MiB; initial C: free 27,793,874,944 bytes and D: free 329,476,165,632 bytes. Backup status/inventory fingerprint, immutable dataset manifest SHA and no-active-acquisition checks passed. Original environment and all dataset payloads were untouched; frozen TEST remained sealed.

Wheel-only resolution and hash-required installation completed successfully in the existing isolated environment. Installed stack: Python 3.12.10, torch 2.11.0+cu128, torchvision 0.26.0+cu128, TerraTorch 1.2.14. The installer prepared 111 packages in 5m34s; this is package preparation time, not model/runtime performance. The sole source exception remained the previously approved local ANTLR4.9.3 wheel. No additional source builds, model substitutions or dependencies outside the locked resolution were enabled.

Frozen requirements-py312.lock SHA-256: `37d10c252beb3d68f48ea6087a304ba71fa6622f03b79e946d68dd26b253ab70`. Installation and setup-complete receipts remain in the private D: environment cache. The lock records distribution hashes. Cumulative dependency transfer charged: 3,138,453,534 bytes, including the proxy's conservative HTTP-header allowance and previous attempts, below 12 GiB. Model transfer remains 0 bytes; no budget reset. No retries were needed in this resume.

## Mandatory stop

Post-installation available RAM was **7.930 GiB**, below the required 8 GiB. Stopped before checkpoint acquisition, torch/model import or GPU execution. GPU free remained 7,956 MiB. The actual installed CUDA runtime, checkpoint loading, native 32x32 named-band handling, normalization/masks, output shapes, frozen gradients and smoke peak memory are UNMEASURED. Successful installation does not establish compatibility.

Next action: free application RAM without altering system settings, then resume after all gates pass. First verify installed distribution identities without reinstalling; reuse setup-complete receipt and the lock. Download only the pinned Tiny checkpoint under the unchanged 250 MB model cap, verify its expected size/SHA, then run the one authorized synthetic smoke with <=300s wall and <=6 GiB process/CUDA limits. Do not repeat dependency installation or the ANTLR build. No research training is authorized; Indian supervised training remains NO-GO, candidates UNKNOWN and operational alerts zero.
