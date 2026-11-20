# Phase 22X — Systematic Meghalaya multi-sensor disturbance assessment

The preregistration was committed as `57c079d` before any request ([phase22x-preregistration.json](phase22x-preregistration.json)). Results are in [phase22x-summary.json](phase22x-summary.json). Code is in `scripts/phase22x_landscape.py` and tests in `tests/test_phase22x_landscape.py`.

**All candidates remain UNKNOWN.** These are landscape screening statistics. They are not mining detections, not accuracy, and not evidence about legality or rivers.

## Design (fixed before measurement)

- **Sampling frame.** Every non-TEST seed-42 5 km block whose centred 1,920 m AOI lies wholly in one district and passes the full-footprint TEST-buffer guard. This gives 59 blocks in East and 54 in West Jaintia Hills.
- **Exclusions.** The four earlier AOI blocks (22L/22Q) are excluded for independence.
- **Sample.** 10 blocks per district, drawn in sha256 order. AOIs are fixed at block centres, with no relocation or replacement. The sample contains 17 TRAIN and 3 VAL blocks.
- **Unchanged methods:**
  - optical: the Phase 22L rule (NDVI drop ≤ −0.30, BSI rise > +0.10);
  - SAR: the Phase 22P Sentinel-1 graph (descending orbit 77, seasonal median dB);
  - products: the Phase 22R GFC v1.13 and WRI/GDM drivers comparison.
- **Statistics.** Background cells must be eligible, SAR-valid and more than 60 m from any candidate. The cluster tests use shape-preserving translation permutations stratified by AOI (10,000 draws). Density uses an AOI bootstrap, with the AOI as the sampling unit.
- **Cloud usage.** 61 Earth Engine requests and 6,913,630 bytes, against a cap of 160 requests and 10 MB. A single writer ran under the exclusive lock, and the ledger matches the request count.

## Results

**Candidate density (ha of candidate cells per 100 eligible ha).**

| Scope | AOIs (with candidates) | Mean | AOI-bootstrap 95% CI |
|---|---|---|---|
| Both districts | 20 (18) | **1.20** | 0.62 – 1.98 |
| East Jaintia Hills | 10 (8) | 1.42 | 0.33 – 2.88 |
| West Jaintia Hills | 10 (10) | 0.99 | 0.59 – 1.43 |

The two districts' intervals overlap, so they do not differ detectably. Density is highly skewed, from 0 (two AOIs) to 6.67 (block 88:558) and 4.01 (87:556). The four earlier coverage-selected AOIs had much lower densities (0.02 to 0.22). They were therefore not representative of the landscape.

**Sentinel-1 corroboration.** 174 clusters in 18 AOIs were tested.
- **dVH:** the cluster mean minus background is **−1.45 dB**. The translation null has median −0.01 and a 95% range of −0.14 to +0.13, so p ≈ 1×10⁻⁴, the smallest value the draws can resolve. **Every one of the 18 AOIs shows the negative direction.**
- **dVV:** −1.12 dB, also p ≈ 1×10⁻⁴. This differs from the 4-AOI pilots, where dVV was not distinct.

**Independent products (Phase 22R tests).**
- **H1 (GFC 2024/2025 loss):** **69 of 174 clusters (39.7%, Wilson 95% CI 32.7–47.1%)** overlap GFC loss. Random shape-preserving placements give 2.3% (95% range 0.6–4.6%), so p ≈ 1×10⁻⁴. The 4-AOI result had been 1 of 18.
- **H2 (hard-commodities probability):** the cluster mean is 0.122, against a null of 0.096 (range 0.084–0.108), so p ≈ 1×10⁻⁴.
  - Hard-commodity-*dominant* 1 km driver cells occur in only two adjacent AOIs: 87:556 (1,873 cells of 30 m) and 87:557 (820 cells).
  - That is the Lumshnong limestone/cement locality in East Jaintia Hills. It was reached by systematic sampling. It is not the rectangle rejected in Phase 22N.
  - The hard-commodities class combines mining with energy infrastructure. Elsewhere the dominant drivers are shifting cultivation, agriculture, logging and settlement.

Per-AOI counts, densities, SAR differences and product overlaps are in the summary JSON. Exact geometries stay local.

## Interpretation

At landscape scale, the optical candidates are **not random noise**:
- They carry a consistent independent Sentinel-1 signature: VH and VV decrease.
- About 40% coincide with independently mapped 2024/25 forest loss, roughly 17 times the chance rate.
- They sit in cells with higher hard-commodity driver probability than their surroundings.

This is the strongest multi-sensor and independent-product agreement in the project. It supports describing the candidates as *real recent land-cover disturbance*.

It still does **not** establish mining:
- 60% of the clusters have no GFC loss.
- The driver evidence is coarse (1 km), dominant-class, covers 2001–2024, and includes energy infrastructure.
- Only two AOIs have hard-commodity-dominant cells.
- Jhum, logging, roads and construction produce the same S1/S2 signals.

## Limitations

- **Sample size.** 20 AOIs is a small sample. Density is heavy-tailed and its CIs are wide.
- **Sampling scheme.** The centred-AOI design samples about 15% of each block.
- **Shared imagery.** AOIs on the same Sentinel-2 tile share acquisitions. Spatial autocorrelation inside AOIs is handled only by stratified translation nulls.
- **Multiple tests.** Several tests were run. All the p-values are descriptive.
- **Domain and data.** This is the unchanged 22L rule at 30 m, so small pits below the resolution are missed. There are no reference labels, so precision is unknown.

## Reproduction

```powershell
python -B -m scripts.phase22x_landscape --analyze   # offline from outputs/phase22x_landscape
python -B -m pytest -q -p no:cacheprovider tests/test_phase22x_landscape.py
```

`--acquire` refuses to run concurrently and skips cached AOIs.
