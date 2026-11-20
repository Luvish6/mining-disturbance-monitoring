# Phase 23E — External mining–river turbidity case study (India): feasibility

This phase starts from `e99475e`. **Meghalaya remains the primary study area**; this is a separate external case. It made zero Earth Engine requests and no downloads. One publisher abstract page was viewed in the browser.

**Decision: CONDITIONAL. NO-GO for acquisition now.** A design is ready if the missing site evidence below is obtained.

## Stage 1 — verified source

The brief described this as a "2026 West Bengal study". Its details were checked against the publisher page:

| Field | Verified value |
|---|---|
| Citation | Gupta, S. & Patel, P. P., *Examining riverbed sand mining induced anthropogenic landforms and its impacts on suspended sediment concentration in select rivers of the Rarh region of West Bengal*, **Advances in Space Research**, issue date 1 Feb 2026, **DOI 10.1016/j.asr.2025.11.028** ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0273117725013122)) |
| Rivers | Three Rarh-region rivers in West Bengal. The abstract names the **Subarnarekha** and the **Damodar**. Search snippets add the **Ajay**, but this is not confirmed on the publisher page. |
| Mining evidence | Riverbed sand-mining landforms (sand pools, hollows, tracks, piles) mapped from multi-temporal Google Earth imagery. Example: a Subarnarekha stretch where sand-pool area grew from 7,650 m² in 2020 to 22,477 m² in 2022. This is **image-interpreted by the authors**, not an official activity record. |
| Field data | Depth-wise YSI ProDSS measurements. Reported TSS: 250–450 mg/L in sand pools; 50–130 mg/L in open-channel reaches; 150–350 mg/L reach-wise in peak-mining January, with the Damodar above 288 mg/L. |
| Satellite method | Multi-year, multi-season Sentinel-2A indices in Google Earth Engine, including turbidity indices |
| **Not verifiable (paywalled)** | Exact reach and sampling coordinates, sampling dates and sample counts, the NDTI/NSMI–TSS calibration statistics (an R² of 0.95 seen in a search snippet is **unverified**), the data-availability statement and any supplementary data |

The paper is relevant and credible. However, the evidence needed for a reproducible external test, namely **site coordinates, dated field measurements and accessible data, is not available to us**. The study does **not** supply usable ground truth as things stand.

## Alternatives (brief)

| Case | Strength | Weakness for this test |
|---|---|---|
| **Sukinda–Damsala Nala → Brahmani (Odisha)**, chromite | Long-documented chromite mining; Cr(VI) literature; the project already has a Brahmani NDTI workflow (Phase 12C/12D) | The Damsala Nala is narrow at 10 m. The Brahmani reaches are wide, but the pollutant of concern is chromium, which NDTI does not measure. Many other sediment sources exist (Talcher coal, Rengali dam). |
| **Mandovi–Zuari (Goa)**, iron ore | Dated activity change: Supreme Court mining halts in 2012 and 2018, within the Landsat/Sentinel era. Wide channels. | **Tidal estuaries**: tides, monsoon and dredging dominate turbidity. Most mining-period contrasts predate Sentinel-2 (from 2015) or need Landsat at 30 m. |
| **Damodar / Subarnarekha (West Bengal)**, sand | The mining is **in-channel**, giving the most direct physical link to suspended sediment. Wide sandy channels. Recent field-measured TSS exists (2023–24). | Coordinates, dates and data are paywalled or not shared. Mining locations are author-interpreted. Seasonal flow and braided channels need care. |

**Selected (conditionally): Damodar/Subarnarekha.** It was chosen for its documented in-channel mechanism, channel width and recent field TSS, not for any NDTI result, since none has been computed. It becomes a GO only if **one** of these is obtained:
- (a) the authors' reach and sampling coordinates and dated TSS (an email request to the corresponding author);
- (b) official **WBMDTCL / West Bengal sand-block** lease coordinates with auction or operation dates, used as independent mining-site locations.

## Stage 2 — proposed experiment (not run)

**Unit and design.** For each river: one **mined reach** and one **upstream control reach** of similar width and flow, at least 2 km above any documented sand block. Optionally one downstream reach. Reaches are fixed from coordinates (a)/(b) *before* any imagery is inspected.

**Windows.** Nov 2023 – May 2024, matching the field period, plus the same months of 2022–23 as a pre-period. Only **same-date, same-tile** upstream/mined pairs are used. This reuses the Brahmani within-date contrast logic.

**Water mask (the Phase 22O rule, unchanged):**
- JRC occurrence ≥ 50% **and** MNDWI > 0 **and** SCL = 6;
- cloud probability < 40, no shadow, edge masks;
- **eroded by 1 pixel**;
- at least **25 interior 10 m pixels** per reach-date, with at least 5 matched dates per season;
- otherwise INSUFFICIENT_DATA.

The SCL = 6 requirement is added because of the Khaddum lesson (Phase 22O).

**Metric.** Per reach-date, the median NDTI = (B4 − B3)/(B4 + B3). The primary statistic is the median over dates of (mined − upstream) same-date NDTI, with a date-bootstrap 95% CI.
- **Sensitivity checks:** NDWI > 0.1, 2-pixel erosion, and B4 reflectance.
- **Stratification:** CHIRPS 3- and 7-day antecedent rain at the reach cells. Discharge is unavailable unless CWC gauge data for the Damodar (DVC) are obtained. Dam releases from the Damodar Valley reservoirs are a major confounder.

**Validation.** Only if dated field TSS with coordinates is obtained: Spearman correlation between same-week TSS and NDTI, with n and dates reported. Otherwise, **no validation claim**.

**SAR.** Sentinel-1 VV/VH, seasonal median on the bar and floodplain strip (excluding water), to corroborate **bar-surface disturbance** (excavation, tracks, piling) in mined against control reaches, using the 22P statistics. SAR is **never** used as a water-quality measure.

**Success / failure (preregistered).**
- **Success:** both reaches pass the support gate on at least 5 matched dates. The result is then reported as measured, positive or not.
- **Failure:** insufficient support, mixed-pixel contamination (SCL ≠ 6 dominant), or missing independent site evidence. Reported, not re-tuned.

**Categories kept separate:**
1. documented mining (official or author-mapped);
2. satellite-observed bar disturbance (S1/S2);
3. relative river turbidity (NDTI);
4. measured water quality (field TSS);
5. causal attribution, which is **not claimed**: other sediment sources, monsoon recession and dam releases remain.

## Resource budget if GO

| Item | Requests | Data |
|---|---|---|
| S2 per reach-season (IDs + URL + download), about 4 reaches × 2 seasons | about 24 | about 6 MB |
| S1 bar strip, 4 reaches | about 12 | about 2 MB |
| JRC + CHIRPS (batched) | about 2 | below 1 MB |
| **Total cap** | **≤ 45** | **≤ 12 MB** |

It runs under the existing exclusive lock and ledger. Compute is CPU seconds. The author-data or WBMDTCL lookup is a manual step and needs your approval before any download.

## Next step

Email the corresponding author (Priyank Pravin Patel) asking for the reach and sampling coordinates and dated TSS for research reuse. Alternatively, approve a search of WBMDTCL sand-block lists for the Damodar/Subarnarekha study stretches, with sizes reported before any download.
