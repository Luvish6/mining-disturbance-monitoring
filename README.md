# Mining-Related Disturbance & River Degradation

**Scope:** Phase 1 authentication, boundary validation and inventory; Phase 2 seasonal preprocessing and change features. This is **not** a trained detector or an operational alert system.

## Demonstration

Use the [offline Streamlit dashboard](docs/reports/phase5a-dashboard.md) to inspect saved real Sentinel layers and river feasibility diagnostics. See the [current research progress](docs/research-progress.md) for validation status.

## Setup (Windows PowerShell)

```powershell
cd mining_monitor_phase1
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set `GEE_PROJECT_ID` in `.env` to your existing registered Google Cloud project ID.

Authenticate once in the terminal:

```powershell
earthengine authenticate
python main.py
```

If needed, use `python main.py --authenticate` instead of the separate authentication command. In Colab, authentication is different: `ee.Authenticate()` followed by `ee.Initialize(project='YOUR_PROJECT_ID')`.

## Critical boundary check

The working Python boundary uses `FAO/GAUL/2025/level2`, `GAUL2_NAME`, and verifies **East Jaintia Hills** and **West Jaintia Hills**. It checks both names and feature count. Expected combined area is approximately 3,818.32 km²; inspect actual output. The original Phase 1 Code Editor script uses older GAUL 2015 names and must not be used to validate the current Python boundary.

The existing `study_area.py` does not implement the optional `GEE_STUDY_AREA_ASSET` override mentioned in `.env.example`; both entry points currently use GAUL 2025. District boundaries and Lukha/Myntdu catchments are different geometries; delineate catchments separately in the river-analysis phase.

## Expected output

`outputs/phase1_inventory.json`: boundary area and raw scene counts for Nov 2023–Mar 2024 and Nov 2024–Mar 2025. **These counts are not cloud-free coverage or classification results.** The program uses a few metadata requests, no imagery exports, and no training.

## Project structure

- `config/settings.py`: season dates, district names, project config
- `src/gee_setup.py`: GEE initialization
- `src/study_area.py`: boundary selection and validation
- `src/data_inventory.py`: metadata-only availability counts
- `gee_js/01_study_area_explorer.js`: visual inspection in Code Editor
- `tests/test_settings.py`: lightweight local unit test

## Next phase

Create season-matched Sentinel-1 VV/VH and cloud-masked Sentinel-2 NDVI/NDTI composites. Keep SAR orbit/pass and incidence-angle effects in mind; avoid comparing incompatible acquisitions. No unsupported claims of illegal mining, measured NTU, acidity, or causal river pollution will be made.

## Phase 2 preprocessing

Phase 1 Python files and requirements are preserved. Phase 2 uses the same `.env`, initialization, boundary checks and exclusive-end seasons: 2023-11-01–2024-04-01 and 2024-11-01–2025-04-01. Run from the project directory with Python 3.10+ and existing requirements installed:

```powershell
python -m compileall -q config src main.py phase2.py tests
python -m pytest -q
python phase2.py --smoke
# If the district centroid is outside the boundary or the patch has no observations:
python phase2.py --smoke --point 92.35 25.35 --pass ASCENDING
# Check coarse district coverage before progressing to Phase 3:
python phase2.py --full-region --relative-orbit NUMBER
# Or request district diagnostics alongside the small-region test:
python phase2.py --smoke --district-coverage
# Optional map (requires geemap); layers are initially hidden:
python phase2.py --smoke --map
```

The example point is only a candidate; the script checks containment. `NUMBER` is a placeholder for a shared relative orbit reported by your test, not an invented orbit. Run `python phase2.py --help` for thresholds and controls. Configuration lives in `config/phase2_settings.py`. Defaults: descending, cloud probability <40, scene cloud percentage <=80, 20 m speckle radius, minimum two observations per season. `--full-region --smoke` is rejected. There are no automatic exports or full-resolution downloads. `build(region, cfg)` in `phase2.py` returns reusable lazy stack and diagnostic images for Phase 3. A graph-built status is not evidence of pixel execution.

SAR (`src/sar_preprocessing.py`): IW, 10 m metadata resolution, VV/VH, fixed pass and a single common relative orbit. Automatic orbit selection maximises the smaller seasonal scene count, with deterministic ties; this does not establish spatial coverage. If coverage is poor, inspect another pass/orbit or use separate orbit-specific analyses rather than merging incompatible geometries. Existing GRD values are dB: convert to linear power, apply a circular focal mean, restore original valid masks, median composite in power, then convert back to dB. dVV/dVH are after minus before in dB. No extra calibration or dB conversion of input log values. A 20 m smoothing radius can blur small disturbances. Orbit-specific footprint gaps remain masked.

Optical (`src/optical_preprocessing.py`): join harmonized SR and cloud probability by exact `system:index`, exclude unmatched scenes, require probability below threshold, retain SCL 4/5/6 (vegetation/bare/water), mask B8A/B9 tile edges and invalid B3/B4/B8 pixels. SCL 0/1/2/3/7/8/9/10/11 are excluded conservatively. SCL shadow masking is not a full projected-shadow model; residual haze/shadows and omission of dark terrain remain possible. Reflectance is divided by 10,000; NDVI=(B8-B4)/(B8+B4), NDTI=(B4-B3)/(B4+B3), with zero denominators masked. Calculate per-image indices then seasonal medians. Changes are after minus before. NDTI is a relative spectral turbidity proxy, not NTU, acidity, a water-only product or a calibrated river measurement. No water mask is applied because land disturbance features also matter.

`src/change_features.py` adds native SRTM elevation (m) and slope (degrees) before clipping. Exact stack order: `dVV,dVH,dNDVI,dNDTI,elevation,slope`. Masks remain separate by band. `ablation(stack, name)` applies a common valid mask only within the selected experiment:

| Experiment | Bands |
|---|---|
| sar | dVV, dVH |
| optical | dNDVI, dNDTI |
| fused | four changes |
| fused_terrain | four changes, elevation, slope |

For the main Phase 3 comparison, all four models must use identical independently held-out locations with valid data for all six bands. Use `src/evaluation_support.py` as described below. Do not globally mask the source stack by optical availability before SAR-only training/coverage analysis; separately report its coverage advantage where optical data is missing.

`outputs/phase2_report.json` records config, dates, selected orbit, bounded per-season orbit histograms, optical raw/joined/unmatched scene counts and execution status. `outputs/phase2.log` records progress/errors. Counts in diagnostic images represent valid contributing observations (including overlapping granules, not unique dates). Smoke mode computes means/ranges of features and counts plus per-band valid fractions over a clipped 500 m radius patch at 30 m, UTM 46N, maxPixels=100000, without bestEffort. It fails if any band has no valid pixels. It also requires a nonzero common six-band valid fraction. Re-run deliberately after inspecting diagnostics; do not repeatedly process the full districts. Quota consumption is not measured or guaranteed by this code.

SAR orthorectification is not radiometric terrain flattening; layover, radar shadow, local incidence angle and moisture differences can mimic changes in these hills. SRTM is about 30 m and optical SCL is coarser than the 10 m reflectance bands. There is no forced reprojection in the lazy stack; consumers must choose an explicit analysis CRS/scale, as the smoke test does. Native masks and nearest-neighbour default sampling remain; a 30 m downstream grid does not create new spatial detail. No classification, accuracy, mining labels, illegality determination or causal downstream degradation claim is produced.

Reference documentation: [Sentinel-1 processing](https://developers.google.com/earth-engine/guides/sentinel1), [cloud probability and edge-mask example](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_CLOUD_PROBABILITY), [S2 SR quality bands](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED).

## Coverage audit and Phase 3 safeguards

Full-region runs now skip centroid creation and containment checks entirely. Only small-region runs validate their test point. `--full-region` automatically evaluates coarse district diagnostics; a small run can request them with `--district-coverage`. If the small run selects an orbit locally, its exact selected orbit is pinned for the district diagnostic build. Both districts and both seasons must be checked for that orbit. The selection heuristic still balances scene counts, but the coverage gate, rather than the scene count, determines whether the selected orbit can proceed. Failed coverage does not automatically select or mix other orbits; inspect another pass/orbit explicitly.

The new `src/coverage_diagnostics.py` performs two bounded district reductions at `--coverage-scale-m 500` (allowed 250–2000 m), UTM 46N, `tileScale=2`, `maxPixelsPerRegion=100000`, without bestEffort. One sums pixel areas of valid coverage and the whole district; the other reports p5/p50/p95 and coarse pixel counts for all four change bands and all four observation counts. Response geometries are removed before retrieval. Reductions use coarse-grid sampling, not expensive native-resolution area aggregation. These are approximate spatial diagnostics and representative distributions; fine gaps or narrow features may be missed. Count distributions include zero outside scene footprints. Change distributions use each band's own valid support.

Each district report contains SAR before/after and optical before/after valid fractions (at least `min_observations`), plus the intersection of all six feature masks. Missing scene footprints are explicitly zero-filled with extended footprint before calculating numerator/denominator areas. The common valid mask is retained as a map layer and reusable image. Full-region coverage gates require every district's SAR fraction in both seasons to meet `--min-sar-coverage 0.90` and each district's common fraction to meet `--min-common-coverage 0.70`. These are configurable screening defaults, not scientifically validated classification reliability thresholds. There is no automatic threshold relaxation. A failed gate is recorded in `phase2_report.json` and exits with an error. Optical-only fractions are reported separately; the common gate limits their shared support. Passing the coverage gate is not approval to train without labels, split design and local inspection.

`--map` now adds dVV, dVH, dNDVI, dNDTI, four observation-count layers, four seasonal-valid layers, common six-band footprint and district outlines. All layers start hidden; opening/activating them requests EE tiles and consumes compute. Use `python phase2.py --full-region --map --relative-orbit NUMBER` for district inspection or `python phase2.py --smoke --map` for the small patch. With `--smoke --district-coverage --map`, the map intentionally shows the small patch; use the full-region command for district maps. Maps are generated before a failed coverage gate raises, when requested, to aid inspection. geemap is optional at runtime. Smoke diagnostics additionally include four seasonal valid fractions and p5/p50/p95, preserving the original nonzero common-data check. A successful smoke does not imply district coverage has passed; `district_coverage_checked` records whether it was tested.

For the main ablation experiment, sample held-out points once:

```python
from src.evaluation_support import shared_evaluation_samples

