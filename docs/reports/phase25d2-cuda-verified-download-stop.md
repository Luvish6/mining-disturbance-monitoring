# Phase25D.2 — CUDA verified; checkpoint redirect blocked

2026-11-25. Resumed ca6ffc2 on phase25-minechange-india. No reinstall, rebuild or dependency resolution. Existing requirement-lock SHA `37d10c252beb3d68f48ea6087a304ba71fa6622f03b79e946d68dd26b253ab70`, backup verification/inventory fingerprint, immutable 80-patch manifest and absent acquisition lock passed. TEST stayed sealed; dataset payloads were not opened or modified.

Initial available RAM8.103GiB; pre-download RAM8.125GiB. VRAM7,956MiB free of8,188MiB. C:27,681,636,352bytes/D:320,977,121,280bytes free initially. Installed distribution metadata matched Python3.12.10, torch2.11.0+cu128, torchvision0.26.0+cu128 and TerraTorch1.2.14. Actual torch import confirmed CUDA available, CUDA12.8 and NVIDIA GeForce RTX4060 Laptop GPU. No packages were modified.

## Download stop

The sole pinned HF resolve URL was requested for revision `2b5ac0a3ed7dd7e922ccfd595b56607f342df343`, file TerraMind_v1_tiny.pt. It returned HTTP302 redirect to a host rejected by the HTTPS source allowlist. The downloader failed before any redirected request or checkpoint body. No retries, host-check bypass or alternate model occurred. The existing ledger retained the request: model body0bytes, conservative charge16,384bytes of the250,000,000-byte cap. Dependency cumulative charge remains3,138,453,534bytes. Header charge is a conservative allowance, not a TLS-wire measurement.

Expected checkpoint size211,873,402bytes; expected SHA `e56ea9ebcd4451078b9ca4893d5cd8a89bbee376ae16829c3e7fbbbc76de0eba`. Actual checkpoint hash/size remain UNVERIFIED because no payload was obtained. The failed redirect target was not persisted by the current downloader, so its identity cannot be established from this receipt; no signed URL or credential is published.

The approved single GPU smoke remains UNEXECUTED. Native32x32 paired named-band inputs, normalization, masks, model/head shapes, frozen gradients and smoke resource peaks remain UNMEASURED. CUDA availability alone is not model compatibility.

Smallest next correction: retain the redirect destination hostname (never signed query strings) in the transfer receipt; authenticate that exact delivery host against official HF/Xet documentation before permitting it. Preserve HTTPS, pinned revision/hash, redirect limit and all cumulative caps. Then retry only the pinned acquisition after gates pass; do not reinstall. No alternate checkpoint or input resizing is authorized. Stop after25D.2; no research training. Indian supervised NO-GO, UNKNOWN candidates and zero operational alerts remain unchanged.
