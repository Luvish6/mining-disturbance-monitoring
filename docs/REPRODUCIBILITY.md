# Reproducibility guide

Run everything from the repository root with the project virtual environment: `python -B -m scripts.<name> ...`.

- **Checks before every acquisition.** Each Earth Engine (EE) acquisition is preregistered, budget-capped and hash-receipted. `--preregister` (where present) writes a JSON report that is committed before any imagery request.
- **Ignored folders.** `outputs/` and `frontend/public/local/` are git-ignored.
- **Committed results.** Committed reports in `docs/reports/` carry the hashes of the inputs they used.

## Current MineMind application and saved-result export

Use the [README offline launch](../README.md#current-offline-minemind-run). Build with `npm --prefix frontend run build`, then run `python -B -m scripts.phase8_planet_portal --without-planet --port 5188` in the existing environment. The local service supplies private allowlisted snapshots; Vite dev alone cannot supply those routes. Restore authorized ignored caches before launch; absent/stale assets fail closed. No acquisition/training is part of this procedure.

```powershell
python -B -m scripts.minemind_deliverables --output outputs/phase25/qa/minemind-research-deliverables-v2
python -B -m pytest -q -p no:cacheprovider tests/test_minemind_deliverables.py tests/test_phase25_minemind.py tests/test_phase25_recovery_portal.py tests/test_phase12d_matched_brahmani.py
npm --prefix frontend test
npm --prefix frontend run build
python -B scripts/audit_publication.py
```

The exporter verifies saved metric/artifact hashes; writes unrounded CSV, a Markdown results section and source checksums; and copies an already generated numeric-only figure. It does not load model weights, score images, access TEST payloads, contact Earth Engine or regenerate datasets. Use a new output directory to reproduce exports without overwriting historical bundles. Source experiments and their frozen configurations remain archived; do not rerun acquisition/training commands below for this finalization.

**Cohorts are separate:** Gevra/Bhubaneswari original scene-disjoint replicas; TRAIN-only adaptive/temporal recovery on the same application cells; and new Haryana/Madhya Pradesh geographic development holdouts. Original calibration quotas and later TRAIN-only thresholds differ. Compare ranking measures within an identical-support cohort; do not compare unsupervised repeatability with supervised F1. The encoder remains pointwise, four original TRAIN blocks only; expanded reliability statistics are not expanded encoder training. Historical Maus footprints and follow-up-derived pseudo labels remain distinct from independently verified labels.

## Frozen design (do not change between runs)

- **Seasons.** Before = [2023-11-01, 2024-04-01), after = [2024-11-01, 2025-04-01), and the persistence follow-up = [2025-11-01, 2026-04-01). Defined in `config/settings.py` and the preregistrations.
- **Spatial validation.** 5 km spatial blocks (seed 42), with a 120 m TEST buffer.
  - Full-footprint guards: `scripts/phase22n_temporal.guards()` and `scripts/phase22q_multi_aoi.guard()`.
  - Indian frozen TEST imagery, labels and predictions remain sealed in this work. The 22H/22K metric JSONs record `test_sealed: true`. Previously authorized RGB benchmark TEST evaluations are archived separately and are not rescored.
- **Candidate rule (22L).** NDVI change ≤ −0.30 and BSI change > +0.10.
- **EE safeguards.** An exclusive lock plus a shared on-disk ledger (`phase22w_ablation.acquire_lock`, `ledger_usage`). The budget is re-read from disk before each request batch.

## Phase commands

Offline steps use saved outputs and need no EE. **EE** marks a step that makes a bounded number of EE requests.

| Phase | Purpose | Commands |
|---|---|---|
| 1–2 | Boundary check and seasonal preprocessing | `python main.py`, `python phase2.py --smoke` (EE); see [PHASE1_2_PREPROCESSING.md](PHASE1_2_PREPROCESSING.md) |
| 11C → 15C → 16A | India lead tiles, unsupervised screening, terrain | `phase11c_india_discovery` (EE); `phase15c_screen <feature> <receipt> <cached> <out>`; `phase16a_regional --inventory ... --site ... --output ... --terrain <tif>` |
| 22L / 22N | Temporal rule pilot and multi-area check | `phase22l_temporal`, `phase22n_temporal` (EE, small) |
| 22O | River NDTI at 10 m (negative result) | `phase22o_river --preregister` / `--acquire` (EE) / `--analyze` |
| 22P / 22Q / 22R | S1 corroboration and independent-product agreement | `--preregister` / `--acquire` (EE) / `--analyze` |
| 22V / 22W | Fusion pilot and sensor ablation | `phase22v_fusion_pilot --verify`; `phase22w_ablation --run` (offline, from cached patches) |
| 22X / 22Y | Landscape sampling and persistence | `--preregister` / `--acquire` (EE) / `--analyze` |
| 22Z / 22AA | Context and OSM audits | `phase22z_context`; `phase22aa_osm --download` / `--analyze` |
| 23A | D8 routing to FFR reaches | `phase23a_river_audit`; `phase23a_linkage --preregister` / `--acquire` (EE) / `--analyze` |
| 23H / 23L / 23M | Reach priority, exposure–observability integration, routing audit | `phase23h_reach_priority`; `phase23l_reach_integration`; `phase23m_routing_audit` (all offline) |
| 23I | Blinded human-review package | `phase23i_review --sample` / `--render` / `--sheet` |
| 23K | PlanetScope 3 m screen (scenes stay private) | `phase23k_planet_screen <scene_dir>` |
| 24B | Config-driven India screening | `phase24b_india_screening` (plan) / `--summarise` (offline) / `--execute --approve --max-requests N` (EE) |
| 24C | Evidence-tier summary | `phase24c_evidence_summary` (offline, reads committed JSON only) |

## Dashboard snapshots

```powershell
python -B -m scripts.phase13_data
python -B -m scripts.phase23_dashboard_data
python -B -m scripts.phase23_dashboard_geo
python -B -m scripts.phase24b_india_screening --summarise
cd frontend; npm run dev
```

## Verification

```powershell
python -B -m pytest -q tests
cd frontend; npm test; npm run build
python -B scripts/audit_publication.py
```

The publication audit also runs in the pre-commit hook (`.githooks`). It blocks:

- files outside the allowed directories;
- private local paths;
- raw imagery;
- `.geojson` files under `docs/`.

## Resuming India screening

`--summarise` writes one checkpoint per AOI to `outputs/phase24b_india_screening/<id>.json`. A checkpoint is reused only when the tile SHA-256 and the config SHA-256 both match, so editing `config/india_aois.json` reprocesses every AOI.

`--execute` fetches only the tiles that are missing. Before each AOI it stops if the ledger shows that the next request would exceed either the `--max-requests` value or the request and byte caps in the config.
