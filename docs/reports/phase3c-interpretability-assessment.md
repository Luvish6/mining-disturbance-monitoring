# Phase 3C LISS-IV interpretability assessment — 2026-11-11

**KORPET — NEEDS FURTHER REVIEW.** The east–west road or linear feature south of the application and the broad bright surface to the north are recognizable in both dates. March detail is weak in parts of the narrow application outline. November shows a distinct dark band north of it. The overlay flags its darkest core, while the visible dark area is broader.

**Sumon Pohduna — NEEDS FURTHER REVIEW.** The broad bright surface and a curving linear feature to the east are recognizable in both dates. November shows dark areas within and immediately southwest of the outline, including near the bright surface margin. The precise edges and smaller apparent differences cannot be attributed confidently. Both sites can be inspected descriptively. Neither site has enough evidence for final reference annotation.

## Source and grid verification

| Acquisition | Orbit/path/row | Primary metadata product ID | BAND_META product ID | Sun elevation / azimuth |
| --- | --- | --- | --- | --- |
| 17 March 2024 | 037752 / 111 / 054 | 2437198211 | 25307537831 | 56.54° / 139.41° |
| 12 November 2024 | 041162 / 111 / 054 | 2410398791 | 2630507321 | 43.88° / 157.91° |

Archive metadata identifies IRS-R2A/L4FX, GEOREF/STD, DEM geometric correction, and cubic-convolution resampling by the provider. B2 is green, B3 red, and B4 near infrared. The provider grid is 5 m with 5.8 m sensor sampling reported in metadata. The archived TIFFs store 10-bit DN in uint16 with pixel-is-point metadata and a WGS 84 / UTM zone 46N definition. The native comparison crops use normalized EPSG:32646, as documented in the [preliminary review](phase3c-preliminary-visual-review.md). Neither date declares a NoData value and the source masks are all-valid, including over possible zero fill. Positive three-band signal is therefore evaluated separately. All 12 crops matched archived DN, masks, data type, NoData and source window transforms. Both dates shared the same crop grid at each site. No further resampling or registration correction was applied. Input archive, crop and boundary hashes were unchanged during assessment.

Acquisition dates and identifiers were read from the ZIP members. The disagreement between the primary and band metadata IDs remains unresolved. The [pair review](bhoonidhi-pair-review.md) also records the inconsistent first March catalog footprint. The embedded metadata identifies processing and band scaling, while calibrated surface reflectance and atmospheric correction remain unverified.

## Evidence table

March → November. Counts in application interiors use pixel-centre inclusion. Surrounding counts exclude those pixels. All denominators refer to the saved 250 m context windows.

| Observation | KORPET | Sumon Pohduna | Supporting evidence and limitations |
| --- | --- | --- | --- |
| Recorded signal | 634/634 inside and 19,618/19,618 outside, both dates | 1,593/1,593 inside and 20,871/20,871 outside, both dates | All bands positive and source-mask-valid. Signal coverage measures support only. |
| March pale appearance and compressed contrast | Interior green/red medians 95/71 → 52/28 DN. Green/red/NIR P95−P05 spans 11/21/48 → 19/24/99 DN. | Interior green/red medians 96/73 → 50/28 DN. Green/red/NIR spans 18/38/64 → 58/94/147 DN. | Shared-stretch B4/B3/B2 panels and DN distributions support higher visible-band floor and lower March contrast. Haze is plausible. Phenology, moisture, lighting and product radiometry remain confounders. |
| Low spatial information | Low texture inside 171/634 → 0/634. Outside 3,801/19,618 → 78/19,618. Interior median local SD 3.52 → 6.43 DN. | Low texture inside 310/1,593 → 0/1,593. Outside 5,072/20,871 → 184/20,871. Interior median local SD 4.41 → 11.52 DN. | Local standard deviation of the three-band DN mean in a 5×5 neighbourhood; low texture means SD ≤3 DN. Smooth ground can trigger this review flag, and local texture alone cannot establish visibility. |
| Dark terrain and possible cast shadow | November dark-tail 0/634 inside, 163/19,618 outside, concentrated north of the outline. | November dark-tail 7/1,593 inside and 173/20,871 outside, including a band southwest and dark areas near the bright margin. | All bands at or below their site-specific pooled two-date P02. March dark-tail count was zero in both windows. Dark elongated terrain and edges are compatible with terrain illumination or cast shadow under the lower November sun. Their causes and extent require terrain/occluder checks. |
| Brightness, cloud and saturation | November bright-tail 1/20,252; March 0/20,252. No samples reached the 10-bit ceiling on either date. | Bright-tail 0/22,464 on both dates. No samples reached the 10-bit ceiling on either date. | Bright-tail means all bands at or above pooled P98. Bright ground is visible on both dates. No obvious large opaque cloud was identified over either outline in the matched panels. Thin cloud and diffuse veiling remain possible. The bright-tail flag is insensitive to many clouds; ceiling counts cannot rule out upstream clipping. |

