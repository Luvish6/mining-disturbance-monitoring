# Phase25D.2 — Supplied Python3.12 reused; dependency policy stop

2026-11-25. Continued on `phase25-minechange-india`,preserving9d6002d and4083b13 rather than resetting history. [Exact progress receipt](phase25d2-python312-progress.json).

Gates passed:8.145GiB available RAM initially,8.083GiB at setup entry;7,956MiB VRAM;C25.93GiB/D306.88GiB free. Backup inventory,frozen dataset-manifest and no-active-acquisition checks passed. Existing user-supplied Python3.12.10 venv was reused unchanged: no environment/interpreter recreation. Resolver uses existing D: cache and persistent transfer ledger. Original project `.venv`,datasets,models and TEST payloads remain untouched.

Candidates remain official torch2.11.0+cu128,torchvision0.26.0+cu128,TerraTorch1.2.14. Python≥3.12 issue is resolved. **New stop:**TerraTorch1.2.14 requires Lightly1.5.22,whose HydraCore dependency requires antlr4-python3-runtime4.9.*. That release is absent from the wheel-only index;only later runtime wheels are available. The retained resolver proof is `resolve-python312.log` in the D: cache. No compatible lock or package installation completed. This is a source-build policy blocker,not evidence that TerraMind or CUDA is incompatible.

No source build was attempted. The guard follows the [approved25D.1 proposal](../../config/phase25d1_comparison.json),`stop_before_budget_or_source_build=true`;the resolver uses`--no-build`. No extra-model/version fallback,padding,band fabrication,GEE request,training or dataset change occurred. Checkpoint transfer remains0 bytes;actual checkpoint hash,model shapes,normalization/mask behavior,frozen gradients and peak smoke memory are **UNMEASURED** because no smoke/checkpoint load ran.

Cumulative actual body/charged transfer counts,including earlier attempts,are in the JSON. Charged bytes add a conservative16KiB HTTP-header allowance per attempt,not a TLS-wire measurement. All counters remain below12GiB dependencies/250MB model. Cached sources/hashes were reused;no counter reset. Proxy binds loopback only and is stopped.

Six focused offline synthetic tests passed:budget-before-body,verified cache reuse/redirect identity,allowlist,low-RAM stop and existing-venv/no-substitution handling. No full-suite rerun. Staged publication/privacy audit passed;environments,wheels,metadata bodies and logs remain private.

**Smallest correction for approval:**allow one audited pure-Python build of the official SHA-verified antlr4-python3-runtime4.9.3 source distribution into a local D: wheel,or provide a verified compatible wheel. This exception is not authorized/executed here. Do not silently override dependency constraints or enable general source builds. Then resolve the same pins/reuse the same venv/cache/remaining counters after rechecking all gates. No model architecture change is needed. Tiny download and sole≤5-minute synthetic smoke remain unexecuted;6GiB process/CUDA limits and all original safeguards persist. Stop after this blocked25D.2 attempt.
