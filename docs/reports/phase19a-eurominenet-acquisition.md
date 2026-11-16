# Phase 19A — EuroMineNet acquisition and development gate

**Development NO-GO.** The frozen 12 TRAIN and four VALIDATION sites were acquired and structurally validated. Visual quality and mine-complex separation remain unresolved. No model fitted, no roster or threshold changed, and TEST pixels stayed sealed.

## Transfer and provenance

The [RODARE direct archive](https://rodare.hzdr.de/record/4656/files/EuroMineNet.zip) supplied **304,543,082 response-body bytes** for the Phase 19A range requests. Conservative accounting charged the full requested range in advance plus a 16 KiB header allowance per request, including retries and interrupted requests. Including 4,259,372 bytes of prior bounded probes, the aggregate charge was **312,931,222 bytes** against **536,870,912**. This leaves **223,939,690 bytes**. The 16 sealed TEST members account for 166,496,150 compressed bytes; an additional 3 MiB was reserved for transport and ZIP overhead. Returned bodies and conservative charged totals are distinct. The range journal and cached range hashes permit resume, and ZIP extraction checks CRC, size, and a locally recorded SHA-256. All 64 extracted development member hashes reverified.

The frozen member receipt records all **80 exact names, ZIP local-header offsets, compressed sizes, uncompressed sizes and source CRCs**. TEST entries exist only in metadata, with no TEST member extracted. The request ledger was checked against the sealed member offsets. Frozen member receipt SHA-256 is `9e4f03b3997f1b5e96289f7c1d1900daa9d09f4c60097ed6985c562d78e30dc4`. Development diagnostics SHA-256 is `823e0217304844241b32f360929dc5ec6e79dfc6eade8a52ae79e986acc4ddb9`.

## Development diagnostics

All 16 annual image pairs agree within site on CRS, affine, dimensions, ten ordered int16 optical bands and scale/offset tags. The two years' shape-matched, binary masks stayed in their original row/column grids. The offline RGB overlays preserve image/mask indexing with no mask georeferencing, resampling or padding. Matching geometry and band encoding permit a stored-value comparison; exact sensing timestamps and radiometric comparability across conditions remain unverified. None of the images declared NoData in the inspected development set. The explicit source-mask plus nonzero-signal check excluded zero pixels. This does not quantify cloud, snow, shadow or illumination exclusions.

| Split | Sites | Provisional nonoverlapping windows | Positive mines in windows | Expansion | Contraction | Unchanged |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TRAIN | 12 | 132 | 9 | 9,884 | 2,444 | 2,150,360 |
| VALIDATION | 4 | 64 | 4 | 1,355 | 4,334 | 1,042,887 |

The counts use deterministic seed-42 windows chosen before examining masks. They measure candidate support on the pixel grid, prior to the visual and independence gate. Over the full development rasters, TRAIN contained 77,275 labeled expansion and 3,396 contraction pixels and VALIDATION 6,201 expansion and 24,285 contraction pixels. Poland_9 is 109 rows high and supplies no full 128 × 128 window under the no-padding rule. Edges and unsampled windows are excluded by construction. The NO-GO leaves **zero certified training/validation windows**. No quantitative snow or cloud mask was invented.

### Why the gate failed

Czechia_2 VALIDATION has extensive bright, winter-like cover in 2023 compared with 2024. This obscures portions of the overlay and stable local anchors. Its exact scene dates and quality masks were unavailable, so the affected areas could not be certified. The development footprint envelopes had zero cross-split intersections, but Czechia_2 and Czechia_3 TRAIN are the closest pair at about **2.23 km**. The records checked do not establish whether the two windows show separate mining complexes. Treat this as an unresolved leakage risk, with no claim of actual overlap. TEST spatial checks remain deferred under the payload seal.

**Next action:** Obtain the exact Czechia_2 acquisition IDs and applicable snow/cloud validity layers or a reviewed visibility mask. Obtain authoritative mine-complex boundaries or identifiers for Czechia_2 and Czechia_3, then revisit the frozen development gate. No training command is released while the gate fails. Indian supervised status is unchanged.

The ignored local workspace is `outputs/external_eurominenet/phase19a/`. It holds the frozen member and transfer receipts, per-member hashes, development diagnostics, overlays and explicit NO-GO decision. From the project root, the original commands are:

```powershell
python -B -m scripts.eurominenet_acquire outputs/external_eurominenet/phase19a
python -B -m scripts.eurominenet_validate outputs/external_eurominenet/phase19a
```

Four focused tests passed for range verification and budget refusal, verified resume, TEST directory-only indexing, and fixed-window transition counting.
