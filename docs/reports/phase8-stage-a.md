# Phase 8 Stage A — React Overview

The separate Vite frontend implements the application bar, navigation rail, Overview summary, map context and coverage table from Figma frame 2:2. The workspace drawer frame 4:1928 informed compact navigation. The other frames were catalogued from page 0:1. The design uses Inter, a 64 px bar and rail, slate panels, teal accents and an amber research-preview status.

The Figma map asset and overlay shapes are illustrative and stay local. The app uses actual raw Phase 1 archive counts, six Phase 6B tile footprints, Day 1 common-valid counts, and the Phase 4A station total. Figma sample candidate rows and counts were replaced with the verified tile coverage table. The season selector changes the archive count window. District selection and text search filter the table. Geographic coordinate search, workspace export and the other research pages await later stages.

From the project root, use the existing Python environment to generate the read-only aggregate snapshot.

```powershell
python -B scripts/phase8_overview_data.py
cd frontend
npm ci
npm run check
npm run build
npm run dev
```

To show the design map, copy the locally retained Figma landscape and four overlay SVGs from the ignored Stage A output folder into the frontend's ignored public/local folder before building. Missing local assets are handled in the Overview. No backend or external runtime data service is required. Keep the populated local public folder and any builds containing it private.

The production Overview was captured in Edge at desktop widths 1440 and 1280. Comparison against the Figma frame retained the shell, panel arrangement and map graphics while substituting real metrics. The 12 existing Python dashboard and tile tests and the TypeScript production build passed.
