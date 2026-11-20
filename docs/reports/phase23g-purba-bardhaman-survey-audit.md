# Phase 23G — Archived Purba Bardhaman District Survey Report: pre-download audit

This audit starts from `6da8d78`. It made zero Earth Engine requests and **0 bytes of PDF content were downloaded**. Only two `HEAD` requests to the Internet Archive were made. No imagery, no TEST access, and the NDTI pilot was not started.

**Decision: NO-GO under the approved 75 MB cap.** The report's true size is about 136 MB.

## Source identity and provenance

| Field | Value |
|---|---|
| Report | *Purba Bardhaman Modified District Survey Report, Final, Mar 2024*. Directorate of Mines & Minerals, Government of West Bengal (Phase 23F, source 1). |
| Original URL | `https://wbindustries.gov.in/files/Mines/DSR/Purba_Bardhaman_Modified_DSR_Final_Mar24.pdf`. The host is unreachable from this network (timeouts in Phases 23F and 23G). |
| Origin `Last-Modified` | Tue, 14 May 2024 11:07:42 GMT, identical in both captures |
| Archive captures | `web.archive.org/web/20240609025639id_/…` (captured 2024-06-09) and `web.archive.org/web/20250327200354id_/…` (captured 2025-03-27) |
| Served `Content-Length` | **135,873,192 bytes** in both captures |
| `x-archive-orig-content-length` | 135,873,192 in both, matching the served length |

**Completeness indicators.** Both captures serve exactly the origin's declared length, with the same last-modified date. Unlike the truncated CPCB captures in [Phase 23D](phase23d-archived-cpcb-verification.md), which stopped at exactly 1 or 5 MiB, this archive is **probably complete**. That is unverified until the file's trailer and page tree are checked.

**Correction to Phase 23F.** The "about 66.0 MB" listed there was the Internet Archive CDX *record length*, the compressed WARC size, not the file size. The other DSR sizes in 23F are likewise CDX record lengths, so their true file sizes are probably about 2× larger:

| DSR | 23F CDX record length | Likely true file size |
|---|---|---|
| Paschim Bardhaman | about 70.8 MB | likely more than 140 MB |
| Bankura | about 180.5 MB | likely more than 300 MB |
| Jhargram | about 53.6 MB | likely more than 100 MB |

## Why stopped

- The approved transfer cap is 75 MB, and the file is 135.9 MB.
- A partial or range download would yield a deliberately truncated PDF, which the stop rule forbids using.
- No integrity checks were possible, and **no coordinates were recovered**.
- No Damodar block was selected, so no upstream or downstream controls were defined.

## Remaining blockers

1. **The download exceeds the cap.** It needs explicit approval for one transfer of about 136 MB, capped at 140 MB, into the ignored cache. Integrity would then be validated (byte count, `%%EOF`, xref, `pdfinfo` page count, text extraction) before anything is extracted.
2. **Even with the file**, Annexure 3 lists *potential* sand blocks. Dated activity, from auctions, lease terms or ECs, must come from separate records.
3. **No accessible dated turbidity or TSS.** The author request is drafted in `docs/outreach/patel-data-request.md` and not sent.

## Options

- **(a)** Approve a single 136 MB download, capped at 140 MB, of the 2025-03-27 capture, with integrity checks before extraction.
- **(b)** Retry the official host later from another network. The file size is the same.
- **(c)** Wait for the author's coordinates and data, which would remove the need for the DSR to fix the paper's study reaches.
