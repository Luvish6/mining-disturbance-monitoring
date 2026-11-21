# Phase 23K — First PlanetScope scene validation (20 Feb 2025)

This applies the [preregistration](phase23k-planet-preregistration.md) committed as `2dc5261` / `e031b86`. Derived statistics are in [phase23k-20250220_045741_92_2534-screen.json](phase23k-20250220_045741_92_2534-screen.json), produced by `scripts/phase23k_planet_screen.py` and tested in `tests/test_phase23k_planet_screen.py`.

**Handling.** The raw Planet files stay only in the git-ignored folder `outputs/phase23k_planet/20250220_045741_92_2534/`. The original ZIP is preserved unchanged outside the repository. There were no Earth Engine requests, no downloads and no TEST access.

**Decision: NO-GO for quantitative NDTI on this date.** No NDTI value was computed.

## Integrity and contents

- The ZIP is 6,976,662 bytes; SHA-256 `1398ad50…eaa8d`. The CRC test passes, and **all 7 files match their manifest MD5 and SHA-256**.
- **Scene `20250220_045741_92_2534`:** Super Dove (PSB.SD), acquired **2025-02-20 04:57:41 UTC**, inside the after season. Satellite 2534; view angle 5°; sun elevation 50.3°; ground control true; standard quality, finalized.
- **Scene-level quality:** cloud 0%, clear 63%, **light haze 37%**.
- **SR raster** `…_AnalyticMS_SR_8b_clip.tif`:
  - 8 bands, uint16, nodata 0;
  - EPSG:32646 at 3 m, 4,764 × 2,566 pixels, extent 434,868–442,566 E and 2,776,377–2,790,669 N;
  - band order coastal_blue, blue, green_i, **green (4)**, yellow, **red (6)**, rededge, **nir (8)**;
  - 6Sv2.1 atmospheric correction (SR v2.1).
- **Scaling.** Reflectance is ×10,000. The observed values are consistent: vegetation NIR has a median of about 0.19–0.22, and green and red are about 0.05.
- **UDM2** `…_udm2_clip.tif` is on the same grid. Its bands are clear, snow, shadow, haze_light, haze_heavy, cloud, confidence and udm1.
- **Deviation.** The delivered metadata **does not indicate harmonization to Sentinel-2**, although the preregistration specified it. This does not affect same-day, same-sensor comparisons, but future orders should match a single setting.

## Window coverage and quality

| Window (Phase 4A, 720 m) | Covered | Valid | UDM2 clear (no haze/shadow/cloud) | Light haze |
|---|---|---|---|---|
| Sunapur 3376 (downstream) | yes | 100% | **100%** | 0% |
| Khaddum 4315 (upstream) | yes | 100% | **0.5%** | **99.5%** |

**Khaddum is unusable on this date**: no corridor pixel is clear. The same-day pair therefore fails, whatever happens at Sunapur.

## Interior water at Sunapur (clear conditions)

- The reach corridor has 8,323 pixels at 3 m, all clear. 357 of them have JRC historical occurrence of at least 50%.
- **Water pixels** (NDWI > 0 and JRC ≥ 50%): **0**. Interior pixels: **0**. **Preregistered gate (≥ 25): FAIL.** All three sensitivities fail too (NDWI > 0.1; 1-pixel erosion; minimum 50).
- **Diagnostics** (read-only; they do not change any gate):
  - NDWI over the whole 720 m window never exceeds −0.023. On the historical-water pixels, NDWI is −0.34 to −0.15, with median green 0.045, red 0.041 and NIR 0.074.
  - The darkest channel-like feature (NIR < 0.07) is one 154-pixel component with an inscribed width of about **22 m**. Loosening the threshold to NIR < 0.09 gives about 34 m.

**Interpretation.** A narrow (about 20–35 m) channel corridor is visible, but at 3 m it shows **no open-water spectral signature**: NIR exceeds green everywhere. That is consistent with shallow February low flow mixed with bed, rock, sand or overhanging vegetation, or with very shallow water whose bottom dominates the reflectance. Water-leaving reflectance cannot be isolated, so **no NDTI can be computed defensibly**.

This is the same limitation found at 10 m (Phases 22O and 23H). Here it is confirmed in clear conditions at 3 m.

## Is ordering the 18 Mar 2024 scene justified?

**Not as the next step.**
- It falls in the same dry-season, low-flow regime (March is even lower, and is the burning-haze season).
- Its preview showed a haze plume.
- This clear February scene, at 3× finer resolution, found no open-water pixels at all.

