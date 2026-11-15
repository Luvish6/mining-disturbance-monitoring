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
