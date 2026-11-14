# Phase 8 Stage C — River Intelligence and Leshka Feasibility

The River Intelligence workspace follows Figma frame 4:181. The Leshka subview uses the same station catalog, evidence area and assessment panel. The geographic view uses projected CPCB points and original Phase 4A screening extents. The illustrative Figma reach, basemap and width profile were replaced by the verified station locations and observation counts. Dated reach previews show the saved HydroSHEDS corridor context when available. Full catchment geometry and flow direction remain unverified.

From the project root, using the existing Python environment and saved Phase 4 outputs:

```text
python -B -m scripts.phase8_river_data
npm --prefix frontend run build
npm --prefix frontend run preview -- --host 127.0.0.1
```

Open #rivers or #rivers-leshka. The adapter validates the station windows against their original georeferenced rasters, recounts distinct UTC dates from the granule records, and checks the Phase 4B geometry and matched dates against the receipts and observation ledgers. It serves ignored local products without Earth Engine access. Keep the populated frontend/public/local directory and any build containing it private.

All four stations expose both seasonal windows, water and interior screening, dated granule diagnostics and provenance. Leshka has five pairs across three calendar months, with 12 common 10 m cells against the 25-cell minimum and no whole native 20 m SCL/B11 footprint inside the common mask. Individual relative spectral indicators remain available as diagnostics. The seasonal contrast stays withheld. Antecedent rainfall describes the coarse CHIRPS station cell. Regulation, hydrology and water quality remain unresolved.

Browser checks covered all four stations, both seasons, 40 date-count assertions, map selection, evidence panels, the Leshka gate, missing data, responsive layouts and Overview/Explorer regressions. Real screenshots stay under the ignored outputs/phase8_stage_c directory.
