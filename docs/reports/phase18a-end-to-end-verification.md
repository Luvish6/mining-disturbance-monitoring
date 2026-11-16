# Phase 18A — Real Indian pipeline verification

## Replayed workflow

The offline replay used the saved Phase 11C Sentinel-1 and Sentinel-2 composites, seasonal observation counts and scene inventory. It rebuilt Phase 16A features from the cache and aligned SRTM terrain. Both 32 × 32, 30 m stacks reproduced all 14 band values, units, masks and grid geometry. The offline preparation writes its own supplied-terrain provenance, so its file bytes need not match the archived preparation. The screen replay used the frozen features and their original input receipts. No Earth Engine request was needed.

| Site | CRS | S1 before/after | S2 before/after | Eligible cells | Cross-sensor cutoff cells | Retained polygons |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Gevra | EPSG:32644 | 13 / 11 | 29 / 26 | 1,021 / 1,024 | 32 | 3 |
| Bhubaneswari | EPSG:32645 | 13 / 12 | 52 / 56 | 1,024 / 1,024 | 4 | 0 |

Both anomaly GeoTIFFs and screening receipts reproduced byte-for-byte, and the GeoJSON contents, polygon geometry and evidence properties matched. Gevra retained projected areas of 3,600, 7,200 and 4,500 m². Every candidate is REVIEW_REQUIRED with UNKNOWN evidence and zero eligible operational observations. The Bhubaneswari zero applies to the retained polygons under the screen. Both portal snapshots report zero operational alerts. The built assets retained CRS, windows, exact scene IDs and dates, counts, and source hashes.

| Output | SHA-256 |
| --- | --- |
| Gevra feature raster, frozen | `a4b79a781c8176c5aaea11b68c6dbe15e6d459fd943db40b2ab91d7e3d68f450` |
| Gevra anomaly | `816fbb2e3baadd7575ae07c03d63a6019a1033b587dcdcd81f70e24c8425d3f6` |
| Gevra screen receipt | `d173b0b3b82170ba0af3896ed7d5e6beb782966a0b25ee31b9a32fe749fa722a` |
| Gevra review GeoJSON | `f6b5148aca94f76fe54296be281e4ed23314de660f6e643a7073d806af7280b5` |
| Bhubaneswari feature raster, frozen | `3bd2e3fb242f6fc2d3d693c5bdf5c90240b6069bbc1e0220c0d36726fcda8a17` |
| Bhubaneswari anomaly | `ed52b5abf933ec96ff5cf3365f48df6d085e2bd42745c7a87d92cbbc34e84370` |
| Bhubaneswari screen receipt | `4961f4212df3336c6b7fb15ef66866d3eaf8a324ab43c0482ee8c60342313490` |
| Bhubaneswari review GeoJSON | `7d09e532fc380630caac6b4b1b5174a7a9f7a308f6544bcb79eefb97b1e12306` |
| Brahmani matched CSV | `de0225dbab204405ab71361658f9cfc5cddd76cf7054d9fe32e69c7024c7dee2` |
| Brahmani upstream 10 m mask | `279707be7721d0c4280bd7c98cfa1120160cfe7746e5c57054adbe794b1c5e9e` |
| Brahmani downstream 10 m mask | `fa5e3edd68a5e5ed900166b83f9a9a8e9f60fe5c3eb8fc4b26765556b46b9433` |
| Meghalaya station CSV | `b31ca02bc3a9e69c8de2491bd93d9d0e7f12480e03ee18ec708b182e1dcfbd8c` |
| Meghalaya daily coverage CSV | `9c20eb047199e6079a79d773a1a5dcbbe0d21f67a0786d8f4f6f4d9568dac6e0` |

Brahmani reproduced 16 matched pairs across five months and both connected EPSG:32645 masks, 93 upstream and 75 downstream cells. Median same-date downstream-minus-upstream NDTI moved from +0.0644323 to −0.0161908 (change −0.0806231). Samal was excluded because its fixed common mask had zero cells. CHIRPS station-cell context was retained. Discharge remains unavailable and mine connectivity UNKNOWN. This is a relative spectral association. The four Meghalaya stations retained insufficient-support decisions. Khaddum, Sunapur and Mihmyntdu lack screened interiors in at least one season. Leshka supplied five matched pairs but only 12 connected cells against the required 25.

## Confirmed fixes and verification

- A failed input rebuild could leave an older portal snapshot visible. Withdraw the affected source snapshot before rebuilding the Phase 15C, Brahmani and Meghalaya views. Rebuild the production assets before serving them.
- The mining adapter previously accepted in-season scene metadata without matching the feature-preparation receipt. Verify the inventory and receipt hashes and the exact scene IDs and UTC timestamps before publishing.
- The Brahmani adapter previously relied on row count and supplied support totals without checking paired date identities or upstream/downstream mask provenance. Check unique same-month pairs, windows, month count, source collection descriptions and the saved Phase 12C receipt, station table and mask hashes. Propagate the verified CRS.
- The real Indian registration interface rejected the external RGB experiment at its required manifest schema and channel gate. The current real reference ledger rejected preparation with zero accepted labels in every split. Neither attempt produced a prediction or supervised dataset.

Twenty-three focused tests passed, including missing/rejected snapshot, date and provenance, registration and alert checks. The React production build and checks against its real saved snapshots passed. Frozen results were preserved. Local replay products and the verification receipt are under ignored `outputs/phase18a_verification/`.

## Remaining evidence and next coding task

Indian supervised training remains NO-GO pending independently dated two-window change and control evidence, admissible positioning and rights, independent review and split support. River attribution still requires study-period outlet and confluence evidence, flow context and field observations.

**Next coding task:** Add an offline preview integrity manifest to the Phase 11C exporter. Bind all six PNG previews per site to their source raster, CRS, affine and render settings. Require those hashes in the Explorer adapter. Existing legacy PNGs were checked for grid dimensions only. Add tests rejecting a wrong-site or swapped-date PNG even when its dimensions match.
