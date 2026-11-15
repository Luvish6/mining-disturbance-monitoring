# Phase 16A — Regional inference readiness

Gevra's Phase 11C cached Sentinel-1/Sentinel-2 observations use the frozen November–March windows. The cached visual stack includes the 12 temporal and change channels but lacks terrain. One bounded Earth Engine terrain download added SRTM elevation and native-projection slope on the exact cached grid. The canonical output has 1,024 of 1,024 common-valid cells on the 32×32 north-up EPSG:32644 30 m grid. Feature stack preparation validates signed differences, mask equality, exact band order and grid alignment. The receipt records acquisition metadata and the source, terrain, inventory and output hashes. This is input coverage within one tile.

From the project root using the existing environment, choose a new ignored output directory:

```powershell
python -B -m scripts.phase16a_regional --inventory outputs/phase11c_india_discovery/inventory.json --site gevra --output outputs/phase16a_gevra --fetch-terrain
```

Use `--terrain` with the aligned saved terrain GeoTIFF for an offline rerun. The existing Meghalaya training loader, reference admission and frozen spatial assignments remain in place. Regional input preparation does not register a supervised experiment.

The regional mapper reuses existing train-only normalisation and eight-channel Siamese inputs or existing RF ablation order. It writes named Phase 14B probability, mask, binary and entropy bands, with the input/model hashes and seasonal window metadata. The mapper uses explicit 64-cell windows by default; Siamese values can depend on tile context. Model execution requires a trusted real admitted project run and approval bound to the region and exact artifact hash. There is no approved Indian checkpoint. The Gevra dry run produced features and receipt only. Synthetic regression used deterministic U-Net weights and an RF interface fixture on a separate synthetic raster. Both reached Phase 14B and remained NOT_VALIDATED. Phase 14B's operational provenance contract currently covers the standalone RF receipt.
