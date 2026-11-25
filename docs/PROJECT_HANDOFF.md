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
