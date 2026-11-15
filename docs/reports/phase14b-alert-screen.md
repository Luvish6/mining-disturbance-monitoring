# Phase 14B — Local disturbance alert screen

Run from the existing project environment:

```powershell
python -B -m src.phase3.alerts <trusted-observations.json> <new-local-output-directory>
```

The manifest contains an `observations` array and optional `rules` overrides. Each observation supplies `region_id`, `before_date`, `after_date`, `raster` and `model_validation`. Paths are relative to the manifest directory. The inference GeoTIFF uses named `disturbance_probability` and `common_valid` bands on a bounded north-up projected metre grid. Optional `features` points to the exactly aligned 14-band source. All paths and evidence declarations are trusted local operator inputs.

Eligibility additionally requires `model_validation: VALIDATED`, a matching `validated_region_id`, `model_sha256`, `raster_sha256`, `features_sha256`, `run_receipt`, `run_sha256`, `evaluation` and `evaluation_sha256`. These checks bind the input to a real Phase 3 RF run, its validation-selected model and its matching held-out test receipt with both classes and at least two spatial blocks. Regional applicability and approval must be established independently by the operator. The receipts check consistency, and do not establish external validity or calibration. Unvalidated entries emit NOT_VALIDATED. Validated entries with insufficient usable coverage or incomplete supporting evidence emit REVIEW_REQUIRED. No real Indian evidence currently meets the eligibility gates.

Default rules are `threshold: 0.5`, `min_area_m2: 2700`, `min_coverage: 0.8`, `high_score: 0.85`, `repeat_dates: 2` and `overlap_iou: 0.5`. Coverage is computed against the full inference grid. Candidates use four-connected projected cells and report projected grid area, WGS84 centroid, raw mean/maximum scores and signed indicator medians and support counts. Consecutive overlapping detections from the same region, model and data kind are grouped. Repeat counts use distinct after dates, with conflicting same-date statuses handled conservatively. HIGH means score and repeat thresholds both passed, ELEVATED means the score threshold alone passed, and STANDARD covers the rest. These priorities describe screening order. No transport or notification is implemented.

`alerts.json` uses the portal's local snapshot envelope (data and sha256), with GeoJSON features in data and run-level gate receipts alongside it. `alerts.geojson` and `alerts.csv` provide the same candidate records for GIS and review. Keep exports in ignored local outputs. A deterministic fixture yields one four-cell, 3,600 m² HIGH-priority record with two dates and NOT_VALIDATED evidence status. The frontend was unchanged.
