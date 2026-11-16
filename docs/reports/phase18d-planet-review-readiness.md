# Phase 18D — PlanetScope independent review readiness

**Decision: diagnostic evidence prepared and held locally. Formal reviewer release remains blocked on positioning and permissions.** This assessment reused only the existing 8 March 2024 and 25 March 2025 pair. The archive, each selected extracted asset, and the prior inspection SHA-256 matched. Exact delivered item IDs, full UTC timestamps, transforms, bounds and source hashes are in the private scene verification receipt.

| Scene delivered | UTC acquisition | Provider ground control | Publishing stage | Quality category | Processing |
| --- | --- | --- | --- | --- | --- |
| 2024-03-08 | 03:41:50.364191 | true | finalized | standard | L3B, Precision Geocorrection, FineDEM, CC |
| 2025-03-25 | 04:53:48.687695 | true | finalized | standard | L3B, Precision Geocorrection, FineDEM, CC |

The provider JSON and STAC properties agree. A separate `ground_lock` field is absent. Neither delivered scene includes a local numeric accuracy value, CE90, RMSE, surveyed check-point coordinates, residual table or documented uncertainty for these two windows. Both delivered SR rasters have eight uint16 bands, NoData 0, and aligned eight-band UDM2 on the shared north-up EPSG:32646 grid at 3 m spacing. The exact common affine is retained privately. Provider geometry and scene quality describe processing and delivered support. They cannot establish absolute positional accuracy at the sites.

## Local positioning and visibility

The local records contain application geometries of unverified survey accuracy, existing scene-relative patch matches, overlapping LISS-IV images without independent positional accuracy, and model-input Sentinel products. No independently georeferenced, uncertainty-documented controls suitable for validating both Planet scenes at these sites were found. Earlier KORPET matches gave about 3–6.7 m relative offsets at four image-selected texture windows. These are image-to-image measurements. Absolute offsets and residuals remain unavailable, and there is no equivalent independently controlled Sumon result. No absolute accuracy was inferred from coincident grids or the provider ground-control flag.

The original coverage receipts retain common UDM-clear support for 1,767/1,767 KORPET and 4,440/4,440 Sumon application-interior cells. UDM cloud shadow and haze checks do not resolve terrain or cast shadow. Both windows use the same overlapping scene pair, so the two sites share an image evidence group. The imagery supplies a real two-date view, with neither a disturbance class nor an unchanged control established.

## Order permission and release

The original ZIP manifests enumerate delivery members. The STAC and provider JSON and XML describe scene properties. The local order files checked contain no order-specific grant establishing whether two named reviewers can view the imagery locally or receive restricted copies. No names, approvals or terms were inferred. Local display and transfer of full images or derivative crops are separate permission questions. No evidence was distributed.

Obtain the following before release:

1. For both delivered order/item IDs, obtain the governing order/license terms or written confirmation from Planet or the institutional account owner. Identify the two reviewers, confirm whether supervised local viewing is permitted, and separately confirm if encrypted restricted copies or derivatives may be sent. Record retention/deletion, permitted analysis and what derived annotations or excerpts may be published.
2. Obtain either a scene-specific, independently checked geolocation report applicable to these areas or distributed independent stable control coordinates around the two windows in a documented CRS, with source date, survey method, accuracy and rights. For both Planet dates, match persistent corners and road bends across the local area, report east/north offsets, radial residuals and control uncertainty, and demonstrate documented positional suitability ≤30 m. Avoid potentially changed edges, cast shadows and using imagery-derived landmarks as their own control.
3. After release, each reviewer works from the same independent evidence separately. Map conservative WGS84 interiors and record observed timing, alternative explanations, confidence and uncertainty. The coordinator adjudicates genuine agreement or preserves UNKNOWN. Apply the [reference admission protocol](../reference/REAL_REFERENCE_PROTOCOL.md) for any later admission, including independent block and class requirements.

## Private package

The ignored local package contains two neutral review windows with matched date-stamped RGB/UDM panels, coordinates and scale context, unchanged native-grid SR and UDM2 GeoTIFFs, scene/hash and quality receipts, and notes about stable roads/structures and uncertain edges. The fixed B6/B4/B2 display uses a common 0–3500 stored-value stretch. The crosshair is a locator. Model scores and candidate predictions are absent.

Two separate header-only interpretation ledgers and empty WGS84 polygon feature collections are provided, plus a separate empty adjudication ledger. Fields cover source evidence and dates, polygon ID linking the geometry, class 1 change, class 0 verified unchanged/non-mining change or UNKNOWN, reviewer identity, independence, confidence, positional error, rights and adjudication. No review decisions, approvals or geometries were populated. Indian supervised training remains **NO-GO**.

Eight focused Planet and reference-admission tests passed. The private ledger, imagery and restricted delivery metadata stay outside Git.