Cloud, haze, terrain-shadow, cast-shadow and jointly interpretable fractions are **unknown** for both dates and sites. The provider reports CloudPercent unavailable. The product has no blue band, and this assessment has no validated cloud mask, independent atmospheric observations, DEM horizon simulation or shadow reference.

## Relative alignment and landmark sensitivity

The [earlier quality review](reference-quality-review.md) shows two persistent-looking rectangular structures and a road bend in the shared southern context. Across three bands, widths and filter settings, their subpixel fits spanned −1.88 to +2.37 m east and −4.11 to −0.36 m north. These are apparent offsets around three clustered, unsurveyed candidates. Visual comparison of the landmark panels supports using them for sensitivity checks, subject to persistence verification.

Four surrounding patches per site were tested on the new native windows. Numbered locations appear on the local panels. High-pass normalized cross-correlation used B2/B3/B4 separately, template widths of 16 and 20 pixels, Gaussian sigma 1.5 and 3 pixels, and an integer ±6 pixel search. Positive east/north denotes November displacement relative to March. Peaks and margins are recorded for all 96 settings; multiple settings at a patch share the same image evidence.

| Site and patch selection | East / north range | Interpretation |
| --- | --- | --- |
| KORPET patches 2–4, around recognizable linear and settlement texture | 0 to +5 / −5 to 0 m | Peaks 0.58–0.88, all inside search. Broad alignment supports visual comparison. |
| KORPET patch 1, diffuse background | −10 to +5 / −5 to +5 m | Peak as low as 0.20. Selection of low-contrast background widens the offset range. |
| Sumon patch 4, near the persistent curving linear feature | 0 to +5 / −5 to 0 m | Peaks 0.55–0.87, all inside search. |
| Sumon patches 1–3, mixed terrain and weaker texture | 0 to +30 / −30 to +5 m | Two B2 fits at patch 1 hit the search edge with peaks 0.20 and 0.26. These failures show sensitivity to texture and template choice. They give no reliable estimate of a 30 m shift. |

Relative agreement of the better textured patches does not establish positional error at either outline. No surveyed control or independently verified application-boundary accuracy was available. The two context windows overlap by 247,900 m² on the common grid. Shared features and patches must not be counted as independent evidence.

## Local review package

The local assessment directory contains two matched panel PNGs, four two-band review GeoTIFFs, source metadata, DN diagnostics and relative offset receipts. Review raster band 1 codes are 1 unflagged, 2 uncertain low texture, 3 potentially obscured or extreme DN, and 4 unsupported. Band 2 records overlapping flags in bit order dark tail, bright tail, 10-bit ceiling, low texture, unsupported. Grey or unflagged areas still require a human visibility decision. These heuristic overlays are neither validated visibility classes nor disturbance labels. No imagery or restricted derivative is included in Git.

## Reference admission still pending

- Reconcile provider product IDs and the March catalog footprint. Record actual acquisition dates, product identifiers, source URLs, processing and rights provenance for any corroboration.
- Establish local visibility using independent inspection and clearer evidence where necessary. Confirm stable features distributed around both sites and document actual positional uncertainty for the images and boundaries under the existing ≤30 m rule.
- Both scenes fall inside their respective study windows. A March snapshot and a November snapshot sample different seasonal states. Use independent dated evidence for both windows and document how it supports the seasonal-composite target despite phenology, moisture and lighting differences.
- Require independent second review and adjudication, conservative target-aligned interiors, original district containment, and adequate positive and negative evidence across the frozen 5 km partitions. Keep ambiguous areas unadmitted and record exclusions. Follow the [reference admission protocol](../reference/REAL_REFERENCE_PROTOCOL.md).

No mining-related change was verified. The application outlines were used only to delimit review areas.
