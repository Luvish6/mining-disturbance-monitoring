# Phase 5C dashboard redesign

Run from the project root with the existing dashboard dependencies installed.

```powershell
$env:STREAMLIT_THEME_PRIMARY_COLOR = '#7cdacf'
python -B -m streamlit run scripts/research_dashboard.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false --theme.base dark
```

Open [the local dashboard](http://127.0.0.1:8501). It reads existing Phase 3G, 4A and 4B products under `outputs/`. See [setup and reproduction commands](phase5a-dashboard.md) for missing products.

| Page | Demonstration |
| --- | --- |
| Overview | Two study districts, saved layer and station counts, seasonal windows and links to the evidence pages. |
| Satellite Change Explorer | The original 23 layer choices, paired previews where both seasons exist, display magnification, legends, validity and observation counts. |
| River Monitoring | Four stations, distinct UTC date totals, a station/season coverage chart and filterable per-granule diagnostics. Missing screened water support leaves river flow unknown. |
| Leshka Feasibility | Five matched date pairs and 12 fixed-footprint cells against the 25-cell pilot minimum. Exclusions and coarse station-cell rainfall remain visible. The seasonal spectral comparison is withheld. |
| Data Quality & Methodology | Collections, dates, processing rules, source resolutions and local receipts. |

The dashboard caches local reads and invalidates the cache when files change. The redesign uses the existing images, receipts and ledgers. No imagery download controls were added because redistribution permissions vary by product. Research validation status appears on every page. See the [Phase 5B integration audit](phase5b-integration-audit.md) for the underlying evidence and outstanding research gates.

Edge checks covered all five pages at 1440 and 1100 pixels using the saved real products. Screenshots stay in the ignored local Phase 5C output directory alongside the Phase 5B baseline captures. The automated suite covers navigation, missing evidence and suppression of unsupported spectral values.
