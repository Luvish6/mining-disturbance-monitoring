# Phase 22P — Sentinel-1 corroboration of Phase 22L optical disturbance candidates

**Question.** Do the nine Phase 22L/22N optical candidate cells show unusual seasonal Sentinel-1 backscatter change relative to the same AOI? The candidate rule (NDVI decrease ≤ −0.30 and BSI increase > +0.10) is unchanged.

**Preregistration.** It was committed as `d7f242b` before the Sentinel-1 request ([phase22p-preregistration.json](phase22p-preregistration.json)). Results are in [phase22p-summary.json](phase22p-summary.json). Script: `scripts/phase22p_sar_corroboration.py`. Tests: `tests/test_phase22p_sar.py`.

**Status of the candidates.** They remain **UNKNOWN — not validated**. SAR agreement is independent-sensor corroboration of a land-cover change. It is not a mining label.

## Method

- **AOI.** east-94-559-c74 is a TRAIN development AOI. The Phase 22N full-footprint guard passed: it is 1,210 m from the nearest expanded TEST block. The grid is 64 × 64 cells at 30 m in EPSG:32646 and is identical to Phase 22L.
- **SAR processing.** The existing Phase 2 `sar.seasonal` graph is used with the Phase 6B configuration:
  - S1 GRD IW, DESCENDING pass, relative orbit 77;
  - linear-power 20 m circular focal mean;
  - seasonal median in dB, with at least 2 observations per season.
  - The orbit supplied 13 before and 11 after scenes.
- **Change features.** dVV and dVH are after − before, in dB.
- **Reproduction gate.** 1,938 AOI cells are shared with the cached Phase 6B tile east-94-559. On those cells, the maximum |difference| is 1.2×10⁻⁶ dB (dVV) and 1.8×10⁻⁶ dB (dVH), against a gate of 0.01 dB. The new fetch therefore reproduces the frozen Phase 6B features.
- **Background.** The background is every eligible SAR-valid AOI cell except the candidates: 4,087 cells. All 9 candidates have valid SAR.
- **Tests.** Both tests are two-sided permutation tests with 10,000 draws:
  - cell level: median of the candidates minus median of the background;
  - cluster level: the six 8-connected cluster means against random six-cell draws.

## Results

| Polarisation | Candidate median (dB) | Background median (dB) | Background 5–95% (dB) | Difference (dB) | Cell-level p | Candidate percentile ranks |
|---|---|---|---|---|---|---|
| dVV | −1.49 | −0.87 | −2.95 … 0.85 | −0.62 | 0.173 | 17, 92, 3, 98, 20, 99, 97, 7, 30 |
| dVH | −2.75 | −1.06 | −3.83 … 0.89 | **−1.68** | **0.004** | 9, 71, 14, 90, 8, 46, 9, 15, 10 |

- **dVH, cell and cluster level.** Six of the nine candidates lie at or below the 16th percentile of background dVH. Five of the six cluster means are below −2.1 dB. C002 is the exception, at +0.46 dB. The cluster-level dVH permutation p is 0.031.
- **Outside the background 5–95% range.** In either polarisation, 4 of 9 candidates fall outside it. A random background cell does so with probability at most 0.20 (union bound), so no more than 1.8 cells would be expected by chance.
- **dVV.** It is mixed. Some cells show strong decreases and others strong increases (C004 is +1.45 dB), and the median difference is not distinguishable from background.

## Interpretation and limits

The Sentinel-1 result agrees with the optical evidence. The optical candidates, selected by an NDVI drop, also show a cross-polarised VH decrease that is unusual for this AOI. That pattern is physically consistent with loss of vegetation volume scattering. **This is the first measured S1–S2 agreement on the project's real temporal candidates.** It supports the claim that these cells mark a real surface change, not optical artefacts such as haze, shadow or registration.

The result does not identify the cause of the change. Forestry, agriculture or shifting cultivation, construction and erosion all reduce VH as well. Other limits:
- n = 9 cells in 6 clusters, inside one AOI.
- The cells are spatially autocorrelated, and the 20 m smoothing straddles 30 m cells, so the p-values are descriptive only.
- There is no control AOI and no independent reference.
- Mixed dVV can come from roughness and moisture changes, or from geometric terrain effects on slopes of 7–21°.

There was no threshold tuning, no new detections and no access to TEST data.

## Cloud usage and reproduction

There were 3 Earth Engine requests and 68,234 response bytes, against caps of 8 and 2 MB.

```powershell
python -B -m scripts.phase22p_sar_corroboration --acquire   # requires GEE; refuses if outputs/phase22p_sar exists
python -B -m scripts.phase22p_sar_corroboration --analyze   # offline
python -B -m pytest -q -p no:cacheprovider tests/test_phase22p_sar.py
```

The SAR cache (`outputs/phase22p_sar`) stays local.
