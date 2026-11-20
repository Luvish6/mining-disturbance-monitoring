# Phase 22R — Agreement with independently published forest-loss products

The preregistration was committed as `0c3e5b4` before any request ([phase22r-preregistration.json](phase22r-preregistration.json)). Results are in [phase22r-summary.json](phase22r-summary.json). Code is in `scripts/phase22r_product_agreement.py` and tests in `tests/test_phase22r_products.py`.

**This is an agreement study, not mining accuracy validation.** No precision, recall, F1 or accuracy is computed. Agreement does not establish that any candidate is mining, illegal mining or confirmed forest loss. All 18 clusters remain **UNKNOWN**.

## Inputs and protocol

**Clusters.** 18 clusters (21 cells) are frozen from four full-footprint-guarded TRAIN/VAL AOIs:

| AOI | Source phase | Clusters |
|---|---|---|
| east-94-559-c74 | 22L | 6 |
| east-90-562 | 22Q | 5 |
| west-82-563 | 22Q | 1 |
| west-85-563 | 22Q | 6 |

The guards were re-checked, and no TEST tile or block was opened. The 22L rule thresholds are unchanged, and no classifier was trained.

**Products.** Both are CC-BY-4.0, and both asset band lists were confirmed by the first request.

| Product | Earth Engine asset | Bands used | Native resolution | Coverage |
|---|---|---|---|---|
| Hansen/UMD Global Forest Change v1.13 | `UMD/hansen/global_forest_change_2025_v1_13` | `lossyear` (1–25 = 2001–2025), `treecover2000`, `datamask` | 27.8 m | 2000–2025 |
| WRI/Google DeepMind *Global Drivers of Forest Loss* v1.2 (Sims et al. 2025, ERL 20:074027) | `projects/landandcarbon/assets/wri_gdm_drivers_forest_loss_1km/v1_2_2001_2024` | `classification` (1–7; 2 = hard commodities, i.e. mining *and* energy infrastructure), `probability_2` (×0.004) | 0.01° EPSG:4326 (≈1.1 km) | Dominant driver of GFC v1.12 loss, 2001–2024 |

**Sampling.** Both products were sampled on the frozen 30 m EPSG:32646 grids using nearest-neighbour cell centres. The driver values were verified to be constant within each locally identified 1 km cell.

**Background.** The background is every land (datamask) eligible cell more than 60 m from any candidate cell: 3,937, 3,966, 4,071 and 3,965 cells.

**Uncertainty.** The primary unit is the cluster.
- **Null model:** each cluster's exact shape is translated to a random position within its own AOI's background (10,000 draws, seed 46). The two-sided p is measured around the null median.
- **Confidence interval:** Wilson 95% interval for the cluster fraction.
- **Driver cells:** these are reported as distinct 1 km cells, because many 30 m cells share one coarse pixel.

## Results

**H1 — GFC loss in 2024 or 2025.** **1 of 18 clusters** overlaps GFC loss: west-85-563 C005, one cell, lossyear 2024. The fraction is 0.056, with Wilson 95% CI 0.010–0.258.
- Random shape-preserving placements give a median of 0 (97.5th percentile 0.056), so p = 0.038.
- This is nominally above chance, but it rests on a **single cell**, so treat it as weak.
- The other 17 clusters show **no** 2024/2025 GFC loss. For these clusters, the products **disagree**.
- No cluster overlaps 2025 loss.

**H2 — hard-commodities driver.** **No 1 km cell in any AOI has hard commodities as its dominant driver.**
- The candidates' mean hard-commodities probability is 0.042, against a null median of 0.039 (95% null range 0.034–0.048), so p = 0.52.
- This is a **null result**. The 18 clusters fall in only 12 distinct driver cells, which shared coarse pixels make nearly unavoidable. The test therefore has little power.

**Per-AOI results:**

| AOI | Clusters with 2024/25 loss | Cell share with any 2001–2023 loss (candidate / background) | treecover2000 mean (candidate / background) | Dominant driver classes in AOI |
|---|---|---|---|---|
| east-94-559-c74 | 0 / 6 | 0.33 / 0.10 | 65 / 49 | shifting cultivation (all cells) |
| east-90-562 | 0 / 5 | 0.20 / 0.13 | 22 / 51 | shifting cultivation, permanent agriculture |
| west-82-563 | 0 / 1 | 0.00 / 0.06 | 0 / 40 | permanent agriculture, logging |
| west-85-563 | 1 / 6 | 0.17 / 0.06 | 42 / 25 | logging, settlements and infrastructure, shifting cultivation, permanent agriculture |

The 2001–2023 loss and tree-cover columns are descriptive context. They were not tested as hypotheses.

## Interpretation

These independent products **do not corroborate** the candidates as 2024/25 forest loss, nor as hard-commodity-driven change.

- **Coverage and resolution.** Most clusters are single 30 m cells. Several have little 2000 tree cover (0–28%), where GFC cannot record loss. GFC also maps stand-replacing Landsat-scale loss, so small or partial clearing can be missed.
- **Timing.** GFC uses calendar years, while the comparison seasons run November–March.
- **Driver context.** The drivers product describes the *dominant 2001–2024 driver per ~1 km cell*. Every AOI is dominated by shifting cultivation, agriculture, logging or settlement, never by hard commodities.
- **Alternative explanation.** This strengthens shifting cultivation (jhum) and other land use as explanations for the candidates. It does not exclude mining: small or artisanal pits can sit inside cells with a different dominant driver.
- **Earlier loss.** Higher earlier GFC loss at the candidates (descriptive) suggests they often recur at previously disturbed locations.

The most defensible finding is the combination across phases. Sentinel-1 and Sentinel-2 agree on candidate vegetation-loss change (22P/22Q). Coarser global products neither confirm it nor attribute it to mining.

## Usage and reproduction

There were 2 Earth Engine requests and 266,451 response bytes, against caps of 8 requests and 1 MB. Both are logged in `outputs/phase22r_products/products.json`, which is local.

```powershell
python -B -m scripts.phase22r_product_agreement --preregister  # offline; rewrites the freeze
python -B -m scripts.phase22r_product_agreement --acquire      # GEE; refuses if products are cached
python -B -m scripts.phase22r_product_agreement --analyze      # offline
python -B -m pytest -q -p no:cacheprovider tests/test_phase22r_products.py
```
