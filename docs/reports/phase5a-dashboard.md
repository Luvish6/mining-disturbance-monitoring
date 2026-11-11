# Phase 5A — Offline research dashboard prototype

Run the app from the existing checkout using its virtual environment. Install the optional dashboard dependency once if needed. Subsequent starts use local artifacts and do not initialize Earth Engine or request basemap tiles.

```powershell
python -m pip install -r scripts/requirements-dashboard.txt
python -B -m streamlit run scripts/research_dashboard.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501 in a browser. The app reads the checkout's outputs directory by default. Set RESEARCH_DASHBOARD_OUTPUTS to another local outputs directory when needed.

| Page | Local products and interpretation |
| --- | --- |
| Satellite change | Uses the existing Phase 3G layer manifest and PNG renders. The app selects layers and magnifies the validated pixel grid using nearest-neighbour display. Legends, season ranges, validity and observation-count summaries come from the original output. [Phase 3G](phase3g-visualization.md) |
| River observations | Uses the Phase 4A receipt for all four stations, including per-granule UTC timestamps and valid, water and interior counts. Filters apply only to the displayed table. The summary preserves the original distinct-date totals. [Phase 4A](phase4a-river-feasibility.md) |
| Leshka feasibility | Uses the Phase 4B fixed-footprint map, matched-date and native-cell support diagnostics, exclusion table and daily coverage/rainfall ledger. The app does not display the diagnostic reflectance columns or a seasonal spectral contrast. [Phase 4B](phase4b-leshka-spectral-pilot.md) |
| Provenance & limits | Shows collections, acquisition dates, source resolutions and processing settings from local receipts, along with interpretation limits and receipt locations. |

Validation status is visible on every page. The project has no admitted real positive or negative mining labels, no trained real mining classifier or held-out accuracy, and no validated river degradation or causal attribution. Heuristic masks are explicitly identified. Synthetic fixtures only exercise software behavior in the test suite.

Missing files display a local recovery path and the existing reproduction command. Restore archived products or reproduce separately in a new output directory. The local Phase 4B verifier rebuilds its daily availability ledger. Reproduction may require Earth Engine access, but the dashboard startup and interactions do not.

Only the app, optional dependency specification, tests and documentation are published. Local images, receipts and screenshots remain ignored. The app performs no mining training, new scientific estimation or modification of research partitions and admission gates.

## Verification

Streamlit 1.67.0 ran on loopback using the real local products. Headless Edge rendered all four pages and requested only loopback resources. All 106 pytest tests passed, including three dashboard tests covering loading, missing data, navigation and scientific guardrails. Synthetic fixtures exercised software behavior only.
