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

## Current offline MineMind run

Use the existing research Python environment and installed frontend dependencies. No CUDA, Earth Engine authentication, model fitting or new downloads are needed to launch cached results. From the project root in PowerShell:

```powershell
$python = if (Test-Path .\.venv\Scripts\python.exe) { '.\.venv\Scripts\python.exe' } elseif (Test-Path ..\.venv\Scripts\python.exe) { '..\.venv\Scripts\python.exe' } else { throw 'Activate the existing project environment first.' }
npm --prefix frontend run build
& $python -B -m scripts.phase8_planet_portal --without-planet --port 5188
```

Open `http://127.0.0.1:5188/#explorer-minemind`; use `#rivers-brahmani` for matched-date river/rainfall charts. Stop with Ctrl+C. The service binds to loopback only. Do not deploy or tunnel it. `--without-planet` prevents loading restricted Planet assets.

The explorer serves frozen NDVI before/after maps (not RGB), screening-score and candidate overlays, uncertainty, provenance, and review-only GeoJSON/CSV. All attribution remains UNKNOWN and operational alerts stay zero. Phase15C remains primary; SSL/recovery results are ablations, not validated mining predictions. The later geographic comparison is a research deliverable and does not replace the frozen dashboard experiment.

**Local data prerequisite:** ignored `outputs/` and `frontend/public/local/` snapshots are required; a fresh Git clone has no imagery/checkpoints. Restore only authorized local caches. Missing, changed or corrupt source receipts withdraw the MineMind snapshot instead of showing stale data. Do not acquire imagery just to launch the portal. `npm run dev` alone does not provide private `/__experimental__/` endpoints.

Read the [consolidated methods/results](docs/reports/final-model-experiment-consolidation.md) and [offline reproducibility commands](docs/REPRODUCIBILITY.md). The saved-result exporter `python -B -m scripts.minemind_deliverables --output outputs/phase25/qa/minemind-research-deliverables-v2` creates exact comparison tables, provenance and a copy of the existing numeric-only research figure; it performs no acquisition, inference or fitting and refuses to overwrite a bundle.

## Private Mining Investigation Studio

After restoring the existing V2/supplement caches and the two user-supplied NGDR ZIPs under `data/Indian Sources/`, build once with `python -B -m scripts.investigation_dataset`. Existing output directories are never overwritten. The active private version is `outputs/phase25/datasets/minechange-india-investigation-v3_1/` (82 patches: 70 TRAIN,12 VAL). V2, supplements and the initial V3 remain unchanged. `manifest.json`, `integrity.json`, `DATASET_CARD.md`, categorical lithology dictionary, context/validity GeoTIFFs, model-ready arrays and separate pair/retrospective score products are inside that directory. Labels remain inherited weak hypotheses, not verified mining classes; categorical geology codes must not be interpreted as ordinal physical measurements.

Launch the same loopback server shown above, then open `http://127.0.0.1:5188/#explorer-studio`. Controls provide synchronized pan/zoom, RGB before/after, contribution/context layers, equal/physical/TRAIN-adaptive weights, thresholds, uncertainty and UNKNOWN review-only GeoJSON/CSV exports. Manual VAL controls are exploration, not independent parameter selection. All operational alerts remain disabled. Studio exports contain algorithmic scores: they are investigation aids, not blinded reference packages or independent truth.

The index is 0–100 **mining-like evidence, not probability**. Physical family weights are vegetation .25,soil .25,SAR .20,persistence .15,terrain .025,geology .05,environment .075. TRAIN-only finite-change quantiles set scales (NDVI floor .30,BSI .10,SAR1dB); TRAIN coverage and Pearson redundancy adjust adaptive weights. Minimum available-weight coverage is60%, actual optical/SAR counts must be>=2, water screens apply, and vegetation/soil-change prerequisites plus a10-point competing margin remain enforced. Minimum components contain four connected cells. Terrain support is neutral; terrain-only alternative evidence is capped so steep slopes are not universally excluded. Uncertainty is a heuristic missing-support/disagreement index, not calibrated confidence. Default pair mode never uses later persistence; retrospective mode explicitly uses the2025–26follow-up and cannot establish early warning.

Agricultural variability and built-up transition scores are competing hypotheses from available land-cover/temporal evidence, not class labels. Bare/impervious spectral confusion motivates caution ([Delaney et al.,2025](https://doi.org/10.3390/rs17040630)); numerical weights/cutoffs are exploratory engineering choices, not validated values supplied by literature. Resource-bearing lithology is weak geological context, not mining attribution. Major leases2022 are administrative polygons and receive zero activity-score weight. Outside lease polygons is UNKNOWN, not verified mining absence. Geological source map scale/date are unprovided; sampling a map on30m cells does not create30m geological knowledge. Legacy Sentinel scene identities remain incomplete.

Bhuvan WMS numeric class access was not established (bounded metadata response cap/timeout); SIS-DP download approval remains pending. No rendered map colours were converted into class IDs. [SIS-DP official manual](https://bhuvanpanchayat.nrsc.gov.in/SISDP/BP-usermanual.pdf) describes its request/download workflow. [NGDR terms](https://geodataindia.gov.in/terms_conditions) retain applicable source-specific restrictions; all NGDR raw/derived data remain private and redistribution permissions unconfirmed. Lease contact attributes are stripped from integrated products.

Compatible uploads stay in bounded process memory: GeoTIFF<=8MB,<=256x256/64bands,north-up EPSG32646,fully within an approved TRAIN/VAL footprint; unknown/TEST regions are rejected before pixel inference. Use explicit before/after band names and dates; multi-sensor scoring additionally requires actual counts/NDWI and `sar_units=dB`. Missing NIR/SWIR/indices are never fabricated. Surface-reflectance RGB previews require `reflectance_units=0_1`. Native uint8 `before_R/G/B` and `after_R/G/B` can use the existing SHA-verified external RGB RF at its frozen0.65cutoff; this is NOT validated Indian/Sentinel mining inference. No arbitrary model upload, dependency installation, resampling or retraining is performed.

Reproduce descriptive weighting/sensitivity comparisons offline with `python -B -m scripts.investigation_compare --output outputs/phase25/qa/investigation-comparison-new`. [Sanitized findings](docs/reports/investigation-studio-results.json) report common-support ranks,40/60/80sensitivity and shared-source legacy-rule overlap, never mining accuracy. The old frozen SSL needs its original seasonal NDTI, which V2 does not supply; no ratio-of-composite substitute is used. Its completed results remain accessible in the frozen MineMind workspace.

## Dashboard

The historical public-snapshot workflow below is retained for provenance. Use the current offline loopback run above for MineMind; do not rerun frozen experiments to launch it.

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

The Phase 23I 30-item reviewer package uses Copernicus Sentinel-2 only (older 30 m chips add Sentinel-1), not PlanetScope. Audit it offline with `python -B -m scripts.audit_review_package` before release. Integrated human reviews record disturbance observations; independent mining attribution and reference admission remain unresolved. They do not establish mining labels.

Downloaded Planet raw scenes, pixel-preserving crops and the loopback Planet viewer are for the licensee's private project use. External reviewers must not access them under this E&R Basic license; they may independently obtain scenes under their own eligible licenses. Do not publish or tunnel the private service. A PNG/JPEG extension alone does not establish Permitted Imagery rights. Any proposed Planet figure or derivative must be non-reconstructable, meet the applicable terms and attribution conditions, and remain **REQUIRES PLANET CONFIRMATION** where those conditions are unresolved. See [the licensing audit](docs/reports/planet-licensing-audit.md).
