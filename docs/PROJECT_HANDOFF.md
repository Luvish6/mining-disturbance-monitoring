# Project handoff: read this first (any new Claude or Codex session)

This file is the single entry point for resuming the project with no chat history. It summarises what was done, what is pending, and the rules every session must follow.

The project's rules for agents are in [AGENTS.md](../AGENTS.md). The numbers behind every claim are in `docs/reports/`.

## 1. What the project is

- **What it is.** A B.Tech major project and research prototype: *Multi-Sensor Mining-Related Disturbance and Downstream River Monitoring Using Sentinel-1 SAR and Sentinel-2 Optical Data*.
- **Primary study.** East and West Jaintia Hills, Meghalaya, on the Lukha and Myntdu rivers.
- **Secondary layer.** India-wide discovery leads.
- **Repository.** GitHub `Luvish6/mining-disturbance-monitoring`.
  - The preserved branch is **`phase22-label-sources`**. All Phase 25 development must use **`phase25-minechange-india`**; do not merge back without approval.
  - `main` is the intended publication branch. Do not merge into it without the user's say-so.
- **Goal.** A working dashboard, a complete pipeline and a publishable paper. Drafts are [docs/paper-draft.md](paper-draft.md) and the IEEE LaTeX version in [docs/paper/ieee-paper.tex](paper/ieee-paper.tex).

## Verified rollback safeguard — 2026-11-25

Stable tag `pre-minechange-india` points to `08604dea4fe39641ea32ebda8a37532669b52933` and is pushed. A private full-parent backup on D: verified 72,005 files / 7,918,850,848 bytes with zero mismatches or missing files. See [rollback commands and limitations](reports/phase25-backup-rollback.md). D: shares the physical disk with C:, so off-device protection is still recommended. New outputs belong under `outputs/phase25/` in unique run directories; no overwrites. Active development branch is `phase25-minechange-india`, while `phase22-label-sources` remains at d0b6dd1. Phase 25B is now complete as cached-only engineering; see the next section.

## Phase 25 extension — 2026-11-25

Phase 25A feasibility is complete; see [the focused report](reports/phase25a-feasibility.md) and [phase progress](phase25-progress.md). MineC2FNet is the primary methodological reference; TerraMind tiny is conditional on raw-band compatibility, an approved isolated environment and a memory smoke test. The host has 8 GB-class RTX 4060 hardware, but the current torch environment is CPU-only. No acquisition, research training, new labels or dashboard change occurred. **Phase 25B was subsequently authorized cached-only and completed; STOP before acquisition, training, publication or 25C–25G without approval.** Historical RF/U-Net, TEST sealing, river findings and Planet restrictions remain in force.

## Phase 25B cached-only result — 2026-11-25

[Report](reports/phase25b-cached-features.md), [summary](reports/phase25b-summary.json), `config/phase25b_v1.json` and `scripts/phase25b_cached.py` define the new isolated pipeline. Backup rechecked; four guarded TRAIN/VAL AOIs produced 36 potential-disturbance, 4,837 potentially stable and 11,511 uncertain cells. These are shared-source retrospective pseudo-states, never reference labels. Four of twelve domains are populated; eight remain unavailable. Legacy scene IDs remain incomplete. 19 focused and 382 full offline tests passed. Outputs stay in `outputs/phase25/experiments/25b-v1/`; historical dashboard/river/models are unchanged. **STOP after 25B; no acquisition, training or later phase without user approval.**

## Phase 25B.1 recovery — 2026-11-25

[Report](reports/phase25b1-recovery.md), [committed preregistration](reports/phase25b1-preregistration.json), `scripts/phase25b1_recover.py` and `src/phase25/acquisition.py`: one locked pilot completed on the same three TRAIN AOIs. 14 requests / 1,069,012 response-body bytes. SRTM, WorldCover and CHIRPS cover all 4,096 cells per AOI; JRC covers only 110 cells in one AOI. Fire has no complete seasonal support; OSM returned HTTP 406, roads remain missing. Current queries recover 24 unique S1 and 214 S2 IDs, corroborated by legacy timestamp/count metadata but not certified as original cache source identities. All four prior pseudo-state hashes remain unchanged; no recalibration, labels, training or TEST payload access. Private outputs: `outputs/phase25/datasets/25b1-v1/`. **This task's bounded acquisition approval is exhausted; STOP before further acquisition, training, publication or Phase25C.**

## Phase 25C private pilot — 2026-11-25

[Report](reports/phase25c-private-pilot.md), [draft card](reports/phase25c-dataset-card.md), `scripts/phase25c_dataset.py` and `src/phase25/dataset.py`:16 non-overlapping32×32 patches /16,384 cells,29 feature slots,12 TRAIN patches from3 blocks and4 VAL patches from1 block. Frozen pseudo counts remain36 potential disturbance /4,837 potentially stable /11,511 uncertain. VAL has zero potential-disturbance cells and no recovered B1 context. Original scene/follow-up provenance remains incomplete. Private outputs: `outputs/phase25/datasets/25c-v1/`; all source hashes unchanged, no requests/training/TEST payload access. Loader requires explicit pseudo opt-in and refuses verified-reference promotion. **Private packaging GO; verified training/evaluation/release NO-GO. STOP after25C; no later phase without approval.**

## Phase25C.1 expansion readiness — 2026-11-25

[Report](reports/phase25c1-expansion-readiness.md), [metadata counts](reports/phase25c1-summary.json):20 eligible cache AOIs (17 TRAIN/3 VAL),14 additional TRAIN +2 additional VAL groups. Target80 non-overlapping crops is a plan, not a new dataset; pixel validity/positive support were not inspected.17 AOIs lack recovered core context. Private plan/contract in `outputs/phase25/datasets/25c1-plan-v1/`, proposal58 requests/30MB expected with60/100MB hard caps, NOT authorized. `src/phase25/review_import.py` and `scripts/phase25c1_readiness.py` support original30 neutral items, preserving originals and preventing interpretation agreement from becoming mining labels. Blank-sheet import:30 pending/zero admitted. **STOP for approval before acquisition or raster replay; no training, release or25D.**

