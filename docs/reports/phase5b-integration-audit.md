# Phase 5B — Integration audit and demonstration readiness

## Verified run

| Check | Result |
| --- | --- |
| Earth Engine and Phase 1 | Existing authentication worked. GAUL 2025 returned East and West Jaintia Hills, 3,818.32 km². Before/after raw counts were Sentinel-1 GRD 52/47, Sentinel-2 SR 178/186 and cloud probability 209/215. These are archive counts. |
| Phase 2 | Existing 300 m smoke window, descending orbit 77 and 30 m grid returned valid support in all six features. Common support was 96.60% in this bounded reduction. District coverage was outside this run. |
| Phase 3G and dashboard | The 27-band GeoTIFF was checked at 32 × 32 cells, 30 m, EPSG:32646. All 23 layer choices and legends plus magnification worked. The saved 960 m tile has 1,024 common-support cells and differs in extent from the Phase 2 smoke window. |
| Phase 4A and dashboard | The eight station-season summary rows and all 24 valid/water/interior filter combinations agreed with the dated granule receipts. Date counts and granule counts remain distinct. |
| Phase 4B and dashboard | Five matched pairs and 12 common cells against a 25-cell floor. Exclusion filtering, the 303-day ledger and station-cell CHIRPS fields loaded. The comparison warning appeared and diagnostic spectral columns remained out of the app. |
| App startup and navigation | The documented localhost command started Streamlit. Edge rendered all four pages with loopback-only requests. Four genuine screenshots were inspected and kept local. Missing/unreadable outputs, recovery commands and scientific wording were exercised with software fixtures. |
| Full automated suite | 106 passed on the final code, including dashboard navigation, missing-file handling and claim guardrails. Synthetic fixtures tested software only. |
| Dependencies and publication | pip check passed. Local Markdown links resolved. No nonignored untracked files were present at baseline. Two checkout files above 10 MiB, the 561.9 MiB source ZIP and 23.5 MiB historical GeoPackage, were ignored. Other source archives reside outside the checkout. The credential filename, planning data and outputs were ignored, and the staged-tree publication audit passed. |

The audit corrected the dashboard magnification label to say “30 m display grid.” It previously called the derived grid native. The README now links to the current dashboard launch instructions. Existing products, thresholds, splits and processing code were preserved.

## Status against the project objectives

| Objective | Completed software | Tested real data or exploratory result | Unvalidated claim or dependency |
| --- | --- | --- | --- |
| Mining-related surface disturbance | Bounded feature preparation, reference admission workflow and RF experiment tooling | Real changes and observation masks displayed. Discovery leads remain UNKNOWN. | No admitted real positives or negatives, trained real classifier or held-out detection performance. |
| Multi-sensor fusion | Common-grid SAR/optical/terrain stack and shared-footprint ablation tooling | Live orbit-77 SAR and masked optical features executed on the smoke tile. | Relative benefit of fusion, district transfer and monsoon performance are unverified. |
| Downstream river investigation | Station-based water/clearance screening, date matching and rainfall context | Four station neighbourhoods inspected. Leshka matched five date pairs but had insufficient common-water support. | No validated spectral trend, degradation, catchment exposure estimate or causal link. |
| Risk visualization | Offline research dashboard with acquisition and validation context | Four real-product pages rendered and were checked against source receipts. | No calibrated risk or confirmed-mining map. |

## Readiness and critical work

The project is ready for a **bounded prototype demonstration** using the saved products. Before the meeting, launch the app from the existing virtual environment, confirm the four pages load with the intended local output folders, and keep the local screenshots available as a fallback. Live Earth Engine can be shown through the saved audit receipts so the demonstration does not depend on network access.

For scientific validation, obtain independently dated, interpretable before/after evidence with documented positional error and independent second review. Populate both classes across the frozen partitions before any real training or held-out ablation. For river interpretation, verify contributing-area geometry and flow/impoundment context, obtain adequate fixed open-water support, and seek synchronous field measurements before calibration or attribution. Keep the [reference protocol](../reference/REAL_REFERENCE_PROTOCOL.md) and [Phase 4 input contract](../reference/PHASE4_INPUT_CONTRACT.md) in force.

See the [supervisor demonstration script](phase5b-supervisor-demo.md) and [dashboard launch instructions](phase5a-dashboard.md). Live receipts, test logs and screenshots are saved locally under the ignored Phase 5B audit output directory.
