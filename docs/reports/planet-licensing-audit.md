# PlanetScope licensing and technical audit

**Date: 2026-11-23. Baseline: fedb5d5, phase22-label-sources.** This is a focused offline audit, not a new scientific experiment. The user relayed Planet support clarification; no original support email or accepted account-specific agreement was independently authenticated in this audit. Public support pages and their linked May 2023 E&R Basic terms were checked. Where specific delivery or figure rights remain unresolved, the decision is **REQUIRES PLANET CONFIRMATION**.

## Highest-priority finding: 30 reviewer items are Sentinel-only

All 30 IDs in `outputs/phase23i_review/crosswalk.json` match the 30 `s2_10m/metadata.json` records and `chips10` PNGs. `scripts/phase23i_review.py::acquire10` uses the existing `src/optical_preprocessing.py::collections` Sentinel-2 SR harmonized / cloud-probability join. Its cached 64 × 64 arrays contain three seasons of B4/B3/B2 plus packed observation counts. Source IDs use Sentinel granule identifiers, not Planet item IDs. No acquisition function was called during this audit.

Using the existing `render10` offline renderer, every blinded chip reproduced **pixel-for-pixel (30/30 decoded images)** from that cached Sentinel data. All 30 ZIP PNGs are byte-identical to `chips10`; ZIP CRC validation passed. The ZIP contains exactly 33 approved files: 30 PNGs, reviewer B HTML, blank CSV sheet and README. The unpacked share folder has the same member set. Its README explicitly identifies Copernicus Sentinel-2. The older `chips/` renderer uses Sentinel-2 seasonal RGB and Sentinel-1 VV only. Neither renderer uses PlanetScope or another licensed commercial sensor.

**Planet's raw-imagery restriction does not affect these chips' source data.** Preserve the Sentinel reviewer package. This source-compliance finding does not turn input-derived visual review into independent mining reference truth, waive admission rules or establish reviewer completion. No returned reviewer decisions were found in the checked review package; sharing history is not proven by a locally prepared ZIP.

| Reviewer / research material | Source and evidence path | Licensing / technical status | Required action |
|---|---|---|---|
| 30-item share ZIP and folder | `outputs/phase23i_review/share_reviewer_B.zip`, `share_reviewer_B/chips10/`; cached `s2_10m/` and source metadata | Sentinel-2 only; all 30 pixels reproduce; Planet restriction inapplicable | Use blinded HTML/CSV offline with Copernicus attribution; no Planet viewer dependency |
| Legacy 30 m chips / coordinator overlays | `outputs/phase23i_review/chips/`, `adjudication/`, `adjudication10/`; existing renderers | Sentinel-1/2 only; coordinator overlays expose screening outlines | Preserve; keep coordinator maps out of blinded review |
| KORPET/Sumon raw review package | `outputs/phase18d_planet_review/withheld_evidence/`, original Phase 7 SR/UDM2 and native-grid crops | Planet raw/pixel-preserving materials; previous release already withheld | Remain licensee-only; no external viewing or copying under owner's Basic license |
| Planet RGB/NDVI display and diagnostic PNGs | `scripts/phase8_planet_portal.py`, `outputs/phase7_korpet_detailed_review/` | Rendered pixels can retain spatial/spectral information; file extension is not a release license | Private only; specific public excerpt use is REQUIRES PLANET CONFIRMATION |
| Phase 23K source scenes, masks and diagnostics | `outputs/phase23k_planet/` | Raw SR/UDM2 private; dense data products are not presumed non-reconstructable | Keep ignored; do not include in reviewer ZIP or public export |
| Published 23K observability summaries | `docs/reports/phase23k-*-screen.json` and first-scene report | Aggregate counts, widths and descriptive summaries; no per-pixel source arrays | Retain scientific limitations and cite Planet; no calibrated water-quality or absolute-accuracy claim |
| Human-created future reference polygons | Empty review ledgers and future original annotations | Generally shareable per relayed support clarification if raw pixels cannot be reconstructed | Document authorship, provenance, rights and actual two-reviewer decisions; do not republish source rasters or third-party original boundaries |

## Sharing history and technical exposure

No evidence of external Planet raw sharing or reviewer access was found in the inspected repository, local package instructions or release records. This is **not proof that no email, upload, screen share or tunnel ever occurred**. Repository records cannot establish that history; the licensee must confirm what was actually sent. No mail was sent, reviewer contacted, account accessed or original evidence removed. No quarantine of the Sentinel ZIP was warranted. Existing withheld Planet evidence remains withheld; a private release-hold note was added under `outputs/planet_licensing_audit/PLANET_RELEASE_BLOCKED.md` without moving originals.

The Planet service binds explicitly to `127.0.0.1`, checks the exact Host and same-origin request headers, uses no-store responses and serves a fixed private in-memory resource map. It has no raw-TIFF download route; only diagnostic PNGs and receipt JSON are exposed there. Existing tests verify wrong Host/origin rejection, unavailable resources and path traversal. These are technical access controls, **not third-party license permission**. Do not tunnel, publish, deploy or let external reviewers use the licensee's service. Public React exports do not fetch raw Planet rasters; the private view calls only `/__planet_review__/` on the loopback service.

No imagery/archive/array paths were found in reachable Git history or the current tracked tree. `frontend/public` and the production build contain no TIFF/ZIP/NPY/NPZ payloads or Planet-named assets. Private resources are generated at runtime, not bundled. The checked paper directory had no Planet figure assets; the paper has no included Planet image to approve. Existing ignore/publication safeguards remain in effect. The build still contains the private workspace code, but no private evidence pixels. This inspection does not certify uninspected external deployments.

## Actual scene and order evidence

