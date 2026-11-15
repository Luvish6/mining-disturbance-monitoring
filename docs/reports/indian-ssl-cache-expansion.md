# Indian Sentinel SSL observation cache expansion

Four new 64 × 64 Meghalaya windows use the frozen 5 km blocks, 120 m core buffers, seed 42 and original GAUL boundaries. For each of the original train and validation slots, the bounded shortlist took three unused blocks in existing hash order. The selected window maximized the difference in coarse median slope from its existing counterpart among options meeting observation preflight. No change values informed selection.

| Additional block | Use | S1 before/after | S2 before/after | Common-valid cells | Median slope |
| --- | --- | --- | --- | --- | ---: |
| east-85-560 | Development | 13/11 | 52/58 | 4,096/4,096 | 4.95° |
| west-88-568 | Development | 13/11 | 51/57 | 4,096/4,096 | 9.61° |
| east-90-557 | Calibration | 13/11 | 47/57 | 4,094/4,096 | 13.73° |
| west-83-556 | Calibration | 13/11 | 47/57 | 4,096/4,096 | 17.20° |

Combined with saved Phase 6B windows this gives four development and four calibration blocks. The two original Meghalaya test blocks remain untouched. Development and calibration sites are spatially separated and may share wide-swath scenes.

The two held-out 32 × 32 windows reuse their Phase 11C extents and quality controls, with Gevra on orbit 19 and Bhubaneswari on orbit 121 (descending). The full-season inventories matched the saved scene IDs and timestamps. The initial split alternates UTC acquisition days independently within sensor and season and keeps acquisitions from the same day together. Gevra passed. Bhubaneswari's first attempt yielded 669 common replica-intersection cells and one replica below the 70% gate. A single coverage-only retry alternated two-day groups of successive acquisition dates, retaining the previous result. The same cloud, shadow, validity, 90% SAR and 70% common-support rules apply.

| Accepted window | Replica | S1 before/after | S2 before/after | Common-valid cells |
| --- | ---: | --- | --- | ---: |
| Gevra | 1 | 7/6 | 14/14 | 1,018/1,024 |
| Gevra | 2 | 6/5 | 15/12 | 1,024/1,024 |
| Bhubaneswari retry | 1 | 7/6 | 25/28 | 1,015/1,024 |
| Bhubaneswari retry | 2 | 6/6 | 27/28 | 757/1,024 |

The verified paired intersections are **1,018/1,024 (99.4%)** at Gevra and **751/1,024 (73.3%)** at Bhubaneswari. Offline checks found zero shared source IDs between accepted replica groups for S1, S2 SR and the matched cloud products. Each source receipt records dates, grid, orbit and processing settings, with count and optical-validity rasters retaining the effect of the cloud and shadow screening. Per-granule cloud masks remain in Earth Engine through their exact source IDs. The cached products are exploratory.

```powershell
python -B -m scripts.indian_ssl_cache --out outputs/indian_ssl_observation_cache
python -B -m scripts.indian_ssl_cache --retry-bhubaneswari outputs/indian_ssl_observation_cache --out outputs/indian_ssl_bhubaneswari_retry
```

Use new output directories for further runs. The saved verified_cache.json identifies both accepted roots and hashes. **GO for one bounded label-free feasibility pilot only.** Freeze the accepted pair manifests and retain both outer sites for evaluation. Scene disjointness provides a repeatability check, and seasonal timing and shared regional weather still influence both replicas. Two held-out sites provide limited generalization evidence. This phase fit no model and produced no mining labels.
