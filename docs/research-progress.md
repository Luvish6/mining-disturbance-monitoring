# Research progress

Initial Git baseline prepared **11 November 2026 (Asia/Kolkata)**. Work existed before version control. This records that prior work retrospectively, without reconstructing historical commits. Report dates are evidence of records, not invented phase-completion dates. File timestamps alone do not establish completion.

## Existing work before initial Git setup

| Milestone | Existing implementation/evidence | Limitations |
|---|---|---|
| Phase 1: study area and inventory | main.py, boundary/inventory modules; live check recorded 8 November 2026 confirmed East/West Jaintia Hills, 3,818.32 km² | Original completion date not independently established; inventory counts are not cloud-free coverage |
| Phase 2: SAR/optical preprocessing | Single-pass/orbit Sentinel-1 VV/VH, masked Sentinel-2 NDVI/NDTI changes, SRTM, coverage gates/smoke diagnostics | Radar/cloud/terrain support limitations; not automatic mining detection |
| Phase 3: RF/evaluation preparation | 100-tree RF, 5 km blocks, frozen manifests, admission checks, four-ablation runner and bounded georeferenced inference preparation | Early audit predates later software additions; accepted real labels, actual trained models and real held-out metrics remain unavailable |
| Phase 3A–3B: reference workflow | Independent reference protocol, manual annotation tools and geographically verified KORPET/Sumon/Lumshnong application locations | Applications are not observed disturbed footprints; no admitted seasonal classes |
| Phase 3C: independent imagery access | Provider records/access plans; nine user-transcribed Bhoonidhi after-season leads from a reported 15 | Six IDs unknown, not invented; catalog hits/footprints do not establish valid pixels |
| 19 November 2024 R2 acquisition inspection | Actual pixels: KORPET/Sumon had no signal; nearest KORPET common signal 5.08 km away | Rejected there; original ZIP/local inspection retained |
| 12 November 2024 R2A inspection | KORPET 634/634 and Sumon 1,593/1,593 polygon pixels have signal; Lumshnong zero | Signal is not cloud-free usability |
| 17 March / 12 November 2024 R2A pair | Complete common KORPET/Sumon signal, matched grids and alignment diagnostics; second March catalog rectangle matches raster | First catalog rectangle ~67.8 km displaced at corresponding corners; March low contrast, metadata ID differences, shadows and absolute positional accuracy unresolved |
| Independent reference quality review | Matched false colour, persistent-landmark sensitivity fits, ambiguity notes and uncalibrated DN-ratio diagnostics; reviewer package | No physical NDVI-change inference, confirmed mining disturbance or labels; quality review ready, accepted reference annotation not ready |

## Newly performed for GitHub setup

Inspected uninitialized local Git and confirmed the named public remote had no refs. Prepared protected publication scope, sanitized copies of project-authored documentation/reports, small signal/sensitivity tables, staged publication checks, tracked hooks and AGENTS.md. Original local docs and raw/restricted data are preserved. Scientific findings/code were not made to appear more complete.

Full current suite: **103 collected, 103 passed, 0 failed, 0 skipped (34.32 s)** using the existing environment/isolated temp directory. Synthetic training fixtures ran only as existing tests; no real model training/evaluation. Initial commit uses actual current date/time; push is verified through real remote receipts, not asserted in advance here. No historical commits/backdates are created.

## Phase 3C preliminary visual review

On 11 November 2026, project-supplied screenshot observations for KORPET and Sumon Pohduna were recorded as preliminary and non-independent. Mining-related change remains unconfirmed at both sites. Native-resolution comparison windows were verified against the archived DN bands and retained locally. See the [review record and checklist](reports/phase3c-preliminary-visual-review.md).

The [native-grid interpretability assessment](reports/phase3c-interpretability-assessment.md) found weaker March contrast and local detail, November dark terrain, and patch-dependent relative offsets. KORPET and Sumon Pohduna both remain **NEEDS FURTHER REVIEW**. Heuristic overlays are retained locally. Cloud, shadow and jointly usable fractions remain unknown.

## Phase 3D independent reference evidence

