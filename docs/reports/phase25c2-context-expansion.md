# Phase25C.2 — Bounded context recovery and private expansion

2026-11-25. Continued fromea25bb7 on `phase25-minechange-india`. [Preregistration](phase25c2-preregistration.md) was committed as31c49d6 before the live session; [sanitized actual statistics](phase25c2-expanded-dataset-summary.json). Original25C is preserved, not expanded in place. No training, TEST payload access, human-review alteration, threshold change, dashboard work or public dataset release occurred.

## Gates and actual offline QA

Exact25C.1 plan and contract SHA256 values matched `e2fa7d831421bae8bd338060193f6104b66ec25524dec5417fd8abfc0e363d84` / `b10e1f803bf38f5471c796a906e5e3947e820a297a3d434e0efdae7376c8a98f`. Their bytes remain unchanged, including historical authorized=false; the user's25C.2 instruction separately authorizes this execution. Stable tag08604dea, historical branch, verified backup inventory/storage gates and original spatial guards passed.80 selected development cache/metadata files and backup copies passed SHA256 checks. No whole-project audit or new backup was performed; the original backup remains on the same physical disk and is not off-device protection.

All20 fixed AOIs passed full-footprint original-district, seed42 block/core and protected TEST-buffer guards **before payload reads**. Offline raster QA verified21×64×64 legacy bands,7×64×64 follow-up arrays, frozen rules, NoData/count behavior and source hashes. All4 historical pseudo masks reproduced exactly. No duplicate raw-array payload hashes were found; no AOI was selected, dropped or replaced based on results. Valid common screening support was69,449/69,632 TRAIN cells and12,284/12,288 VAL cells. The latter includes retrospective follow-up support, not early prediction evidence.

## Actual dataset and class distribution

| Frozen split |32×32 patches| Blocks | Cells | Potential disturbance1 | Potentially stable0 | Uncertain/ignore255 |
|---|---:|---:|---:|---:|---:|---:|
|TRAIN|68|17|69,632|84|20,329|49,219|
|VAL (development)|12|3|12,288|84|3,057|9,147|
|Total|**80**|**20**|**81,920**|**168**|**23,386**|**58,366**|

Potential-disturbance support spans21 TRAIN patches/10 TRAIN blocks and6 VAL patches/2 VAL blocks (87:556 and88:564).80:559 still has zero pseudo-positives; it was retained unchanged. Potential-disturbance area is15.12ha within73.728km², **not mining area**. All states are shared-source, uncalibrated, retrospective pseudo labels; verified reference labels remain0. No mining performance is computed. The original30 blinded review items/sheets remain unchanged and pending.

The versioned29-slot contract is unchanged: paired VV/VH,B2/B3/B4,NDVI/BSI/NDWI; four signed changes; slope and context. Raw B8/SWIR are not reconstructed. Validity masks and QA counts remain separate; follow-up count is retrospective diagnostic evidence, not an earlier model input. Missing values stay NoData/false validity/blank CSV, not zero substitutes.

## Acquired source coverage and traffic

All17 missing-context AOIs were acquired in the frozen priority order. Existing verified context for3 TRAIN AOIs was reused. The first new TIFF passed64×64×7,30m EPSG32646,affine,source-graph band order,counts and NoData checks before subsequent downloads. Every accepted TIFF passed the same checks. Native nearest-neighbor sampling onto30m does not create fine-resolution context.

| Layer |TRAIN valid cells|VAL valid cells| Native/temporal limitation |
|---|---:|---:|---|
|SRTM elevation and legacy slope, each|69,632|12,288|~30m,February2000 terrain; not excavation depth|
|WorldCover|69,632|12,288|10m,2021 model-derived classes; context only|
|CHIRPS seasonal-total change|69,632|12,288|0.05° (~5.6km);152 BEFORE/151 AFTER dates; unequal season lengths|
|JRC occurrence|231|15|30m,1984–2021; historical context; missing is not no water|
|Fire,roads,geology,mining context, each|0|0|Explicitly unsupported/unavailable|

