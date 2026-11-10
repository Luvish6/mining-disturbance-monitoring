> Text-only publication copy prepared 11 November 2026 from `outputs/phase3c_bhoonidhi_acquisition_20261110/ACQUISITION_REPORT.md`. Private paths/session URL fragments sanitized. Referenced local imagery and licensed assets deliberately excluded. Findings preserved; publication does not admit reference labels.

# Phase 3C — replacement LISS-IV acquisition plan

10 November 2026. **No accepted higher-resolution before/after pair has yet been obtained.** This is a screening/download plan, not confirmation of usable scenes. Original ZIP, inspection outputs and Phase 1–3C code/tests remain unchanged. No classifier training, mining labels, orders, messages to providers or satellite downloads were performed.

## Evidence and coverage distinctions

Reviewed `outputs/phase3c_bhoonidhi_inspection/REPORT.md`, `inspection.json`, copied product metadata, existing crop; the Phase 3C verified-candidate GeoJSON, scene inventory, catalog receipt and reference-admission protocol. The nine after-season records below were supplied by the user from logged-in portal screenshots; screenshots are not available in the project. The portal reportedly returned 15 scenes: **six IDs are unknown and are not invented**. The saved 401 response is expected without portal/API login and does not establish absence of imagery.

| Coverage term | What it establishes | What it does not establish |
|---|---|---|
| Catalog bounding box / raster rectangle | Broad spatial search hit or storage envelope | A swath, non-padding pixels, cloud-free ground |
| Actual image footprint / image-corner polygon | Provider's nominal acquired swath geometry, potentially slanted | Internal gaps, pixel validity or local clear ground; verify whether portal geometry is image or product extent |
| Valid-pixel coverage | Actual required-band signal/quality support at the full site and context | Cloud/shadow-free interpretability; nonzero alone is only a support proxy |
| Cloud-free usable coverage | Locally interpretable, adequately located pixels after checking clouds, haze, terrain/cloud shadows, saturation and resolving power | A mining label, change between seasons or illegality |

The rejected 19 November 2024 scene illustrates these distinctions: KORPET is inside the rectangle but outside recorded signal. At KORPET and approximately 5 km × 5 km around it all three bands are zero; nearest common-positive pixel is 5.08 km away. TIFF masks misleadingly report all-valid because source nodata is undeclared. The full-scene 78.10% nonzero support is **not** a clear-sky percentage. CloudPercent is blank. ProductID differs between the primary metadata/accuracy report and BAND_META.txt; retain this provenance discrepancy.

Additional read-only check of the existing 5 m crop using the original published application polygons: **0/634** pixel centres have positive B2/B3/B4 inside KORPET, **0/1,593** inside Sumon Pohduna. These are rasterized polygon pixels, not independent samples or surveyed areas. The full polygons lie within the saved crop. Thus this acquisition is also unsuitable for Sumon. Lumshnong is east of the original scene rectangle; it is not covered by this product. No new source pixels were downloaded.

## Search anchors — longitude first in GIS files

| Site | Latitude N | Longitude E | Search strategy |
|---|---:|---:|---|
| KORPET | 25.21552876312328 | 92.07169655129559 | Replace rejected after image; search full source polygon and context |
| Sumon Pohduna | 25.21908290812763 | 92.0732783689618 | Search jointly with KORPET, then verify each site independently |
| Lumshnong (70 ha) | 25.16639280941408 | 92.36492230074244 | Separate eastern AOI; re-evaluate existing leads here |

These are existing KML ring-vertex anchors, **not mine centres**, with undocumented positional accuracy. The source polygons in `search_aois.geojson` are geographically verified application boundaries, not disturbed masks. KORPET and Sumon anchors are ~425 m apart; a single well-positioned scene may serve both but this is not guaranteed. Use polygons and a proposed 1 km context margin for screening, not just an anchor or a district-wide bbox. The margin is an operational preference, not a scientific acceptance threshold. Preserve original geometry.

## Candidate-scene shortlist and next human action

All nine dates fall in the after window. **No before-season LISS-IV scene ID is available.** User reports the eight remaining displayed catalog footprints missed KORPET. Accordingly none is recommended for a blind KORPET download. All eight remain unverified at Sumon/Lumshnong; proximity, satellite, path/row and repeated dates cannot establish coverage.

