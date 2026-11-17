# Phase 22E — Maus weak-label optical training-set attempt

**DATASET NO-GO.** The frozen patch plan contains 24 TRAIN windows across eight states and 15 validation windows in Odisha. All 39 exports failed the required image/mask grid check. Zero patches and zero positive-bearing groups were admitted in either split. No normalization, QA overlays or model diagnostic were produced. All visual interpretations remain HUMAN REVIEW PENDING.

The dated [preregistration amendment](../preregistration-phase22e-v1.md) was committed at `16a141ca3aa745467be1299606ab8624f1cf611d` before Earth Engine imagery export. The designation is WEAK_UNVERIFIED for both Maus foreground and explicitly sampled background. Background may contain unmapped mines. Validation scores would measure agreement with these annotations. Verified reference counts remain zero.

## Frozen plan and resource gate

| Split | Planned positive windows / groups | Planned background windows | Geographic coverage | Accepted |
|---|---:|---:|---|---:|
| TRAIN | 8 / 8 | 16 | Eight states | 0 |
| Validation | 5 / 5 | 10 | Odisha | 0 |

Two of the ten fixed TRAIN anchors failed the full window plus buffer geometry test before resource estimation. Neither was replaced. The background plan preserved the 1:2 target in both splits and includes random and all four prespecified spectral proxy strata. The proxy strata are sampling heuristics. Full windows and their projected 2,050 m guard were checked against state boundaries and opposing split polygons. Background windows avoided all Maus polygons and the available project candidate exclusion files. All planned windows were non-overlapping.

The plan estimated 39 direct TIFF work units at up to 2 MiB each (81,788,928 bytes). The 39 returned TIFF bodies totalled 1,641,911 bytes. The original split was verified before and after at SHA-256 `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`. Plan and export used no TEST imagery or model labels. The geographic exclusions used frozen source polygons across all splits.

## Grid failure and corrected export contract

The first acquisition reused the Phase 22C optical graph and downloader. The latter requested its hard-coded 64 × 64 dimensions. Patch affines had 10 m cells and the mask rasterizer wrote the correct 128 × 128 layout, so the image occupied only one quadrant of each planned window. The alignment gate rejected every patch and preserved source IDs, grid metadata, hashes and the rejection reasons. Cropping the masks to the smaller images would change the frozen support and was not used.

The isolated Phase 22E downloader now explicitly requests and verifies 128 × 128 before writing a TIFF. A regression test exercises 64 × 64 rejection and 128 × 128 acceptance with synthetic in-memory TIFFs. The correction has no new live export verification. A complete retry would need 39 more responses after 39 completed responses, exceeding the preregistered 45-response limit for this attempt. The old rasters and receipts remain intact. A separately preregistered acquisition attempt can reuse the same plan bytes in a fresh ignored directory. It must verify a real 128 × 128 response before proceeding through the remaining frozen plan.

## Artifacts

Local `outputs/phase22e_maus/` contains the complete patch plan with geometry, the two empty accepted manifests, patch rejection/provenance receipts, and the dataset summary. The [sanitized attempt ledger](phase22e-training-set-manifest.json) records aggregate counts, anonymized patch receipts and freeze hashes. Source footprints, full georeferenced plans, rasters and weak masks are local. The engineering diagnostic will run only after a new acquisition passes the DATASET GO checks.
