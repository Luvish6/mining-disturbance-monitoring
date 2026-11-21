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
