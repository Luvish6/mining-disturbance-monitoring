# Phase 8 Stage E1 — Local release audit and demonstration

The saved-product demonstration passed on Windows with Python 3.13.2, Node 22.15 and npm 10.9.2. The scientific workflows and model methodology were preserved. The audit used existing Phase 1 inventory, Phase 2 diagnostics, Phase 3G and Phase 6B/7 satellite products, Phase 4 river receipts and private PlanetScope receipts. No Earth Engine request or real model fit was needed. This verifies the offline demonstration and saved evidence.

## Functionality checklist

| Workspace | Verified behavior | Interpretation |
| --- | --- | --- |
| Overview | Saved district inventory, six tile counts, navigation and missing snapshot message | Raw scene inventory and tile support are different denominators. |
| Satellite Change Explorer | All six tiles, four native signed layers, EPSG:32646 bounds, pixel colours and NoData alpha, all three threshold summaries, zoom and pan | SAR in dB, NDVI/NDTI unitless. Low and high render saved spatial patterns. Middle provides statistics only. Patterns are exploratory. |
| River Intelligence | Projected CPCB station selection, all four stations and both seasons, 40 date-count checks, dated quality flags and provenance | Screened water and interior support describe observation availability. Station windows are not catchments. |
| Leshka Feasibility | Five matched date pairs, evidence tables, rainfall context and support gate | 12 common 10 m cells fall below the minimum of 25. The seasonal comparison remains withheld. CHIRPS is coarse station-cell rainfall. |
| Private Reference Review | Verified before/after scenes, synchronized navigation, swipe, native RGB and NDVI layers, common transparency, missing-receipt state | Relative registration evidence and UDM2-clear coverage leave KORPET UNKNOWN. Reviewer-use rights, independent positional controls and first and second reviews are pending. |
| Streamlit | Live navigation through Overview, Satellite Change Explorer, River Monitoring, Leshka Feasibility and Data Quality & Methodology | Saved outputs and published caveats remain available offline. |

The full Python suite passed 147 tests. The existing shifted-mask regression covers the two equivalent affine matrix operations updated to remove deprecation warnings. TypeScript, Vite build, browser checks and the staged publication audit passed. The browser verified narrow React layouts and live Streamlit page navigation. Planet routes rejected missing origin metadata, an incorrect Host and a foreign Origin in the automated HTTP test. Both original archive hashes matched their receipts. A local inspection of all 60 build files found no matching private review products, private route payloads or Planet scene IDs. The Git tree contains no saved imagery. Screenshots and the private integrity receipt remain in the ignored Stage E1 output directory.

## Verified PowerShell launch

From the existing checkout root, with the existing virtual environment active. On this checkout the environment can also be activated from the parent directory using ..\.venv\Scripts\Activate.ps1.

```powershell
# Install locked dependencies once if frontend/node_modules is absent.
npm ci --prefix frontend

# Rebuild the ignored snapshots after a source receipt changes or on first setup.
python -B -m scripts.phase8_overview_data
python -B -m scripts.phase8_explorer_data
python -B -m scripts.phase8_river_data
npm --prefix frontend run build
python -B -m scripts.phase8_planet_portal
```

Open http://127.0.0.1:5188/#overview. The scoped local service prints its address, and reports missing or inconsistent Planet inputs while leaving the other workspaces available. The launch after dependency installation uses local products. Optional Figma Overview assets are described in [Stage A](phase8-stage-a.md). Keep populated builds, the Planet server and screenshots local.

For the existing Streamlit interface, use another terminal with the same activated environment.

```powershell
python -B -m streamlit run scripts/research_dashboard.py --server.address 127.0.0.1 --server.port 8519 --server.headless true --browser.gatherUsageStats false
```

Open http://127.0.0.1:8519/.

## Live demonstration

1. Start on Overview. Explain the districts, seasonal inventory and the six verified feature tiles.
2. Open Explorer. Switch district, tile and signed band. Show NoData and quality counts. Compare the low, middle and high thresholds, and show the middle overlay unavailable message.
3. Open Rivers. Select different stations and compare seasonal screening counts. Open Leshka and show why the 12-cell footprint withheld the seasonal result.
4. On the authorized local machine, open Review. Switch between RGB, NDVI and difference. Point out the date provenance and explain why detectable spectral differences leave KORPET UNKNOWN.
5. Open Streamlit's Data Quality & Methodology page to show the evidence sources and validation boundaries.

## Release decision

The offline research demonstration has no known critical software blocker with the verified local products present. There are no admitted real supervised training labels or held-out accuracy claims. Synthetic tests validate software behavior. A validated mining study still requires independent two-window evidence, reviewed target attribution, documented positional uncertainty and sufficient independent class support in each frozen partition. River degradation and causation remain unverified. NDVI and NDTI are relative spectral indicators rather than field measurements.

Non-blocking follow-ups include a verified contextual basemap and a saved middle-threshold overlay only if a future research task explicitly generates one. The Planet worksheet currently retains notes only for the active browser visit. The offline check does not establish future Earth Engine availability.
