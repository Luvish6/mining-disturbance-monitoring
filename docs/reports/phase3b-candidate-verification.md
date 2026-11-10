> Text-only publication copy prepared 11 November 2026 from `outputs/phase3b_20261108_01/PHASE3B_CANDIDATE_VERIFICATION_REPORT.md`. Private paths/session URL fragments sanitized. Referenced local imagery and licensed assets deliberately excluded. Findings preserved; publication does not admit reference labels.

# Phase 3B candidate verification — 8 November 2026

Five existing mining leads investigated; one geographically verified, zero verified seasonal disturbances, four unresolved. Two historical background/hard-negative leads identified; zero current admissible non-mining references. No real reference polygons accepted and no supervised training or Phase 4 started.

## Repository and preservation

Canonical repository: `<PROJECT_ROOT>`. Inspected the four reference/labeling guides, annotation modules, reference inventory, original GAUL boundary and original Phase 3A workspace. Original inventory contained five null geometries. Existing drafts had only empty revision_000000; the user's browser test polygon was not promoted to a reference. Existing phases and outputs preserved; new versioned directory and separate annotation workspace used. Fixed 5-km blocks, buffered cores and seed 42 unchanged. Random Forest code unchanged.

Baseline: 97 passed, 0 failed, 0 skipped in 34.94 s. Final: 103 passed, 0 failed, 0 skipped in 38.02 s. Logs supplied separately. Exact invocation: project venv Python, `-B -m pytest -q -p no:cacheprovider` from canonical repository.

Changes: added src/phase3/candidate_geometry.py and tests/test_candidate_geometry.py (six tests). Parser preserves original KML polygon vertices, validates KML WGS84 geometry, rejects unsafe XML/network links and invalid coordinates/rings, checks original GAUL containment and matching district. No geometry repair or invented transformation. Two minimal display changes in annotation_map.py and annotation_editor.js show source geometry as candidate evidence, site name and original-source link. Editor workflow reused, not rebuilt. Originals backed up in .phase3_audit_backups/phase3b_candidate_maps_20261108. Test fixtures are synthetic, not scientific evidence.

## Verified geography: KORPET

Candidate korpet-kml-v1, parent lead korpet. West Jaintia Hills. Original perimeter vertex used as map anchor: longitude 92.07169655129559, latitude 25.21552876312328. Full original polygon retained, not a centroid or interpreted disturbance footprint. It is valid and wholly covered by the original unsimplified study boundary and correct district.

