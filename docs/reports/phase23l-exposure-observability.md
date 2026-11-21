# Phase 23L — Exposure-to-observability integration (paper-ready summary)

**Records.** The table is [phase23l-reach-integration.csv](phase23l-reach-integration.csv), with rules and provenance in [phase23l-reach-integration.json](phase23l-reach-integration.json). It is built by `scripts/phase23l_reach_integration.py` and tested in `tests/test_phase23l_reach_integration.py`. The dashboard view is *Rivers → Exposure & priority → Reach detail*.

**Inputs.** Every input is already committed and hash-recorded. The repository contains **no Phase 23B report**, so none was used. There were no Earth Engine calls, no downloads and no TEST access.

## Methods

We joined two independent axes for the four CPCB station reaches on the Lukha and Myntdu, keeping them separate.

**1. Upstream disturbance burden (modelled exposure).**
- The 174 systematically sampled candidate clusters (Phase 22X), with their persistence classes from a third dry season (Phase 22Y), were routed with 90 m HydroSHEDS D8 flow directions to Free-Flowing-Rivers reaches. They were then followed along the NDOID topology to the station reaches (Phase 23A).
- 174 of 174 routed; 1 snap was ambiguous; no paths crossed a TEST block; the median path to the first reach is 0.99 km.
- Counts are cumulative down the main stem.
- **Burden classes** use upstream persistent clusters: HIGH ≥ 10, MODERATE 3–9, LOW < 3.

**2. Downstream observability (satellite measurability).**
- **Sentinel-2 10 m** (Phase 22O): the preregistered water screen with interior erosion, at least 5 dates per season, and water identity consistent across seasons.
- **PlanetScope 3 m** (Phase 23K): two preregistered dates (2024-11-08 and 2025-02-20) for Khaddum and Sunapur only, with UDM2 clear, NDWI > 0, JRC ≥ 50%, 6 m erosion and at least 25 interior pixels, plus three sensitivity checks.
- **Observability classes:**
  - OBSERVABLE: gate and all sensitivities pass;
  - MARGINAL: the gate passes but a sensitivity fails;
  - UNOBSERVABLE: every assessed date fails;
  - UNKNOWN: inconsistent water identity, or never assessed at 3 m.

**Monitoring label.** This is a fixed lookup over the two axes, not a calibrated risk score. It ranks where *measurements are missing relative to modelled exposure*.

## Results

| Reach | Upstream clusters (persistent) | Burden | Sentinel-2 10 m | PlanetScope 3 m | Observability | NDTI available | Monitoring label |
|---|---|---|---|---|---|---|---|
| Lukha · **Sunapur 3376** | 80 (28) | **HIGH** | Unobservable (4/0 dates) | Gate fails on both dates: 0 interior px; about 8.5 m of water on 8 Nov | **UNOBSERVABLE** | None | **PRIORITY FIELD MONITORING** |
| Lukha · Khaddum 4315 | 11 (1) | LOW | Unobservable (water identity not established) | 8 Nov: marginal pass, 44 px, fails 2/3 sensitivities. 20 Feb: hazy. | **MARGINAL** | Single date, fragile: median −0.002 | REFERENCE / LOW |
| Myntdu · Mihmyntdu 4316 | 15 (7) | MODERATE | Unobservable (no interior water) | Not acquired | UNOBSERVABLE | None | FIELD MONITORING |
| Myntdu · Leshka 3379 | 17 (8) | MODERATE | Inconsistent water identity (impounded) | Not acquired | UNKNOWN | None | FIELD MONITORING |

**Key finding.** The most exposed reach in the study area, Sunapur, is also among the least observable from space. Its upstream burden includes the Lumshnong persistent-disturbance locality. Even at 3 m, its dry-season channel yields no interior open water. No reach supports the preregistered paired upstream/downstream NDTI comparison.

**Contribution.** This is a reproducible way to separate *where disturbance drains* from *where satellites can measure the river*. It identifies Sunapur as the priority site for **in-situ** monitoring, rather than as a polluted reach.

## Limitations

- **Burden is modelled exposure geometry.** The 90 m D8 routing cannot resolve 30 m drainage, culverts, roads or karst conduits. Station snapping is 27–101 m.
- **Candidate clusters remain UNKNOWN** land disturbance, not verified mining.
- **Limited Planet coverage.** Only two Planet dates exist, for two reaches. Mihmyntdu and Leshka were never assessed at 3 m. Khaddum's NDTI is a single, fragile date.
- **No measurements.** There are no official station records, discharge or field samples, so there is no claim of pollution, measured runoff, turbidity, acidity or causation.
- **Label thresholds.** The burden thresholds (10 and 3 persistent clusters) and the label lookup are transparent review heuristics. They are not validated risk calibrations.
