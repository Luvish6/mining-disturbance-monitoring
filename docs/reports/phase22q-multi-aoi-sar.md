# Phase 22Q — Multi-AOI replication of the optical rule with Sentinel-1 corroboration

The preregistration was committed as `e362a54` before any Sentinel-2 request: see [phase22q-preregistration.json](phase22q-preregistration.json). Results are in [phase22q-summary.json](phase22q-summary.json). Code is in `scripts/phase22q_multi_aoi.py` and tests are in `tests/test_phase22q_multi_aoi.py`. This phase extends [Phase 22P](phase22p-sar-corroboration.md).

**All candidates remain UNKNOWN — not validated.**

## AOI selection (fixed before measurement)

The AOIs are every tile in the Phase 6B roster except the following:
- **TEST tiles** `east-91-561` and `west-81-557`. They were excluded without being opened.
- **`east-94-559`.** It shares 1,938 cells with the Phase 22L AOI, so it is not independent.

The Phase 6B tiles were originally chosen for coverage, before any disturbance detection existed. No AOI was moved or added.

| AOI | Split | Block | Full-rectangle guard | Distance to nearest TEST buffer |
|---|---|---|---|---|
| east-90-562 | VAL | 90:562 | District-contained; no TEST intersection | 2,015 m |
| west-82-563 | TRAIN | 82:563 | District-contained; no TEST intersection | 6,420 m |
| west-85-563 | VAL | 85:563 | District-contained; no TEST intersection | 1,430 m |

The VAL tiles are used for evaluation only. No rule, threshold or parameter was fitted or tuned on them.

## Method

**Optical.** The Phase 22L `seasonal_graph` and `select_candidates` were reused unchanged on the exact Phase 6B 64 × 64 grid (30 m, EPSG:32646):
- Candidate rule: NDVI decrease ≤ −0.30 and BSI increase > +0.10.
- Each season needs at least 2 observations.
- Masks: NDWI < 0, brightness ≥ 0.04, SCL 4/5 and cloud probability < 40.

**SAR.** dVV and dVH come from the cached Phase 6B features. These use relative orbit 77 and the same graph that Phase 22P reproduced to within 1.8×10⁻⁶ dB. File hashes were frozen in the preregistration.

**Statistics.** These are the Phase 22P statistics:
- Each AOI gets its own test only when it has at least 3 candidate cells.
- The pooled test is a stratified permutation: the mean of candidate dVH minus each AOI's own background median.

## Results

| AOI | S2 scenes (capture days), before / after | Eligible cells | Candidate cells (clusters, ha) | dVH, candidate vs background median (dB) | dVH p | dVV difference (dB), p | Outside background 5–95% |
|---|---|---|---|---|---|---|---|
| east-90-562 | 52 (51) / 58 (56) | 4,091 | 5 (5, 0.45) | −2.93 vs −0.96 (Δ −1.97) | 0.003 | −0.40, 0.50 | 2 / 5 |
| west-82-563 | 24 (24) / 29 (28) | 4,096 | 1 (1, 0.09) | — | — | — | TOO_FEW_CANDIDATES |
| west-85-563 | 52 (51) / 58 (56) | 4,089 | 6 (6, 0.54) | −2.20 vs −0.71 (Δ −1.49) | 0.012 | −0.28, 0.62 | 2 / 6 |
| *Phase 22L AOI (22P)* | 13 / 11 S1 scenes | 4,096 | 9 (6, 0.81) | −2.75 vs −1.06 (Δ −1.68) | 0.004 | −0.62, 0.17 | 4 / 9 |

**Pooled results:**
- **Primary (new AOIs only):** 12 candidate cells. Mean dVH relative to background is **−1.77 dB**, with a stratified permutation p of 1.0×10⁻⁴. That is the smallest p-value 10,000 draws can resolve.
- **Secondary (adding the Phase 22L AOI):** 21 cells, −1.48 dB, p = 1.0×10⁻⁴.

## Interpretation

The 22P finding replicates. In every AOI with enough candidates to test (two new AOIs plus the 22L AOI), the optical NDVI-drop/BSI-rise candidates show an unusually strong **Sentinel-1 VH decrease**. VV does not separate from background in any AOI.

These are independent-sensor measurements. The agreement is consistent with real loss of vegetation volume, not optical artefacts. The rule is sparse: 0.09–0.81 ha per 369 ha AOI.

**This does not identify mining.** Forestry, shifting cultivation, construction and landslides produce the same S1/S2 signature.

## Limits

- **Small and dependent sample.** n = 12 new cells. The cells within each AOI are spatially autocorrelated, so the p-values are descriptive only.
- **Shared acquisitions.** east-90-562 and west-85-563 lie on the same Sentinel-2 tile (T46RDP) and use identical acquisitions. Their atmospheric and seasonal sampling is shared, not independent.
- **Partly circular VH signal.** VH and NDVI both respond to vegetation, so their agreement is expected for any vegetation-clearing process.
- **No reference.** There are still no reference labels and no eligible control AOI. Accuracy, precision and mining attribution remain unmeasured.

## Cloud usage and reproduction

This phase used 9 Earth Engine requests and 623,267 response bytes, against caps of 20 requests and 5 MB. No Sentinel-1 requests were made, because the cached 6B features were reused.

```powershell
python -B -m scripts.phase22q_multi_aoi --preregister   # offline; rewrites the preregistration
python -B -m scripts.phase22q_multi_aoi --acquire       # GEE; refuses if outputs/phase22q_multi_aoi exists
python -B -m scripts.phase22q_multi_aoi --analyze       # offline; needs the 6B tiles and the 22P cache
python -B -m pytest -q -p no:cacheprovider tests/test_phase22q_multi_aoi.py
```

The local caches (`outputs/phase22q_multi_aoi`) stay unpublished.