## Phase25C.2 private expansion — 2026-11-25

[Report](reports/phase25c2-context-expansion.md), [actual counts](reports/phase25c2-expanded-dataset-summary.json): all20 preregistered AOIs passed offline QA. One locked session completed17 new context rasters with48 requests/1,528,746 body bytes;3 existing context caches reused. New `outputs/phase25/datasets/25c2-v1/`:80 patches (68 TRAIN/12 VAL),81,920 cells,29 slots. Pseudo counts TRAIN84 disturbance/20,329 potentially stable/49,219 uncertain; VAL84/3,057/9,147. Potential positives span10 TRAIN/2 VAL blocks; no labels admitted. SRTM/WorldCover/CHIRPS complete; JRC231 TRAIN/15 VAL cells; unsupported layers missing. Original25C,reviewer sheets,thresholds,splits and backups unchanged. Current IDs corroborate legacy metadata but remain uncertified originals; scene sharing and mine-complex independence limits persist.411 tests passed; all actual raster/table/hash checks passed. **STOP after25C.2: no more requests, training, dataset release or25D without approval.**

## Phase25D.1 model readiness — 2026-11-25

[Report](reports/phase25d1-model-readiness.md), [proposal](../config/phase25d1_comparison.json), [counts](reports/phase25d1-summary.json). New isolated input/loss/evaluation adapters use actual B2/B3/B4+VV/VH,not invented NIR/SWIR. Same fixed pretraining normalization and conservative16×16 complete-token mask for both prospective systems;67 TRAIN/12 VAL patches usable,81/60 pseudo-positive cells across10/2 groups. Original80-patch dataset unchanged. Existing Siamese U-Net5-channel synthetic forward/backward passed without optimizer updates; TerraMind weights/runtime absent and actual32×32/native30m/API/mask behavior untested. GPU hardware8GB exists,torch CPU-only;availableRAM4.68GiB below proposed8GiB setup guard.20 focused tests passed. **STOP after25D.1: next approval is isolated CUDA environment,exact verified Tiny checkpoint and≤5-minute synthetic GPU smoke; no training authorized.** RF/historical experiments remain intact;no RF in the active proposal.

## Phase25D.2 resource stop — 2026-11-25

[Report](reports/phase25d2-cuda-smoke.md), [gate](reports/phase25d2-resource-gate.json):availableRAM3.474GiB failed mandatory8GiB minimum;VRAM7,956MiB and disks passed. Stopped before package resolution,environment creation,downloads or checkpoint load. No GPU smoke;shape/mask/gradient/peak results unmeasured. Existing environments/data/TEST safeguards unchanged. **Resume only after manually freeing RAM to≥8GiB and rechecking gates;no threshold relaxation or system-setting changes.** One authorized setup/checkpoint/synthetic smoke remains unexecuted;no research training authorized.

## Phase25D.2 resumed partial setup — 2026-11-25

[Progress](reports/phase25d2-setup-progress.md),[receipt](reports/phase25d2-setup-progress.json):initialRAM8.089GiB passed;empty D: Python3.11.8 environment created. Official TerraTorch1.2.14/TorchGeo0.10 metadata requiresPython≥3.12;resolution failed before install. A laterRAM gate7.856GiB stopped before managed3.12 acquisition.151 metadata HTTP attempts,41.93MB body/44.40MB conservatively charged under12GiB;model0 bytes. No packages/checkpoint installed,smoke unrun,oldvenv/data/settings unchanged. Four offline tests passed. Resume only after≥8GiB RAM,using3.12 and the SAME D: ledger/cache;preserve empty3.11 bootstrap and recreate active env deliberately. **No further setup or GPU work until gates pass;no research training.**

## Phase25D.2 Python3.12 reuse — 2026-11-25

[Progress](reports/phase25d2-python312-progress.md),[counts](reports/phase25d2-python312-progress.json):user-supplied3.12.10 venv reused without recreation. RAM8.145/8.083GiB gates passed. Resolver now blocked by wheel-only policy:TerraTorch→Lightly→Hydra requires antlr4-python3-runtime4.9.*,no matching wheel. Stopped before installs,checkpoint or smoke. Same D: ledger/cache retained;model0 bytes. Six focused tests passed. **Next approval:one audited official pure-Python4.9.3 source-to-wheel build or verified compatible wheel;no generic source builds,model fallback or research training.**

## 2. Current state (end of Phase 24, commit after `c38cddb`)

The headline tables are in [docs/reports/final-project-status.md](reports/final-project-status.md). In short:

| Area | Outcome |
|---|---|
| Meghalaya screening (22L → 22X/22Y) | 20 systematically sampled AOIs and 174 disturbance clusters. Density 1.20 ha per 100 ha. S1 ΔVH negative in 18 of 18 AOIs. 30.5% of clusters persistent. All are **UNKNOWN**, not confirmed mining |
| Model experiments | 22W ablation on weak labels: fusion ≈ optical (+0.006 F1, CI spans 0). SAR alone is weaker and terrain hurts. U-Net weak-label validation F1 0.713. MineNetCD external RGB F1 0.246. **None of these is Indian accuracy** |
| River | 23A D8 routing of all clusters to 4 CPCB station reaches; 23M audit 27 of 27 checks pass. 23L labels: **Sunapur = PRIORITY FIELD MONITORING** (not confirmed pollution). River NDTI closed as a **negative result**: 10 m S2 (22O) and 3 m Planet (23K) cannot observe the narrow channels |
| India | Phase 11C has 6 leads in 5 states. Phase 15C/16A screened Gevra and Bhubaneswari. Phase 24B adds config-driven, resumable, budget-guarded screening (`config/india_aois.json`), demonstrated offline on the 6 cached tiles (5.5 km²). **No national coverage** |
| Dashboard | `frontend/` (React and Vite). The India discovery view is the default Overview, and the Meghalaya detailed study is at `#meghalaya`. Also Explorer, Rivers, Analytics and Evidence views, and the Brahmani pilot kept separate |
| Verified detections | **0.** Mining attribution is **UNKNOWN** everywhere |

