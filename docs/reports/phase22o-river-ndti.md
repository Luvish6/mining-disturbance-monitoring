# Phase 22O — Guarded relative-NDTI river feasibility pilot (Lukha / Myntdu)

I committed the preregistration as `2a7a5bdf527f9300a9bb5af95dfeb4d6cbafddfe` before making any imagery request ([phase22o-preregistration.json](phase22o-preregistration.json)). The measured results are in [phase22o-summary.json](phase22o-summary.json). Script: `scripts/phase22o_river.py`. Tests: `tests/test_phase22o_river.py`.

**NDTI = (B4 − B3)/(B4 + B3)** is computed on Sentinel-2 L2A land surface reflectance. It is a *relative spectral proxy*. It is not NTU, suspended sediment, acidity or contamination. It is not evidence that mining degraded a river, and no causal claim is made.

## Reach provenance and geometry guards

- **Stations.** The four CPCB WQMN stations come from the [Phase 4A](phase4a-river-feasibility.md) receipt: Khaddum 4315, Sunapur 3376, Mihmyntdu 4316 and Leshka 3379. Each analysed footprint is the Phase 4A 720 m × 720 m window on the 10 m EPSG:32646 grid.
- **Reach.** The reach is the nearest intersecting HydroSHEDS Free-Flowing-Rivers line, buffered by 80 m, limited to 260 m from the station and clipped to the window. For every station the re-fetched reach GOID equals the Phase 4A GOID, and the script asserts this.
- **TEST guard.** Each *complete window*, not just its centre, was tested against every canonical seed-42 TEST 5 km block expanded by 120 m (the Phase 22N `guards()`, unchanged).
  - All four windows are contained in the districts.
  - None intersects a protected TEST buffer. Separations are 4,600 / 4,235 / 4,500 / 5,250 m.
  - The windows fall in TRAIN or VAL blocks only. No reach was shifted.
- **Not tested.** The parts of the HydroSHEDS segments that lie outside each window were not sampled, so they were not guard-tested.

## Preregistered screen (feasibility criteria, not validated water-quality thresholds)

1. **Masks.** The Phase 2 `prepare()` masks are reused: cloud probability <40, SCL 4/5/6, and B3/B4/B8/B8A/B9 edge masks. B11 must also be present.
2. **Water.** A pixel counts as water when JRC GSW occurrence is ≥50% and Sentinel-2 MNDWI = (B3 − B11)/(B3 + B11) is >0 with a positive denominator. JRC is a 30 m historical layer sampled on the 10 m grid. B11 is native 20 m, resampled to the 10 m grid by nearest neighbour.
3. **Interior.** The water mask is eroded by one 10 m pixel (3×3 neighbourhood; pixels on the window border fail), then intersected with the corridor.
4. **Per granule.** A granule needs at least 3 interior pixels with B3 + B4 > 0. It yields one median NDTI.
5. **One record per date.** For each UTC date, the granule with the most interior pixels is kept; ties go to the lowest scene ID.
6. **Seasons.** Each season needs ≥5 usable dates. The confidence interval is a date-bootstrap 95% percentile interval (10,000 resamples, seed 42). Seasons with fewer dates get `INSUFFICIENT_DATES` and no interval. Reaches with no interior water get `UNRESOLVED`.
7. **Pre-acquisition check.** Mihmyntdu was judged UNRESOLVED **before acquisition**. Eroding the cached JRC ≥50% layer left at most 1 pixel within 260 m, and the screen needs 3. No imagery was requested for it.

## Results

| Reach | Granules (B/A) | Dates with granules | Usable dates | Median NDTI before [95% CI] | Median NDTI after [95% CI] | After − before [95% CI] | Status |
|---|---|---|---|---|---|---|---|
| Lukha · Khaddum | 98 / 114 | 52 / 57 | 19 / 24 | −0.041 [−0.069, 0.001] | −0.020 [−0.050, 0.018] | +0.021 [−0.033, 0.076] | SUPPORTED by screen; **water identity unverified** |
| Lukha · Sunapur | 47 / 57 | 47 / 56 | 4 / 0 | −0.481 (no CI) | — | — | INSUFFICIENT_DATES / UNRESOLVED |
| Myntdu · Mihmyntdu | not requested | — | — | — | — | — | UNRESOLVED (pre-acquisition) |
| Myntdu · Leshka | 75 / 87 | 43 / 52 | 15 / 13 | −0.530 [−0.606, −0.491] | −0.505 [−0.577, −0.445] | +0.025 [−0.105, 0.130] | SUPPORTED; **potentially impounded water** |

