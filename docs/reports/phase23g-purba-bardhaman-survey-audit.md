# Phase 23G — Archived Purba Bardhaman District Survey Report: download, verification and extraction

This phase starts from `6da8d78`. The pre-download audit was committed as `6b42408`. Download approval was given at **140 MB**, for a single transfer with no retries. Zero Earth Engine requests, no imagery, no TEST access, and the NDTI pilot was not started.

**Decision: CONDITIONAL. NO-GO for an NDTI pilot now.**
- **Verified:** official block coordinates and 2018 lease authorisations.
- **Missing:** evidence that excavation took place in 2023–25, the datum, and a block-free upstream control.

## Source provenance and integrity

| Check | Result |
|---|---|
| File | *Purba Bardhaman Modified District Survey Report, Final, Mar 2024*. Directorate of Mines & Minerals, Government of West Bengal. |
| Source | Internet Archive capture `20250327200354id_` of `wbindustries.gov.in/files/Mines/DSR/Purba_Bardhaman_Modified_DSR_Final_Mar24.pdf`. The origin's last-modified date is 2024-05-14 11:07:42 GMT. |
| Bytes downloaded | **135,873,192**, equal to the origin and archive `Content-Length` (cap 146,800,640). Exactly one transfer. |
| SHA-256 | `9d09d3001ff0483e04919e74cbd7458a4c5e453bf5449ccde4eb9cbafeec16b8` |
| Structure | `%PDF-1.7` header; `startxref` plus a final `%%EOF`; not encrypted |
| Pages | **328**, all opened by poppler. 315 pages have extractable text, and one benign font warning was logged. |
| Document metadata | Adobe Acrobat Pro; created 2024-03-15, modified 2024-03-19 (IST) |
| Verdict | **COMPLETE and readable** |

The raw PDF, the extracted text, the local provenance file and the parsed vertices are kept only in the git-ignored folder `outputs/phase23g_dsr/`. Nothing raw is committed.

## Extracted evidence

**1. Annexure 3, "Boundary Coordinates of Potential Blocks"** (PDF pp. 176–214, printed A3-1 to A3-37).
- Codes follow `PBBD_<block>_<river>_<n>`, with `DA` = Damodar. Each block is a polygon of numbered vertices given as DMS latitude/longitude, e.g. `23° 14' 36.462" N  87° 44' 51.131" E`.
- **28 Damodar potential blocks** were parsed, with 559 vertices. Every block had parseable vertex pairs. Layout-mode extraction misaligns the columns; raw-order extraction is clean and was used.
- The blocks lie along the river from **87.54°E (Galsi-I, PBBD_GL1_DA_01) to 88.01°E (Jamalpur/Memari)**, at about 23.24°N in the west and down to about 22.96°N (Raina-II) in the south-east.
- The only stretch on the district's Damodar bank without a listed block is about **7 km** (87.549–87.621°E), between GL1_DA_01 and GL2_DA_03_04_I. From there to 88.01°E the blocks are nearly continuous.
- **CRS/datum: NOT STATED.** The report says only that surveys used "GPS/DGPS/Total Station". WGS84 is plausible but **unverified**, so it is flagged and not assumed.
- **Status:** these are *potential* blocks, with no activity dates.

**2. Table 8.1, "Details of Sand mining leases of the districts"** (PDF pp. 96–107, printed pp. 77–). The columns are sand ghat ID, river, block, mouza, JL no., plot, at least 4 coordinates, mineable reserve and **LOI DATE**. The first page was checked visually.
- Rows are wrapped, so text extraction alone cannot assign coordinates to rows reliably. Rows must be read visually.
- Damodar rows on p. 96:

| Sand ghat ID | Mouza (Bardhaman-I block) | LOI date |
|---|---|---|
| 271/SB2021 | Bangpur | 2-12-2018 |
| 1372/SB2021 | Bangpur | 4-13-2018 |
| 288/SB2021 | Fakirpur | 10-1-2018 |
| 294/SB2021 | Idilpur | 3-26-2018 |
| 323/SB2021 | Idilpur | 3-26-2018 |

- The date format is M-D-Y, since 13 and 16 appear in the second position.
- **Mineable reserve: "Not Available"** for all five rows.
- Each row has four DMS corners, at about 23°12'–23°13' N and 87°48'–87°50' E. These lie inside the extent of potential block **PBBD_BD1_DA_12**.
- Lessee names are not reproduced here.
- **Status:** permitted leases with a **2018 LOI**. The lease term and any operation in 2023–25 are not documented in the report.

## Candidate site (evidence fixed before any NDTI)

**Damodar, Bardhaman-I (Bangpur, Fakirpur, Idilpur), within PBBD_BD1_DA_12.** This is the only Damodar location with both official coordinates and a dated authorisation in the pages read.

**Upstream control: not defensible.**
- Blocks are nearly continuous for about 25 km upstream (Galsi-II, Khandaghosh).
- The only block-free district reach (87.549–87.621°E) is about 20 km upstream, with several blocks in between, and itself lies downstream of GL1_DA_01.
- The opposite (Bankura) bank's blocks are unknown; that DSR is likely more than 300 MB.
- Durgapur-barrage releases regulate the flow.

## Remaining blockers

1. **Activity in the study period.** Lease validity and extraction in 2023–25 must be documented, for example through WBMDTCL lease or e-challan records, environmental clearance and compliance reports, or the author's field data.
2. **Datum.** The datum of the DSR coordinates needs confirmation; it is unstated.
3. **Upstream control.** A clean upstream control needs Bankura-bank block locations and barrage-release records. Otherwise only a within-river longitudinal gradient is possible, which is weaker and confounded.
4. **Dated turbidity/TSS.** The author request is drafted in `docs/outreach/patel-data-request.md` and not sent.

## Next decision

Either:
- **(a)** send the author email, whose study reaches may include mined and unmined Damodar stretches with field TSS; or
- **(b)** accept a preregistered **longitudinal-gradient exploratory** design, in which NDTI is described along the Bardhaman-I reach against the 7 km block-free reach. This would have no causal claim, no "control" label, and would use the Phase 23E budget (at most 24 requests, at most 6 MB).

**Recommendation:** pursue (a) first.