## 3. What is pending (do not mark as done without real evidence)

1. **Human review (23I).** Two reviewers, blinded sample of 30 items.
   - The packages are built in git-ignored `outputs/phase23i_review/`, including `share_reviewer_B` and its zip.
   - Reviewer results have **not** been returned. The 30 share-package chips are Sentinel-2 only; do not supply external reviewers with downloaded Planet raw scenes or the private Planet viewer under the owner's E&R Basic license. See [the licensing audit](reports/planet-licensing-audit.md).
2. **Reference labels.** Verified classification is BLOCKED until accepted independent Indian labels exist. Do not retrain or report Meghalaya accuracy before then.
3. **Official data requests.** Drafts are in `docs/outreach/`, which is **local only and deliberately not committed**: DMR/MBDA letter and email, Nursamsi, and Dr Patel (Presidency University). The user sends them; nothing has been confirmed received.
4. **Field or official water quality.** Needed for Sunapur and the other reaches. The CPCB archive copies were unusable (23C–23G).
5. **Wider India screening.** Needs approved Earth Engine quota. Use `python -B -m scripts.phase24b_india_screening` to plan, then `--execute --approve --max-requests N`.
6. **Paper.** Fill in the author and affiliation lines and add figures from the dashboard and reports (see the figure table in `paper-draft.md`). Then choose a venue.

## 4. Non-negotiable rules (from the whole project history)

- **Frozen TEST data.** Never open frozen TEST imagery, labels or predictions (5 km seed-42 spatial blocks, 120 m buffer). Use the guards `phase22n_temporal.guards()` and `phase22q_multi_aoi.guard()`.
- **No invention.** Never invent labels, coordinates, dates, F1, precision, recall or "confirmed mining" or "pollution" claims.
- **Never commit** any of the following; the pre-commit audit enforces this through `scripts/audit_publication.py` and `.githooks`:
  - `.env` or credentials;
  - raw imagery, including Planet zips and the LISS-IV zips in the parent folder;
  - `outputs/`, `results/` or `frontend/public/local/`;
  - `docs/outreach/`, private local paths or `.geojson` under `docs/`.
- **Earth Engine work.** Preregister and commit before acquiring. Set a request/byte budget, use `phase22w_ablation.acquire_lock`/`ledger_usage`, and record any breach honestly.
- **No new data spending.** No new Planet orders or river-image searches unless the user asks.
- **Git.** No force-push. Commit only explicit paths. Ask before destructive, costly or credentialed actions.
- **Frozen design.** The seasons `[2023-11-01, 2024-04-01)` and `[2024-11-01, 2025-04-01)` (follow-up `[2025-11-01, 2026-04-01)`) and the 22L rule (ΔNDVI ≤ −0.30 and ΔBSI > +0.10) are frozen.
- **Routing source.** The routing source is **Phase 23A**. There is no Phase 23B.

## 5. Where things are

| Need | Location |
|---|---|
| Install, run, dashboard | [README.md](../README.md) |
| Every phase's command | [docs/REPRODUCIBILITY.md](REPRODUCIBILITY.md) |
| Chronological phase log | [docs/research-progress.md](research-progress.md) and `git log --oneline` (about 150 descriptive commits, one or more per phase) |
| Phase reports and JSON results | `docs/reports/phaseNN-*.md` / `*.json` |
| Earlier handoff (Claude → Codex) | [docs/reports/claude-handoff-to-codex.md](reports/claude-handoff-to-codex.md) |
| Model consolidation | [docs/reports/final-model-experiment-consolidation.md](reports/final-model-experiment-consolidation.md), [phase24c-evidence-summary.json](reports/phase24c-evidence-summary.json) |
| Python environment | `.venv` in the **parent** folder of this checkout (`../.venv/Scripts/python.exe`) |
| Dashboard dev server | `cd frontend; npm run dev` (port 5173). A preview config is in the parent folder's `.claude/launch.json` |
| Large local data (not in git) | `outputs/` (tiles, checkpoints, review packages), `results/`, plus Planet/LISS-IV zips and `phase3_delivery/` in the parent folder |

## 6. How to resume

1. Run `git status --short --branch` and `git log --oneline -5`. Expect a clean tree apart from the untracked `docs/outreach/` and `results/`.
2. Run the checks:
   - `python -B -m pytest -q tests` (370 pass at Phase 24);
   - in `frontend/`: `npm test` (11 pass) and `npm run build`.
3. Rebuild the dashboard snapshots (commands are in the README), then open `#overview`.
4. Pick from the pending list in section 3. If reviewer results arrive, adjudicate them under `docs/reference/REAL_REFERENCE_PROTOCOL.md` before any accuracy claim.

## 7. Phase index (one line each)

