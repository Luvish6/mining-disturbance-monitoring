# Phase25D.1 — U-Net and frozen TerraMind Tiny readiness

2026-11-25,fromc9a6b0a,branch`phase25-minechange-india`. [Frozen proposal](../../config/phase25d1_comparison.json); [actual counts/hardware](phase25d1-summary.json). No acquisition,installation,fitting,pretrained loading,TEST access or publication of data/models occurred.

## Safety and immutable data

Backup inventory/storage gates and80 selected development backup hashes passed. All20 parent AOIs retain original district/core/TEST-buffer guards. The80-patch manifest remains `3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa`;all602 artifact hashes and spatial assignments passed. Original pseudo masks,reviewer sheets,models,RF results,river analysis and dashboard are unchanged. No historical model code changed.

## Shared-input comparison

Both systems receive actual **B2,B3,B4,VV,VH per date**,32×32 at30m. Use S2L2A BLUE/GREEN/RED and S1GRD VV/VH,not the uint8 RGB modality or GRD-as-RTC. SR×10,000 and dB use the same pinned publisher means/SDs for both systems,exactly once; constants and channel order are in the proposal. No normalization is fitted to TRAIN or VAL.

The [cached official TerraTorch registration](https://github.com/torchgeo/terratorch/blob/297b9dea723a147aef6b778041af111b71494e59/terratorch/models/backbones/terramind/model/terramind_register.py) supports named band subsets by selecting pretrained embedding columns. Constants were verified by parsing cached data literals without executing publisher code. Cached SHA256:`01ccbea7cc7ed0f49482427dbddd42e9a47d12fe1edd51ae980c9069718b1c2d`. Default12-band S2 is incompatible; the3-band named subset is conditional. **NIR/B8,red-edge and SWIR are unavailable and never invented or padded.** Derived indices/terrain/context are excluded from BOTH primary inputs; separate matched context ablations need approval.

Reuse `SiameseUNet(channels=5,width=16)`,new initialization,without changing historical8-channel or3-channel weights. Its absolute encoder difference is temporally symmetric. Proposed TerraMind uses the same frozen encoder per date,absolute feature differences and a small trainable head; its actual feature API/head layout remains unverified. Neither system can infer change direction from symmetric differences alone. Different capacities/pretraining make this a system comparison,not proof of a causal pretraining benefit. RF is not in the new active comparison.

Native30m composites differ from pretraining imagery.32×32 supplies only2×2 native16-pixel tokens/modality: positional behavior,segmentation detail and normalization/API compatibility need a real smoke test. Do not resize to pretend10m or silently pad to224. Unsupported32×32 input means BLOCKED.

## Common masks and class imbalance

Before measuring outcomes,we fixed one label-independent policy for both models: all5 channels valid in both dates;exclude any16×16 token containing an invalid input;supervise only original0/1 states,ignore255. Computational normalized-zero fills remain masked,not observations. Complete-token scoring does not establish that invalid context cannot influence global attention; missing-mask behavior remains a smoke gate. No pseudo-label threshold or source mask changed.

|Split|Original/usable patches|Usable stable0|Usable disturbance1|Positive patches/groups|Foreground prevalence|
|---|---:|---:|---:|---:|---:|
|TRAIN|68 /67|18,638|81|21 /10|0.433%|
|VAL|12 /12|3,036|60|6 /2|1.938%|

All17 TRAIN/3 VAL groups remain represented. One TRAIN patch has empty supervision:retain its record and log a skipped batch,never replace it. The new eligibility mask excludes1,694 previously labeled TRAIN cells,including3 positives,and45 VAL cells,including24 positives. Original84/84 positives and49,219/9,147 unknowns remain unchanged. TRAIN stable/positive ratio is230.10:1;proposed TRAIN-only BCE positive weight caps at10.

**Zero admitted mining references.** Shared-sensor pseudo labels use retrospective2025–26 persistence. Scores can only measure pseudo-label agreement,not mining accuracy or early warning. Only3 VAL groups/2 positive groups,spatially clustered cells,shared scenes(48 S1/212 S2 across splits),unknown mine-complex independence and incomplete original/follow-up identities limit inference. TerraMind pretraining geographic exposure is unverified.

## Delivered contracts and evaluation

`src/phase25/learning.py`:shared raw-band/normalization adapters,token/ignore masks,an injected frozen-encoder guard,masked BCE+foreground Dice,and hash-authenticated expected-frame comparison checks. No pretrained loader or training runner. `scripts/phase25d1_readiness.py` measures data/hardware only;it never forwards real data through a model. Private receipts:`outputs/phase25/qa/25d1-readiness-v1/`.

Both systems must match the frozen VAL pixel IDs/order,groups,labels,masks,dataset and contract hashes. Unknown cells contribute no gradient;empty batches fail explicitly;background-only batches use BCE because foreground Dice is undefined. Report pooled/per-group confusion counts,precision,recall,Dice/F1,IoU,FPR,predicted-positive counts,prevalence and exclusions. For zero-positive groups,recall/foreground Dice/IoU remain undefined;report FPR separately. No pixel-independence significance claims. Epoch/threshold selection on these12 pseudo-labelled VAL patches produces selection-biased agreement,not independent accuracy. Report group variation and matched completed-seed mean/sampleSD only when≥2 pairs finish.

## Hardware and checkpoint

Snapshot:RTX4060 Laptop8,188MiB/7,956MiB free,driver610.91;RAM15.29GiB/4.68GiB available;free diskC26.29GiB/D306.94GiB. Existing Python3.13.2 has torch2.15.0+cpu,CUDA unavailable;TerraTorch absent. The launcher lists no installed3.11/3.12. GPU hardware presence does not establish a compatible CUDA runtime/package lock.

Reuse Phase25A's [pinned Tiny metadata](https://huggingface.co/ibm-esa-geospatial/TerraMind-1.0-tiny/tree/2b5ac0a3ed7dd7e922ccfd595b56607f342df343):Apache-2.0,211,873,402 bytes,SHA256 `e56ea9ebcd4451078b9ca4893d5cd8a89bbee376ae16829c3e7fbbbc76de0eba`. No checkpoint exists in the scoped Phase25/default revision caches;**actual hash is unverified**. Source LICENSE/NOTICE and imagery rights remain separate.

## Bounded proposal and exact next approval

1. **Not authorized now:**resolve/pin isolated Python3.11/3.12,official CUDA PyTorch+matching torchvision and recorded TerraTorch compatibility. Proposed new environment/cache/temp under`D:/ResearchEnvironments/minechange-india-gpu-v1*`,outside existing environment/backup. Exact package/CUDA versions remain unresolved offline;no invented lockfile. Dependency transfer cap12GiB;one exact model transfer cap250MB including metadata/retries. Keep≥20GiB destination free and≥10GiB system-disk reserve;stop rather than build unexpected source dependencies.
2. Require≥8GiB available RAM and≥7GiB free VRAM;current RAM fails this conservative guard. After explicit setup/download approval,one≤5-minute,batch1,FP32 **synthetic-only GPU smoke**,no optimizer step. Verify checkpoint size/hash before load,strict key accounting,subset mapping,normalization once,paired32×32 output grid,missing-mask behavior and frozen gradients. Process RSS≤6GiB;CUDA allocated/reserved≤6GiB. Stop on OOM/NaN/hash/key/shape/API/normalization/resource failure. No generated modalities or silent fallback.
3. Only after reviewed smoke and **separate training approval**:≤30 combined minutes,three seeds42/43/44,≤5 epochs and5 minutes/fit,matched completed pairs only. Same inputs/groups/masks,AdamW3e-4,weight decay1e-4,clipping1,batch1/accumulation4,FP32,masked loss/cap10 weight. VAL loss selects epochs,patience2;thresholds0.25/0.50/0.75 select maxIoU−0.25FPR,ties lowerFPR/nearest0.50;also report fixed0.50. Log partial fits/all-background collapse;no extra recovery tuning. Budgets are not measured training runtimes.

**Decision:**U-Net adapter/loss engineering READY;frozen Tiny CONDITIONAL/BLOCKED until runtime,weights and32×32/native30m/API/mask smoke passes. Verified Indian mining training/evaluation remains NO-GO.20 focused synthetic/contract tests passed(4.18s);no full-suite rerun for isolated non-production code,as requested. Synthetic forward/backward tests make no optimizer updates and report no scientific performance. Staged publication/privacy audit passed; no dataset,weights,private frame or restricted assets are included. Stop after25D.1.
