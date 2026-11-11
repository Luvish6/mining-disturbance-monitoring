# Phase 3E — Discovery leads and independent evidence plan

## Live discovery run

The run sampled 123 points across nine existing 5 km buffered cores, three per partition, and selected 27 distinct **UNKNOWN** leads. Each sampled block contributed one joint-change lead, one potential background lead and one lead for investigating alternative disturbance explanations. The latter two sets are separate internal acquisition queues. Low change does not establish stability, and optical/SAR disagreement does not identify a non-mining cause.

| Partition | Frozen blocks sampled | Joint change | Background | Alternative disturbance |
| --- | --- | ---: | ---: | ---: |
| Train | 84:568, 87:558, 92:565 | 3 | 3 | 3 |
| Validation | 80:559, 87:566, 92:556 | 3 | 3 | 3 |
| Test | 80:557, 86:568, 88:554 | 3 | 3 | 3 |

The workflow checks original district containment for a 300 m planning neighbourhood around each point, checks the existing 120 m buffer and seed-42 partition, and spreads the three selected cores within each split by distance. The neighbourhood is a location check. Feature values and observation counts are sampled at a single nominal 30 m grid point. No raster export, district-wide ranking, or model inference was needed.

The existing Phase 2 graph supplied descending orbit 77 dVV/dVH and cloud-screened dNDVI/dNDTI for the frozen seasons. Local support required all four finite change values and at least two observations from each sensor in each season. Within each block, the optical ordering used max absolute dNDVI/dNDTI and the radar ordering used max absolute dVV/dVH. The joint lead maximized the smaller of its two ranks, the background lead minimized the sum among remaining sites, and the alternative-disturbance lead maximized optical rank minus radar rank among the remainder. These are acquisition heuristics. The two streams respond to moisture, seasonality, land use, shadow, terrain and geometry. The block quota and relative rankings do not estimate prevalence or provide a representative evaluation sample.

## Immediate and external work

- **KORPET and Sumon Pohduna** can be inspected now using their local two-date Resourcesat pair. They share test block 81:557 and overlapping evidence. March haze and November shadow, product-ID provenance and independent positional evidence remain open. See the [interpretability assessment](phase3c-interpretability-assessment.md).
- **Lumshnong** can enter archive search now using the known application location in validation block 87:556. The existing Resourcesat pair lacks signal there. Seek a replacement pair through independent imagery or dated official records.
- **New Sentinel leads** can enter archive search immediately. The local acquisition queue prioritizes leads by the smaller of the two Landsat QA-pass point counts. QA uses Landsat 8/9 Tier 1 Collection 2 Level 2, QA_PIXEL bits 0–5 unset and QA_RADSAT zero. All 27 new leads had QA-pass observations at the sampled point in both windows. This is a coarse 30 m context check. Suitability at a conservative interior, scene dates and IDs for any selected imagery, and high-resolution availability remain to be established. [USGS QA documentation](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands)

## Independent acquisition checklist

1. Search the actual review coordinates in both windows, **2023-11-01 through 2024-03-31** and **2024-11-01 through 2025-03-31**. Match seasons and lighting where possible. Record exact IDs, capture times, footprint, source lineage and access terms, including negative search results. Product posting or processing dates do not substitute for acquisition.
2. Request authorized archival native PlanetScope scenes and usability masks, or Resourcesat/Cartosat scenes with provider quality and geometric metadata. Inspect local visibility, cloud, shadow, haze, scale, and geometry in both seasons. Prefer individually dated scenes over undated mosaics. [Planet academic access](https://www.planet.com/industries/education-and-research/) · [Planet usable data masks](https://docs.planet.com/data/imagery/udm/) · [Bhoonidhi access and terms](https://bhoonidhi.nrsc.gov.in/bhoonidhi/htmls/FAQ2.html)
3. Where imagery alone cannot identify the cause, seek dated government survey or inspection maps, original georeferenced photos, or dated land-use, agriculture and construction records. Work through available state, district or university routes while IBM requests are pending. A lease, proposed work or contemporary field visit cannot establish a historical change pair.
4. For any proposed reference, retain independent provenance, documented positional error of at most 30 m, conservative interpretable interiors and a second independent review. Keep ambiguous areas UNKNOWN. Check district and buffered-core containment and group shared evidence before any admission. Follow the [real-reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md).
5. Keep screening tables and the internal ID key with the acquisition coordinator. Give interpreters only neutral review IDs, coordinates and independently acquired evidence. Withhold Sentinel feature values, screening categories, thresholds, ranks, partition assignments and model outputs. Keep review results and any future admission in the existing independent workflow.

The local Phase 3E folder holds the live receipt, internal tables by lead type, three existing-location records, a Landsat acquisition queue, and a coordinates-only handoff. No imagery, screen values, candidate coordinates, or third-party source assets are published. The existing labeling workspace and partitions remain unchanged.

## Reproduce the discovery run

Run from the checkout root using the existing virtual environment and an authorized Earth Engine project. Both commands write local-only outputs. The context command defaults to the canonical Phase 3E folder and accepts an explicit alternative directory when using a new run.

```powershell
python -B scripts/screen_phase3e.py --output outputs/phase3e_candidate_discovery
python -B scripts/landsat_phase3e.py --output outputs/phase3e_candidate_discovery
```