| Phases | Summary |
|---|---|
| 1–3 | GEE setup, GAUL 2025 boundary check, seasonal S1/S2 preprocessing, coverage gates, inference contracts |
| 5–8 | Streamlit dashboard, then React portal and local release |
| 11–16 | India discovery leads (11C), unsupervised cross-sensor screening (15C), regional terrain features (16A), MineNetCD external benchmark (17x) |
| 22A–22K | Indian label-source audits and Maus weak-label RF/U-Net training. TEST stays sealed |
| 22L–22N | Temporal NDVI/BSI candidate rule and multi-area pilot |
| 22O | River NDTI at 10 m: negative |
| 22P–22R | S1 corroboration and agreement with GFC/WRI products |
| 22S–22T | Official data audit; U-Net transfer NO-GO |
| 22V–22W | Sensor-fusion ablation |
| 22X–22Y | Systematic 20-AOI sample and persistence |
| 22Z–22AA | Mining-context and OSM audits (NO-GO for attribution) |
| 23A | Drainage linkage |
| 23C–23G | Official water-quality and external-case searches (unusable or over budget) |
| 23H | Reach priority |
| 23I | Blinded human-review workflow |
| 23J | Dashboard and GIS map |
| 23K | PlanetScope 3 m: river NDTI closed |
| 23L–23M | Reach integration and routing audit |
| 24A | India discovery dashboard |
| 24B | Generalised India screening |
| 24C | Evidence tiers, final docs and paper |

## Phase25D.2 ANTLR exception progress (2026-11-25)

Approved one-time pure-Python ANTLR4.9.3 wheel built and hash-verified without executing setup.py. Setup then stopped on missing local HTTP HEAD support; fixed and covered by eight focused tests, not retried. No installation/checkpoint/smoke ran. Reuse existing wheel/receipt and counters; do not rebuild or reset budgets. [Progress and hashes](reports/phase25d2-antlr-progress.md). Resume only after resource gates; original limits persist.

## Phase25D.2 isolated stack installed (2026-11-25)

Existing Python3.12.10 venv now has the hash-locked CUDA torch2.11.0+cu128/torchvision0.26.0+cu128/TerraTorch1.2.14 stack. Installation completed; cumulative dependency charge 3,138,453,534 bytes. Post-install RAM7.930GiB failed the8GiB gate, so checkpoint/model import/GPU smoke did not run. Reuse setup-complete receipt and lock; do not reinstall or rebuild ANTLR. Model transfer remains0; original budgets and single-smoke authorization persist. [Progress](reports/phase25d2-installed-progress.md).

## Phase25D.2 CUDA verified; checkpoint redirect stop (2026-11-25)

Without package changes, torch confirmed CUDA12.8 available on RTX4060; locked distribution versions match. Pinned checkpoint request returned302 to an unapproved host; stopped before redirected request/body. Model charge16,384bytes/body0; no smoke ran. Need audited delivery-host handling before retry; preserve counters and pinned hash. [Evidence and next correction](reports/phase25d2-cuda-verified-download-stop.md).

## Phase25D.2 one functional smoke completed; RAM certification unresolved (2026-11-25)

Pinned Tiny211,873,402bytes/SHAe56ea9eb… verified. Official HF CDN authenticated and model-only allowlisted. One native32x32 paired synthetic CUDA smoke passed shapes/normalization/masked loss/frozen gradients in102.190s; CUDA reserved44MiB. Original watchdog sampled Windows launcher only, so worker RAM peak is UNVERIFIED. Corrected recursive-tree accounting and21focused tests pass; no rerun. Exactly one smoke consumed. Need approval for one download-free resource-verification rerun before full25D.2 certification. No training. [Report](reports/phase25d2-synthetic-smoke.md). Model charge211,938,938bytes; dependency charge3,138,453,534bytes. Preserve existing environment/checkpoint/ledgers and all data.

## Phase25D.2 approved RAM-verification rerun passed (2026-11-25)

One additional offline synthetic run completed,43.366s. Corrected watchdog independently tracked actual worker3144/launcher22640; conservative process-tree peak1.731GiB, CUDA allocated38.96MiB/reserved44MiB.363samples/0.1s requested interval; max gap0.127097s. Functional checks and loss exactly match prior run. No downloads, package changes, optimizer steps, dataset or TEST payload access; ledger unchanged.22focused tests pass. Prior failure/caveat preserved; [new report and measurement limitations](reports/phase25d2-ram-verification.md). Synthetic25D.2 gate completed under sampled working-set accounting; no research training authorized. Stop here.

## Completed30-item blinded review integration (2026-11-25)

Private originals and ID-joined outputs: outputs/phase25/experiments/human-review-integration-v1/.30matched IDs,29complete pairs:10YES/YES,4NO/NO,1UNCERTAIN/UNCERTAIN,14disagreements,1missing response(A,RE2F35EF0). Kappa0.256410; five priority disturbance-review items, four excavation-like flags. Zero admitted positive/negative labels: shared-Sentinel evidence, UNKNOWN attribution, unconfirmed A/B identities and missing independent positional/paired/polygon evidence remain blockers. Existing strict importer/admission unchanged; new intake is analysis-only.13focused tests pass. [Report](reports/human-review-integration.md). No training or TEST access.

## Phase25E.1 multi-layer methodology/cache pilot (2026-11-25)

Added guarded unsubmitted GEE graph composition reusing existing optics/SAR/context code and frozen thresholds; no online execution. One label-blind TRAIN32x32cache patch:1024eligiblecells, evidence-count0/1/2/3=591/391/41/1; existing pseudo-states284stable/0potential-disturbance/740uncertain preserved. Terrain/WorldCover/CHIRPS available, other contextual layers missing. Five human leads remain separate UNKNOWN inspection leads, not references. Requests/downloads/training0;18focused tests pass. [Methodology/limitations](reports/phase25e1-multilayer-methodology.md). Next: independent paired evidence and adjudication, not accuracy claims or new discovery.

## First trained MineChange-India pseudo-label U-Net pilot (2026-11-25)