If one more test is wanted, use quota on **one early-November date** (post-monsoon, higher flow) where both windows are clear, applying the same unchanged rules. If that also fails, close the river NDTI objective as **NO-GO at both 10 m and 3 m** for these Lukha stations, and report it as a resolution- and flow-limited negative result.

## Final test — 8 November 2024 (post-monsoon), same unchanged rules

**Scene and integrity.** Derived statistics are in [phase23k-20241108_044308_36_24f0-screen.json](phase23k-20241108_044308_36_24f0-screen.json).
- The ZIP is 7,189,529 bytes, SHA-256 `6fb2f0a1…19eb0`. The CRC test passes and all 7 manifest digests match.
- **Scene `20241108_044308_36_24f0`:** Super Dove (PSB.SD), acquired **2024-11-08 04:43:08 UTC**, satellite 24f0, view angle 1.4°, sun elevation 46.3°, ground control true, finalized.
- **Scene quality:** **100% clear**, with 0% haze, shadow and cloud.
- The grid, bands, nodata value and ×10⁻⁴ scaling are identical to the February scene, and again there is no harmonization flag. The raw data stays local and git-ignored.
- **Unchanged rules:** the 720 m windows, UDM2 clear mask, NDWI > 0, JRC ≥ 50%, the reach corridor, 2-pixel (6 m) erosion and the 25-pixel gate.

| Station | Window clear | Corridor water px (NDWI > 0) | Interior px (2 px erosion) | Largest water body (inscribed width) | Primary gate | Sensitivities (NDWI > 0.1 / 1 px erosion / ≥ 50 px) | Verdict |
|---|---|---|---|---|---|---|---|
| Khaddum 4315 (upstream) | 100% | 234 (2 components) | **44** (2 components) | ≈ 24 m | **PASS (marginal)** | **fail** (9) / pass (120) / **fail** (44) | **FRAGILE: descriptive only** |
| Sunapur 3376 (downstream) | 100% | 41 (4 fragments) | **0** | ≈ 8.5 m | **FAIL** | fail / fail / fail | **NO-GO** |
| *Feb 2025, Khaddum* | 0.5% (99.5% light haze) | 0 | 0 | — | FAIL | — | NO-GO (haze) |
| *Feb 2025, Sunapur* | 100% | 0 | 0 | — | FAIL | — | NO-GO (no water signature) |

**Khaddum, single date (descriptive only).** Over the 44 interior pixels:
- **NDTI median −0.002**, IQR −0.019 to 0.015;
- pixel-bootstrap 95% CI of the median −0.014 to 0.011. The pixels are spatially dependent, so this CI is descriptive only;
- interior NDWI 0.13–0.25 (median 0.22).

The pixels are unusually bright for open water: median green 0.146, red 0.144, NIR 0.094. That is consistent with milky or turbid, bright water, but the cause cannot be identified from reflectance. The result **fails 2 of 3 preregistered sensitivities**, so it is fragile. It is **not** a turbidity, NTU, acidity or pollution value, and no causal reading is made.

**Sunapur.** Water-like pixels appear in November (41, against 0 in February) but only as fragments about 8 m wide. None survive the conservative bank exclusion.

**November vs February.** These are the same two windows under the same rules, but the comparison is not controlled for flow or conditions. With clear skies, November shows **some** open-water signal at both stations, and February showed none at Sunapur. Two dates do not show that November is generally wetter; February's Khaddum window was hazy and could not be assessed.

**Paired statistic.** The preregistered same-day Sunapur − Khaddum difference needs **both** gates on at least 5 paired dates per season. It is **not feasible** on either date, because Sunapur never passes.

## Conclusion of Phase 23K

**NO-GO: close the satellite-only river-NDTI objective for the Lukha stations.**

| Evidence | Result |
|---|---|
| Sentinel-2, 10 m (Phases 22O, 23A, 23H) | 9 windows; no flowing reach observable |
| PlanetScope, 3 m (this phase) | Downstream Sunapur fails on both dates (0 interior px). Upstream Khaddum passes once, marginally, and fails the sensitivity checks. |

Searching further for favourable scenes would risk selection bias, so it is not recommended. The river component should be reported as a **resolution- and flow-limited negative feasibility result**: the channels are roughly 8–24 m of open water in the dry season.

Any future river-impact work would need **field sampling** (turbidity/TSS, pH, conductivity, metals) at Khaddum and Sunapur matched to dates, or official MSPCB/CPCB station records.
