# Phase 8 Stage D — Private reference review

The existing React portal adds a Reference Review view based on Figma frame 4:270. The queue, linked scene panels, evidence register and worksheet show the verified KORPET evidence. The Figma placeholder imagery and sample decisions are replaced by local diagnostic products and pending review status.

Build the frontend, then start the dedicated local server from the project root with the existing Python environment active.

```text
npm --prefix frontend run build
python -B -m scripts.phase8_planet_portal
```

Open http://127.0.0.1:5188/#review. The server binds to numeric loopback and checks the request host and browser same-origin metadata for private routes. Private responses use no-store and same-origin resource policy. It verifies the original archive hashes, extracted asset hashes, native SR/UDM2 grid, quality masks, and statistics receipt before exposing display layers in memory. No Planet assets are copied to Vite public or dist. Keep source files, receipts and screenshots under ignored local directories. Do not proxy or tunnel this local service.

Open the two RGB or NDVI scenes separately, side by side or in swipe mode. Pan and zoom are shared. The NDVI difference uses the verified common-clear footprint. The review worksheet keeps notes in browser memory for the current visit and leaves both reviews pending. KORPET remains UNKNOWN. Independent position controls, Planet reviewer-use documentation and two human assessments remain required. Relative texture matching and visible tonal differences support diagnostic review only.