Private run: outputs/phase25/experiments/25e2-unet-pseudo-v1/. Existing SiameseUNet(channels=5,width=16), frozen D.1 normalization/token masks/BCE+Dice, TRAIN-only capped positive weight10, AdamW3e-4, batch1/accumulation4, seeds42/43/44 each5epochs. Total fit wall41.266s; overall run68.750s on existing CUDA environment. TRAIN68patches(67usable),81positive/18,638stable pixels; VAL12patches/3groups,60positive/3,036stable pixels. Fixed0.50: every seed TN3036/FP0/FN60/TP0; recall/F1/IoU/FPR0, precision undefined, identical to constant background. Best epochs5/5/4 by VAL loss. No useful disturbance discrimination demonstrated; severe imbalance remains. Checkpoints/histories/per-group metrics,36georeferenced predictions and3comparison figures saved privately. Read-only hash/contract-bound load_model hook verified in existing CPU environment: max probability difference0.000302 versus saved CUDA on one patch, zero0.5decision differences; no bitwise parity claim.14focused tests and publication audit pass; no TEST/GEE/downloads/human-review labels. All findings are pseudo-label agreement, not independent mining accuracy; supervised mining validation remains NO-GO. No standalone report or further training authorized by this completed run.

## Controlled pseudo-U-Net recovery and local dashboard integration (2026-11-25)

Private recovery: outputs/phase25/experiments/25e3-recovery-v1/. Baseline VALmax0.460888; masked gradients valid(ignored0), TRAINpositive81/18,719. Diagnosis: imbalance/exposure and fixed0.5suppression, not a mask/sigmoid bug; baseline0.25TP28/FP36 is diagnostic only. Two seed42TRAIN-only sampling ratios preregistered before fitting,10epochs each,last epoch/no VAL checkpoint selection,109.453s total GPUtraining.2positive:2background stays all-background;3positive:1background qualifies: at0.5TN3036/FP0/FN46/TP14,precision1,recall0.2333,F1/Dice0.3784,IoU0.2333,FPR0. AllTP in87:556; misses all18positivepixels in88:564. Full per-group metrics,0.25/0.5/0.75sensitivity, probability distributions and unequal step/exposure counts retained privately. Different exposure/step totals limit causal comparison of sampling settings. No further tuning.

Existing React Explorer now links #explorer-experimental. Existing loopback portal serves verified saved VAL snapshots at /__experimental__/ only(same-origin/Host guards,no arbitrary rasters/weights or inference). Generate with python -B -m scripts.phase25_model_portal; npm --prefix frontend run build; python -B -m scripts.phase8_planet_portal --port5188; open http://127.0.0.1:5188/#explorer-experimental. Active private snapshot outputs/phase25/experiments/25e3-portal-v2/; older v1 preserved. Three saved runs ×12VALpatches, source/checkpoint hashes, before/after30mRGB, probability/binary overlay and opacity, group metrics and honest limitations. Original/river/Planet routes preserved.9targeted Python/11existing frontend tests and TS/build/browser checks pass; publication/privacy audit passed; desktop/narrow screenshots private under outputs/phase25/qa/recovery-browser-v1/. NOT VALIDATED, UNKNOWN attribution,zero operational alerts remain. No independent mining accuracy established.

## MineChange-India multiclass private dataset candidate (2026-11-25)

Active candidate outputs/phase25/datasets/minechange-india-multiclass-v2/; original80patch dataset and first multiclass v1 preserved.68TRAIN/12VAL across17/3frozen5kmblocks,73.728km².55observation/QA/annotation bands;43model-array channels exclude future follow-up/persistence and original count QA. Dynamic World seasonal crops/built/water/bare probabilities and MODIS QA acquired with existing metered transport;49initial requests covered20AOIs, total59requests/5,718,825responsebytes after two failed bounded TRAIN supplement scans. Supplement two-band reducer required2048pixels not1024; code corrected4096, no remaining quota for initialization/retry. No supplemental patches admitted. Same ledger/caps60/100MB; no reset. Exact AOIs/plan remain private, policy config/hash committed.

Actual cells:stable23,386;persistent unattributed mining-like/other exposure168;other transient682;uncertain57,684. Agriculture/construction0: unsupported, excluded from active taxonomy. Stable/persistent/other support20/12/18groups. Fire-history values remain QA-masked; fire counts retained. Roads/geology/mining context unavailable; built probability is only infrastructure proxy. Bhoonidhi/Planet raw/restricted products excluded; no TEST payloads opened. Human reviews/reference truth remain separate, no new verified mining labels. Candidate contains georeferenced masks/evidence/margins,arrays,provenance,source permissions,dataset card and portable paths. Original source identities incomplete; margin not calibrated; no external release authorized.80masks replay identically and arrays/geometries verified;11focused tests and publication/privacy audit passed. Source-specific rights and independent reference/class diversity still block publication/accuracy claims. No retraining or dashboard changes.

## Multiclass retrospective weak-label experiment (2026-11-25)

Private run: outputs/phase25/experiments/25e4-multiclass-v1/. Verified all80V2patch hashes, source/array pixel equality, CRS/affine, masks and canonical TRAIN/VAL spatial groups. Original classes0/1/4 map internally0/1/2;2/3/255 excluded. TRAIN68patches/17groups:20,329stable/84persistent-unattributed/587other-transient cells; VAL12patches/3groups:3,057/84/95 (3,236identical evaluated pixels for every model). Follow-up/persistence, evidence scores, confidence, masks and observation-count QA excluded from inputs. Persistent/transient labels depend on2025-26follow-up, so this is retrospective weak-label agreement, NOT early warning or independent mining accuracy. Physical indices also participate in label generation; high agreement cannot validate attribution.

RF100trees/depth16/leaf2/seed42/n_jobs1/class-balanced;10,200unique TRAINpixels,<=600/group, class-aware allocation, same sample indices across ablations, TRAIN-only median imputation. Optical14features/SAR6/fused33available physical/context features. VALmacro-F1:optical0.846418,SAR0.612056,fused0.840863; majority0.323852. Optical class0/1/4F1=1/0.729730/0.809524,IoU=1/0.574468/0.680000; confusion actual rows/predicted columns=[[3057,0,0],[0,54,30],[0,10,85]]. Per-group macro-F1 spans0.589744-0.982759. Added context did not improve this selection-biased VAL agreement. Frozen rule is the future-dependent annotation generator, not a comparable predictive baseline.

