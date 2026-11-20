# Phase 22S — Official Indian mining-reference data audit (East/West Jaintia Hills)

**Starting point.** This audit started from commit `1c19b1f`. It reuses the earlier findings in [Phase 3B](phase3b-candidate-verification.md), [Phase 3D](phase3d-reference-evidence.md), [Phase 14A](phase14a-indian-reference-acquisition.md), [Phase 22A](phase22a-indian-label-feasibility.md) and [Phase 7 Day 3](phase7-day3-reference-decision.md).

**Constraints.** No Earth Engine requests were made. No coordinates were invented, no unreferenced pit grid was georeferenced, no thresholds were changed and no TEST data was accessed. Manual labelling remains a last resort.

**Key distinction.** A *lease, application or boundary-pillar perimeter* is an administrative boundary. It does **not** show where excavation occurred, or when. Only a dated survey of the actual worked area (a pit or dump footprint) can serve as an activity reference. Neither type establishes legality or illegality from imagery.

## Source-by-source findings

| # | Source | Access verified (20 Nov 2026) | Format / CRS | Coverage / dates | Class meaning | Reuse | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | **PARIVESH / environmentclearance.nic.in** proponent KMLs (Form 1/2, ToR) | Per-project direct links. The KORPET KML was archived earlier (sha256 `c0b032cf…`). The Mynkree linked KML returned an HTML page, not KML. | KML, WGS84 lon/lat (OGC KML) | Individual proposed projects. KORPET and Sumon Pohduna lie in **TEST block 81:557**. Dates are administrative (e.g. ToR 2021-03-13); survey dates are unknown. | Application or lease perimeter (**administrative**) | Public record; no explicit licence; proponent survey accuracy unknown | Accessible but **administrative only**. The two known perimeters are frozen TEST geography and are unusable for development. |
| 2 | PARIVESH EAC/SEAC minutes with geotagged site photos (e.g. 33rd EAC, Lumshnong 44.58 ha) | Public PDFs | Photo overlays with camera coordinates; accuracy unknown | 27 June 2024: between the two seasonal windows | Field photographs at boundary pillars, not footprints | Public record | Context only; not a footprint or a dated change |
| 3 | **IBM inspection reports** (Lumshnong 38MEG03016, Brishyrnot 38MEG657001, Mynkree) | Public PDFs | Pit and proposal grids in **unstated CRS/datum** | Inspections Nov 2023, Sep 2024, Dec 2024 and Jan 2025 | Inspector-described actual working pits | Citation only; publication rights unestablished | **Blocked**: the grids cannot be placed without guessing a datum or zone, which is forbidden |
| 4 | **IBM Mineral Map Cell / Mining Tenement System** (mts.ibm.gov.in) | The portal exists, but layers sit behind single sign-on login. The Brishyrnot "Boundary Pillars.xlsx" lead (miningplan.ibm.gov.in) now returns a **"Session expired" login page**, not data. | The Mineral Map Cell states that lease boundaries are geo-referenced from mining plans, schemes, studies and inspections. The DGPS boundary-pillar survey is guideline methodology. | National lease tenements | Lease boundaries (**administrative**) | Not public | **Inaccessible**: needs a formal request to IBM |
| 5 | **ISRO Bhuvan / NRSC** LULC 1:50k (includes a mining class) and **Wastelands Atlas 2019** ("mining wastelands"; change 2008-09 → 2015-16) | Display WMS. Per-state atlas PDFs are public on dolr.gov.in. Vector export and research or redistribution rights are **unverified** (Phase 22A). | WMS / PDF; vector CRS unverified | Static; latest cycles predate the 2023–25 windows | Broad land-cover or wasteland class, not dated excavation | Bhuvan terms limited | **Conditional**: static context only, not change labels |
| 6 | **GSI Bhukosh** | Portal downloads after accepting terms, delivered by email (one user reports empty carts) | Shapefiles for geology and mineral occurrences | Geological mapping | Mineral *occurrence*, not mining activity or leases | GSI copyright (Data Dissemination Policy 2019) | **Not suitable** as a mining-footprint reference |
| 7 | **Meghalaya Directorate of Mineral Resources (DMR) / Mining & Geology Dept.** | Only an online lease and permit *application* portal was found (NIC workflow); no public GIS | — | — | — | — | **No public geodata found** |
| 8 | **DC East Jaintia Hills public notice No. EJHD/NGT-6/Pt-I/2026/1 (14 Feb 2026)** | The public notice PDF was read | Notice only | The Meghalaya Basin Development Authority (MBDA) is assisting DMR and Police with a **drone survey to identify rat-hole coal mining** across East Jaintia Hills, after a blasting incident at Mynsngat Thangsko | Official dated survey of actual mining | Survey outputs not public | **Best request target**: dated, official, district-wide. It post-dates both windows, so it would give a static 2026 inventory, not change labels. |
| 9 | **Justice Katakey committee (Meghalaya High Court) aerial survey**, Garuda UAV, report submitted 19 Mar 2025 | Known only through news (EastMojo, 25 Mar 2025); the report itself was not found publicly | The survey used coal-dump coordinates from the State's **2019 Supreme Court affidavit**, within a 1 km radius of each dump | East Jaintia Hills plus three other districts | Coal dumps and illegal coal | Court record | **Request target**. The underlying coordinates are in a court affidavit. |
| 10 | **NESAC (ISRO) coal-mine mapping for the NGT committee** (about 24,000 mines reported, undivided Jaintia Hills, around 2018–19) | News reports only; final GIS not found. The [CPCB NGT report of 15 Jan 2019](https://www.cpcb.nic.in/NGT/Report-NGT-15.01.2019.pdf) is a public lead that was **not inspected** here. | Unknown | Satellite-mapped mines, roads and drainage | Mine locations (activity status unclear) | Unknown | **Request target**: ask NESAC or the NGT committee for the GIS |
| 11 | NGT IA No. 04/2024 in OA 154/2023/EZ (pp. 3083–3156) | Public PDF; index and first pages read | Legal filing (Shyam Century Ferrous impleadment) | Annexures are court orders and corporate papers | — | — | **No geospatial content** |

## Conclusion

**No openly licensed, downloadable, georeferenced mining-activity footprint dated within the 2023–24 / 2024–25 windows exists for East or West Jaintia Hills among the official sources checked.**

What is accessible falls into three groups:
- administrative project perimeters (PARIVESH KMLs, which are TEST geography where known);
- static land-cover context (Bhuvan, the wasteland atlas);
- documents whose grids lack a stated CRS (IBM).

The dated activity surveys that do exist are held by government bodies and are not published:
- the 2026 MBDA/DMR drone survey;
- the 2025 Katakey-committee UAV survey;
- the NESAC coal-mine inventory;
- IBM's geo-referenced tenements.

## Best next actionable dataset

The best next step is a formal written request, signed by the supervisor or the university, for the **East Jaintia Hills 2026 rat-hole-mining drone survey outputs**. The request should go to the Director of Mineral Resources, Meghalaya, with the Meghalaya Basin Development Authority and the Deputy Commissioner, East Jaintia Hills, in copy. It should ask for:
- mine and pit locations or footprints as KML or shapefile, with CRS/datum and positional accuracy;
- capture dates;
- the class definitions (active / abandoned / dump);
- permission for research use.

At the same time, request the 2019 affidavit coal-dump coordinates and the 2025 Katakey UAV report via the committee or an RTI application. Also request the NESAC coal-mine GIS.

**How these could be used, if obtained:**
- They would allow a *static known-mine proximity/agreement test* of the existing candidates. For example: are candidates closer to inventoried mines than random cells?
- Activity-dated subsets that fall inside the two seasonal windows could become independent reference labels.
- Every use must keep the frozen TEST exclusions.

Searches used: [IBM Mineral Map Cell](https://ibm.gov.in/IBMPortal/pages/MINERAL_MAP_CELL_), [Mining Tenement System](https://mts.ibm.gov.in/SSO/), [Wasteland Atlas 2019](https://dolr.gov.in/wasteland-atlas-of-india-2019/), [GSI dissemination policy](https://geodataindia.gov.in/assets/Document_Pdf/4.%20Data%20Dissemination%20policy%202019.pdf), [DC East Jaintia Hills notice](https://www.meghalaya.gov.in/sites/default/files/announcement/EJDH_NGT_6_Pt_I_2026_1.pdf), [EastMojo, 25 Mar 2025](https://eastmojo.com/meghalaya/2025/03/25/illegal-coal-mining-in-meghalaya-aerial-survey-reveals-large-reserves/), [Assam Tribune on the NESAC count](https://assamtribune.com/over-24000-coal-mines-in-jaintia-hills), [NGT IA 04/2024](https://www.greentribunal.gov.in/sites/default/files/news_updates/IA%20No.%2004-2024-EZ%20in%20OA%20154-2023-EZ%2C%20page%203083-3156.pdf), [Meghalaya DMR portal (NeGD)](https://negd.gov.in/isl/Directory/statedata/912).
