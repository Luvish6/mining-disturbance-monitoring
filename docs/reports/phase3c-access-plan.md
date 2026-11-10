> Text-only publication copy prepared 11 November 2026 from `outputs/phase3c_20261108_01/PHASE3C_ACCESS_REQUEST_PLAN.md`. Private paths/session URL fragments sanitized. Referenced local imagery and licensed assets deliberately excluded. Findings preserved; publication does not admit reference labels.

# Academic imagery access plan — prepared, not submitted

User confirms no provider access; requested prepared requests. No email sent, application submitted, account created or paid order placed.

## First route: Planet academic Basic application

Official page: https://www.planet.com/industries/education-and-research/ . Open Apply Now, use your actual university email, affiliation and supervisor information. Eligibility/approval is determined by Planet. Basic access is currently listed as free for university users, with limited non-commercial research access; preserve the exact license accepted. Do not select a paid subscription or assume institutional access. Ask for archival PlanetScope native single-scene imagery (preferably orthorectified ~3 m or finer if legitimately available), not fused Sentinel-based products. Actual historical scene availability is unknown until authorized search.

AOIs: attach PHASE3C_VERIFIED_MINING_CANDIDATES.geojson (published source perimeters, not observed mining). Start KORPET, then Lumshnong for a second spatial block; Sumon shares KORPET's block. Include a small surrounding context margin, not the full districts. Request dates in [2023-11-01,2024-04-01) and [2024-11-01,2025-04-01). Prefer similar seasonal timing, low cloud/shadow over each source polygon, native orthorectified RGB/multispectral imagery with acquisition timestamp, scene ID, original footprint, CRS, UDM/quality mask, processing level, and documented local/geometric accuracy. Requested <=3 m resolution is a preference, not a claimed delivered spec or accuracy. Actual independent reference positional uncertainty must meet the existing <=30 m policy; ground sampling distance alone is insufficient.

Purpose: non-commercial B.Tech study of new/expanded mining-related surface disturbance in East/West Jaintia Hills, independently interpreted before Sentinel-1/2 model feature extraction. No claim to establish mining illegality.

Preserve license/attribution, keep raw commercial assets private unless redistribution explicitly permitted. Ask whether thesis figures, derived conservative reference polygons and reproducibility metadata may be published. After access, provide original scene metadata, exact dates/IDs, permitted local imagery, UDM, accuracy statement and license receipt through the authorized local project workflow. Never paste API keys into reports or source control. Then two independent reviewers interpret conservative interiors and adjudicate disagreement; access alone does not create accepted labels.

## Parallel route: NRSC/Bhoonidhi and NSIL

Official API/access: https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/ ; portal https://bhoonidhi.nrsc.gov.in/bhoonidhi/home.html ; order policy https://www.nrsc.gov.in/nrscnew/archive_order_procedure.php . Contact bhoonidhi@nrsc.gov.in for portal/access support or data@nrsc.gov.in for institutional eligibility, using the official current contact instructions. Government-academic classification applies only if the institution qualifies; do not assume all universities are Government Entities. Ask the supervisor/institution to confirm category. For finer-than-5-m data, consult official NSIL instructions (eodata@nsilindia.co.in) and obtain a research quote/permission if needed. No purchase authorized.

Request archived Cartosat/appropriate IRS orthorectified imagery for the same polygons/windows, product-level source dates, cloud-free AOI coverage, actual GSD and positional error, delivery/license details. Ask for an inventory-only reply first if imagery requires an order. Bhuvan 2025 and 2024–2022 mosaic labels are insufficient: request underlying scene acquisition date at the exact location. A 2025 mosaic could be outside the after season.

## Other routes and historical ground evidence

Maxar/Vantor official access: https://developers.maxar.com/docs/discovery/guides/discovery-guide . Ask university GIS/remote-sensing library for existing entitlement, or request an academic archival quote at the official provider site. Specify same AOIs/windows and product metadata. No free entitlement or actual availability established.

NASA Earthdata Login can unlock HLS L30 assets (https://hls.gsfc.nasa.gov/data-access-and-tools/), but these remain 30-m Landsat-derived observations and should not delay the high-resolution request. Public USGS Landsat previews already acquired.

Ask Indian Bureau of Mines/Meghalaya Mining & Geology/MSPCB and the relevant mine operators for original 2023–2024 and 2024–2025 drone/orthomosaic surveys, inspection photos or mine plans. Require actual capture timestamps in both study windows, camera/survey locations, CRS/datum, documented geolocation uncertainty, original provenance and reuse permission. An annual report title, administrative approval date or geotag without accuracy is insufficient. Request historic non-mining forestry/agriculture/road records and matching imagery across several fixed blocks, including train blocks. A current visit helps corroborate identity but does not substitute for historic dates.

## Email template — edit placeholders, do not send automatically

Subject: Academic request for archival imagery over three small Meghalaya research sites

Dear Imagery Access Team,

I am [your name], a B.Tech student at [university], supervised by [supervisor]. I request academic, non-commercial access to archival imagery for the small East/West Jaintia Hills project perimeters in the attached GeoJSON: KORPET, Sumon Pohduna and Lumshnong (70 ha).

We require independently dated scenes acquired during 1 November 2023–31 March 2024 and 1 November 2024–31 March 2025 to interpret mining-related surface disturbance before extracting Sentinel-1/2 model features. We prefer orthorectified imagery of approximately 3 m or finer, low cloud/shadow over the AOIs, acquisition timestamps, original scene identifiers/footprints, quality masks, CRS/datum and documented positional accuracy.

Please confirm actual archive availability, the appropriate student or institutional access route, costs if any, and permission to include attributed figures and derived reference annotations in a non-commercial thesis. We will retain raw imagery privately and follow your license and attribution requirements. These project perimeters identify candidate locations and are not verified excavation boundaries or assertions of illegality.

Could you advise which scenes and metadata can be provided and what institutional documentation you require?

Kind regards,
[your name]
[university and department]
[university email]
[supervisor, if appropriate]