| Date | Satellite | Scene ID | Evidence / uncertainty | Next human action |
|---|---|---|---|---|
| 12 Nov 2024 | R2A | `041162_111_54` | Catalog lead; reported KORPET miss; no local pixels examined | First metadata/quicklook recheck at Lumshnong/Sumon, not blind download |
| 19 Nov 2024 | R2 | `070502_110_54` | Downloaded: rejected at KORPET and Sumon; Lumshnong outside rectangle | Preserve archive/report; do not redownload |
| 24 Nov 2024 | R2 | `070573_111_54` | Catalog lead; reported KORPET miss; no local pixels examined | First metadata/quicklook recheck at Lumshnong/Sumon |
| 1 Dec 2024 | R2A | `041432_110_54` | Catalog lead; reported KORPET miss; no local pixels examined | Next geometry/preview check, comparing actual swath with 19 Nov |
| 6 Jan 2025 | R2 | `071184_110_54` | Catalog lead; reported KORPET miss; cloud/footprint unknown locally | Backup only if new site-specific screen passes |
| 11 Jan 2025 | R2 | `071255_111_54` | Same uncertainty; different listed path from rejected scene | Backup geometry/preview check; path alone is not evidence |
| 18 Jan 2025 | R2A | `042114_110_54` | Catalog lead; reported KORPET miss; no local pixels examined | Backup geometry/preview check |
| 16 Feb 2025 | R2A | `042526_111_54` | Catalog lead; reported KORPET miss; no local pixels examined | Later-season fallback; seek seasonally comparable before scene |
| 7 Mar 2025 | R2A | `042796_110_54` | Catalog lead; reported KORPET miss; no local pixels examined | Last timing fallback; seek March before evidence if used |

The first three rechecks (12 Nov, 24 Nov, 1 Dec) are a **workflow priority**, chosen for early-season timing and sampling both listed paths, not an evidence-based ranking of cloud-free coverage. A later scene with demonstrated full AOI support must outrank them. Because all other reported footprints missed KORPET, new coordinate/polygon searches, including the six untranscribed records, are more promising for KORPET than downloading these leads. Do not identify a particular one as a confirmed hit until its geometry is inspected.

## What Bhoonidhi offers before a full download

