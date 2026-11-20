# Phase 23F — Recovering verified sand-mining sites and river sampling locations (Damodar / Subarnarekha)

This phase starts from `9908e2c` and builds on [Phase 23E](phase23e-external-river-case-feasibility.md). It made zero Earth Engine requests and no imagery or document downloads. Only search results, HEAD requests and Internet Archive index metadata were used. Meghalaya remains the primary study area.

**Decision: NO-GO for the pilot now.** Every candidate source of verified coordinates either needs an approved large download or is unreachable.

## Source inventory

| # | Source (issuer) | What it should contain | Record type | Access status (2026-11-21) |
|---|---|---|---|---|
| 1 | **District Survey Reports (DSRs)**, Directorate of Mines & Minerals, West Bengal (`wbindustries.gov.in/files/Mines/DSR/`): Purba Bardhaman (modified, Mar 2024), Paschim Bardhaman (modified, Mar 2024), Bankura (modified), Jhargram (Nov 2022) | Annexure 3 "Coordinates of Potential Blocks (Sand)" (about 30 pp. for Purba Bardhaman; about 117 pp. for Bankura), plus maps of auctioned blocks on the potential blocks. Paschim Bardhaman adds a map of the Damodar dams. | **Potential and permitted sand blocks.** Some maps show auctioned blocks. These are **not** dated active-excavation records. | Official host **unreachable** (HTTPS timeout). **Internet Archive copies exist**: Purba Bardhaman about 66.0 MB (2024-06-09, 2025-03-27); Paschim Bardhaman about 70.8 MB (2024-03-26, 2025-03-27); Bankura about 180.5 MB (2024-03-04, 2025-03-27); Jhargram about 53.6 MB (2023-12-15). The listed size is the archive record length; completeness is unverified (see the Phase 23D truncation lesson). |
| 2 | WBMDTCL sand RFPs and e-auction notices (`wbindustries.gov.in`, `industry.wb.gov.in`, `jhargram.gov.in`, `eauction.gov.in`) | Per-block locations, sometimes as latitude and longitude. Bid and lease periods would give **activity-authorisation dates**. Jhargram notices cover auctions of stockpiled sand (Gopiballavpur I/II, Sankrail) and a Subarnarekha desilting tender at Sankrail. | Permitted lease or tender. Stockpile auctions are not excavation sites. | Not inspected: host unreachable or not opened. Coordinates not seen in snippets. |
| 3 | PARIVESH / SEIAA environmental clearances for sand blocks | KMLs of individual blocks with clearance dates | Permitted lease (administrative) | Not searched block by block in this phase |
| 4 | NGT records (e.g. an 11.10-acre block at Mouza Palshora, P.S. Sonamukhi, Bankura; illegal extraction on the southern Damodar bank) | Named blocks and alleged violations | Legal allegation, not a measured footprint | Found in search only. Coordinates not verified. |
| 5 | Gupta & Patel (2026), *Adv. Space Res.*, doi:10.1016/j.asr.2025.11.028; related EGU26-832 abstract | Author-mapped sand pools 2020–2022; YSI field TSS from monsoon 2023 to pre-monsoon 2024 | Author image interpretation plus field measurements | Paywalled. No public supplement or dataset was found. A public funding-agency record lists the PI's institutional email (not copied here). **Draft request: `docs/outreach/patel-data-request.md`** (untracked; not sent). |
| 6 | WBPCB / CPCB NWMP Damodar and Subarnarekha stations (dated TSS or turbidity) | Station water quality | Measured, usually monthly | Not verified. CPCB has been unreachable since Phase 23C, and WBPCB was not checked. |

## Assessment

- **Coordinates.** The DSR Annexure 3 tables are the best **official, georeferenced** source. They describe **potential or permitted** blocks, not dated excavation, and need to be crossed with auction or lease dates (source 2) to show authorised activity within a window.
- **Activity dates.** These are not yet available from any accessible official record. The paper's 2020–2022 mapping is dated but author-interpreted.
- **Upstream/downstream controls.** Controls can be defined *after* block coordinates are known: a reach of similar width at least 2 km upstream of the nearest listed block. The Damodar is regulated by DVC dams, which must be logged as a confounder.
- **Measured turbidity/TSS.** Only the paper's field data exists, and it is unavailable until the author replies.
- **No site is selected.** Selecting a reach now would mean picking a stretch without fixed independent evidence, which the protocol forbids.

## Proposed next steps (approval needed)

1. **Download one DSR from the Internet Archive.** The suggested file is the **Purba Bardhaman modified DSR (Mar 2024), about 66.0 MB**, covering the Damodar. Put it in an ignored cache, then verify integrity (page count, trailer, text extraction) before any use. If it is truncated, mark it UNUSABLE and stop. Alternatively, use Jhargram (about 53.6 MB) for the Subarnarekha.
2. **Send the author email** after you review it. Paper-based ground truth requires the author's coordinates, dates and TSS.
3. **If (1) yields usable block coordinates *and* a lease or auction date overlaps 2023–24:**
   - preregister one mined reach and one upstream control on the Damodar;
   - run the [Phase 23E](phase23e-external-river-case-feasibility.md) NDTI + Sentinel-1 bar design, unchanged;
   - **pilot budget: at most 24 Earth Engine requests and 6 MB** (2 reaches × 2 seasons × S2 3 requests, plus 2 reaches × S1 3 requests, plus 1 CHIRPS request), under the exclusive lock and ledger;
   - validation against TSS only if the author's data arrives.
