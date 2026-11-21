# Phase 23K — PlanetScope 3 m Lukha upstream/downstream relative-NDTI pilot: preregistration

This preregistration was committed **before** any PlanetScope data was selected or downloaded. Its purpose is to test whether 3 m imagery resolves the interior-water gap that blocked the 10 m analyses (Phases 22O, 23A and 23H). Mining attribution stays UNKNOWN. NDTI is a relative optical proxy, not NTU, acidity or metals. No causal claim will be made.

## Sites (fixed)

The AOIs are in [phase23k-planet-aoi.json](phase23k-planet-aoi.geojson): the Phase 4A 720 m CPCB station windows, verified offline to be inside the districts and clear of all TEST buffers.

| Role | Station | Phase 23A exposure |
|---|---|---|
| Upstream (lightly exposed) | Lukha · Khaddum 4315 | 11 upstream clusters, 1 persistent |
| Downstream (most exposed) | Lukha · Sunapur 3376 | 80 upstream clusters, 28 persistent |

The Lunar confluence is **not** included, because its station coordinates are unverified (Phase 23C).

## Scene selection (outcome-blind; uses only Planet catalogue metadata and the preview)

- **Product:** PlanetScope Scene, **Surface Reflectance** (4-band, or 8-band where available), **with UDM2**, **clipped to the AOIs**, with harmonization to Sentinel-2 **on**. The same settings are used for every order.
- **Windows:** [2023-11-01, 2024-04-01) and [2024-11-01, 2025-04-01), the project's frozen seasons.
- **Eligible date:**
  - **both** AOIs are fully covered on the **same UTC day**;
  - the catalogue cloud cover is at most 10%;
  - the preview shows no cloud or shadow over either AOI.
- **Selection:** all eligible dates, capped at **12 per season**. If more exist, take the 12 most evenly spaced through the season, ties going to lower cloud cover.
- Turbidity, colour and river appearance are **never** used to choose a date.
- **Raw data stays local** (`outputs/phase23k_planet/`, git-ignored). The Planet licence forbids redistribution; only derived statistics are published.

## Analysis (fixed before download)

1. **Clear pixels:** UDM2 `clear` = 1, with no cloud, shadow, haze or snow.
2. **Water:** NDWI = (green − NIR)/(green + NIR) > 0, **and** JRC occurrence ≥ 50% (the cached Phase 4A 30 m layer, sampled at 3 m), **and** inside the Phase 4A reach corridor (80 m around the mapped reach, within 260 m of the station).
3. **Interior water:** the water mask eroded by **2 pixels (6 m)**. A date is valid for a site if it has **at least 25 interior pixels**.
4. **Per site and date:** the median NDTI = (red − green)/(red + green) over the interior pixels.
5. **Primary statistic:** the same-day **downstream − upstream** NDTI difference (Sunapur − Khaddum), on dates valid at both sites.
   - Requires **at least 5 valid paired dates per season**; otherwise the result is INSUFFICIENT_DATA.
   - Report the per-season median of the paired differences with a **date-bootstrap 95% CI** (10,000 draws, seed 23).
   - Report the after-minus-before change in that median, with its CI.
6. **Context:**
   - CHIRPS 1-, 3- and 7-day antecedent rain, from the cached station-cell series, per date;
   - the median interior-pixel count;
   - per-date NDWI and red reflectance distributions.
7. **Sensitivities:** NDWI > 0.1; 1-pixel erosion; and a minimum of 50 interior pixels.
8. **Interpretation rules:**
   - A CI that excludes 0 is a *relative optical difference between reaches*, not pollution.
   - A CI spanning 0 is *no detectable difference*, not proof of no effect.
   - Insufficient data is reported as such, never as zero.

## Confounders to report

- Lunar tributary and other inflows between the stations;
- the two reaches differ in width and depth (bottom reflectance);
- sun and view geometry differences between Planet satellites;
- harmonization residuals;
- the after season was about 45% drier;
- no discharge data;
- karst.
