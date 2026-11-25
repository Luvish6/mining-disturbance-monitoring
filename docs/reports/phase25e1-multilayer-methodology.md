# Phase25E.1 — Multi-layer disturbance methodology and cached pilot

2026-11-25; baseline453e19f. Reused frozen spatial groups, rule configuration, registered25C.2 rasters and completed human-review integration. No discovery rerun, supervised fit, threshold tuning, imagery download or GEE request. [Versioned contract](../../config/phase25e1_methodology.json); [sanitized actual pilot results](phase25e1-methodology-results.json).

## Implementation and layers

The reusable GEE graph bundle composes Phase22L seasonal RGB/NDVI/BSI/NDWI preprocessing, Phase2 SAR seasonal processing and Phase25B.1 environmental sources, preserving the fixed Nov2023–Mar2024/Nov2024–Mar2025 windows. It checks full frozen TRAIN AOI guards before graph construction, pins descending relative orbit77 and does not initialize EE, evaluate metadata or start exports. The graph interface was tested with injected local stand-ins; no new live-server validation is claimed.

S2 retains cloud-probability<40, SCL4/5, edge/all-required-band masks, water NDWI<0 and the existing dark-surface screen. SAR retains IW/VV/VH, one orbit/pass, linear-power20m-radius smoothing then seasonal median/dB conversion. At least2valid observations per season/sensor are required. Later exports must explicitly preserve the frozen30m north-up EPSG:32646 affine; graph-native support is not identical across sources. The static2019 weak-label model is not used.

| Layer/source | Purpose and support | Limitation/use |
|---|---|---|
| S2 NDVI change | vegetation decline; native10m bands,30m output | seasonality/forestry/agriculture possible; not mining-specific |
| S2 BSI change | exposed-ground increase; B11 native20m with10m optical inputs | correlated with NDVI, mixed pixels and illumination; no new30m independent detail |
| S1 VV/VH change | complementary structural/moisture response; dB | terrain/moisture/orbit effects; nonincrease is not a mining signature |
| SRTM slope | terrain/erosion/landslide review context; ~30m | historical terrain, steep areas retained, not excluded as non-mining |
| SRTM elevation | terrain context; ~30m,2000 | not current excavation topography |
| ESA WorldCover | class40cropland/class50built-up context;10m,2021 | predates study; cannot certify stable controls or current cause |
| CHIRPS | after-minus-before seasonal rainfall totals;0.05degree | coarse station-cell context, not catchment rainfall or independent30m observations |
| JRC Global Surface Water | historical occurrence;30m,1984–2021 | missing support retained; no inference of dry land from masked pixels |
| MODIS MCD64A1 | potential competing fire history;500m | unsupported in pilot cache, remains missing |
| OSM roads | competing road-work context | no eligible supplied layer; missing, not zero distance; ODbL obligations apply |
| Geology | possible landscape context | unverified GSI product/rights; missing |
| Mining context | possible historical mine-site context | missing; neither lease nor static footprint proves seasonal change |

Source attribution follows the existing source contract: Copernicus Sentinel, NASA/USGS/JPL SRTM, WorldCoverCC-BY4, CHIRPS citation and JRC/Google attribution. MODIS/OSM requirements remain relevant only if separately acquired. No release permission for private rasters is implied.

## Interpretable score and separate evidence

Count three frozen conditions on common valid land/sensor/count support: dNDVI<=-0.30, dBSI>+0.10, and both dVV/dVH<=0dB. Score0–3 is an exploratory diagnostic condition count, **not mining probability, calibrated risk, a reference label or a new pseudo-label**. Missing signals yield NaN, not zero. No score threshold was optimized on human reviews or VAL. Indicators are correlated; three conditions are not three independent proofs.

Persistence remains in the unchanged historical retrospective0/1/255pseudo-state mask. Follow-up NDVI/BSI are absent from this dataset's feature bands, so the new count does not infer persistence or reuse pseudo-labels as independent evidence. Context does not vote in the score; it raises review questions about agriculture, forestry, road works, construction, landslides, erosion, moisture and artifacts. Context-class absence cannot rule those causes out.

Independently verified references, human visible-disturbance observations, algorithm pseudo-states and algorithm scores have separate namespaces. The five human consensus leads remain R0442ACAF,R0A099D23,R2C582A69,R6947EBA0,RB9952572. All retain UNKNOWN mining attribution; three have excavation-like votes needing independent verification. Their scores were NOT evaluated by this single-patch pilot, and the two VAL leads were not used to fit/select anything. No independent positive/negative mining labels or operational alerts exist.

## Actual bounded pilot and costs

A label-blind sha256(42:25E1:patch_id) ordering selected one frozen TRAIN32x32patch in block83:557; no replacement after seeing results.1024/1024cells eligible(100%). Score counts:0=591,1=391,2=41,3=1. The one all-condition cell is900m² of support, not a validated disturbance object or mining area. Original pseudo-mask preserved:284potentially-stable,0potential-disturbance,740uncertain. A zero persistent pseudo-positive count does not mean zero mining activity.

Terrain,2021land cover and rainfall context each have1024valid cells. Elevation456–617m; slope0.927–28.803degrees. Rainfall seasonal difference−127.855 to−125.559mm is coarse contextual support. No cropland/built-up class cells or>=30degree cells occurred in this patch; non-mining causes remain unresolved. JRC/fire/roads/geology/mining context have0valid cells and remain MISSING, never fabricated.

Wall6.163seconds for cache integrity/load, score calculation and output preparation (not a live GEE cost or full CLI runtime). GEE requests0, received bytes0, training0. No large-area processing. Private outputs: outputs/phase25/experiments/25e1-methodology-v1/{evidence_count.tif,score_components.tif,validity.tif,summary.json,source_provenance.json,receipt.json}. Source manifest/rule/review hashes are linked; original scene identities remain INCOMPLETE, and current-query/follow-up identities are not certified as original sources.

## Validation and next gate

Eighteen focused tests passed: score arithmetic/missingness, optional-context independence, pseudo-label separation, invalid masks, TEST denial, lazy GEE composition, review intake and unchanged strict admission. Publication/privacy audit passed for staged safe changes. Original CSVs, frozen blocks/buffers, historical results and checkpoints remain unchanged.

Next research step: independently document the five reviewed leads and explicit non-mining controls with paired dated imagery/survey evidence, source rights, conservative polygons,<=30mpositional suitability, confirmed independent reviewers and adjudication. Use TRAIN only for any future calibration; keep held-out groups sealed. Shared-Sentinel review agreement(kappa0.2564) is neither mining accuracy nor independent validation. A fresh GEE pilot is unnecessary while registered caches suffice; any later acquisition must have a separately frozen quota/geometry plan using existing metered locks, with no unrestricted large-area calls. No supervised training or broader phase is authorized here.
