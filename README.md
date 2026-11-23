# Multi-Sensor Mining-Related Disturbance and Downstream River Monitoring (Sentinel-1 SAR + Sentinel-2)

Research prototype (B.Tech major project). It screens land disturbance with seasonal Sentinel-1/Sentinel-2 change features, routes disturbance to downstream river reaches and tests whether satellite water colour can observe those reaches.

- **Primary study:** East and West Jaintia Hills, Meghalaya (Lukha and Myntdu rivers).
- **India discovery layer:** six configurable lead AOIs in five states.

This is **not** an operational detector, a pollution index or a legal determination. Mining attribution remains **UNKNOWN** everywhere, and there are **zero verified detections**.

## Scope at a glance

| Component | Status | Coverage actually analysed |
|---|---|---|
| Meghalaya systematic screening (22L rule, 22X/22Y) | Done, exploratory | 20 sampled 64×64-cell AOIs; 174 clusters |
| India screening (Phase 11C → 24B) | Config-driven pipeline; offline demonstration | 6 tiles, about 5.5 km² in total. **No national or state coverage.** |
| Sensor ablation (22W) | Done on weak labels | 11 Odisha validation groups |
| River routing and priority (23A/23H/23L/23M) | Final | 4 CPCB station reaches |
| River NDTI (22O at 10 m, 23K at 3 m) | Closed as a negative result | Khaddum marginal; Sunapur not observable |
| Verified classification | **BLOCKED** | Needs accepted independent reference labels |

## Installation (Windows PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-phase3.txt
Copy-Item .env.example .env   # set GEE_PROJECT_ID
earthengine authenticate
cd frontend; npm ci; cd ..
```

Earth Engine is needed only for acquisition steps. Analysis, reports and the dashboard run offline from saved outputs.

## Architecture

```
config/          season dates, AOI config (india_aois.json), preprocessing settings
src/             EE setup, S1/S2 preprocessing, change features, coverage, phase-3 inference contracts
scripts/phaseNN_*.py   one script per research phase (preregistered, hash-receipted)
docs/reports/    committed reports and JSON summaries (the source of every dashboard number)
frontend/        React 19 + Vite dashboard; reads git-ignored snapshots in frontend/public/local/
tests/           pytest (Python) and node --test (frontend helpers)
outputs/         git-ignored imagery, tiles, checkpoints and private review material
```

**Pipeline:**

1. **Seasonal composites.** S1 GRD (one relative orbit, 20 m focal mean in linear power, seasonal median in dB) and S2 SR harmonized (cloud probability < 40, SCL 4/5/6, seasonal medians of NDVI/NDTI/BSI).
2. **Change features.** dVV, dVH, dNDVI, dNDTI (after − before, Nov–Mar 2023/24 vs 2024/25), plus SRTM elevation and slope.
3. **Screening.** Rule-based screening (22L), followed by S1 corroboration (22P/22Q), external-product agreement (22R) and persistence (22Y).
4. **Routing.** HydroSHEDS D8 routing to the Free-Flowing-Rivers reaches (23A), then reach priority (23H/23L).

## Data sources

All imagery is processed in Earth Engine:

- Sentinel-1 GRD and Sentinel-2 SR harmonized, plus S2 cloud probability;
- SRTM, JRC GSW, Hansen GFC v1.13, WRI/GDM drivers;
- HydroSHEDS FFR and 03DIR;
- CHIRPS;
- FAO GAUL 2025 boundaries.

Other sources:

- **PlanetScope SR (23K):** two scenes under the educational licence. Raw scenes are never committed.
- **Lead locations:** public environmental-clearance documents (environmentclearance.nic.in).
- **Weak labels:** Maus et al. v2 mining footprints, which are unverified.
- **External benchmark:** MineNetCD256.

## Running

See [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) for every phase. India screening:

```powershell
python -B -m scripts.phase24b_india_screening              # plan: cached/missing tiles, request estimate (no EE)
python -B -m scripts.phase24b_india_screening --summarise  # offline summaries, checkpointed per AOI
python -B -m scripts.phase24c_evidence_summary             # evidence-tier summary from committed reports
```

To add an AOI, add `{"id": ..., "anchor": [lon, lat]}` under a region in `config/india_aois.json`. Then check the plan output, and only then run the acquisition:

```powershell
python -B -m scripts.phase24b_india_screening --execute --approve --max-requests N
```

Acquisition takes an exclusive lock, reads the budget from the on-disk ledger before each AOI, stops at the caps in the config, and reuses the Phase 11C S1/S2 graph.

## Dashboard

```powershell
python -B -m scripts.phase13_data; python -B -m scripts.phase23_dashboard_data; python -B -m scripts.phase23_dashboard_geo
python -B -m scripts.phase24b_india_screening --summarise
cd frontend; npm run dev    # http://127.0.0.1:5173
```

| View | Route |
|---|---|
| India discovery (default Overview): leads, evidence tiers, state filter, 24B summaries with provenance | `#overview` |
| Meghalaya detailed study | `#meghalaya` |
| Explorer, with India deep links | `#explorer`, `#explorer-india/<id>[/site]` |
| Rivers (Lukha/Myntdu stations; exposure and priority) | `#rivers`, `#rivers-exposure` |
| Brahmani pilot (kept separate) | `#rivers-brahmani` |
| Analytics and Evidence | `#analytics`, `#evidence` |

Unmarked areas of India were not analysed.

## Limitations

- **No independent reference labels.** Weak-label F1 values measure agreement with unverified footprints, not accuracy.
- **Small screening tiles.** Each India tile is 0.92 km², and the summaries are tile-relative.
- **Residual SAR and phenology effects.** SAR layover, moisture and phenology effects are not removed.
- **River colour is unresolved.** 10 m and 3 m imagery cannot resolve the narrow Jaintia channels. NDTI is a relative proxy, not NTU or acidity.
- **Sunapur.** It is a field-monitoring priority, not confirmed pollution.

Pending human-review and field-data dependencies are listed in [docs/reports/final-project-status.md](docs/reports/final-project-status.md).

## Further documentation

- [Final project status](docs/reports/final-project-status.md)
- [Paper draft](docs/paper-draft.md)
- [Evidence tiers (24C)](docs/reports/phase24c-evidence-summary.json)
- [Model consolidation](docs/reports/final-model-experiment-consolidation.md)
- [Phase 1–2 preprocessing detail](docs/PHASE1_2_PREPROCESSING.md)
- [Publication audit](docs/publication-audit.md)

### PlanetScope licensing and reviewer access

The Phase 23I 30-item reviewer package uses Copernicus Sentinel-2 only (older 30 m chips add Sentinel-1), not PlanetScope. Audit it offline with `python -B -m scripts.audit_review_package` before release. Review is still pending and does not establish mining labels.

Downloaded Planet raw scenes, pixel-preserving crops and the loopback Planet viewer are for the licensee's private project use. External reviewers must not access them under this E&R Basic license; they may independently obtain scenes under their own eligible licenses. Do not publish or tunnel the private service. A PNG/JPEG extension alone does not establish Permitted Imagery rights. Any proposed Planet figure or derivative must be non-reconstructable, meet the applicable terms and attribution conditions, and remain **REQUIRES PLANET CONFIRMATION** where those conditions are unresolved. See [the licensing audit](docs/reports/planet-licensing-audit.md).