The official [user manual, section 2.3.3.3](https://bhoonidhi.nrsc.gov.in/bhoonidhi_resources/help/docs/Bhoonidhi_ISROEOHub_UserManual_V2.0.pdf) documents product metadata, a quick view, footprint and metadata download. These can reject obvious swath misses or poor-looking scenes before downloading the archive. The publicly indexed [Browse & Order interface](https://bhoonidhi.nrsc.gov.in/bhoonidhi/) also exposes scene date, quality, corner coordinates and Download Meta; interpretation and completeness must be checked per product. A quicklook is a screening aid, not proof that a small mine is resolved or cloud-free. The reviewed official documentation does **not** establish a LISS-IV per-pixel clear-sky mask or guaranteed valid-data footprint available before download.

The [official API specification](https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/) documents authenticated catalog access, geometry-intersection search and item details. Authentication is required; Online=Y concerns delivery readiness, not imagery quality. Online=N uses Browse & Order for delayed delivery. The reviewed API text does not promise a LISS-IV cloud mask. No private session or fresh authenticated search was accessed in this task. Human portal login is the practical route here; no new API software is needed.

For each promising lead save the preview, metadata and a screenshot of the candidate polygon over the footprint, with scene ID/date visible. Prefer actual ImageUL/UR/LR/LL corners over ProdUL/UR/LR/LL rectangular corners when both are available. If only one unnamed corner set is supplied, ask what it describes; mark coverage uncertain. Do not georeference a quicklook by stretching its rectangle over geographic bounds without a documented image transform. Record preview resolution and black padding; a 512-pixel overview is too coarse to certify a tiny AOI. If a preview cannot resolve the question, ask for a site-specific crop or download only the best-screened single archive.

## Acquisition checklist

- [ ] Resourcesat-2 or 2A **native LISS-IV multispectral B2/B3/B4**, about 5.8 m native resolution; verify product mode and whether only mono/pan is offered. A 5 m resampled grid is not new native detail. Avoid synthetic/fused bands as independent evidence.
- [ ] Actual acquisition falls within **2023-11-01 to 2024-03-31** or **2024-11-01 to 2025-03-31** (exclusive ends 2024-04-01 and 2025-04-01). Record date, scene/product IDs, processing level and sensor.
- [ ] Overlay the full candidate polygon plus desired context on the actual image footprint. Reject clear misses and black swath margins; prefer an interior position. Bbox intersection is insufficient.
- [ ] Inspect preview at the candidate for clouds, haze and terrain/cloud shadows; blank cloud metadata means unknown. Scene-average cloud cover cannot certify the site.
- [ ] Save metadata/quicklook and local evidence of coverage before a large download. Verify delivery status and research usage/figure/derived-label permissions; no paid order is authorized here.
- [ ] Download one screened scene at a time, hash ZIP and retain it unchanged. Inspect all three actual bands at the exact anchor, entire polygon and context; distinguish declared masks from inferred fill. Do not use universal DN>0 as a cloud-clear mask.
- [ ] Produce a georeferenced B4/B3/B2 crop, per-band data/support statistics and manual interpretability notes. Green/red/NIR have no blue, so this is false colour, not true RGB.
- [ ] Seek same-sensor/mode, similar month and viewing/illumination for the counterpart; independently inspect both dates and their shared usable polygon. Check alignment on stable features and document positional uncertainty, not just GSD.
- [ ] Apply the existing admission policy (including documented positional error <=30 m and independent second review) before any reference labeling. Unknown accuracy stays unknown; exposed soil is not proof of mining.

## Practical sequence to obtain the first pair

1. In the logged-in portal, make two precise AOI searches for both seasons: the KORPET–Sumon cluster and Lumshnong. Search both R2 and R2A LISS-IV; do not lock to the rejected path/row. Recover metadata for all 15 original results if available; keep the six missing identifiers unknown until transcribed. Save actual hit lists locally.
2. Recheck 12 Nov / 24 Nov / 1 Dec against Lumshnong and Sumon first; reject any proven footprint miss without a full download. For KORPET, seek a new swath that encloses the full polygon. A before image cannot repair the missing after signal in the existing archive.
3. Before downloading, confirm at least one geometrically plausible counterpart exists in the other season. Choose the site with the strongest **two-season** coverage/preview evidence, not a desired mining-change appearance. The cluster is efficient because one pair may cover two sites; Lumshnong is an independent fallback, not a claimed better-covered site.
4. Download only the best screened after scene; inspect a small full-resolution crop. If rejected, record why and try the next lead. If accepted for visual evidence, download the seasonally matched before candidate and inspect it independently. Reverse order if only the before season has a clearly promising available product.
5. Once both are interpretable over the same site, retain original dates/metadata/license/accuracy and review coregistration. Record a pair as accepted for **reference interpretation**, not automatically as positive mining disturbance. If no LISS-IV pair exists, use the existing institutional/academic request plan for other native dated higher-resolution imagery; do not substitute Sentinel-2 classifier inputs, mosaics without pixel dates, or invented labels.

**Immediate human action:** open the logged-in portal at Lumshnong (25.16639280941408 N, 92.36492230074244 E) and the KORPET–Sumon polygons, inspect the first three metadata/quicklooks, and save scene ID/date, image-corner coordinates, preview and AOI overlay. Download only the first scene that passes that screen and has a plausible before counterpart. No particular scene is yet authorized scientifically as usable.

## Deliverables and preservation

`scene_shortlist.csv` preserves all nine IDs and per-site uncertainty; `site_search_coordinates.csv` and `search_aois.geojson` preserve verified locations; `catalog_provenance.json` records user-transcribed origin and six unknown IDs. No satellite data was staged, committed or uploaded to GitHub; no Git operation was performed. Existing .gitignore lacks a data-wide satellite exclusion, so it must not be relied on to protect ZIP/TIFF files in a future commit. Keep raw ZIP/TIFFs local or use an appropriate explicit ignore rule before any future Git workflow; no Git configuration or production file was changed here. Tests were **not run**, as requested for a documentation/data-inventory-only task; the previously observed 103 passing result was not newly revalidated.
