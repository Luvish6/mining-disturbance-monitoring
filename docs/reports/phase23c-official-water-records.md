# Phase 23C — Official river water-quality records discovery

This discovery starts from `0740c20`. It made zero Earth Engine requests and **no dataset downloads**: public portal pages and documents were only *viewed*. It follows [Phase 23A](phase23a-river-linkage-feasibility.md), where drainage routing put most Lumshnong-area clusters into the Lukha **between Khaddum and Sunapur**. No Phase 23B report exists.

All values below are quoted from official publications as ranges. They are not re-measured or modelled. Nothing here establishes mining causality or measured degradation.

## Source inventory

| # | Source and agency | Stations found | Dates and frequency | Parameters | Form and access | Status |
|---|---|---|---|---|---|---|
| 1 | **MSPCB "Monthly Water Quality Index of Identified Polluted River Stretches"** ([megspcb.gov.in/wqi](https://megspcb.gov.in/wqi)), Meghalaya State Pollution Control Board | **3375 Lunar river (tributary of Lukha) at Myndihati**; **1428 Kyrhuhkhla**; **1631 Myntdu at Jowai**; plus Shillong-area stations | Monthly, 2020–2026. **All 10 study months** (Nov–Mar 2023–24 and 2024–25) are present for 3375 and 1428. 1631 is missing Feb 2025. | pH, DO, BOD, faecal coliform, total coliform, faecal streptococci, and a status flag. **No turbidity, TSS, conductivity, iron or sulphate.** | HTML table, one month per query, a few KB each. Open, no login. It is a dynamic portal, so a scripted fetch returns only a stub; it was read in a browser. | **Verified viewable** |
| 2 | CPCB NWMP annual river tables 2023 ([main rivers](https://cpcb.nic.in/wqm/2023/WQuality_River-Data-2023.pdf), [medium/minor rivers](https://cpcb.nic.in/wqm/2023/Water_Quality_data_of_Med_Min_River_2023.pdf)); 2024 editions unconfirmed | Expected to include Khaddum 4315, Sunapur 3376, Mihmyntdu 4316 and Leshka 3379 (the station codes come from the CPCB register used in Phase 4A) | Annual min/max/mean summaries, not raw dated observations | Usually temperature, DO, pH, conductivity, BOD, nitrate, coliforms | PDF, likely several MB each | **Inaccessible**: `cpcb.nic.in` refused connections (ECONNREFUSED) on 2026-11-21. Contents unverified. |
| 3 | CPCB station register ([WQMN_list.pdf](https://cpcb.nic.in/wqm/WQMN_list.pdf)) | Coordinates for 4315, 3376, 4316 and 3379 (used in Phase 4A). **Needed for 3375 Myndihati and 1428.** | Register | Location only | PDF | Not reachable on 2026-11-21. **Myndihati and Kyrhuhkhla coordinates are unverified**, so they are not placed on the drainage network. |
| 4 | NGT OA 1271/2024 (Khroo L Pariat vs State of Meghalaya): CPCB-led joint-committee report (10 Feb 2025) and MSPCB affidavit (2026) | **Myntdu** near Jowai, about 100 m below the Mynkrem–Myntdu confluence at Urkhla. **No Lukha station.** | One MSPCB test report (9 Jan 2025) and preliminary turbidity observations | pH, coliforms and similar; turbidity described as elevated (qualitative) | Text PDFs, 16 and 46 pages | Read for discovery only. **Records a non-mining confounder**: Jowai-bypass road-construction debris entering the upper Myntdu, 2023–2026. |
| 5 | MSPCB Lukha action plan 2020 ([PDF](https://megspcb.gov.in/documents/Revised_and_Action_Plan_of_Lukha_River2020.pdf)) | Historical Lukha/Lunar context | Before the study period | — | PDF | A scripted fetch returned the portal stub. Not re-read here; earlier phases cited it for the Lumshnong → Lunar → Lukha drainage narrative. |

## What the verified source shows (MSPCB monthly portal, study seasons)

| Station | Season 2023–24 (Nov–Mar), pH range | Season 2024–25 (Nov–Mar), pH range | DO (mg/L) | BOD (mg/L) | Coliforms |
|---|---|---|---|---|---|
| 3375 Lunar at Myndihati (Lukha tributary) | **2.5 – 2.9** (5 / 5 months) | **2.8 – 3.1** (5 / 5) | 6.4 – 7.8 | 1.7 – 2.5 | Not detected |
| 1428 Kyrhuhkhla | 2.8 – 3.7 (5 / 5) | 3.0 – 3.4 (5 / 5) | 6.6 – 7.4 | 1.9 – 2.4 | Not detected |
| 1631 Myntdu at Jowai | 6.7 – 7.0 (5 / 5) | 6.9 – 7.0 (4 / 5) | 6.5 – 7.4 | 1.6 – 2.6 | FC 240–630 before, 410–840 after |

**How to read the Lunar series.** It shows **persistently extreme acidity, pH below 3.2, in every study month of both seasons**. That is consistent with long-documented acid drainage in the Lunar (MSPCB, 2008 onwards), but the data cannot attribute it to a source.
- There is **no change between seasons** to interpret.
- The record contains **no upstream control** and no turbidity or metal measurements.
- No coordinates are verified, so the station cannot yet be placed relative to the Phase 23A routed clusters.

**Myntdu at Jowai** has near-neutral pH, but coliforms rise across the seasons, which points to domestic sources. The Jowai road-construction case is a separate confounder.

## Khaddum (upstream) vs Sunapur (downstream): can they be paired?

**Not with any source verified today.**
- The MSPCB monthly portal does not list 4315 or 3376.
- The CPCB annual tables that should cover them were unreachable. Even if available, they are annual summaries, not dated observations, and they usually lack turbidity, TSS and metals.

So no official dated measurements exist for a paired upstream/downstream comparison in the study windows.

**Interpretation records also missing:**
- **Discharge:** no CWC or other gauge on the Lukha was found.
- **Dam releases:** only the MeECL release *guidelines* for Myntdu–Leshka are known, not release logs.
- **Rainfall:** only the coarse cached CHIRPS series. IMD district rainfall was not located.

## Decision

| Analysis | Decision |
|---|---|
| Paired Khaddum–Sunapur measured comparison | **NO-GO** until CPCB/MSPCB station records are obtained |
| Descriptive tabulation of the MSPCB monthly portal (3375, 1428, 1631; 10 study months) | **GO, if you approve.** About 10 page queries, roughly 50 KB in total, stored locally as a CSV with URL and access timestamp. The report would describe the measurements only, with no causal claim and no seasonal "effect" (the Lunar shows none). |
| Linking 3375 Lunar/Myndihati to routed disturbance clusters | **Blocked** until the station coordinates are verified from the CPCB register or an MSPCB confirmation |

## Proposed next steps and estimated size

1. **Retry CPCB** (`cpcb.nic.in`) from the browser or a different network. Download, with your approval:
   - `WQMN_list.pdf` (station coordinates);
   - the 2023 and 2024 NWMP river tables (main plus medium/minor).

   The total is probably under 30 MB. Confirm the exact sizes before downloading.
2. **Formal request to MSPCB.** The address is in the portal footer. Ask for the monthly raw NWMP records for 4315 Khaddum, 3376 Sunapur, 3375 Lunar/Myndihati, 4316 and 3379 for Nov 2023 to Mar 2025. Include turbidity, TSS, conductivity, sulphate and iron where measured, with sampling dates and coordinates. This can be added to the existing DMR/MBDA letter in `docs/outreach/`.
3. **Then preregister** a descriptive upstream/downstream table. Khaddum vs Sunapur would be ordered by the Phase 23A routing, with the Lunar as the tributary input. It would be reported with no causal inference: one bracket, short records, no discharge data, and karst and dam confounders.

## Addendum — CPCB retry (2026-11-21)

`cpcb.nic.in` was still unreachable. Both the built-in browser and a direct HTTPS client timed out connecting on port 443. Nothing was downloaded.

**Internet Archive copies of the official files.** Metadata only was checked: the Wayback availability and CDX APIs, plus `HEAD` requests.

| File | Archived snapshot | Size reported by the archive | Note |
|---|---|---|---|
| `WQMN_list.pdf` (station register with coordinates) | 2024-03-05; same digest as the 2021-03-02 snapshot. A different 2021-12-27 version also exists. | 1,048,576 bytes served; original crawler length 1,828,746 | The exact 1 MiB size suggests a **possible truncation**. Integrity is unverified. |
| `2023/WQuality_River-Data-2023.pdf` (NWMP 2023 river table) | 2025-05-12 and 2025-04-26 (different digests) | 5,242,880 bytes served; original crawler length 5,586,691 | The exact 5 MiB size suggests a **possible truncation**. Integrity is unverified. |
| `2023/Water_Quality_data_of_Med_Min_River_2023.pdf` | none | — | Not archived |
| 2024 river tables (both) | none | — | Not archived; existence unconfirmed |

**Proposed download (needs approval).** Fetch the two archived PDFs, about 6.3–7.4 MB in total, into an untracked local folder. Then check integrity: `pdfinfo` page count, a full-text extraction test, and every page readable. Use them **only if complete**. Report the rows for stations 3375, 3376, 4315, 4316, 3379 and 1428, along with their coordinates. A truncated file would be recorded as such and not used.
