# Phase 23D — Archived CPCB data recovery and verification

This phase starts from `554ce4b`. It made zero Earth Engine requests. Exactly the **two approved downloads** were made, into the git-ignored `outputs/phase23d_cpcb_archive/` folder. That folder also holds the HTTP headers and `provenance.json`. No TEST access.

**Decision: NO-GO. Both archived copies are UNUSABLE.** No station data was extracted, repaired or inferred.

## Downloads and integrity

| File | Internet Archive capture | Bytes received | Original length (crawler header) | Missing | SHA-256 (received) |
|---|---|---|---|---|---|
| `WQMN_list.pdf` (CPCB station register; origin last-modified 2020-10-19) | `web.archive.org/web/20240305011943id_/https://cpcb.nic.in/wqm/WQMN_list.pdf` | 1,048,576 | 1,828,746 | 780,170 (42.7%) | `76be0982…17f2` |
| `WQuality_River-Data-2023.pdf` (NWMP 2023 river table; origin last-modified 2025-03-17) | `web.archive.org/web/20250512025648id_/https://cpcb.nic.in/wqm/2023/WQuality_River-Data-2023.pdf` | 5,242,880 | 5,586,691 | 343,811 (6.2%) | `6624df16…371d` |

**Total downloaded:** 6,291,456 bytes. The full SHA-256 hashes are recorded in `provenance.json`.

**Checks** (`file`, `pdfinfo`, `pdftotext` from poppler):
- **Received sizes.** Both are exactly 1 MiB and 5 MiB. Each equals the archive's stored `content-length`, but is shorter than the crawler-recorded original. **These are truncated captures**: the archive stored only the first part of each file.
- **Structure.** Neither file ends with `%%EOF`. Both lack the trailer dictionary and the cross-reference table. The river table's linearization header declares **82 pages**, but poppler cannot open the page tree. For the station register, the page tree resolves to *null*.
- **Text.** **Zero pages are readable and zero text was extracted** from either file. poppler's automatic xref reconstruction also failed.
- **Fidelity.** Neither file can be compared page by page with the original CPCB document, because the original is unreachable (`cpcb.nic.in` timed out on 2026-11-20 and 2026-11-21).

Both files are therefore **UNUSABLE**. Following the stop rule:
- no repair tools were applied;
- no salvaged partial content was read;
- no attempt was made to locate stations in the surviving bytes.

## Station data (verified content only)

| Station | Coordinates | Dates, pH, DO, BOD, turbidity, TSS | Status |
|---|---|---|---|
| Khaddum 4315 | — | — | Not recovered: source unusable |
| Sunapur 3376 | — | — | Not recovered |
| Lunar at Myndihati 3375 | — | — | Not recovered here. The MSPCB monthly portal series remains the only verified record ([Phase 23C](phase23c-official-water-records.md)). |
| Mihmyntdu 4316 | — | — | Not recovered |
| Leshka 3379 | — | — | Not recovered |
| Kyrhuhkhla 1428 | — | — | Not recovered here. The MSPCB monthly portal has it ([Phase 23C](phase23c-official-water-records.md)). |

Even a complete 2023 annual table would cover only **calendar 2023, as annual summaries**. It could not represent the Nov–Mar 2023–24 and 2024–25 study seasons.

## Upstream/downstream comparison

**Not supported.** No verified Khaddum or Sunapur measurement exists from any source checked in Phases 23C and 23D.

## Next decision (each needs approval or an outside action)

1. **The other station-register capture.** The Internet Archive holds a 2021-12-27 `WQMN_list.pdf` with a *different* digest, about 1.2 MB by CDX record length. It may be complete, but its integrity is unknown until downloaded. It would supply coordinates only, not measurements.
2. **Retry `cpcb.nic.in` later** from another network for the original PDFs, including the 2024 tables, which have never been archived.
3. **Formal data request to MSPCB.** Ask for the monthly raw NWMP records, with coordinates, for stations 4315, 3376, 3375, 4316 and 3379 from Nov 2023 to Mar 2025. This is the only route to dated observations within the study seasons. The request can be added to the drafted DMR/MBDA letter (`docs/outreach/`).
4. **Meanwhile**, the only verified river measurements remain the MSPCB portal series for the Lunar (3375), Kyrhuhkhla (1428) and Myntdu at Jowai (1631). They are descriptive only and include no Lukha main-stem station.
