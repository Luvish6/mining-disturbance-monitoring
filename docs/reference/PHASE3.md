> Publication copy prepared 11 November 2026. Local paths/session-bearing URL components sanitized; scientific findings unchanged. Original local document preserved and excluded from Git. Historical statuses describe their report context, not necessarily the latest implementation.

# Phase 3: reference-supervised mining-related disturbance screening

Phases 1–2 remain in place. The sole existing-code correction materializes a
bounded three-row list of coverage properties so nested EE collections do not
lose their feature rows during response retrieval. The default 500 m diagnostic
can exceed its existing pixel cap; use the explicit 1 km audit command when
needed, keeping coverage thresholds unchanged. This extension is not a detector
of illegality.
No real reference labels or satellite raster exports were present at audit.
No real model has been trained. Synthetic tests are software checks only.

## Reproduce in the existing repository

```powershell
cd <PROJECT_ROOT>
$py = '<PROJECT_PARENT>\.venv\Scripts\python.exe'
# Already installed during this implementation; for a fresh environment:
& $py -m pip install torch --index-url https://download.pytorch.org/whl/cpu
& $py -m pip install -r requirements-phase3.txt
& $py -B -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\mining-phase3-tests"
& $py -B phase3.py --help
# The following require actual independently reviewed labels and imagery:
& $py -B phase3.py prepare data\paired.tif data\reviewed.geojson data\dataset_v1
& $py -B phase3.py train data\dataset_v1\manifest.json outputs\run_v1 --device cpu
# Inspect validation only during model selection:
& $py -B phase3.py infer data\dataset_v1\manifest.json outputs\run_v1 outputs\validation_v1 --split validation
# Freeze model and threshold before final test evaluation:
& $py -B phase3.py infer data\dataset_v1\manifest.json outputs\run_v1 outputs\test_v1
```

Use a new output directory for each dataset, run and evaluation. Synthetic inputs
require `prepare --synthetic` and `train --synthetic-smoke`; they cannot silently
pass through real mode. The CPU torch wheel includes no pretrained weights.
CUDA fallback exists but CUDA was not tested. Choose a compatible CUDA build
separately if needed. Run only trusted, locally produced RF pickle artifacts.

## Label collection and review

1. In QGIS or Earth Engine, inspect both seasonal observations, acquisition
   availability, clouds, shadows and higher-resolution reference imagery where
   its license permits. Keep evidence/source dates; never derive labels by
   thresholding the model's own change features.
2. Digitize conservative polygon interiors, excluding mixed boundary pixels.
   Class 0 means explicitly reviewed stable land or non-mining disturbance;
   class 1 means reference-labeled mining-related disturbance. Unknown areas
   remain unknown (255). Include hard negatives such as road work, landslides,
   agriculture and bare river sediment where independently verified.
3. Compare the specified seasons (2023-11-01 through 2024-03-31 and 2024-11-01
   through 2025-03-31). Do not label every pre-existing mine as new disturbance.
   Document ambiguous/excluded areas and the interpretation definition.
4. Have a second reviewer adjudicate uncertainty. Import only reviewed high or
   medium confidence polygons, with no overlaps and unique stable IDs.
5. Export RFC 7946 WGS84 GeoJSON. Every polygon must have these properties:

```json
{
  "label_id": "your-stable-reference-id",
  "label": 1,
  "source": "actual reference source and acquisition dates",
  "provenance": "how the seasonal mining-related disturbance interpretation was verified",
  "interpretation_date": "2026-11-08",
  "reviewer": "actual reviewer identifier",
  "reviewed": true,
  "confidence": "high",
  "synthetic": false
}
```

This property example supplies no geometry and is not a training label.
`load_labels` accepts GeoJSON or a bounded EE FeatureCollection; to persist an
EE import, initialize the existing project and call
`save_ee_labels(ee.FeatureCollection(actual_asset_id), output_path)`. The default
5,000-feature cap is explicit. The asset must carry the same required metadata.
No assets are invented or created automatically.

## Paired imagery contract

The main experiment uses one bounded tile, up to 4,000,000 pixels, with one
north-up square-pixel EPSG:32646 grid. Prefer 30 m to match Phase 2. Ingestion
rejects a different CRS or inconsistent band descriptions; it never silently
reprojects or rescales. Align future tiles to the same origin and resolution
before extending this initial single-tile pipeline.

Exact band descriptions and ordering:

```
before_VV, before_VH, before_NDVI, before_NDTI,
after_VV, after_VH, after_NDVI, after_NDTI,
dVV, dVH, dNDVI, dNDTI, elevation, slope
```

SAR is seasonal dB; optical inputs are seasonal NDVI/NDTI derived from Sentinel-2
reflectance. This compact initial model uses these two optical indices, not RGB
reflectance. Terrain and six change features feed RF; optional neural auxiliary
feature fusion is deferred. Before/after map bands are explicitly NDVI, not RGB.