# `heldout_points` is an independently held-out EE Point FeatureCollection
# with stable unique `sample_id` and non-null `label` properties.
evaluation = shared_evaluation_samples(stack, heldout_points, cfg)
sar_test = evaluation['experiments']['sar']
optical_test = evaluation['experiments']['optical']
fused_test = evaluation['experiments']['fused']
terrain_test = evaluation['experiments']['fused_terrain']
print(evaluation['audit'])
```

This helper samples all six bands once at the explicit 30 m UTM grid and derives each model's evaluation table from that same master collection. It checks geometry types, IDs, labels, empty results and sample loss with bounded scalar metadata, not a full downloaded table. Missing six-band rows fail by default. An explicit `allow_dropped=True` supports a deliberately restricted common-footprint experiment and reports input/retained/excluded counts; document this exclusion bias. Save/freeze the master point collection for reproducibility. Preserve spatial train/test separation, report per-class attrition separately, and never independently resample held-out points for each model. The helper does not create labels, split data or train models. Point sampling cost scales with the supplied held-out collection; keep it appropriately sized.

SAR-only coverage under cloud-limited conditions is a separate analysis from the common-footprint main comparison. Dry-season composites cannot demonstrate monsoon performance; add a separately defined cloud-season evaluation before making that claim. The conservative SCL 4/5/6 policy remains unchanged; reported optical fractions expose the resulting support rather than silently relaxing the mask.

Coverage API references: [bounded district reductions](https://developers.google.com/earth-engine/apidocs/ee-image-reduceregions), [extended-footprint zero filling](https://developers.google.com/earth-engine/apidocs/ee-image-unmask), [masked point sampling](https://developers.google.com/earth-engine/apidocs/ee-image-sampleregions).

