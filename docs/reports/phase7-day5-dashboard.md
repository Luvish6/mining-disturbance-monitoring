# Day 5 — Monitoring dashboard polish

The existing Streamlit dashboard has a navy/slate header with a teal accent, a study overview drawing metrics from saved receipts, and an evidence navigation sidebar. The satellite page opens on the six-tile results. District, tile, map layer and threshold controls surface saved maps and statistics. Single-band views crop the existing annotated sheet and retain its colour scales. Low and high directional overlays are available. The middle threshold updates the metrics and table and displays the saved sheet with a note about overlay availability. The Jaccard chart uses the full 0–1 scale.

The river page prioritizes station and season selection. All-station summaries and dated granules remain accessible in expandable sections. Leshka shows the withheld-result notice and fixed footprint before the sensitivity and matched-date details. The methodology page keeps source receipts expandable. The app retains the Phase 3G layer controls and reads local files offline. Scientific processing and the separate Planet preflight are unchanged.

Run from the checkout root with the existing virtual environment.

```powershell
$env:STREAMLIT_THEME_PRIMARY_COLOR = '#63c7bb'
python -B -m streamlit run scripts/research_dashboard.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --theme.base dark --client.toolbarMode minimal
```

All five pages rendered in Edge at 1440 × 1200 with loopback-only requests. AppTest exercised all six saved tiles, all Phase 7 layers and cutoffs and all four river stations. The full suite passed with 146 tests and two existing Planet affine deprecation warnings. Desktop screenshots are in the ignored local directory `outputs/phase7_day5_dashboard/` in sidebar order. No screenshots or research products are distributed with the commit.