The [provenance reconciliation](reports/phase3d-provenance.md) verified both archive hashes and the second March footprint against the archived raster. Provider product-ID reconciliation remains open. The [evidence inventory and admission assessment](reports/phase3d-reference-evidence.md) found in-window IBM inspections for Lumshnong, but no admissible paired disturbance geometry or stable background reference. The checked application leads occupy one validation block and one shared test block. All remain UNKNOWN.

## Phase 3E candidate discovery

The [discovery and acquisition plan](reports/phase3e-candidate-discovery.md) records 27 UNKNOWN leads from a bounded Sentinel sample, nine per split. All have Landsat QA-pass point context in both windows. Independent high-resolution evidence and reference admission remain pending. Screening outputs are kept local and separate from the independent review workflow.

## Phase 3F archive availability pilot

The [six-site archive pilot](reports/phase3f-archive-pilot.md) found actual Resourcesat signal on both dates at three sites and verified no usable reference-interpretation pair. Public archive search receipts and reviewer imagery are local. Additional authorized scene search and positional documentation remain pending.

The [no-cost public-data follow-up](reports/phase3f-public-data.md) verified two-window Landsat QA context at all six pilot points and found three single-season Wayback metadata leads. No independently verified reference pair was established. Processing and visualization checks can continue without Planet or IBM.

## Phase 3G real satellite visualization

The [bounded Earth Engine visualization](reports/phase3g-visualization.md) verified a 32 × 32 real Sentinel tile, with 23 selectable local layers and common preprocessing support in all 1,024 cells. The viewer has no classifier, reference labels or accuracy results.

## Phase 4A river monitoring feasibility

The [Sentinel-2 river feasibility pilot](reports/phase4a-river-feasibility.md) checked four Lukha/Myntdu station neighbourhoods. Leshka was the only site with repeated screened interior water pixels in both windows. It is a candidate for a separate impoundment-aware spectral pilot. No seasonal river condition or mining association was estimated.

## Phase 4B Leshka spectral pilot

The [fixed-footprint pilot](reports/phase4b-leshka-spectral-pilot.md) matched five date pairs across three months. Only 12 connected 10 m cells were common to every matched date, below the exploratory comparison floor. No seasonal contrast was reported. Local receipts retain dated diagnostics, fixed support and coarse station-cell rainfall.

## Phase 5A local research dashboard

The [Streamlit prototype](reports/phase5a-dashboard.md) integrates the existing Sentinel visualization, river observation support and Leshka feasibility receipts on loopback. Validated mining detection and river degradation findings remain unavailable.

## Phase 5B integration audit

The [integration audit](reports/phase5b-integration-audit.md) reproduced the live Phase 1 inventory and bounded Phase 2 smoke test. The dashboard was checked against Phase 3G and 4A/4B receipts, with genuine local screenshots and a [supervisor walkthrough](reports/phase5b-supervisor-demo.md). The bounded prototype is ready to demonstrate while scientific validation remains pending.

## Blockers and next steps

1. Review March interpretability and November shadows independently; seek clearer/seasonally comparable evidence if needed. Establish documented image/boundary positional uncertainty under the existing <=30 m policy.
2. Verify persistent controls/band-dependent alignment and provider product-ID/footprint provenance. Sensitivity envelopes and numerical subpixel fits are not survey accuracy or confidence intervals.
3. DN products are not calibrated reflectance; resolve calibration/atmospheric/illumination treatment before physical NDVI comparison.
4. Obtain independent dated positive/negative reference evidence with conservative interiors, second review and adequate class/block support in frozen train/validation/test partitions. Do not manufacture labels or random-split pixels.
5. Only after gates pass, train/evaluate real models and ablations, preserve artifacts and verify disturbance-layer valid support. Disturbance-linked river analysis and validated detection reporting remain deferred.

The repository contains source/tests, templates and small original text/tables. Local imagery links in historical reports intentionally refer to excluded artifacts. No third-party imagery/geodata/document redistribution or blanket license is inferred. See [publication audit](publication-audit.md), [reports](reports/README.md) and [prompt archive](development-prompts/README.md).

### Phase 5C dashboard redesign

The [Phase 5C dashboard redesign](reports/phase5c-dashboard-redesign.md) adds a study overview, paired satellite previews and station-level river diagnostics from the existing local products. The Leshka comparison remains withheld under the Phase 4B evidence gate.
