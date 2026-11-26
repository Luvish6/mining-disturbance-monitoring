# Mining-change experiments and evidence limits

## Contribution

The project provides reproducible, provenance-linked Indian Sentinel-1/Sentinel-2 disturbance screening with observation support, a review-only workflow and a parallel downstream river degradation monitoring framework. A site-disjoint RGB benchmark measures the performance and failure modes of two supervised model families. An Indian label-free ablation tests repeatability on scene-disjoint composites. These experiments address different questions and use different outcome measures.

## Supervised RGB benchmark

MineNetCD256 uses paired RGB imagery and independently annotated binary change masks in the [publisher release](https://huggingface.co/datasets/HZDR-FWGEL/MineNetCD256). The original U-Net and RF used 30 patches from six training mines and 15 patches from three validation mines. The expanded balanced RF used 36 training patches from eight mines, with a balanced sample of 100,000 pixels. Its .75 cutoff was selected on 21 patches from five validation mines. The original U-Net and RF used .50. Site IDs follow official train, validation and test assignments. The cropped records lack a verified mapping to georeferenced patch footprints.

| Frozen evaluation | Model | Threshold | Sites / patches | Valid / changed pixels | Precision | Recall | F1 | IoU | FPR |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Initial held-out test | Original Siamese U-Net | .50 | 3 / 15 | 983,040 / 8,238 | .197 | .575 | .293 | .172 | 1.98% |
| Initial held-out test | Original RF | .50 | 3 / 15 | 983,040 / 8,238 | .014 | .828 | .028 | .014 | 48.11% |
| Fresh held-out test | Expanded balanced RF | .75 | 2 / 10 | 655,360 / 50,959 | .449 | .500 | .473 | .310 | 5.18% |
| Label-blind validation audit | Original Siamese U-Net | .50 | 10 / 40 | 2,621,440 / 207,471 | .143 | .078 | .101 | .053 | 4.04% |
| Label-blind validation audit | Expanded balanced RF | .75 | 10 / 40 | 2,621,440 / 207,471 | .102 | .229 | .141 | .076 | 17.28% |

Precision, recall, F1 and IoU refer to the positive change class, and FPR uses actual negative pixels. Brunei_01 supplied all positives in the initial held-out sample. Canada_01 supplied all positives in the fresh sample, which used separate sites and offers no controlled before/after RF improvement estimate. The validation audit sampled four fixed first rows per site. Six sites had zero sampled positives. RGB validation measures a precision/recall tradeoff. U-Net had lower FPR at nine of ten validation mines but low recall. RF reached 54.93% FPR at SouthAfrica_08. Nearby patches can be correlated and these results do not establish full-benchmark or Indian accuracy. The [initial test](minenetcd-heldout-rgb.md), [expanded experiment](minenetcd-validation-expansion.md) and [cross-site audit](minenetcd-representative-validation.md) retain per-site results, confusion matrices, sampling and threshold details.

## Indian exploratory screening and SSL ablation

Phase 15C remains the primary method. Its signed SAR/optical inputs use the frozen Nov 2023–Mar 2024 and Nov 2024–Mar 2025 windows. Under the fixed cross-sensor, support, slope and area rules it retained **three Gevra polygons** from **1,021** eligible cells and **zero Bhubaneswari polygons** from **1,024**. Zero describes the retained count for that window and rules. Mining activity remains unknown. [Phase 15C method](phase15c-unsupervised-screening.md)

SSL is an experimental ablation. Its single fit used before-season VV, VH, NDVI and NDTI in four Meghalaya development blocks. Four separate blocks supplied the latent cutoff by matching Phase 15C exceedance count. Gevra and Bhubaneswari were both excluded from training and calibration. Metrics below use identical masks and two scene-disjoint replicas per site. The recalculated Phase 15C replica scores differ from the full-season run above.

| Held-out Sentinel window | Method | Cells | Replica rank Spearman | Top-5% Jaccard | Candidate Jaccard | Retained area R1 / R2 (m²) | Same-season exceedance before / after |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Gevra | Phase 15C | 1,016 | .523 | .325 | .206 | 10,800 / 26,100 | .98% / 0% |
| Gevra | SSL | 1,016 | .473 | .259 | .380 | 53,100 / 71,100 | .49% / .98% |
| Bhubaneswari | Phase 15C | 751 | .287 | .188 | .000 | 0 / 13,500 | .53% / 1.20% |
| Bhubaneswari | SSL | 751 | .615 | .357 | .265 | 17,100 / 21,600 | .13% / 0% |

These are unsupervised repeatability and workload diagnostics. No ground-truth label enters the comparison. Same-season exceedance is a proxy that can include genuine change. SSL missed its prespecified promotion rule at Gevra and increased review area at both sites. Keep all Indian candidate statuses EXPLORATORY, REVIEW_REQUIRED and UNKNOWN. **Indian supervised validation remains NO-GO; operational alerts remain zero.** [SSL pilot](indian-multisensor-ssl-pilot.md)

## Portal verification

The production build and launch smoke test verified both site snapshots, 14 image responses, before/after and sensor-layer switching, Gevra outlines and the Bhubaneswari zero-count wording. Source hashes and uncertainty remain visible. Both snapshots reported zero operational alerts. The Explorer retains NO-GO for Indian training and NOT VALIDATED for model performance. The linked Brahmani and Leshka views retained their seasonal and feasibility gates.

## Independent evidence required

Request from CMPDI Geomatics and SECL dated actual-work boundaries or independently sourced orthorectified imagery and quality masks covering the **three existing neutral Gevra review windows and separate controls**. Require dates in **1 Nov 2023–31 Mar 2024** and **1 Nov 2024–31 Mar 2025**, native vectors or GeoTIFFs, documented CRS, exact scene/survey identifiers, interpretable and common valid coverage, source lineage, documented positional error **≤30 m** and written research/reviewer rights. For controls, require independently demonstrated unchanged interiors or non-mining change in both windows. For positives, require observed new or expanded mining-related surface disturbance. Lease extents, shared Sentinel sources and screening outputs cannot establish either class.

Send only neutral search windows and admissible evidence to two independent reviewers, with separate forms and without model scores or anomaly outlines. Require agreement on conservative mapped interiors, retain unresolved cases as UNKNOWN, and keep evidence groups intact across frozen spatial splits. A Gevra supervised study needs a separate frozen regional split and registered 14-band coverage before fitting. The [handoff instructions](phase15e-indian-dataset-integration.md) and [admission protocol](../reference/REAL_REFERENCE_PROTOCOL.md) define the operational steps.

## Paper outline and claim boundaries

1. **Introduction.** Explain the need for traceable screening and independent evidence admission. State that mine-specific legality, downstream causality and operational detection are unverified.
2. **Data and methods.** Specify the land-disturbance screen and RGB benchmark splits as one core method and the matched-date downstream river design as the other. Explain the water-support gates, flow routing and rainfall context.
3. **Land-disturbance results.** Report RGB benchmark performance, Indian review leads and SSL repeatability in separate tables.
4. **Downstream river degradation monitoring results.** Present Brahmani matched-date NDTI and contrast the withheld Lukha/Myntdu results. Separate spectral observations, antecedent rainfall and candidate-to-reach linkage. See the [river consolidation](downstream-river-consolidation.md).
5. **Limitations and conclusion.** Discuss site and class concentration, missing crop georeferencing, lack of admitted Indian labels, and spectral and hydrological confounding. Conclude that the prototype produces review leads and uncertainty-aware observations. Validation of Indian accuracy, mining attribution, pollution measurements and deployment requires new evidence.

<!-- MINEMIND_FINAL_RESULTS_V1 -->
## Final MineMind methods and saved-result comparison

The canonical 30 m stack retains registered before/after VV, VH, NDVI and NDTI, their signed differences, elevation and slope. SAR smoothing is performed in linear power before dB compositing. Cloud-probability <40, accepted SCL classes, at least two observations and the existing <=25-degree slope support are retained for comparison; this slope restriction is not a mining-location assumption. Seasons are [2023-11-01,2024-04-01) and [2024-11-01,2025-04-01).

The frozen pointwise 8D encoder learned cross-sensor masked Huber reconstruction using four BEFORE-season TRAIN blocks, with TRAIN median/MAD normalization. Four separate blocks supplied original calibration cutoffs. Sensor-only variants and reliability weighting use the same observed cells. Adaptive weights combine modality availability, count saturation and TRAIN cross-reconstruction/latent-scale statistics; they are not calibrated sensor-quality probabilities. The temporal auxiliary reconstruction attempt retained the original encoder architecture and used TRAIN seasonal pairs only. No follow-up, human review or independent mining labels entered these SSL fits.

One six-state expansion supplied four new reliability-fit regions and two geographic development holdouts, inside previously frozen TRAIN geography. These holdouts were not moved from official TEST. Encoder weights and normalization stayed frozen. A single 0.00723-second reliability fit used 8,191 balanced BEFORE cells across eight TRAIN blocks. All geographic methods selected 41 cells from the same TRAIN sample; historical cutoffs/results were preserved. The original 5 km/120 m design and inherited 2,050 m Maus opposing-group guard remain unchanged.

The table below reports saved values to six decimals; the [machine-readable CSV](minemind-comparison.csv) preserves unrounded values, cutoffs, areas and counts; blank CSV ratios mean undefined, never zero. Comparisons are within cohorts on identical support. Cutoff-dependent areas from different calibration policies are not matched comparisons. No pixel-level significance or mining accuracy is inferred.

| Cohort | Site | Method | Cells | Spearman | Top-5% Jaccard | Candidate Jaccard |
|---|---|---|---:|---:|---:|---:|
| learning_recovery | gevra | frozen_adaptive | 1016 | 0.503554 | 0.416667 | 0.431193 |
| learning_recovery | gevra | temporal_uniform | 1016 | 0.403102 | 0.259259 | 0.000000 |
| learning_recovery | gevra | temporal_adaptive | 1016 | 0.469871 | 0.360000 | 0.382979 |
| learning_recovery | bhubaneswari | frozen_adaptive | 751 | 0.612408 | 0.433962 | 0.544118 |
| learning_recovery | bhubaneswari | temporal_uniform | 751 | 0.473609 | 0.357143 | 0.666667 |
| learning_recovery | bhubaneswari | temporal_adaptive | 751 | 0.527394 | 0.357143 | 0.187500 |
| geographic_development_holdouts | Haryāna | phase15c | 1024 | 0.317725 | 0.094737 | 0.000000 |
| geographic_development_holdouts | Haryāna | frozen_ssl | 1024 | 0.415784 | 0.130435 | 0.126316 |
| geographic_development_holdouts | Haryāna | prior_adaptive | 1024 | 0.452822 | 0.106383 | 0.094937 |
| geographic_development_holdouts | Haryāna | expanded_adaptive | 1024 | 0.465395 | 0.106383 | 0.089385 |
| geographic_development_holdouts | Haryāna | frozen_sar | 1024 | 0.214009 | 0.083333 | 0.000000 |
| geographic_development_holdouts | Haryāna | frozen_optical | 1024 | 0.388983 | 0.118280 | 0.084559 |
| geographic_development_holdouts | Madhya Pradesh | phase15c | 1024 | 0.308709 | 0.142857 | undefined |
| geographic_development_holdouts | Madhya Pradesh | frozen_ssl | 1024 | 0.390610 | 0.368421 | 0.333333 |
| geographic_development_holdouts | Madhya Pradesh | prior_adaptive | 1024 | 0.509702 | 0.424658 | 0.358209 |
| geographic_development_holdouts | Madhya Pradesh | expanded_adaptive | 1024 | 0.533207 | 0.424658 | 0.378378 |
| geographic_development_holdouts | Madhya Pradesh | frozen_sar | 1024 | 0.094879 | 0.094737 | undefined |
| geographic_development_holdouts | Madhya Pradesh | frozen_optical | 1024 | 0.589227 | 0.444444 | 0.445652 |

**Negative findings and decision.** Temporal recovery reduced pretext loss (0.386740 to 0.358242) without consistent repeatability gains. Expanded adaptive ranking improved modestly over prior adaptive on the two new holdouts, but top-5% overlap did not improve; Haryana after-season same-season exceedance increased from 12.890625% to 14.648438%. This proxy is NOT a true false-positive rate. Optical-only was more repeatable than fusion in the Madhya Pradesh window. Missing-sensor rankings remain sensor-dependent. Stop optimization; retain Phase15C as primary and SSL/adaptive variants as ablations. No model was promoted to operational use.

**Geographic/evidence limits.** Both geographic holdouts have historical cropland context. Six acquired AOIs do not provide balanced agriculture/built-up/forest/disturbance coverage: built-up support is limited. WorldCover2021 is historical context, not current reference truth. The source mining-study sampling frame is biased, and only four Meghalaya blocks trained the encoder. Controlled sensor withholding does not validate natural missingness. Reconstruction disagreement may suppress real discordant change. Competing-explanation separation is undefined without independently reviewed class evidence; candidate polygons remain UNKNOWN/REVIEW_REQUIRED. No national generalization, mining legality or causal river attribution is established.

**Other frozen experiments remain separate.** The later preregistered [RGB RF test](phase17g-rf-heldout-results.md) used 60 patches/15 official TEST mines, 3,932,160 pixels/421,918 changed pixels, cutoff0.65: precision0.2374, recall0.2554, F1 0.2461, IoU0.1403, FPR0.0986; confusion [[3164101,346141],[314144,107774]]. The [RGB U-Net recovery](phase17e-unet-recovery.md) was not promoted. These reports are reused, not rescored. RGB benchmark performance cannot validate Indian Sentinel inference. The [2019 static weak-label experiment](phase22h-expanded-training.md) reported U-Net weak-label VAL F1 0.7131+/-0.0848, IoU0.5585+/-0.0989 and FPR0.0838+/-0.0468 across seeds; all VAL groups were in Odisha and model selection reused those weak labels. Static footprint agreement, temporal pseudo-label agreement and unsupervised repeatability are different outcomes; they must not be pooled or ranked as equivalent accuracy.

**River result.** The separate [Brahmani matched-date comparison](downstream-river-consolidation.md) retains16 pairs/five months,93 upstream/75 downstream common cells and seasonal downstream-minus-upstream contrast change -0.08062309711104701 dimensionless NDTI. Leshka12<25 cells remains insufficient. NDTI is not NTU, acidity or contamination; mining-to-reach attribution remains unverified. No river recomputation is needed for this consolidation.

**Reproduction and artifacts.** See [README offline launch](../../README.md#current-offline-minemind-run) and [commands](../REPRODUCIBILITY.md#current-minemind-application-and-saved-result-export). `scripts.minemind_deliverables` verifies saved artifact hashes and exports tables plus a copy of the existing numeric-only geographic comparison figure. The PNG remains private in the output bundle; no satellite pixels or restricted imagery enter the committed CSV/provenance. The [provenance manifest](minemind-comparison-provenance.json) records exact source metric hashes. Models, imagery, scene receipts, full figures and review materials remain local. No new training, acquisition, TEST payload access or experimental tuning was performed for this deliverable.
