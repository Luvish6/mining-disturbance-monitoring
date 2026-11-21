# Phase 24A — India discovery dashboard integration

Overview now opens on **India — Discovery**. The existing Meghalaya view is unchanged and stays available as **Meghalaya — Detailed Study** (`#meghalaya`), via a scope switch in the Overview toolbar.

## What is shown

- The **6 existing Phase 11C leads** (`frontend/public/local/india-candidates.json`, built by `scripts/phase13_data.py`; the same data and coordinates the Explorer already displayed), plotted on a plain lon/lat graticule.
  - No basemap or boundary layer is shown, because none was downloaded.
  - The verified Meghalaya study extent from `geo.json` is drawn as a link to the detailed study.
  - Near-coincident points (Gevra and Kusmunda, about 8 km apart) keep their true positions; only their labels are stacked.
- **Evidence tiers** (`frontend/src/india-data.ts`):

| Tier | Leads | Meaning |
|---|---|---|
| Screened site | 2 (Gevra, Bhubaneswari) | Saved site observations from Phases 15C/16A; still UNKNOWN |
| Unverified lead | 3 | Location from a public environmental-clearance document, plus one seasonal screening summary |
| Meghalaya lead | 1 (R008) | Inside the detailed study state |

- **Counts:** 6 leads, 5 states, 2 screened sites, **0 verified detections**. Unmarked areas are labelled *no analysis*.
- **Links:**
  - each lead opens the Explorer via `#explorer-india/<id>`;
  - screened sites also open their saved site observations via `#explorer-india/<id>/site`;
  - Bhubaneswari links to the existing Brahmani river view (`#rivers-brahmani`);
  - navigation cards lead to the Meghalaya study, the India leads in the Explorer, and the river studies.

## Safeguards

- No Earth Engine calls, downloads, training or new detections.
- No national coverage, accuracy or risk scores are claimed.
- No locations beyond those already in the local Explorer snapshot are shown. Snapshots stay git-ignored and TEST-free.

## Tests

- `tests/frontend_india_data.test.js` (run with `npm test`) checks:
  - tier logic, including that no tier text claims a confirmation;
  - that verified detections are always 0;
  - the graticule projection;
  - the local snapshot: 6 UNKNOWN leads, 2 screened sites.
- `npm run build` passes.
- In the browser: the India view, label stacking, the Gevra site deep link and the unchanged Meghalaya scope all render with no console errors.
