> Publication copy prepared 11 November 2026. Local paths/session-bearing URL components sanitized; scientific findings unchanged. Original local document preserved and excluded from Git. Historical statuses describe their report context, not necessarily the latest implementation.

# Labeling and imagery preparation

Run from `<PROJECT_ROOT>` using
`<PROJECT_PARENT>\.venv\Scripts\python.exe`.
These commands prepare inputs; none trains a classifier or invents labels.

## Start a reference collection

```powershell
$py='<PROJECT_PARENT>\.venv\Scripts\python.exe'
& $py -B phase3_data.py init-labels data\labels\draft.geojson
```

The starter is deliberately empty. In QGIS create a WGS84 polygon layer and add
fields `label_id` (text), `label` (integer), `source` (text), `provenance` (text),
`interpretation_date` (ISO date text), `reviewer` (text), `reviewed` (boolean),
`confidence` (text: high/medium), and `synthetic` (boolean, false for real data).
Export as RFC 7946 GeoJSON after independent review. GeoJSON with no features
cannot itself define QGIS field types; create the fields in the QGIS layer.

Draw polygons only where independent evidence supports the seasonal class:
0 = stable/non-mining disturbance; 1 = mining-related disturbance. A mine already
present before the comparison is not automatically a new disturbance. Record
actual imagery acquisition dates and evidence in source/provenance. Keep unknown
areas unlabeled; include verified hard negatives. Use conservative interiors,
exclude ambiguous boundaries, and obtain second-review adjudication. Metadata
validation cannot verify that an interpretation is scientifically true.

## Plan the spatial partitions before labeling

Save your actual small study AOI as one WGS84 Polygon/MultiPolygon or Feature.
The grid command does not choose an AOI or assign reference classes:

```powershell
& $py -B phase3_data.py block-grid data\aoi.geojson data\labeling_cores.geojson
```

Load the resulting cores in QGIS. They use the same 5 km grid, seed 42 and 120 m
interior buffers as dataset preparation. Each core has a frozen train,
validation or test assignment. Digitize within a core; polygons crossing cores
will be excluded by dataset preparation. Do not search seeds or boundaries for
favorable test results. Collect independent positive and negative references
across many blocks and partitions. Avoid copying one site's interpretation into
both training and held-out regions. Restrict this EPSG:32646 workflow to the
project's Meghalaya study region.

```powershell
& $py -B phase3_data.py check-labels data\labels\reviewed.geojson outputs\label-check-v1.json
```

Exit code 2 means corrections or additional reference coverage are needed. The
report includes polygon areas, core exclusions, partition class counts and
independent block IDs. Counts here are polygons, not pixels. Even a passing label
check leaves `training_ready=false`: imagery validity, class support after
rasterization and the prepared manifest must still be checked.

To import an existing reviewed Earth Engine reference asset (no asset is created):

```powershell
& $py -B phase3_data.py import-ee-labels YOUR_ACTUAL_ASSET_ID data\labels\reviewed.geojson
```

The importer uses existing authentication and caps collection size at 5,000.
All required reference properties and review checks still apply.

## Register a genuine paired export

Use the paired export graph described in PHASE3.md and keep its successful
seasonal coverage report. No export is automatically submitted by these commands.
The original satellite export remains unchanged. For a downloaded 14-band,
30 m north-up EPSG:32646 GeoTIFF with explicit nodata, create a provenance JSON
with these fields filled from actual records:

- `source`, `export_id`, `operator`, `retrieved_date` (YYYY-MM-DD).
- `data_kind`: `real`; synthetic test rasters must remain `synthetic`.
- `raster_sha256`: SHA-256 of the original downloaded file.
- `coverage_report_sha256`: SHA-256 of the saved successful report.
- `relative_orbit` and `orbit_pass`: exactly those used in the report/export.
- `seasons`: `[["2023-11-01","2024-04-01"],["2024-11-01","2025-04-01"]]`.
- `band_order`: the exact 14 source bands listed in PHASE3.md.

Obtain hashes using PowerShell `Get-FileHash -Algorithm SHA256`; JSON hashes use
lowercase hex. The command checks the hash, seasonal coverage match, source grid,
nodata and declared band order. It assigns missing band descriptions only from
the explicit recorded band order; conflicting descriptions fail. It preserves
existing validity masks and never treats numeric zero as nodata.

```powershell
& $py -B phase3_data.py register-raster data\raw\paired.tif data\raw\provenance.json data\paired-v1.tif --coverage-report outputs\coverage_1km\phase2_report.json
& $py -B phase3_data.py audit-raster data\paired-v1.tif outputs\raster-check-v1.json
```

The audit reads windows and reports per-band finite valid coverage, range, mean
and common-valid coverage. This does not certify label quality or fine-scale
remote-sensing suitability. Inspect actual before/after imagery, cloud and SAR
artifacts. Do not infer illegal mining or water chemistry from these statistics.

## Prepare the frozen dataset

Only after reference review and image checks:

```powershell
& $py -B phase3.py prepare data\paired-v1.tif data\labels\reviewed.geojson data\dataset_v1
```

Inspect manifest exclusions, class pixel counts and independent partitions before
any training. A single small AOI may not contain sufficient independent blocks;
expand acquisition and reference collection rather than random-splitting pixels.
All output files use new paths and refuse replacement. See PHASE3.md for model
training and final-test safeguards. No real labels or results are supplied by
these tools.
