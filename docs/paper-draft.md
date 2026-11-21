# Paper draft: Multi-sensor screening of mining-related land disturbance and downstream river observability in the Jaintia Hills, Meghalaya, using Sentinel-1 and Sentinel-2

This draft uses verified, committed results only. Every number cites a file in `docs/reports/`. Mining attribution is **UNKNOWN** throughout, and no accuracy against independent reference data is claimed.

## Contributions

1. **Reproducible screening pipeline.** A seasonal S1/S2 change-screening pipeline that is preregistered and hash-receipted, with full-footprint TEST guards and Earth Engine request ledgers. It generalises to configurable Indian AOIs (24B).
2. **Systematic landscape estimate.** A sampling-based estimate of disturbance-candidate density over 20 Jaintia Hills AOIs, with independent-sensor (S1) corroboration and a three-season persistence typology (22X/22Y).
3. **Controlled sensor ablation.** A SAR, optical, fusion and terrain ablation on spatially blocked weak labels (22W). It shows that S1 adds no detectable F1 over S2 for footprint agreement.
4. **Exposure–observability framework.** A framework linking upstream disturbance, via D8 routing (23A), to downstream reach priority (23H/23L).
5. **Negative feasibility result.** Neither 10 m Sentinel-2 (22O) nor 3 m PlanetScope (23K) can observe the narrow channels' water colour. This motivates field monitoring.

## Study area and data

- **Study area.** East and West Jaintia Hills (FAO GAUL 2025, about 3,818 km²), Lukha and Myntdu catchments, with four CPCB station reaches.
- **Seasons.** Nov–Mar 2023/24 (before) and 2024/25 (after), with 2025/26 for persistence.
- **Imagery and terrain.** Sentinel-1 GRD (descending, relative orbit 77), Sentinel-2 SR harmonized with cloud probability, and SRTM.
- **Context products.** Hansen GFC v1.13, WRI/GDM drivers v1.2 and JRC GSW.
- **Hydrography.** HydroSHEDS FFR and 03DIR.
- **Other.** CHIRPS rainfall and two PlanetScope SR scenes.
- **India leads.** Public environmental-clearance documents (Phase 11C).

## Methods

1. **Composites.**
   - **SAR:** speckle-filtered (20 m focal mean in linear power), with a seasonal median in dB.
   - **Optical:** S2 cloud- and SCL-masked, with seasonal medians of NDVI, NDTI and BSI.
   - **Change:** after − before.
2. **Candidate rule (22L).** ΔNDVI ≤ −0.30 and ΔBSI > +0.10 on a 30 m grid, with 4-connected clusters.
3. **Landscape sampling (22X).** 20 AOIs, each 64×64 cells (1,920 m). These are 10 per district, drawn in SHA-256 order from the non-TEST seed-42 5 km blocks that pass the full-footprint TEST-buffer guard (59 East and 54 West blocks; 17 TRAIN and 3 VAL in the sample).
4. **Statistics.** Density with AOI-bootstrap CI. Cluster-minus-background ΔVH tested with a translation null. Agreement with GFC/WRI products measured in 22R.
5. **Persistence (22Y).** A third season classifies clusters as persistent, partial or recovering, tested with within-AOI permutation.
6. **Ablation (22W).** RF on VV/VH (SAR), on B3/B4/B8 (optical), on both (fusion) and on fusion + elevation/slope. Compared with an NDVI rule. Uses 11 Odisha validation groups, a group bootstrap for CIs and a sealed TEST split.
7. **Routing (23A).** 90 m D8 from each cluster to an FFR reach, then along the NDOID topology to the station reaches. Cumulative counts. Audited in 23M.
8. **Observability (22O/23K).**
   - Preregistered water screens: interior erosion, at least 25 interior pixels and three sensitivities.
   - Burden and observability are kept as separate axes (23L).
9. **India generalisation (24B).** 32×32-cell, 30 m UTM tiles around configured anchors, with descriptive ΔVV, ΔVH, ΔNDVI and ΔNDTI quantiles.

## Results tables

**Table 1. Meghalaya screening (exploratory).** Source: [phase22x-summary.json](reports/phase22x-summary.json), [phase22y-summary.json](reports/phase22y-summary.json).