[Official application](https://environmentclearance.nic.in/state/FB_ECGeneral_Report.aspx?pid=197899) identifies KORPET LIMESTONE MINING PROJECT, applicant Preciously Bareh, Korpet/Nongtalang, West Jaintia Hills. Its direct [KML attachment](https://environmentclearance.nic.in/download.aspx?files=writereaddata/FormB/TOR/GPS/1501202296671119KML.kml) is archived with SHA256 c0b032cf10395266ae57b5759419b99ce6c7a4d4106cce6a78b887fc842504fe. KML WGS84 longitude/latitude follows [OGC KML Annex B](https://docs.ogc.org/is/12-007r2/12-007r2.html). Identity horizontal conversion; altitude discarded; no guessed projected datum. Survey observation date, publication date and measured positional accuracy unknown. ToR issue date 13 March 2021 is a separate administrative date, not a survey date.

Important source discrepancy: summarized application bounding ranges do not encompass every original KML vertex. Preserve the linked geometry and flag the mismatch for human scrutiny. Application geography supports a proposed mining-project location; it does not establish active mining, seasonal change, precise disturbance edges or illegality. Public access permits inspection/citation, but no open redistribution license was established; external reuse requires a rights check. Confidence: defensible published project geography, not field validation. Status verified_geographic_location; seasonal status awaiting_independent_imagery.

## Other four original leads

Brishyrnot I investigated first. [IBM inspection](https://ibm.gov.in/writereaddata/files/173028842167221b2556cb8Brishyrnot.pdf), 10–11 September 2024, mine code 38MEG657001, 42.051 ha. Page 3 actual pit 2 grid E441704–442000, N2784069–2784179 is distinct from proposals. Full inspection text and relevant rendered page inspected; accessible 270-page operator compliance/approved-plan annexures examined for corroborating CRS. Pit-grid CRS remains UNRESOLVED: no independently tied datum/zone established. No EPSG:32646 assumption and no WGS84 transformation. Separate 65-ha Brishyrnot Deposit-II documents excluded. September inspection lies between the study windows; actual operations are not paired seasonal disturbance evidence. Additional source: https://www.starcement.co.in/api/uploads/1765689392979-951792410-SCML-42.051%20Ha-EC%20Compliance%20Report-Apr%2725%20to%20Sep%2725.pdf . A remaining original boundary-pillar spreadsheet lead is https://miningplan.ibm.gov.in/MINING_PLAN/tempfolder/1679049459641442f3392e0Boundary%20Pillars.xlsx ; not yet verified.

Mynkree [IBM inspection](https://ibm.gov.in/writereaddata/files/174065170867c03cbc8fd51Mynkree_Limestone_Mine.pdf), 5 December 2024, is accessible. Rendered page 3 confirms proposed grid N2789636–2789793, E437823–438013; actual work Nil, discontinued operations, but historical benches/excavation noted. Unstated CRS prevents transformation. This does not qualify the site as a negative label.

Saryngkham A: original Ministry of Coal publication reports production commencing 3 June 2025, outside after season. Migrated EIA old URL now returns HTML. Public hearing metadata identifies 23 July 2024 record/file 133, but full original coordinate table not inspected. Indexed WGS84 snippets were not admitted as geometry. Original lead citation: https://www.coal.nic.in/sites/default/files/2025-08/PIB2153719.pdf . EIA: https://megspcb.gov.in/public%20hearing%20compressed/Ms_saryngkham_a_coal_mine_draft_eia_23rd_july_2024.pdf .

Amsyndui: original URL returns portal HTML, not PDF. Public hearing metadata identifies 17 September 2024 record 22, Draft EIA file 92. Public file endpoint returned HTTP 401; no authentication bypass attempted. Dominic Pohrmen's 4.50-ha proposal was not conflated with different owners/areas. Original URL retained in unresolved CSV. Hearing metadata: https://megspcb.gov.in/pollution/public/hearing .

All four remain unresolved_coordinates; no candidate map falsely locates them. No spatial accuracy, publication date or license invented. IBM and EIA publication permissions remain unestablished beyond public consultation/citation.

## Map and independent evidence

candidate_review_maps/korpet_01/review.html generated with existing annotation map command, point 92.07169655129559 25.21552876312328, radius 400 m, --live. Original GAUL boundary, fixed blocks/cores, before/after RGB, cloud/observation context, drawing/editing, draft download/import preserved. Candidate source polygon explicitly is not a disturbance label. Imagery acquisition records alongside map.

Before window 2023-11-01 through 2024-04-01 exclusive: 46 Sentinel-2 scenes, 24 unique acquisition dates, optical-valid fraction 1. After 2024-11-01 through 2025-04-01 exclusive: 58 scenes, 28 unique acquisition dates, optical-valid fraction 1. These are source-pipeline seasonal medians, not single-date observations or independent reference evidence. Actual source dates retained in imagery_record.json and CSV. No district-scale export or raster training-feature extraction run. Live tile credentials expire; regenerate into a new versioned directory when needed.

No independently inspected, dated high-resolution before/after pair obtained. Google Earth historical imagery capability documented, but no visible site image date inspected. Planet program access/license and actual scene availability not obtained. Official proposal geography is not paired seasonal imagery. Independent imagery CSV distinguishes provider possibilities from actual acquired context. Ground sampling is not positional accuracy. No restricted imagery downloaded.

## Background discovery

Two historical leads only: Um-Tyraa RR soil sampling reference (2013; published 2017, table 1 unmined) and Lukha/Lunar SS3 exposed riverbed/boulders (2013–2014; published 2016). Original raw DMS retained in CSV, not transformed/admitted because datum and accuracy unverified. Neither establishes present non-mining conditions. No qualified cross-block background coverage yet; do not change partition or assign blocks from approximate geography. Published sources linked per CSV.

## Browser QA

User previously confirmed page opening, imagery, drawing, selection and metadata display. This run obtained a Chrome accessibility snapshot only; did not exercise save/download/reimport on a synthetic isolated map. Thus browser functional QA INCOMPLETE. No claim of successful browser round trip. Existing automated suite covers backend review invalidation and rejection of insufficient evidence; this is distinct from browser testing. Exact isolated manual procedure in NEXT_ACTIONS. No synthetic annotation entered genuine candidate workspace or accepted data.

## Research readiness

Geographic discovery PARTIAL. Independent seasonal evidence NOT READY. Real accepted references 0. Phase 3 supervised training BLOCKED. Location verification does not imply seasonal disturbance or legality. Existing quality gates remain enforced.
