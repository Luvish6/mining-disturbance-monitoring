# Phase25D.2 â€” Approved offline RAM verification completed

2026-11-25. Resumed8a66e02 on phase25-minechange-india. **PASS for the approved synthetic compatibility/resource smoke under the documented sampled working-set accounting.** No research-training authorization or Indian scientific-performance claim follows.

## Gates and isolation

Available RAM8.213GiB initially,8.244GiB at preflight and8.241GiB at launch; free VRAM7,956MiB. C:27,795,488,768bytes/D:320,765,247,488bytes free initially. Backup status/inventory fingerprint, immutable80-patch dataset manifest, frozen dependency lock and absent acquisition lock passed. Python3.12.10, torch2.11.0+cu128, torchvision0.26.0+cu128 and TerraTorch1.2.14 reused without installation/resolution/build. Pinned211,873,402-byte Tiny checkpoint SHA `e56ea9ebcd4451078b9ca4893d5cd8a89bbee376ae16829c3e7fbbbc76de0eba` reverified offline. Transfer ledger byte-identical before/after; no acquisitions, downloads or budget resets. Model charge211,938,938bytes and dependency charge3,138,453,534bytes unchanged.

Exactly one newly approved batch1 FP32 rerun was executed; no retries. Original smoke receipts are unchanged. New private directory: outputs/phase25/experiments/25d2-ram-verification-v2/. It contains worker-identity.json, process-tree.jsonl, monitor.json, result.json, comparison.json, smoke.log and integrity.json. Separate preflight receipt: outputs/phase25/receipts/25d2-ram-rerun-preflight.json. [Sanitized results/hashes](phase25d2-ram-verification.json).

## Measured resources and process identity

| Item | Result | Limit |
|---|---:|---:|
| Conservative process-tree peak working set |1,859,121,152bytes (1.731GiB)|6GiB|
| Model worker peak working set |1,854,644,224bytes|included above|
| CUDA peak allocated |40,852,480bytes (38.96MiB)|6GiB|
| CUDA peak reserved |46,137,344bytes (44MiB)|6GiB|
| Wall time including imports/checks |43.366seconds|300seconds|

Worker self-reported PID3144/parent22640. The watchdog independently observed that worker under launcher22640, whose parent was supervisor22884. Both launcher and actual worker memory were counted; worker_observed=true.363samples were recorded, requested interval0.1seconds, maximum observed sample gap0.1270969seconds. No memory, timeout, watchdog, OOM or API failure; returncode0. Owned-tree termination remains active on failure.

The accounting sums observed per-process peak working sets, so individual peaks need not occur simultaneously: it is conservative for observed processes. It is sampled Windows working-set/RSS monitoring, not a Windows Job Object/kernel-enforced allocation quota. Very short-lived unobserved descendants and non-working-set memory are outside the measurement. CUDA values are PyTorch allocated/reserved peaks, not whole-device driver/context memory. These limitations prevent a claim of universal hard memory bounds, but the observed worker/tree stayed well below the prescribed limits.

## Functional comparison with preserved prior smoke

Before launch, AST comparison verified the synthetic model computation unchanged; only worker identity logging was added to the child. Inputs, seed42, architecture, checkpoint, normalization, masks, random diagnostic head and no-optimizer behavior were retained.

Both runs: native paired1x5x32x32 B2/B3/B4+VV/VH; S2L2A BLUE/GREEN/RED and S1GRD VV/VH;12feature layers, final1x4x192, head logits1x1x32x32;768masked-valid cells. Normalization-once, nonfinite computational-fill equivalence, zero ignored-logit gradients, finite head backward and frozen/no-gradient encoder checks all matched. No image padding/resizing; only head logits interpolated. No optimizer steps.

Prior and rerun masked loss both0.6502230167388916; difference exactly0.0. CUDA peaks identical. All compared contract/functional fields matched. Prior102.190seconds versus rerun43.366seconds is not a controlled speed benchmark. This diagnostic loss is not accuracy. Input masks exclude incomplete tokens from supervision but are not explicit encoder attention masks; valid embeddings may depend on fills.30m/pretraining-domain shift remains unresolved.

Twenty-two focused adapter/watchdog tests passed. Publication/privacy audit passed for the staged safe changes. No dataset payload access, TEST access, research training, real inference, GEE, dashboard work or new phase. Indian supervised training stays NO-GO, candidates UNKNOWN, operational alerts zero. Phase25D.2 stops here; any later research experiment requires separate approval.
