# Local end-to-end monitoring demo

From the project root in PowerShell, activate the existing environment. Install the locked frontend dependencies once if they are absent.

```powershell
..\.venv\Scripts\Activate.ps1
npm ci --prefix frontend
python -B -m scripts.phase8_overview_data
python -B -m scripts.phase8_explorer_data
python -B -m scripts.phase8_river_data
python -B -m scripts.phase13_data
python -B -m scripts.prototype_data
npm --prefix frontend run build
python -B -m scripts.phase8_planet_portal
```

Open [the local Explorer](http://127.0.0.1:5188/#explorer). Choose **Indian candidates**, a state and **Gevra** or **Bhubaneswari**, then **Inspect saved site observations**. Switch the observation window and choose Sentinel-2 false colour, Sentinel-1 VV/VH or anomaly score. Gevra exposes three review outlines, their WGS84 centroids and scores. Bhubaneswari retained no polygons under the Phase 15C screen. Both show zero operational alerts. Open the provenance section for individual source timestamps, UTM bounds and hashes. Select **Open Brahmani river indicators** for the existing Phase 12D matched-date NDTI and CHIRPS view. Meghalaya tiles, Leshka and the other portal views remain available.

No live Earth Engine request is made. The local adapter needs the Phase 11C tile and PNGs, Phase 15B source receipt, Phase 15C anomaly and Phase 14B polygon outputs. Rivers use existing Phase 4 and Phase 12D products. Existing authorised Planet data is optional for the separate private review workspace. Keep the populated frontend build and its snapshots local. Python dependencies and Node/npm are required.

Browser smoke testing used the production build and existing loopback portal. Both JSON responses and all 14 image responses loaded. Site and layer switches, polygon detail, dates/provenance, the zero-count wording, the Brahmani link and season selector, and the Leshka gate passed. The screenshot and request checks are private local outputs. The reproducible browser path relies on saved products and surfaces missing site receipts as unavailable.

Indian supervised training remains NO-GO pending independently reviewed dated labels and spatially held-out validation. Phase 15C scores are exploratory. Mine drainage linkage and discharge remain unavailable for the Brahmani comparison.
