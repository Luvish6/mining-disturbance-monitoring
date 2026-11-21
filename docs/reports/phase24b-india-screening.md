# Phase 24B: generalised India screening

## How it works

- **AOIs.** They live in `config/india_aois.json`. Each region holds AOIs with either `anchor_from: phase11c` or an explicit `[lon, lat]`. Anchors are validated against India's envelope.
- **Tiles.** Each AOI is a 32×32-cell, 30 m tile in its local UTM zone. Acquisition reuses the Phase 11C/3G S1/S2 graph unchanged: one relative orbit, speckle filter, cloud and SCL masks, and frozen Nov–Mar seasons. Script: `scripts/phase24b_india_screening.py`.
- **Modes:**
  - `plan` (the default) reports cached and missing tiles with a request and byte estimate, and makes no Earth Engine (EE) calls.
  - `--summarise` writes descriptive change-feature quantiles and resumable per-AOI checkpoints, keyed by the tile and config SHA-256.
  - `--execute --approve --max-requests N` acquires only the missing tiles. It holds an exclusive lock and re-reads the ledger budget before each AOI.

## Offline demonstration (no new downloads)

- **Coverage.** All 6 configured AOIs were already cached, so `plan` estimated 0 requests. `--summarise` covered 6 tiles in 5 states, 5.532 km² in total.
- **Reproduction check.** The tile medians reproduce the Phase 11C values; for example, Bhubaneswari ΔVH is −0.376 dB.
- **Screened sites.** Gevra and Bhubaneswari also carry their Phase 16A terrain and Phase 15C review-only anomaly polygon counts (3 and 0).
- **Outputs.** The report is [phase24b-india-screening.json](phase24b-india-screening.json). The git-ignored dashboard snapshot is `frontend/public/local/india-screening.json`.

## Limits

- **No coordinates in the report.** The report omits coordinates; locations stay in the existing Phase 11C snapshot.
- **22L rule not applied.** The cached tiles have no BSI band. Only an NDVI-drop share (≤ −0.30) is reported.
- **No detection claims.** The statistics are tile-relative. They are not detections, accuracy or mining attribution, which stays UNKNOWN.
- **No wider coverage.** There is no national or state coverage. Wider acquisition is BLOCKED pending approved EE quota.

Tests: `tests/test_phase24b_india_screening.py` and `tests/frontend_india_data.test.js`.