| Local item ID | UTC acquisition | Use |
|---|---|---|
| 20240308_034150_36_24bf | 2024-03-08T03:41:50.364191Z | Existing KORPET/Sumon pair, before |
| 20250325_045348_68_24cb | 2025-03-25T04:53:48.687695Z | Existing KORPET/Sumon pair, after |
| 20241108_044308_36_24f0 | 2024-11-08T04:43:08.363827Z | Phase 23K river observability |
| 20250220_045741_92_2534 | 2025-02-20T04:57:41.926618Z | Phase 23K river observability |

Delivered scene metadata records ground_control=true, finalized publishing stage and standard quality for these four items. The checked KORPET receipt records L3B; its separate ground_lock field is absent. No local scene-specific RMSE/CE90 or independent surveyed positional-control report establishes ≤30 m suitability. Existing 3–6.7 m KORPET texture-match offsets are relative image-to-image offsets, not absolute geolocation accuracy. Pixel size, shared affine and provider ground control cannot replace independent control.

Exact catalog UUIDs, order-like descriptions, item IDs and manifest hashes are retained privately in `outputs/planet_licensing_audit/private_order_inventory.json`. Four catalog identifiers were recovered; they must be matched to the original Planet order confirmations before being asserted as authenticated order IDs. Do not send signed asset URLs, credentials or raw metadata wholesale to reviewers. Original ZIPs were only enumerated/read for metadata; none was modified.

## Governing conditions and unresolved questions

The checked [sharing guidance](https://support.planet.com/hc/en-us/articles/22540409084701-Dataset-sharing-guidelines-for-the-Education-and-Research-Basic-program) and linked [E&R Basic terms](https://assets.planet.com/docs/E%26R_Basic_ToS_Revised_May_2023.pdf), definitions and sections 4–5, distinguish non-reconstructable representations from licensed source data and require attribution. A JPEG/PNG label alone proves neither. The applicable accepted account/order terms must still be retained. The user-reported support clarification bars external reviewer access to the downloaded raw scenes under this account, including local display. Reviewers can acquire the same items independently under their own eligible licenses.

For any proposed Planet publication image, retain the specific excerpt, intended resolution/distribution, processing, original rights notices and release decision. Do not distribute native RGB band arrays, per-pixel indices, analytical crops or map tiles by renaming them as screenshots. The public sources do not settle whether these existing dense diagnostic RGB/NDVI PNGs satisfy all Permitted Imagery conditions: **REQUIRES PLANET CONFIRMATION**. No such image was released here. Summaries were checked for absence of source-pixel arrays, not granted a blanket license for every possible derivative.

[Citation guidance](https://support.planet.com/hc/en-us/articles/115006038627) requests a Planet source citation and an adjacent image copyright notice using the content year. The private viewer now credits Planet Labs PBC for 2024/2025. The paper identifies Planet as the source, dates the two 23K scenes and explains private-only handling; any future figure must carry its own adjacent notice and rights clearance. Attribution is not permission.

[Planet's CE90 guidance](https://support.planet.com/hc/en-us/articles/36564214987421-How-to-translate-the-RMSE-value-to-CE90) describes a factor of 1.51. It supplies neither a scene RMSE nor independent control for this project. No scene-specific CE90 was calculated; no unsupported numeric scene-accuracy claim was found in the active paper/viewer. The paper now states this limitation explicitly. Missing positional evidence should be obtained from an independently georeferenced control provider, not invented from aggregate Planet specifications.

## Necessary corrections and recommended workflow

1. Added `scripts/audit_review_package.py`: fail closed on unexpected/duplicate ZIP members, altered PNGs relative to trusted chips, non-Sentinel metadata, or remote/private-viewer dependencies. Before future release, regenerate trusted chips from the documented Sentinel cache and rerun the audit. Private per-item source/render hashes are in `outputs/planet_licensing_audit/review_chip_provenance.json`.
2. Corrected the existing private viewer's rights notice and added Planet image attribution. Added current guidance to README/handoff and a superseding addendum to the historical Phase 18D report; original results are preserved.
3. Corrected the IEEE draft's mistaken implication that Sentinel-2 uses UDM2; only Planet uses UDM2. Added Planet acquisition dates, attribution, handling and absolute-accuracy limitations. No scientific result or mask was recomputed.
4. Continue the 30-item Sentinel-only blinded review. For genuinely independent Planet reference interpretation, each reviewer needs their own eligible access or a specifically cleared non-reconstructable evidence package. Preserve UNKNOWN until actual independent interpretation, positional evidence, rights and admission requirements pass.

**Next support clarification, only if Planet excerpts are needed:** privately match the recovered catalog IDs to order confirmations, provide the exact four item IDs and the intended flattened RGB/NDVI excerpt plus reviewer/publication use, and ask whether that particular representation qualifies under the account's accepted terms and what attribution applies. Do not ask reviewers to use the licensee's raw scenes. No additional Planet clarification is needed to release these Sentinel-only chips as Sentinel materials. Prior external sharing history and original account/order terms still require licensee confirmation.

## Validation

All 30 blinded PNGs reproduced exactly; 30/30 ZIP images matched and CRC passed. Existing Planet service tests and three new package tests are included in the full offline suite. The first full run had 372 passes and an unrelated Windows temporary-directory rename PermissionError; a fresh permitted temporary directory yielded **373 passed**. Frontend **11 tests**, TypeScript and production build passed. The corrected paper rebuilt locally (3 pages) with package installation and shell escape disabled; PDF remains ignored at `outputs/planet_licensing_audit/ieee-paper.pdf`. No raw imagery, restricted metadata or images are proposed for Git publication. Publication/privacy audit passed on the staged safe files.

No Earth Engine requests, imagery downloads, training, new labels or TEST evidence processing occurred. Indian supervised admission remains NO-GO, candidates UNKNOWN and operational alerts zero.
