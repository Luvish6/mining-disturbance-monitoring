# One Indian Sentinel masked-sensor pilot

**NO-GO for replacing Phase 15C.** The single fit used 16,384 before-season pixels from four verified, nonoverlapping development blocks. Four separate frozen calibration blocks supplied thresholds. Gevra and Bhubaneswari were held out from fitting and calibration. The two frozen Meghalaya test rasters were never opened. Roster hashes, feature and QA hashes, projected grid, exact feature order and scene IDs were checked. No accepted Sentinel-1, Sentinel-2 SR or cloud product occurred in both replica groups.

The pointwise encoder takes four standardized features, VV, VH, NDVI and NDTI, plus two mask indicators. It masks one sensor pair at a time and reconstructs the held-out channels through an eight-dimensional bottleneck and a linear head, using Huber loss. Median/MAD scales are learned from before-season development pixels only with Phase 15C floors. Use seed 42, five CPU epochs, two threads, batch 512 and Adam .001. Huber training loss declined from .4281 to .3636. Anomaly scores are L2 distances between after/before embeddings, each averaged across the two masked views.

Calibration matched Phase 15C's 81 threshold exceedances among 14,455 eligible cells across the four calibration blocks, before connected-component filtering. The latent cutoff was .89325 and Phase 15C retained its fixed 2.5/6 cutoff. This calibrates review area and does not make scores probabilities. Both methods use the same common replica support including slope ≤25 degrees, and four-connected components of at least four 30 m cells. Held-out scores recalculate Phase 15C on those same masks. They differ from the full-season screen exported previously.

| Site and method | Eligible cells | Spearman | Top-5% Jaccard | Candidate Jaccard | Replica polygons | Replica area m² | Same-season before / after exceedance |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Gevra Phase 15C | 1,016 | .523 | .325 | .206 | 2 / 3 | 10,800 / 26,100 | .98% / 0% |
| Gevra SSL | 1,016 | .473 | .259 | .380 | 9 / 8 | 53,100 / 71,100 | .49% / .98% |
| Bhubaneswari Phase 15C | 751 | .287 | .188 | 0 | 0 / 1 | 0 / 13,500 | .53% / 1.20% |
| Bhubaneswari SSL | 751 | .615 | .357 | .265 | 3 / 5 | 17,100 / 21,600 | .13% / 0% |

Each overlap is between replicas for the same method. Stable row order breaks ties at the rank cutoff. Constant-score rank correlation and an empty candidate union are undefined. Neither undefined case arose in these runs. The same-season statistic is the fraction above threshold when comparing the two scene-disjoint composites within one season. It can include real short-term change and does not estimate the true false-positive rate.

The promotion rule requires improved Spearman and top-5% overlap without increasing either same-season exceedance at either site. SSL fell short at Gevra and generated more review area at both sites. Retain Phase 15C and seek replication on additional independent held-out regions before reconsidering. The outputs remain EXPLORATORY, REVIEW_REQUIRED and UNKNOWN, with zero operational alerts. No labels, mining accuracy or claims of causality are inferred.

Reproduce offline from the project root using the existing environment and accepted cache. Choose a new output path.

```powershell
python -B -m scripts.indian_ssl_pilot --out outputs/indian_ssl_pilot_v1
```

The ignored output includes the encoder checkpoint, GeoTIFF score and candidate masks, the full statistics and the hash manifest.
