> Publication copy prepared 11 November 2026. Local paths/session-bearing URL components sanitized; scientific findings unchanged. Original local document preserved and excluded from Git. Historical statuses describe their report context, not necessarily the latest implementation.

# Deferred Phase 4 input contract

Status: planning only. Phase 3 remains PARTIAL, so no river analysis or dashboard
processing is authorized by this contract or has been started.

After all Phase 3 gates pass, supply a versioned package with:

- A georeferenced, checked disturbance probability raster, binary screening map
  and explicit valid-data footprint. Initial RF output bands are probability,
  binary, common-valid and predictive entropy. Zero disturbance and unmapped
  pixels are different states; invalid predictions use nodata=-9999.
- EPSG:32646, 30 m grid and full affine transform, spatial extent, comparison
  seasons, feature definitions, model/dataset IDs and SHA-256 values.
- Training/reference provenance, frozen spatial partitions, four-ablation
  evaluation receipt, per-class support/metrics, independent block counts,
  validation selection policy and threshold. Do not use test results to revise
  the classifier after publishing the final evaluation.
- Coverage and omission documentation. SAR-only and common-valid comparison
  footprints must not be conflated. RF probabilities are uncalibrated and their
  entropy is not an empirical confidence interval.

The next phase must separately verify Lukha and Myntdu catchment boundaries,
drainage direction and river masks; district boundaries are not catchments.
Assign upstream/downstream observation locations using drainage evidence and
field validation where feasible. Summarize upstream disturbance exposure with
valid-area denominators and threshold sensitivity, recording missing areas.

Use actual season-matched Sentinel-2 river observations, spectral NDTI and
coverage counts, with documented CHIRPS rainfall timing and potential lag effects.
Retain observational dates and independent spatial sampling units. Any resulting
association is exploratory, with explicit confounders and uncertainty.

NDTI is not measured NTU, acidity or chemical contamination. Neither a spectral
association nor a screening map proves mine-specific downstream causation or
illegality. Underground activity and monsoon reliability require separate
evidence. This document defines future interfaces, not Phase 4 conclusions.
