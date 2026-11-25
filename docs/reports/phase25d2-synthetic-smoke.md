# Phase25D.2 â€” Tiny compatibility smoke; resource certification incomplete

2026-11-25. Continued from e6df01d on phase25-minechange-india. **Functional synthetic smoke PASS; process-RAM certification BLOCKED. No research training authorized.** Existing packages, dataset, historical results, frozen TEST and model contracts preserved.

## Gates, source and acquisition

RAM8.215GiB initially,8.287GiB for redirect diagnosis,8.309GiB for acquisition and8.305GiB before smoke; VRAM7,956MiB free. Disk reserves passed. Verified backup status/inventory fingerprint, unchanged80-patch manifest SHA `3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa`, requirement lock SHA `37d10c252beb3d68f48ea6087a304ba71fa6622f03b79e946d68dd26b253ab70` and absent acquisition lock. Stable annotated tag still resolves to08604dea4fe39641ea32ebda8a37532669b52933. No dependency installation/resolution/build occurred.

Installed Python3.12.10, torch2.11.0+cu128, torchvision0.26.0+cu128 and TerraTorch1.2.14 were reused. Prior actual import verified CUDA12.8 and RTX4060; this run performed CUDA model operations successfully.

Redirect destination was us.aws.cdn.hf.co. [Official Hugging Face model-download documentation](https://huggingface.co/docs/hub/models-downloading) lists this exact CDN hostname. Added only that exact host for model transfers; HTTPS, source pinning, checksum and cap guards remain. Receipts now retain redirect hostnames without signed URLs/query strings. One diagnostic302 and the successful acquisition were charged to the existing ledger.

Downloaded only ibm-esa-geospatial/TerraMind-1.0-tiny, revision2b5ac0a3ed7dd7e922ccfd595b56607f342df343, TerraMind_v1_tiny.pt. Exact size211,873,402bytes and SHA-256 `e56ea9ebcd4451078b9ca4893d5cd8a89bbee376ae16829c3e7fbbbc76de0eba` verified. Apache-2.0 checkpoint remains private in the existing D: cache. Cumulative model charge211,938,938/250,000,000bytes; dependency charge3,138,453,534/12GiB unchanged. Charges conservatively include16KiB per HTTP attempt, not exact TLS-wire overhead. No budgets reset.

## One completed offline synthetic run

Private receipts: outputs/phase25/experiments/25d2-synthetic-smoke-v1/{result.json,monitor.json,smoke.log,resource-accounting-caveat.json}. [Sanitized machine-readable summary](phase25d2-synthetic-smoke.json).

- Wall102.190seconds, return code0, batch1 FP32, no optimizer steps. Seed42. HF/Transformers offline flags set; no automatic pretrained acquisition.
- Native input per date1x5x32x32; B2/B3/B4 mapped to S2L2A BLUE/GREEN/RED, VV/VH to S1GRD. No fabricated bands, padding or input resizing. Fixed publisher normalization applied once and numerically checked against the adapter.
- Every required encoder key/shape existed in the pinned checkpoint, strict subset load succeeded;154 unused checkpoint keys from other embeddings and decoder components were excluded. Named-band projection selection used the official helper after weight loading.
- Twelve encoder feature layers; final feature1x4x192, corresponding to2x2 native16x16 tokens after modality merging. Small linear absolute paired-feature-difference head produced1x1x32x32 logits by interpolating head logits only.
- Synthetic common token support768cells. Nonfinite-input fills were equivalent; ignored pixels had exactly zero loss gradient. Frozen encoder parameters had no gradients; head backward finite. Masked diagnostic loss0.650223 is a software check, not scientific performance.
- CUDA peak allocated40,852,480bytes and reserved46,137,344bytes(44MiB), below6GiB. Per-process CUDA allocation fraction0.70 was also set. No OOM occurred. A Triton flop-counting warning did not prevent completion; no Triton package was installed.

## Confirmed watchdog defect and honest stop

The original external monitor sampled the Windows venv launcher only. Its4,464,640-byte RSS reading is **not the model worker peak** and cannot certify the6GiB process-memory gate. Original receipts are preserved; a separate caveat records the failure. Functional results remain actual measured synthetic results, but overall resource certification is incomplete.

Corrected the monitor to include recursive launcher descendants and conservative sampled peak working sets, with owned-tree termination. Added a regression fixture where a tiny launcher has a worker exceeding6GiB. No second model run occurred: exactly one approved smoke has been consumed. A newly approved resource-verification run is required before claiming full25D.2 resource compliance; it must reuse the verified checkpoint and installed environment, download nothing, preserve all limits and not train.

## Limitations and checks

Input mask handling is computational fill plus complete-token support/loss exclusion; this encoder has no explicit spatial attention mask. Valid embeddings may still depend on filled invalid tokens. Missing full modalities, real-data robustness and scientific utility are not established. Native32x32 operation does not remove the30m/pretraining-domain shift. No independently verified Indian labels, mining accuracy or operational readiness are implied.

Twenty-one focused adapter/setup/smoke tests passed. Publication/privacy audit passed for the staged safe source, tests and documentation. No full-suite rerun, GEE, dataset payload access, frozen TEST access or research training. Indian supervised NO-GO, candidates UNKNOWN and operational alerts zero persist. Stop after25D.2; do not begin25D.3.
