> Publication copy prepared 11 November 2026. Local paths/session-bearing URL components sanitized; scientific findings unchanged. Original local document preserved and excluded from Git. Historical statuses describe their report context, not necessarily the latest implementation.

# Reference-source investigation â€” 8 November 2026

No independently verified positive or negative seasonal reference samples were
admitted from the sources examined. A known mine, lease or permit does not prove
new disturbance in the two comparison seasons. Absence from an inventory does
not prove non-mining. Candidate records remain separate from training labels.

| Source | Geographic/date utility | License/access | Decision |
|---|---|---|---|
| [Maus et al., PANGAEA.942325](https://doi.pangaea.de/10.1594/PANGAEA.942325) | Georeferenced global mining polygons and validation points, interpreted from 2019 imagery | CC-BY-SA-4.0; two GeoPackages downloaded and hashed | Local intersection yielded zero polygons and zero control points. Historical data is not seasonal change evidence. |
| [Ministry of Coal, 7 August 2025](https://www.coal.nic.in/sites/default/files/2025-08/PIB2153719.pdf) | Named Saryngkham A in East Jaintia Hills; production began 3 June 2025 | Public report; open geospatial redistribution license not established | Known location only. Production starts after March 2025; prior surface preparation remains unverified, so assign neither class. |
| [Saryngkham A draft EIA, July 2024](https://megspcb.gov.in/public%20hearing%20compressed/Ms_saryngkham_a_coal_mine_draft_eia_23rd_july_2024.pdf) | Indexed document includes lease coordinates and a proposed project description | Government-hosted consultant document; license and positional accuracy not established | Candidate evidence. Search index readable; direct web retrieval did not expose the PDF for full verification. No perimeter or labels imported. |
| [Amsyndui limestone EIA, September 2024](https://megspcb.gov.in/public%20hearing%20compressed/Amynsyndui_limestone_quarry_deia_17th_sep_2024_compressed.pdf) | Indexed West Jaintia Hills lease pillars; underlying mining plan dated 2021 | Redistribution and positional error unverified | Useful candidate location; a lease is not an observed new-disturbance mask. Not admitted. |
| [KORPET environmental-clearance application](https://environmentclearance.nic.in/state/FB_ECGeneral_Report.aspx?pid=197899) | Indexed West Jaintia Hills bounded coordinates and a 2021 proposal | Public application; direct open returned cache miss; license/accuracy unverified | Candidate only, without paired seasonal surface-disturbance verification. |
| [West Jaintia Hills consent records](https://ocmms.nic.in/OCMMS_NEW/getData.action?application=approved&district=WEST+JAINTIA+HILLS+DISTRICT&state=Meghalaya&status=consent&yearFrom=2014&yearTo=2024) | Several named limestone/stone operations and consent dates | Public indexed listing; session-dependent URL; geospatial license not verified | Consent status establishes no seasonal disturbed footprint or independent negative labels. |
| [Indian Bureau of Mines, 2024â€“25 Guwahati inspections](https://ibm.gov.in/IBMPortal/pages/mcdr-inspection-reports-and-violation-letters---2024-25---guwahati-region) | Inspection listings include East Jaintia Hills limestone operations | Public listings; map accuracy/license not established | Investigated as corroborating records; no paired reference polygons obtained. |
| [MineNetCD, original publisher](https://rodare.hzdr.de/record/3251) | Global paired high-resolution change benchmark, 100 sites | CC-BY-4.0; archive approximately 3.5 GB | Regional coverage, exact dates and compatible geographic labels not verified. Large archive not downloaded or substituted for this study's labels. |
| [NATMO Jaintia Hills portal](https://geoportal.natmo.gov.in/dataset/jaintia-hills) and [Meghalaya state GIS](https://stategisportal.nic.in/stategisportal/Home/State/17) | Potential cartographic context | Direct retrieval timed out; layers/terms not verified | No dataset acquired or asserted usable. |
| [Planet Tropical Forest Observatory](https://www.planet.com/nicfi/) and [Planet GEE access documentation](https://docs.planet.com/platform/integrations/google-earth-engine/nicfi-gee/) | Dated higher-resolution archive could support independent manual interpretation | Account/license restrictions; present service is not assumed free; no access purchased or imagery redistributed | Potential review source only. Confirm actual archive dates, permitted use and access before interpreting samples. |
| [Dynamic World, original project](https://www.dynamicworld.app/about/index.html) | Sentinel-2-derived land-cover context | CC-BY-4.0 | Not independent mining truth and not automatic non-mining labels. |

## Actual acquired files

Under `data/reference_discovery_20261108/raw/`:

- `global_mining_polygons_v2.gpkg`: 24,657,920 bytes,
  SHA-256 `6936e2743a21ba952b4de3e4b6f77099a0aa4479f7e2639d9d1b0787876a3ea1`.
- `validation_points_v2.gpkg`: 229,376 bytes,
  SHA-256 `569a933dc2d267bc824c5dff9f507f0d9e5a09bb859e7f7c341cb2b192b93031`.

Citation: Maus et al. (2022), Global-scale mining polygons (Version 2), PANGAEA,
DOI 10.1594/PANGAEA.942325. Preserve CC-BY-SA-4.0 attribution and share-alike terms.
Raw files are source evidence, not the project's supervised dataset.

`discovery.json` records download URLs, hashes and local candidate counts. The
two `*_local_candidates.geojson` files are empty. Selection used intersection
with the existing 100 m simplified district planning outline; this is a discovery
filter, not an exhaustive mining census. No full official EIA PDF, commercial
imagery or contemporary independently labeled mining dataset was obtained.

Confirmed target-aligned mining-disturbance samples: **0**. Independently
confirmed non-mining/stable samples: **0**. New disturbances verified: **0**.
Historical unchanged mining areas verified: **0**. Named candidate sites in
the table remain unclassified and must not enter training or evaluation.

Use REAL_REFERENCE_PROTOCOL.md to collect and review suitable evidence before
running supervised training. No source's published validation scores are this
project's model scores.
