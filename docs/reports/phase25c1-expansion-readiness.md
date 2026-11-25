# Phase25C.1 — Private expansion readiness, not acquisition

2026-11-25. Continued from60fdc9b on `phase25-minechange-india`. [Measured metadata summary](phase25c1-summary.json). No imagery/masks were opened or hashed for this audit, no GEE calls or downloads occurred, and no new dataset or labels were built. Historical25C remains16 patches;80 is a **planning target**.

## Actual reusable inventory

All20 previously preregistered development AOIs pass the original district, canonical seed42 partition,120m core and protected TEST-buffer guards. Exhaustive32×32 subdivisions also pass non-overlap/buffer checks. No TEST payload or new geographic selection was used. Backup inventory/status/storage gates passed;40 selected sidecars and backup copies were hash-checked. Existing raw NPY files were only checked for existence/size:9,180,160 bytes unopened. Source sidecar sizes total71,936 bytes; this is not an I/O-traffic counter.

| Frozen split | Cache AOIs / blocks | Additional versus25C | Proposed32×32 patches | Recorded independent S2 days BEFORE / AFTER |
|---|---:|---:|---:|---|
| TRAIN |17 (East9,West8)|14|68|24–52 /28–57|
| VAL (development only)|3 (East1,West2)|2|12|24–51 /29–56|

TRAIN blocks:83:557,83:561,83:563,84:558,85:565,86:555,86:561,87:557,87:563,87:564,88:556,88:558,88:563,88:567,89:557,91:556,91:558. VAL remains80:559,87:556,88:564; no group was moved. The latter two provide separate development-validation geography but **positive-class support is unknown**. Neither VAL masks nor outcome tables were inspected or used for selection. Source-scene counts and file existence cannot establish valid ground pixels, pseudo-positive support or mining evidence. Cache dimensions/radiometry/masks require a later approved offline replay.

Every AOI has recorded paired S1 counts (TRAIN13/26 BEFORE,11/22 AFTER; VAL13/11), S2 timestamp lists and follow-up joined-scene counts. Counts may include overlapping scene fragments; they are not independent days or orbit certification. Follow-up exact original IDs/dates remain absent. Three TRAIN AOIs have existing25B.1 SRTM/WorldCover/CHIRPS context receipts; JRC supports110 cells in one of those. This task did not re-read those raster values. The other17 AOIs lack that acquired context, including all3 VAL groups. Slope is present in the legacy schema. Fire/roads/geology/mining-context gaps remain unchanged.

## Dataset design without outcome selection

Use **all20 eligible existing AOIs**, rather than choosing a positive-rich subset. Four exhaustive non-overlapping crops per parent give a target68 TRAIN +12 VAL =80 patches/81,920 cells if later QA passes; retain the original16 patches/results separately and record logical lineage so they are not duplicated in a combined version. Adjacent crops and shared scenes are dependent;20 blocks are not verified independent mine complexes. Evidence-group/mine-complex cross-split checks remain necessary before independent evaluation.

Mining-context disturbance, potential stability and challenging alternatives (farming, forestry, exposed ground, roads/construction, erosion/shadow) are **hypotheses for later blinded review**, not classes assigned here. Existing30-item review design comprises8 PERSISTENT,6 PARTIAL,6 RECOVERING and10 CONTROL discovery strata. CONTROL is not verified mining-free; temporal strata do not prove mining. Do not use these strata, scores or model outcomes to select VAL. Spatial coverage is expanded by the unchanged original roster, with no patch filtering by foreground. No new class-balancing, rule threshold or normalization fit is authorized.

## Bounded missing-data proposal — NOT EXECUTED

Private frozen plan:`outputs/phase25/datasets/25c1-plan-v1/plan.json`; SHA256 `e2fa7d831421bae8bd338060193f6104b66ec25524dec5417fd8abfc0e363d84`.
Companion acquisition contract:`acquisition-contract.json`; SHA256 `b10e1f803bf38f5471c796a906e5e3947e820a297a3d434e0efdae7376c8a98f`.

The contract binds exact original AOI bounds/affines, sources and seasons to the existing25B.1 preregistration. Propose seven context bands for the17 missing AOIs only: SRTM elevation, WorldCover class, two CHIRPS totals, two daily-count diagnostics and JRC occurrence. Keep source masks and native temporal/spatial support. No new SAR/optical imagery is needed for the first cache replay. First priority is all3 VAL context gaps (hash order88:564,87:556,80:559), then14 TRAIN gaps in deterministic seed42 hash order. No priority uses observed outcomes. Known unsupported MODIS/OSM/geology/mining layers are not requested again without new source evidence.

Estimate:4 initialization/auth/discovery attempts +10 metadata chunks (two AOIs/chunk, all20) +34 export-RPC/TIFF attempts +10 retry reserve = **58 attempts**. Raw seven-band64×64float32 context is1,949,696 bytes total before TIFF/compression/headers. Planning allowance **30MB response bodies** covers metadata, TIFFs and reserve; it is an estimate, not measured traffic or guaranteed cost. Proposed hard cap60 requests/100,000,000 response-body bytes,2MB per-response bound, all retries/auth/discovery counted under one persistent meter and lock. Stop before caps or oversized/identity/grid failures; do not substitute sites. Existing approximate55MB scaled patch payload suggests a55–75MB dataset planning range, with≤250MB working-data allowance and1GB free scratch; runtime/RAM must be measured before any fitting. No model fit is proposed here.