Existing SiameseUNet5pairedchannels/width16 with three-class head; TRAIN-normalizedB2/B3/B4/VV/VH, masked weighted cross-entropy, positive-aware TRAIN exposure, seeds42/43,10epochs each,last complete epoch, no VAL checkpoint/threshold tuning.51.047seconds combined GPUfit; macro-F1=0.526712/0.495907. Seed42 predicts no persistent-class pixels; seed43persistent recall5/84. No further recovery tuning. Initial deterministic CUDA nll_loss2d incompatibility failed before any optimizer step; fixed with mathematically equivalent masked log-softmax CE, preserving completed RF fits. Loss equivalence/ignored gradients tested. Checkpoints, histories, class/per-group metrics, class probabilities and original-taxonomy GeoTIFFs, baseline, configs and three comparison panels remain private; CPUcheckpoint roundtrip verified. RF fit times0.969/1.266/1.312s. No GEE, downloads, TEST, new labels or package changes.

Local Explorer experimental route now includes five multiclass runs plus three historical binary runs, before/after RGB, argmax/uncalibrated-score/weak-label layers, class confusion metrics, group results and source hashes. Active private snapshot outputs/phase25/experiments/25e4-portal-v2/; previous snapshots untouched. OpticalRFselected by highest VALmacro-F1 among frozen configurations, explicitly selection-biased. Launch unchanged: npm --prefix frontend run build; python -B -m scripts.phase8_planet_portal --port5188; http://127.0.0.1:5188/#explorer-experimental. No raw rasters/checkpoints or arbitrary inference endpoint.17focused Python/11frontend tests, production build and desktop/narrow browser checks passed; screenshots private in outputs/phase25/qa/multiclass-browser-v1/. UNKNOWN attribution, Indian supervised validation NO-GO and zero operational alerts remain. Next: independent reference evidence/adjudication; no automatic further tuning or acquisition.

## Official-source access and append-only competing-class recovery (2026-11-25)

Private extension: outputs/phase25/datasets/competing-supplement-v1/. Parent80V2patches and old59request ledger hash-verified unchanged;12VALpatches/TEST, models and30human-review items preserved. Official source catalog/access facts: config/phase25_official_context_v1.json. Bhuvan catalog/WMS/WFS/terms probes timed out; no numeric Indian thematic layer/legend acquired. Bhoonidhi documentation HTTP200,collections401: authenticated manual access required. Older LULC/degradation/geomorphology maps are context, not2023-25change labels. Existing LISS-IV assessments reused metadata-only: protected site footprints plus unresolved radiometry/QA/position/permissions prevent TRAIN substitution. No Planet payload used or NRSC sharing permission invented.

Corrected multiband reducer limit4096for2x32x32cells; one new40request/100MBledger used24requests/3,688,853response bytes including auth,metadata,failures/resumes. Seven separate NRSC probes received61,645bytes; aggregate recorded response bodies3,750,498bytes.17unchanged TRAINwindows screened; DWcrop/built-gain screen allzero. Hash-frozen pre-acquisition amendment used historicalWorldCover2021cropland as weak selection context, retaining every location. Two selected blocks received paired Sentinel1/2,early/late/follow-up diagnostics and context stacks,69bands at30m with source IDs/dates/native-support provenance. Two new TRAINpatches=>82total (70TRAIN/12VAL), no new geographic groups. New weak counts448stable/1agricultural-context temporal-variability/1other-transient/1598uncertain;0persistent/0construction. One isolated agricultural-context cell in one group is insufficient: class-support NO-GO; zero construction candidates does not mean absent construction.

Supplement-only agriculture uses crop context plus paired observations and within-season vegetation/exposed-soil variation in either direction, without mining-style SAR/NDVI-decline requirements. Construction needs dated built gain/follow persistence and optical corroboration. Parent rules/masks unchanged. New taxonomy names explicitly weak context; future/early-late label diagnostics remain annotation-only. No model training or dashboard change. Fixed missing TIFF NoData-tag handling using the explicit-9999export contract; valid0retained. Server-side band-order/graph verification handles absent descriptions without relaxing grid guards. Actual parent/new integrity, pixel alignment, mask/rule replay and spatial-buffer checks passed;14focused tests passed. Source-specific rights and independent attribution/admission remain unresolved; verified labels0,alerts0,external release unauthorized.

Exact manual login/product/date/coordinate instructions and AOIs: outputs/phase25/datasets/competing-supplement-v1/manual_acquisition.md, manual_acquisition.csv, manual_aoi.geojson. These cover two crop-context TRAINwindows plus one existing built-context TRAINwindow. Prefer ResourcesatLISS3BOA paired in frozen2023-24/2024-25seasons; conditional LISS4/AWiFS/EOS04 corroboration requires original radiometric/geographic/quality/rights metadata. Numeric thematic exports require verified legend/dates/CRS/resolution and product permissions; never infer codes from WMS colors. Next: manual evidence acquisition and independent review, not training or quota-filling requests.

## Offline LISS-III BOA evidence recovery (2026-11-26)

Recovered pending2cf69f1push before work. Private source/evidence package: outputs/phase25/datasets/nrsc-liss3-evidence-v1/. Two user-supplied archives verified by SHA256,streamed ZIPCRC/member hashes and safe resumable extraction; originals unchanged. Actual Resourcesat2LISS3 dates2024-01-17/2025-01-11. Four real bands2345=green/red/NIR/SWIR; metadata declares atmospheric correction,valid0..10000,scale0.0001. Source TIFFscales1are not the BOAscale; radiance Lmax fields were not applied. Native sampling23.5m,resampled output24m,EPSG32646; per-band dimensions/transforms/metadata centers agree. TIFFNoData absent; all-band-zero padding/range failures explicitly masked,valid single-band zero retained. Product-specific license/order/reviewer-sharing evidence absent; keep imagery and derivatives private. Metadata accuracy0.0values do not establish measured accuracy; cloud/quality fields blank and no cloud/shadow/haze QA supplied.