| Quantity | Value |
|---|---|
| AOIs / clusters | 20 / 174 |
| Candidate density (ha per 100 ha) | 1.20 [0.62, 1.98] |
| Cluster ΔVH − background | −1.45 dB; negative in 18/18 AOIs; translation-null p ≈ 1e-4 |
| Persistent / partial / recovering | 53 (30.5%) / 77 / 44 |

**Table 2. Sensor ablation, validation F1 against unverified weak labels.** Source: [phase22w-metrics.json](reports/phase22w-metrics.json).

| Arm | F1 [group 95% CI] |
|---|---|
| SAR (VV, VH) | 0.378 [0.239, 0.480] |
| Optical (B3, B4, B8) | 0.533 [0.354, 0.637] |
| Fusion | 0.539 [0.386, 0.628] |
| Fusion + terrain | 0.463 [0.290, 0.583] |
| NDVI rule | 0.437 [0.199, 0.637] |
| Fusion − optical (ΔF1) | +0.006 [−0.039, 0.058] |

Context (not comparable to Table 2): 22H U-Net validation F1 0.713 ± 0.085 on weak labels. 17G MineNetCD256 RF held-out pooled F1 0.246 on an external RGB benchmark ([phase24c-evidence-summary.json](reports/phase24c-evidence-summary.json)).

**Table 3. Reach exposure and observability.** Source: [phase23l-reach-integration.csv](reports/phase23l-reach-integration.csv).

| Reach | Upstream clusters (persistent) | Burden | Observability | Label |
|---|---|---|---|---|
| Lukha–Khaddum | 11 (1) | LOW | MARGINAL (3 m, 1 date) | REFERENCE / LOW |
| Lukha–Sunapur | 80 (28) | HIGH | UNOBSERVABLE | PRIORITY FIELD MONITORING |
| Myntdu–Mihmyntdu | 15 (7) | MODERATE | UNOBSERVABLE | FIELD MONITORING |
| Myntdu–Leshka | 17 (8) | MODERATE | UNKNOWN | FIELD MONITORING |

**Table 4. India AOI screening.** Source: [phase24b-india-screening.json](reports/phase24b-india-screening.json).

- 6 tiles in 5 states, 5.53 km² in total.
- Descriptive quantiles only.
- No national coverage; status UNKNOWN.

## Figure references

Every figure is regenerated from the listed artifact.

| Figure | Content | Artifact |
|---|---|---|
| Fig. 1 | Study area, AOIs, stations and routed reaches | dashboard `#meghalaya`, built from `frontend/public/local/geo.json` (`scripts/phase23_dashboard_geo.py`) |
| Fig. 2 | Density by district and the ΔVH translation null | `phase22x-summary.json` |
| Fig. 3 | Persistence shares | `phase22y-summary.json` |
| Fig. 4 | Ablation F1 with CIs | `phase22w-metrics.json` |
| Fig. 5 | Exposure and observability matrix | `phase23l-reach-integration.csv`, dashboard `#rivers-exposure` |
| Fig. 6 | India leads and evidence tiers | dashboard `#overview`, built from `india-candidates.json` and `phase24b-india-screening.json` |

## Limitations

- **No accepted independent reference labels.** Weak-label scores are agreement with unverified footprints, not accuracy. Verified classification is BLOCKED.
- **Alternative explanations remain.** Composites are 30 m, so small excavations are unresolved. SAR layover, moisture, phenology, agriculture, forestry and construction are not ruled out.
- **Small India screening.** India tiles are 0.92 km² each, and the summaries are tile-relative.
- **River colour.** River NDTI is a relative proxy and is unobservable at Sunapur. There is no NTU, pH or causal pollution claim, and Sunapur is a monitoring priority only.
- **Routing.** D8 routing is at 90 m. One snap is ambiguous, and karst flow paths are unverified.

## Pending dependencies (not completed)

- Human review of the 23I blinded sample (two reviewers).
- Field or official water-quality data.
- Official DMR/MBDA lease boundaries.
- EE quota for wider India screening.

Each of these is listed in [final-project-status.md](reports/final-project-status.md).