`ee_inputs.paired_graph` reuses the existing seasonal preprocessing and requires
an explicitly pinned orbit. `export_task` requires a matching successful district
coverage report and returns an **unsubmitted** small-region Drive export. Review
its region, grid, nodata (-9999), budget and metadata before calling `start()`.
No export or imagery download was submitted during this work. Record the export
task ID, Phase 2 report, project, dates, orbit/pass, thresholds, CRS and transform
in a sidecar next to the downloaded raster. Confirm channel descriptions and
nodata in the downloaded GeoTIFF. Set the raster tag `data_kind=real` only after
verifying that provenance; for synthetic fixtures use `data_kind=synthetic`.
The code cannot authenticate the truth of manually supplied provenance.

Masked/nodata pixels remain invalid. Four validity channels accompany each
four-channel temporal observation, making eight model inputs per branch.
Missing values are replaced by normalized zero only after attaching validity
flags. Supervision and the principal RF/CNN comparison require all 14 channels
valid and an explicit reference label. No unknown pixel becomes class 0.

## Splits, statistics and reproducibility

Default patches are 64×64, non-overlapping, anchored on the tile pixel grid.
Deterministic SHA-256 hashing assigns metric 5 km blocks to nominal 60/20/20
train/validation/test partitions (actual fractions vary for small block counts).
A 120 m interior buffer is applied to every block. Entire polygons crossing
block cores and patches touching buffered boundaries are excluded. Cross-split
patches therefore have a minimum 240 m gap. This is a conservative initial
design, not proof that landscape autocorrelation vanishes at that distance.
Increase `--buffer-m` and assess sensitivity for local geology and disturbance
clusters. Nearby cores in the same partition also lose edges intentionally.
Polygon groups spanning blocks are excluded rather than split across partitions.

Dataset manifests preserve raster/label/patch SHA-256 hashes, channel order,
grid, seed, block IDs, splits, transforms, per-class partition counts and
exclusions. Keep source imagery and label provenance with this manifest.
Do not search split seeds to optimize test scores. Missing partitions or absent
training classes fail before training; obtain more independent labels instead.
Manifest checks reject altered patches, overlapping windows and block leakage.

Channel-wise normalization pools before/after **training block observations
only**, separately for VV, VH, NDVI and NDTI. It uses population variance with a
small constant-channel floor. Valid unlabeled pixels within training patches
may inform this unsupervised scaling. RF uses raw six features and training-only
pixels (deterministic cap 100,000), with balanced class weights.

The shared encoder has widths 16/32/64 by default; absolute temporal feature
differences feed a small U-Net decoder. Logits are trained with masked BCE,
training-derived positive weight capped at 20, including negative-only patches.
Sigmoid is applied at inference. Adam, plateau learning-rate reduction,
validation-loss early stopping, seeds, history, model/data version and a best
checkpoint are recorded. The test partition never selects the checkpoint.

## Evaluation and outputs

RF and CNN use one ordered set of common valid labeled pixels; IDs are frozen in
`common_pixels.npz`. Reports include both classes' precision, recall, F1, IoU,
support, confusion matrices, class balance, supplementary overall accuracy,
per-block scores and paired block-bootstrap uncertainty for positive-class F1
differences. Undefined metrics are null. A single block gets no confidence
interval; fewer than ten blocks carry an explicit instability warning.
Threshold is fixed a priori at 0.5; changing it requires validation-only selection
and recording the new policy before test use. Never tune on the final test map.

Outputs: loss curves, confusion plots, prediction/reference/validity and seasonal
NDVI GeoTIFF bands. Unlabeled but common-valid pixels receive probability maps;
evaluation uses labeled pixels only. Edge strips and excluded blocks are not
predicted by this initial patch workflow. Full-tile sliding-window inference,
overlap blending and RGB exports are future extensions. Raster tags and plot
titles distinguish synthetic demonstrations from real inputs. None of the
synthetic test scores is scientific evidence.

## Before real training

Resolve live district coverage and inspect the actual common-valid footprint;
acquire a small paired export with documented provenance; supply reviewed
positive and hard-negative reference polygons across enough independent blocks;
review exclusions and all partition class counts. Automated metadata validation
cannot establish label truth. No claim of confirmed illegal mining is supported.

## River and dashboard preparation (future)

Delineate Lukha and Myntdu catchments independently from district boundaries.
After validating disturbance maps, define upstream/downstream sampling locations,
season-matched NDTI observations, river masks, observation coverage and CHIRPS
rainfall controls. Test temporal/spatial associations with explicit uncertainty.
NDTI is a relative spectral indicator, not NTU, acidity or chemical contamination.
Imagery cannot establish mine-specific causation, see all underground mining,
or demonstrate monsoon performance from dry-season data.

Prepare dashboard interfaces around georeferenced probability/validity rasters,
model and manifest IDs, independent evaluation and coverage reports. Alerts must
say screening indicator or field-verification priority. No dashboard or river
conclusions have been generated from synthetic tests.