Optical signed dNDVI/dBSI support:69,473 TRAIN /12,286 VAL cells. SAR signed-change support:69,632 /12,288. Environmental context neither alters pseudo states nor independently establishes causes.

**One session completed:48 counted attempts and1,528,746 received response-body bytes**, below60 /100,000,000. This includes auth/discovery,10 metadata requests and17 export-RPC/TIFF pairs. No request failures/retries or pending reservations occurred. The prior25B.1 ledger remains unchanged; its budget was not reset. The new persistent ledger is `outputs/phase25/datasets/25c2-acquisition-v1/http-ledger.jsonl`; global lock is released. No more requests are authorized by this completion. Header/TLS wire overhead is not the response-body counter specified by the frozen contract.

## Provenance, duplicates and rights

Current queries capture48 unique S1 and316 unique S2 before/after IDs, plus192 unique follow-up S2 IDs, dates,collection references and native grids. All40 S2 timestamp multisets and40 S1 counts match original before/after metadata. This is corroboration, **not certification of original scene membership**. Original follow-up identities remain incomplete even with new query lists. NPY georeferencing is inherited from the frozen validated exporter, not newly independently measured absolute accuracy.

Shared current scene IDs across TRAIN/VAL:48 S1 /212 S2. Such scene reuse is not duplicate ground windows; all patches remain geographically disjoint with original buffers. It does introduce common acquisition conditions, and the20 spatial blocks are not verified independent mine complexes. Future evaluation must acknowledge this dependence and establish independent reference/evidence groups. No frozen split was changed to remove it.

Copernicus Sentinel acknowledgement, NASA/USGS/JPL SRTM source policy, ESA WorldCover CC-BY4.0, CHIRPS citation and JRC/Copernicus ECJRC/Google attribution remain required. Static/coarse sources are never ground truth or equal-resolution observations. GSI/Bhuvan/Bhoonidhi/OSM/fire access gaps are not bypassed. No Planet/LISS-IV pixels, restricted orders, credentials, geodata or generated datasets enter Git. Independent source/date/positional/reviewer admission and complete redistribution/privacy review remain unresolved. **Public release and verified Indian supervised training remain NO-GO.**

## Reproducibility and checks

- Offline QA:`outputs/phase25/qa/25c2-offline-v1/`.
- Session/source caches:`outputs/phase25/datasets/25c2-acquisition-v1/`.
- Expanded private dataset:`outputs/phase25/datasets/25c2-v1/` with80 patch folders,CSV tables,per-band masks,three-state masks,20 private QA examples and source receipts.
- Independent integrity summary:`outputs/phase25/qa/25c2-integrity-v1/summary.json`.
- Manifest SHA256:`3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa`.

The existing25C crop writer was factored for reuse; no scientific processing or legacy result was changed. Build35.03s wall/28.67s process CPU before final replay. Private payload55,513,524 bytes. Independent verification61.01s:602 artifact hashes,132 source hashes,all80 rasters and81,920 CSV rows/unique pixel IDs,mask/grid/band/change arithmetic,zero overlap/buffer violations,unchanged original25C/reviewer artifacts and released lock. No peak-RAM measurement was made.

23 focused tests and the full offline suite **411 passed in58.24s** before acquisition. These cover frozen hashes,context grids/bands/counts,masked signed changes,metadata completeness,no-overwrite writing,offline EE graphs and inherited budget/resume/label guards. Staged publication/privacy audit passed; only safe code/tests and sanitized documentation are included. Private imagery,CSV tables,source receipts and generated datasets remain excluded. Synthetic fixtures are software tests, not new scientific evidence or model training.

Entry point:`python -B -m scripts.phase25c2_expand --qa|--acquire|--build --backup <verified-private-backup>`. Completed output targets are immutable; do not rerun QA/build into them. Acquisition resumes only this fingerprinted session with the same persistent meter; completed caches require no new auth. No additional phase is started. Stop after25C.2; references remain UNKNOWN and operational alerts0.
