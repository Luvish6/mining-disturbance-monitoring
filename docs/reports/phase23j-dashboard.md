# Phase 23J — Research dashboard completion (React portal)

This work extends the existing **React 19 + Vite + TypeScript** portal in `frontend/`, keeping its Figma-derived dark theme, shell, rail, tokens and the Inter font. No new framework or dependency was added.

## Audit (before changes)

| Area | State found |
|---|---|
| Routes (hash) | Overview, Explorer (India candidate sites), Rivers (station monitoring, Leshka, Brahmani), Review (Planet). The **Quality** and **Reports** rail items were disabled stubs. |
| Data layer | Python adapters (`scripts/phase8_*_data.py`, `phase13_data.py`) write git-ignored JSON snapshots to `frontend/public/local/`, loaded by `useSnapshot`. |
| Missing | Phase 22X–23I results: candidate density, SAR and product corroboration, persistence, sensor ablation, river exposure, human-review status and exports. |

## What was added

- **Data adapter** `scripts/phase23_dashboard_data.py` writes `frontend/public/local/research.json` (git-ignored).
  - It reads **only committed** `docs/reports` artifacts: 22X, 22Y, 22W, 23H and 23I, plus the 23C pH ranges.
  - Each block carries its source file and SHA-256.
  - Coordinate-like keys are stripped. No imagery, blinded-review crosswalk or reviewer answers are included.
  - It makes zero Earth Engine requests.
- **Overview.** Landscape-screening KPIs (Phase 22X) follow the district filter:
  - candidate density with its 95% CI;
  - Sentinel-1 VH agreement (18/18 AOIs);
  - GFC overlap against chance;
  - an explicit *Mining attribution: UNKNOWN* notice.
- **Analytics** (`#analytics`, formerly the disabled "Quality" item):
  - interval charts with real CIs: district density and persistence shares;
  - corroboration facts;
  - a filterable table of the 20 AOIs;
  - the Phase 22W sensor ablation, labelled **External weak-label benchmark — NOT Meghalaya**, with paired-difference CIs.
- **River exposure** (`#rivers-exposure`, linked from the Rivers tabs):
  - D8 connectivity chains (Khaddum → Sunapur, Mihmyntdu → Leshka);
  - the Phase 23H reach table with category and priority badges and a category legend. *River unobservable* and *Unknown* are styled distinctly from any "unchanged" state.
  - The MSPCB pH records sit in a separate panel marked *Not linked to any reach*.
- **Evidence** (`#evidence`, formerly the disabled "Reports" item):
  - methodology and limitations;
  - the human-review panel, showing **PENDING** until 2 reviews are returned, with stratum counts only;
  - aggregate exports (JSON, plus CSV for AOIs, reach priority and ablation);
  - a provenance table with hashes.
- **UI states.** Loading, error (with the adapter command to run) and empty-filter states. Focusable controls, ARIA labels, responsive grids down to phone width, and the footer states *frozen results — not real-time monitoring*.

## Run and build

```powershell
python -B -m scripts.phase23_dashboard_data      # writes frontend/public/local/research.json
cd frontend
npm run dev                                       # http://127.0.0.1:5173/#analytics
npm run build                                     # tsc --noEmit + vite build -> frontend/dist
```

The existing Phase 8 adapters still populate the Overview map, Explorer and Rivers views. See the [Phase 8 release guide](phase8-stage-e1.md).

## Verification

- `tests/test_phase23_dashboard_data.py` checks that:
  - the payload is aggregate-only, with no coordinate keys;
  - every block carries provenance;
  - values match the frozen reports;
  - the review shows PENDING with no answers.
- `npm run build` passes (TypeScript plus Vite).
- In the browser preview, all new routes render with no console errors, at desktop and phone widths.

## Not done / remaining

- The Explorer's satellite imagery is still the existing India candidate-site view. **No Meghalaya per-candidate imagery is published to the dashboard**, because exact candidate geometry stays local by project rule.
- The Overview map is still the Figma illustrative context, not a georeferenced map.
- Human-review results will appear only after both independent reviews are returned and analysed.

## Update — real GIS map and end-to-end audit

**Overview map.** The illustrative Figma picture is replaced by an **offline vector GIS map** (`frontend/src/geomap.tsx`, with pure helpers in `geo-utils.ts`). It keeps the same frame, zoom stack and dark styling.
- **Layers** (`scripts/phase23_dashboard_geo.py` writes `public/local/geo.json`, which is git-ignored, from verified local assets only):
  - GAUL 2025 district polygons, hash-checked against the Phase 6B roster;
  - HydroSHEDS FFR reaches draining at least 25 km², labelled *DEM-modelled*;
  - NDOID main-stem paths between the CPCB station pairs (15 and 19 reaches, *modelled*);
  - the 4 CPCB stations;
  - the 20 Phase 22X sample squares, shaded by fixed candidate-density classes (AOI aggregates only).
- **Controls:**
  - drag to pan, wheel or buttons to zoom about a point, and reset;
  - layer toggles with a legend that separates observed, official and modelled layers;
  - hover and focus tooltips;
  - the district filter fits and dims the map and filters the AOIs.
- **Not shown** (stated on the map): exact candidate locations, surveyed or named river centrelines, catchment polygons and basemap tiles. No external tile requests are made.

**Audit fixes.**
- `overview.json` and `explorer.json` previously included the **two frozen TEST tiles**: their tile IDs and coverage, plus per-pixel change layers and overlap statistics derived from TEST imagery. Both adapters now drop TEST-split tiles.
- The existing snapshot was filtered by its `split` label alone, without reading TEST rasters again.
- The Explorer loader now rejects any snapshot that contains TEST tiles, instead of requiring exactly 6.
- The Analytics rail icon was corrected, and unused map state was removed.
- The layers panel starts collapsed on narrow screens.

**Tests.**
- `npm test` runs the Node built-in test runner (`tests/frontend_geo_utils.test.js`) on `geo-utils` (projection, geometry parsing, zoom anchoring, fit, district filter, density classes).
- `tests/test_phase23_dashboard_geo.py` checks the layers' provenance, chain topology, that there are no TEST or candidate locations, and that the snapshots exclude the TEST tiles.
- `npm run build` passes.
- In the browser, Overview (including the filter, tooltip and layers), Explorer, Rivers, Exposure, Analytics, Evidence and Review all render with no console errors.

**Regenerate.**

```powershell
python -B -m scripts.phase23_dashboard_geo
python -B scripts/phase8_overview_data.py
```