**Separate user approval and a committed executable acquisition specification are required.** This planner has no acquisition mode. A future implementation must verify both plan/contract hashes, run one smoke test, reuse valid caches, never overwrite25B/25C, and retain partial receipts on failure. Exact current source IDs/dates and orbit settings must be captured with new exports; current metadata queries do not certify old cache membership.

## Provenance certification and release gates

First-choice original-source proof is the original exporter/task-operation receipt or immutable original scene list/log. Existing legacy sidecars contain S2 times and S1 counts but not complete original IDs; follow-up records contain counts without exact source dates. Smaller reviewer-chip metadata cannot certify full-AOI composite membership. The existing reconstructed24 S1/214 S2 query identities corroborate some caches but are not original-source certification. Without authentic original logs, retain INCOMPLETE or approve a separately versioned reconstruction; never rewrite old receipts as certified. No broad archive search was repeated.

Redistribution review must retain Copernicus S1/S2 attribution, SRTM NASA/USGS/JPL source policy, WorldCover CC-BY4.0, CHIRPS citation and JRC/Copernicus ECJRC/Google conditions, with exact product/version/native support. WorldCover2021 and JRC1984–2021 are context, not current labels; coarse CHIRPS is not independent30m rainfall. GSI/Bhuvan/Bhoonidhi extraction/rights remain unresolved. Private Planet/LISS-IV imagery is excluded. Before release, resolve source membership, source-specific redistribution conditions, participant identity/consent and coordinate privacy; no public dataset license or publication approval is created here.

## Blinded review import and adjudication handoff

`src/phase25/review_import.py` and `scripts/phase25c1_readiness.py --import-reviews` reuse the existing30 neutral IDs and original CSV schema/allowed interpretations. They reject foreign/duplicate/missing IDs, incomplete interpretations, automatic A/B placeholders as completed identities, non-UTC/future timestamps, non-UNKNOWN attribution and the same declared reviewer on both sheets. Distinct supplied identities are a necessary declaration, not independent proof of actual reviewer independence. Conflicts enter ADJUDICATION_REQUIRED; matching visible interpretations remain INTERPRETATION_AGREEMENT_ONLY. Both paths keep mining UNKNOWN, reference_label null and verified_reference false.

The coordinator-only JSON has blank adjudicator, decision, polygon, independent evidence/date, positional uncertainty and rights fields. Originals are preserved; input copies/hashes and the frozen roster are recorded in a fresh private output. Do not show reviewers the crosswalk, splits, candidate strata, pseudo masks or model maps. Existing blinded HTML/chips remain unchanged. Reusing shared Sentinel inputs for visible-change interpretation cannot by itself satisfy independent mining-label admission; adjudicated external evidence must still pass `src/phase3/admission.py`, geometry, source-independence and spatial/evidence-group gates in the existing protocol.

An offline import of the original blank sheets yielded **30 PENDING,0 agreements,0 disagreements,0 verified labels**. This is interface verification, not completed human review. Private example:`outputs/phase25/receipts/25c1-review-import-v1/`.

```powershell
# Metadata-only planner: one immutable target, no overwrite or online fallback
python -B -m scripts.phase25c1_readiness --plan --backup (Read-Host 'Verified private backup root')
# When genuine completed sheets arrive; use a NEW private output path:
python -B -m scripts.phase25c1_readiness --import-reviews <reviewer-A.csv> <reviewer-B.csv> --out outputs/phase25/receipts/<new-import-id>
```

## Checks and next approval

Six focused tests passed: blank-input preservation, agreement without admission, disagreement/adjudication, reviewer/ID/attribution rejection, metadata date/support semantics and no payload/acquisition interface. Full offline regression: **405 passed in60.96s**. Both plan/contract hashes,40 sidecar hashes, original reviewer sheets and the prior25C manifest passed integrity verification. Staged publication/privacy audit passed; only code, tests and sanitized planning documentation are included. Private plans, source metadata and submissions remain excluded. No requests, downloads, training, TEST access, label admission or operational alerts. Original backup/tag/branch,30 review items, pseudo-state rules, datasets, U-Net/RF and river results remain unchanged.

**Expansion plan READY FOR APPROVAL; acquisition NOT AUTHORIZED.** Actual reusable coverage is20 metadata-described cache AOIs, not80 completed patches or valid mining positives. Independent supervised training and release remain NO-GO. Next approval should authorize metadata-to-raster QA/replay and the exact missing-context/provenance pilot, without choosing new VAL groups based on replay outcomes. If no pseudo-positive VAL support exists, report it; never replace groups to manufacture support. Independent mining evaluation additionally requires external dated/registered evidence and two-reviewer admission of both classes across multiple groups. Stop after25C.1.