The table rows are `INSUFFICIENT_DATES` and `UNRESOLVED` outcomes, not zeros. There are no fabricated values.

**Rainfall context.** This comes from the CHIRPS daily station cell (≈0.05°). The season totals are complete-day sums over the half-open windows: 275.7 / 149.9 mm at Khaddum, 295.6 / 180.8 mm at Sunapur and 252.7 / 136.3 mm at Leshka. So the after season was roughly 45% drier at every station, and the two seasons are not hydrologically comparable. The 1-, 3- and 7-day antecedent totals, excluding the acquisition day, are stored for each usable date:
- Median 7-day antecedent rain on usable dates was 0 mm for Khaddum and Leshka.
- All four Sunapur dates fall in November 2023. Three of them follow about 54 mm of rain in the previous 7 days.

None of this is gauge, catchment-area or discharge data.

**Flow topology.** This is DEM-derived HydroSHEDS NDOID linkage, not field-verified.
- Khaddum → Sunapur: 14 downstream hops, with no reverse path.
- Mihmyntdu → Leshka: 18 hops, with no reverse path.

The ordering is supported. **But no upstream–downstream NDTI contrast is possible**: on each river, one member of the pair is INSUFFICIENT or UNRESOLVED.

## Post-hoc diagnostics (do not change any preregistered status)

**Khaddum.** The interior pixels have **0% SCL water class on all 43 usable dates**. Median B3 reflectance is about 0.17, and NDTI is near 0. Phase 4A had already found no SCL-6 / NDWI > 0 water at Khaddum on any date. Each date also has only 3–12 interior pixels.
- These pixels pass the preregistered JRC + MNDWI screen. Yet they are spectrally more consistent with bright mixed, bank, gravel or very shallow pixels than with open water.
- **Khaddum's NDTI should not be interpreted as a water-colour signal** until the bank outlines are checked against finer dated imagery.
- This exposes a weakness in the preregistered screen. MNDWI > 0 plus historical occurrence does not, on its own, ensure that the current pixels are open water in narrow channels.

**Leshka.** This reach has about 259 interior pixels on most dates and dark water (B4 about 0.015–0.02). It is the only reach where open water is plausibly sampled.
- The SCL water share fell from a median of 1.00 before to 0.06 after, even though MNDWI and JRC still passed. SCL classified the same water differently between the seasons.
- The difference in seasonal medians, +0.025, has a CI that spans zero. **No seasonal NDTI change is detected.**
- [Phase 4B](phase4b-leshka-spectral-pilot.md) documents dam and backwater context. Reservoir operation, rainfall (much drier after), date sampling and adjacency confound any comparison.

## Conclusion

A relative-NDTI comparison is feasible at one station-window only: Leshka, a potentially regulated reservoir/backwater reach. There it shows no detectable seasonal change. The flowing Lukha and upper Myntdu reaches are too narrow for 10 m interior water under this protocol. Khaddum passes the screen, but its water identity is doubtful.

**The data do not support any downstream river-degradation claim.** For the paper, this is a scientifically useful *negative feasibility result*. It shows that 10 m Sentinel-2 cannot resolve the narrow Jaintia Hills channels for water colour, and it motivates field turbidity sampling, finer imagery or wider downstream reaches.

## Cloud usage and changes after preregistration

- **Usage.** 22 Earth Engine requests and 7,323,424 response bytes, against caps of 40 and 50 MB. Download bytes are exact; getInfo bytes are serialized JSON sizes. GEE initialization is not counted. The ledger is in `outputs/phase22o_river/budget.json` (local).
- **Fetch bug fix.** The first acquisition serialized HydroSHEDS window-line *collection metadata* instead of features. One repair request (`--refetch-lines`) re-fetched them, and this is recorded in the ledger.
- **Other changes.** I also added post-hoc diagnostics and removed scene IDs from the published summary.
- **Analysis rules.** No analysis rule or threshold changed after preregistration.

Frozen TEST imagery, labels and predictions were not accessed; only geometry was used.

## Reproduction

```powershell
python -B -m scripts.phase22o_river --preregister   # offline, rewrites preregistration
python -B -m scripts.phase22o_river --acquire       # requires GEE; refuses if outputs/phase22o_river exists
python -B -m scripts.phase22o_river --analyze       # offline from local cache
python -B -m pytest -q -p no:cacheprovider tests/test_phase22o_river.py
```

The Phase 4A local receipt and JRC rasters must be present. The local cache (`outputs/phase22o_river/cache`) and the per-granule CSVs with scene IDs stay unpublished.
