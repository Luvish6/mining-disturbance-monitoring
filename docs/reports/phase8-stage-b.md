# Phase 8 Stage B — Satellite Change Explorer

The React Explorer uses the Stage A shell and the Satellite Explorer desktop, compact and map-focus frames (Figma nodes 2:6, 4:1519 and 4:2481). It renders the native north-up tile raster on a plain grid. Geographic context comes from the verified EPSG:32646 bounds and the hovered cell's projected coordinates.

From the project root, with the existing research environment active:

```text
python -B -m scripts.phase8_explorer_data
npm --prefix frontend run build
npm --prefix frontend run preview -- --host 127.0.0.1
```

Open the local preview with #explorer. The adapter verifies the Phase 6B tile source receipts and Phase 7 Day 2 overlap table against the native-grid arrays. It writes ignored local data under frontend/public/local. Run only a local preview of builds containing those products. The application reads a static payload and makes no Earth Engine requests.

The four signed layers retain their original values and common-valid mask. The map clips display colours at ±5 dB or ±0.30 index units. Low and high render the existing directional overlap masks. Middle provides statistics only. Observation-count ranges describe common-valid pixels. KORPET remains UNKNOWN and the patterns are exploratory.

Browser verification covered six tile selections, native bounds, all signed-layer pixels and NoData alpha, every threshold, zoom, pan, visibility, sidebar collapse, narrow layout and return to Overview. Desktop and narrow screenshots remain under the ignored local outputs/phase8_stage_b directory.