All three preregistered TRAIN AOIs have100%valid/common-signal support:1640/1640,1600/1600,1600/1600native pixel centres (rasterized rectangle boundary convention retained; not independent samples or confirmed clear ground). Native FCC NIR/red/green and SWIR/NIR/green,NDVI/NDWI/MNDWI/NDBI/brightness,diagnostic differences,masks and area-averaged30mevidence copies saved. No blue: trueRGBand standardBSI unavailable; no fabricated bands. Display stretch fixed0..0.5; improved private panels are aois/*/private_review_panel_v2.png. Vegetation/exposed-looking tonal variation is visible,not verified agriculture/construction/mining; January-to-January pair alone cannot prove seasonal cultivation. Shadows/haze/illumination remain alternatives; sun elevations36.90/33.81degrees.

Registration gate UNRESOLVED: shared24mlattice does not prove coregistration. Internal NIRhigh-pass correlation peaks0.640(atsearchboundary),0.095,0.100(atboundary). Raw image(row,column)lags(3,-3),(-2,0),(-3,-1)are diagnostic only,not absolute accuracy or trusted offsets; no shifts applied. Correct map east/north sign conventions recorded in evidence_manifest.json; noRMSE/CE90claimed. Raw paired median dNDVI+0.0493/+0.0861/+0.0059cannot be interpreted as confirmed ground change. Single-date NRSCversus seasonal Sentinel NDVIdelta correlations0.034/-0.149/0.060are descriptive/non-equivalent temporal estimands,not validation accuracy.

Added three private diagnostic AOIevidence attachments with source hashes/IDs/dates,24mgeoreferencing,30malignment and explicitly unknown quality masks. Model-input eligibilityFalse; new weak/verified labels0,all82existingpatches/labels/VAL/TEST and experiments unchanged. Independent two-reviewer interpretation/control forms EMPTY; reviewer panels exclude algorithm predictions/pseudo-labels. Existing source-integrity/replay guards passed;16focused tests passed,including extraction traversal/resume,BOAscaling,missing-blue indices,relative-shift conventions and blocked unapproved evidence promotion. Final original ZIP/member/evidence hashes and parent82integrity verified. No downloads,GEE,training or TESTanalysis. Next: independently georeferenced stable controls and provider geometric/quality/product-rights documentation; no automatic reference admission or additional imagery request merely to resolve already complete coverage.

## NRSC interpretation-readiness clarification (2026-11-26)

New private package: outputs/phase25/qa/nrsc-review-readiness-v1/index.html and readiness.json. Cached reference checks were restricted to the three authorized TRAIN AOIs. Planet footprint metadata excludes allthree (no Planet/TEST pixels opened). Cached March17/November12LISS-IV:AOI83:561has100%nonzero signal bothdates,butafterpreview shows broad bright obscuration/dark region consistent with clouds/shadows andbeforeis lowcontrast; no qualified distributed control set. AOI89:557beforehas0nonzero signal,afterdoes not fully cover; AOI87:557bothhave0nonzero signal. Reference-annotation caches contain metadata/plans,not a qualifying new positional image. Accepted stable independent landmarks0. Relative offset/uncertainty/absolute accuracy remain undefined,not0; original correlation lags48-102magnitude are texture diagnostics,not measured error or confidence intervals. No correction,expanded search or forced landmark coordinates.

LISS-IIIvalidsignal remains100%,but clear/cloud/haze/shadow fractions unknown: no providerQA/blue/cirrus information. Existing bright-proxy counts0throughout;afterdark-proxy counts1/1640(0.061%),0/1600,4/1600(0.25%)are not verified shadows. Solar-elevation difference3.090187degrees retained as context only. Three new unshifted paired FCC/NDVI/NDBI panels use identical display scales and explicit quality/registration warnings; omitted spatial-difference maps from blinded interpretation panels. Original panels,blank blinded forms and all82patches/labels/VAL/TEST unchanged and hash-verified. No model-input or label promotion; no training/GEE/data download.

Official current Bhoonidhi EULA checked with NRSC licensing page; safe policy record config/phase25_nrsc_permissions_v1.json. Registered lawful private research is conditionally supported; exact-product reviewer sharing/public redistribution remain unconfirmed and blocked. Product-specific accepted terms/order records absent; no blanket prohibition on noncommercial use invented and no oldCartosat/NovaSARpaidlicenses imported. Product-quality disclaimer fetch timed out; no accuracy inferred. Proposed external requirements/empty six-distributed-checkpoint-per-AOIcollection sheet and unsent provider questions are private in external_requirements.md/external_control_requirements_empty.csv. This is a proposed evidence-collection plan,not a new admission threshold. Need independent surveyed/orthophoto landmarks with documented dates/CRS/uncertainty suitable for existing<=30madmission,unobscured ground-quality evidence and exact-product permission clarification. Local owner qualitative inspection only; verified reference interpretation/external reviewer release NOT READY.12focused tests passed; publication audit required before safe source/docs commit.

## MineMind cached integration (2026-11-26)

Reused the frozen 8D masked cross-sensor encoder; the authoritative checkpoint SHA256 is retained and verified in the private run receipt. No fitting, downloads, GEE or NRSC work. Four BEFORE-only development blocks and four separate calibration blocks retained. New controlled sensor-withholding comparisons use the same 1,016 Gevra / 751 Bhubaneswari cells and calibration-only review quotas. Phase15C remains primary; SSL remains an ablation. Spearman replica consistency (Gevra/Bhubaneswari): Phase15C 0.523/0.287; frozen both-sensor SSL 0.473/0.615; SAR-only SSL 0.488/0.652; optical-only SSL 0.786/0.240. Matched physical SAR baseline 0.514/0.702 and optical 0.770/0.105 show no consistent SSL advantage. High ranking consistency with zero retained candidates is not mining accuracy. Controlled withholding does not establish reliability under all natural missingness.

Private outputs: outputs/phase25/experiments/minemind-cached-v1 (analysis 2.042 seconds, training zero), minemind-portal-v2; screenshots/comparison figure/browser receipts under outputs/phase25/qa/minemind-app-v1. Source/score hashes, common support, georeferencing, missing-sensor flags, observation counts and terrain context are preserved. Unavailable rainfall/landcover/fire/roads/persistence at these windows remain missing; competing mining/agriculture/construction/landslide explanations remain UNKNOWN. Pointwise encoder is not a spatial segmentation model. Legacy <=25-degree support is retained for fair comparison, not a mining-location assumption. Application sites were previously studied and are not fresh independent TEST sites. No frozen TEST payload or future follow-up was used.

Existing read-only portal now includes #explorer-minemind: seven methods, two scene-disjoint replicas, before/after NDVI, score/candidate layers, opacity, evidence inspection and CSV/GeoJSON. Scores are not probabilities; all candidates UNKNOWN/REVIEW_REQUIRED and operational alerts zero. River adapter checks frozen receipt/mask hashes: Brahmani 16 matched pairs over five months, 93/75 common cells, seasonal contrast change -0.0806231 dimensionless NDTI. Leshka 12<25 cells remains withheld. These spectral observations do not establish degradation, concentration or mining causality. No verified mining-to-reach linkage is added.

Launch from project root: npm --prefix frontend run build; then python -B -m scripts.phase8_planet_portal --without-planet --port 5188 using the existing environment. Open http://127.0.0.1:5188/#explorer-minemind. The optional flag avoids loading private Planet review assets. Missing/corrupt MineMind assets fail closed independently of historical workspaces. Raw checkpoints/rasters are not served. Focused Python checks:20 passed; frontend tests:11 passed; TypeScript/build passed; browser28 combinations, four river stations/two seasons, historical eight models and desktop/narrow layouts passed with no horizontal overflow. Frozen encoder replay difference <=8.94e-8. Independent mining labels remain absent; Indian supervised validation NO-GO. NRSC9437442 remains completed diagnostic-only.

## MineMind TRAIN-only learning comparison (2026-11-26)

Implemented three fixed configurations without VAL/application tuning: frozen encoder with adaptive reliability fusion; one five-epoch temporal reconstruction recovery with uniform fusion; the same recovered encoder with adaptive fusion. Seed42, Adam0.001, batches512, two CPU threads, masked cross-sensor Huber plus0.25TRAIN paired-difference Huber and random modality-view dropout. A separate linear difference head is a training-only auxiliary; inference retains the original8D encoder. Frozen normalization unchanged. Reliability uses TRAIN BEFORE latent SD, observation-count saturation and cross-reconstruction consistency; sensor-distance averaging avoids vector cancellation. No independently calibrated quality probability is claimed. New cutoffs are TRAIN99.5th-percentile; old baseline cutoffs remain their original calibration values, so areas are not matched-quota comparisons. Three configurations only, no retries/search. Available RAM3.62GiB prevented heavy GPU use; tiny CPU fit completed in0.551seconds, five checkpoints, no environment changes.

TRAIN15,280paired cells across4Meghalaya blocks; VAL14,455cells across4separate blocks. Encoder has numerical rank8in each TRAINgroup, no dimensional collapse. Median cancellation ratio0.848-0.869suggests partial rather than catastrophic cancellation; cross-reconstruction MSE0.403-1.093in standardized units varies bygroup. Original objective lacks explicit temporal differences and equal fusion ignores count/reconstruction heterogeneity. These are plausible limitations, not proven causes. Recovery total loss0.38674to0.35824, temporal component0.16244to0.09387; improved pretext loss did not ensure repeatability.

Saved experiment: outputs/phase25/experiments/minemind-learning-v1. All methods share original1,016Gevra/751Bhubaneswari application cells. Spearman(Gevra/Bhub): Phase15C0.523/0.287; frozen SSL0.473/0.615; frozen-adaptive0.504/0.612; temporal-uniform0.403/0.474; temporal-adaptive0.470/0.527. Top5Jaccard: frozenSSL0.259/0.357; frozen-adaptive0.417/0.434; temporal-uniform0.259/0.357; temporal-adaptive0.360/0.357. Individual frozen sensor/physical baselines remain in the comparison receipt unchanged. Adaptive SAR-only replica Spearman0.484/0.640,optical-only0.796/0.167; ranks versus full adaptive shift substantially for optical-only (0.087-0.247),so missing-modality tolerance is not modality-invariant inference. Withheld-sensor tests exercise actual availability routing; natural missingness is not validated. VALgroup score/exceedance distributions reported without selection; no independent VALreplicas exist to estimate repeatability there.

Prespecified no-promotion: Phase15Cremains primary and dashboard stays unchanged. Adaptive improves top5overlap but no consistent global fusion advantage; temporal recovery not promoted. Cross-reconstruction weighting can suppress genuine discordant change. Only four TRAINblocks fromMeghalaya, pointwise architecture, limited domain diversity, no TRAIN scene-disjoint replicas to separate nuisance from seasonal change. TRAIN original2023-24/2024-25seasonal pairs are allowed learning inputs; no2025-26follow-up, pseudo-labels, human labels, NRSCorTESTpayloads used. Reliability BEFOREvalues use eligible paired support; original normalization retains its separate BEFORE-only selection. Competing-explanation separation is UNDEFINED without independent class evidence; signed/context evidence retained with UNKNOWN attribution, no verified mining accuracy and zero operational alerts. All previous results/checkpoints/reviewer materials remain unchanged. Focused learning/routing tests15passed; publication audit required before commit.
