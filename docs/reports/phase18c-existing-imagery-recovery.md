# Phase 18C — Existing imagery recovery

## Archive inventory and coverage

Found eight distinct ZIPs in the project parent and data directory: five PlanetScope orders and three Bhoonidhi LISS-IV products. The five Planet downloads contain delivered SR and UDM2 rasters. The SHA-256 checks matched the earlier inspection records. No catalog-only item was counted as imagery and no new imagery was acquired. The private inventory records exact filenames, delivered Planet item IDs, acquisition UTC, bounds, item footprints and per-site recorded signal. The misplaced original Planet after order is identified by its *actual* acquisition date below.

All Planet deliveries have eight-band surface reflectance in order coastal blue, blue, green I, green, yellow, red, red edge and NIR, plus aligned UDM2, on native delivered 3 m EPSG:32646 grids. Stored SR NoData is zero. Counts use positive signal in all eight bands and the original UDM clear screen.

| Planet order or delivery | Actual acquisition UTC | KORPET valid / clear, within 300 m | Sumon valid / clear, within 300 m | Decision |
| --- | --- | ---: | ---: | --- |
| Original before, filename March 25 | 2024-03-25 04:35:45 | 0 / 0 | 0 / 0 | Rejected for these sites; off-site delivery |
| Original after, filename March 26 | 2025-03-25 04:45:29 | 0 / 0 | 0 / 0 | Rejected; different delivered scene without recorded site signal |
| Replacement before | 2024-03-18 04:35:39 | 31,406 / 0 | 31,411 / 0 | Rejected; every valid cell within each circle flagged haze |
| Final before | 2024-03-08 03:41:50 | 31,406 / 31,406 | 31,411 / 31,411 | Strong paired coverage; requires positional evidence and permissions |
| Replacement after | 2025-03-25 04:53:48 | 31,406 / 31,406 | 31,411 / 31,411 | Strong paired coverage; requires positional evidence and permissions |

The clear pair also has full common clear support across the saved application outlines: **1,767/1,767 KORPET** and **4,440/4,440 Sumon** 3 m cell centres. These outlines are context, with unverified survey accuracy. Circles and scene context overlap so the sites do not constitute independent image evidence. The retained scenes share a common lattice. Earlier KORPET texture matches suggested 3–6.7 m relative offsets. These are not positional control, and Sumon has no independent registration check. No UDM haze, cloud, shadow or unusable flags occur within the paired circles. Terrain and cast shadow remain uncertain. The local Sumon panels show broadly recognizable exposed-looking and vegetated patterns and tonal differences. They do not establish a target change or stable control. Reviewer-use and research rights for the exact orders remain undocumented in the materials checked.

The three Bhoonidhi ZIPs have 10-bit DN in uint16, B2 green, B3 red and B4 NIR, with a delivered 5 m WGS84/UTM 46N grid and nominal 5.8 m sensor sampling. They declare no TIFF NoData or validated cloud/shadow QA. Positive common signal excludes zero padding but cannot establish interpretability. Product-specific research and reviewer-use terms and absolute positioning remain unverified.

| Bhoonidhi ZIP | Platform and date | Site coverage and decision |
| --- | --- | --- |
| RAF17MAR2024037752011100054SSANSTUC00GTDA.zip | Resourcesat-2A, 2024-03-17 | Signal across both outlines. Pale, low-contrast image with possible haze. Requires additional quality/accuracy and permissions. |
| RAF12NOV2024041162011100054SSANSTUC00GTDA.zip | Resourcesat-2A, 2024-11-12 | Paired signal on identical grids, 634/634 KORPET and 1,593/1,593 Sumon cells; darker terrain and potential shadow. The pair requires further review. |
| R2F19NOV2024070502011000054SSANSTUC00GTDB.zip | Resourcesat-2, 2024-11-19 | Both anchors inside the product rectangle, zero positive three-band pixels within 300 m at both. Rejected for these sites. |

The March/November 12 LISS-IV pair has relative alignment consistent with close agreement in better-textured windows, with band-dependent offsets and unstable fits in weak texture. Provider IDs and the conflicting March catalog footprint remain unresolved. Lumshnong lacks signal in this pair. None of the inspected Planet or LISS-IV delivered footprints covers the Gevra or Bhubaneswari locations.

## Private handoff and next action

Private diagnostic packages retain unchanged native eight-band values and UDM2 GeoTIFFs for the clear Planet pair at both sites. Matched native-grid panels use a fixed B6/B4/B2 display stretch of 0–3500 stored values, explicit unsupported and UDM-flagged overlays, and warnings for terrain shadow and positional uncertainty. The companion LISS-IV folders retain the existing native DN crops, side-by-side panels and uncertainty overlays. No imagery or private delivery metadata is staged.

**Formal independent review is pending.** Both sites have a real paired Planet option. No new Planet search is needed to establish coverage. First verify written permission for the two independent reviewers and obtain independent stable control around the shared site cluster with documented positional error at or below 30 m. Then have the reviewers assess dated, conservative interiors separately, excluding ambiguous shadow and registration edges. If controls cannot be established, the exact evidence gap is positioning, not an additional nominal scene. A clearer, seasonally closer alternative before image is relevant for the LISS-IV route only if the stronger Planet pair cannot proceed. Training also requires corroborated change and control labels across independent frozen blocks. Candidates remain UNKNOWN and Indian training remains NO-GO.

Eight targeted Planet and reference-admission tests passed. See [LISS-IV interpretation](phase3c-interpretability-assessment.md), [provenance reconciliation](phase3d-provenance.md), and the [reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md).
