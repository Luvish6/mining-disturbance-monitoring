# Phase 22Y — Persistence-based typology of disturbance clusters

The preregistration was committed as `ca851a3` before any request ([phase22y-preregistration.json](phase22y-preregistration.json)). Results are in [phase22y-summary.json](phase22y-summary.json). Code is in `scripts/phase22y_persistence.py` and tests in `tests/test_phase22y_persistence.py`.

**What PERSISTENT means.** It is a *non-revegetating, mining-compatible review-priority class*. **It is not a mining label.** All candidates remain UNKNOWN.

## Method (fixed in advance)

- **Clusters.** The 174 SAR-tested Phase 22X clusters across 18 AOIs. No new detection was run.
- **Follow-up season.** **[2025-11-01, 2026-04-01)**, processed with the unchanged Phase 22L optical graph on the identical 22X grids.
- **Usage.** 60 Earth Engine requests and 1,877,433 bytes, against a cap of 70 requests and 6 MB. One writer ran under the lock.
- **Classes.** Each class is computed on the cluster-mean change from the **2023–24 baseline** to the follow-up season:
  - **PERSISTENT:** ΔNDVI ≤ −0.30 and ΔBSI > +0.10. This is the original 22L rule, still met two seasons later.
  - **RECOVERING:** ΔNDVI ≥ −0.10.
  - **PARTIAL:** anything in between.
  - **UNOBSERVED:** fewer than 50% of the cluster's cells were valid in the follow-up season.
- **Tests.**
  - Associations: class labels permuted *within each AOI* (10,000 draws), so between-AOI differences cannot drive them.
  - Shares: AOI-bootstrap 95% CIs.

## Results

| Class | Clusters | Share | AOI-bootstrap 95% CI |
|---|---|---|---|
| PERSISTENT | 53 | **30.5%** | 17.1 – 42.0% |
| PARTIAL | 77 | 44.3% | 35.8 – 54.4% |
| RECOVERING | 44 | 25.3% | 16.3 – 37.0% |
| UNOBSERVED | 0 | 0% | — |

**By district.**

| District | PERSISTENT | PARTIAL | RECOVERING |
|---|---|---|---|
| East Jaintia Hills | 34 | 36 | 25 |
| West Jaintia Hills | 19 | 41 | 19 |

**Associations (PERSISTENT vs other).**

| Covariate | Mean by class (PERSISTENT / PARTIAL / RECOVERING) | Within-AOI test |
|---|---|---|
| Hard-commodities probability | 0.188 / 0.099 / 0.085 | p = 0.59. The difference is *between* AOIs, not within them. |
| Any 2024/25 GFC loss | 0.42 / 0.34 / 0.48 | p = 0.017. Within AOIs, PERSISTENT clusters overlap loss more often than the permutation null. |
| dVH minus background (dB) | −1.37 / −1.34 / −1.75 | p = 0.57. No difference: every class shows the Sentinel-1 decrease. |
| Mean slope (°) | 8.1 / 11.3 / 12.5 | p = 0.038. PERSISTENT clusters sit on gentler ground. |
| Lumshnong blocks (87:556 / 87:557) | 28 of 53 PERSISTENT clusters | The within-AOI test is uninformative by design, because this covariate is constant within an AOI. |

**Lumshnong descriptive split.** In the two Lumshnong blocks, 28 of 54 clusters (52%) are PERSISTENT, against 25 of 120 (21%) elsewhere. These are the only sampled AOIs with hard-commodity-dominant driver cells.

## Interpretation

- **About 30% of the clusters are still bare two seasons later.** These persistent clusters are concentrated in the Lumshnong limestone/cement locality and sit on gentler slopes. That pattern is consistent with quarry floors, dumps, roads or built surfaces, rather than hillside jhum plots that regrow.
- **About 25% revegetate**, consistent with shifting cultivation, logging or other temporary clearing.
- **Persistence does not separate classes by Sentinel-1 VH.** All classes show the VH decrease, so the SAR signal marks *loss of vegetation*, not its cause.
- **The hard-commodity association is a between-locality pattern.** It is driven by Lumshnong, which already holds the driver map's only hard-commodity cells. It is not a within-AOI discriminator.

The PERSISTENT clusters, especially those around Lumshnong, are the defensible **review-priority shortlist** for official DMR/MBDA data or expert verification. None is labelled mining.

## Limitations

- **Short follow-up.** One follow-up season is short. Some jhum fallows stay bare for more than a year, and some excavations are revegetated or flooded.
- **Other persistent surfaces.** Roads, construction, settlements and landslide scars also persist.
- **Small sample.** 18 AOIs, with Lumshnong contributing 54 clusters. Results are sensitive to that single locality.
- **Fixed threshold.** The 0.10 recovery band is preregistered but not validated.
- **Descriptive statistics.** Several tests were run and clusters within an AOI are dependent, so the p-values are descriptive.
- **No labels.** With no reference labels, the precision of any class is unknown.

## Reproduction

```powershell
python -B -m scripts.phase22y_persistence --analyze   # offline; needs the 22X and 22Y caches
python -B -m pytest -q -p no:cacheprovider tests/test_phase22y_persistence.py
```
