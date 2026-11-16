# Phase 17C — Transfer-efficient MineNetCD256 acquisition

Phase 17B spread each mine's rows over its whole official row order. Both the primary and fallback touched 27 TRAIN and five validation groups. The pinned Parquet reader needs complete compressed column chunks. Reducing selected rows within those same groups saved no network bytes. A smaller HTTP request can split a chunk for transport, but cannot extract an arbitrary row from the compressed column. Prior caches contain derived decoded records, not reusable verified compressed ranges. The primary selection has no exact row match in the checked paired development and representative validation caches; no prior-cache credit was applied.

The new planner scans only Parquet headers, exact footers and domain columns. It retains as many official validation sites as possible, then up to 20 training sites, maximizing distinct training domain prefixes before minimizing bytes for the fixed site counts. Rows are spread by equidistant rank within each site's selected groups. Seed-42 site ordering supplies the tie preference. This design favors geographically varied site prefixes but clusters crops within fewer physical groups and can favor geographically clustered archive rows. It is a bounded site-disjoint sample, with no claim of uniform geographic or patch coverage. Test shards are excluded.

Both new selections retain 20 TRAIN mines and all 10 validation mines. The primary has 240/80 patches and the fallback 120/40. Both use seven TRAIN and five validation groups and estimate **299,883,038 bytes** including **142,268 metadata bytes**. Selected compressed chunks account for 138,049,437 before RGB, 159,668,260 after RGB, 1,885,047 mask and 1,479 domain bytes. The remaining acquisition bytes cover exact headers and footers. The manifest gives exact per-group ranges and source footer hashes. Raw original source encodings are preserved in provenance hashes. The acquisition decodes original color assets directly and requires lossless binary PNG masks.

Run from the project root with its Python environment:

```powershell
python -B -m scripts.minenetcd256_efficient plan outputs/external_minenetcd256/phase10c.json outputs/external_minenetcd256/phase17c_plan
python -B -m scripts.minenetcd256_efficient acquire outputs/external_minenetcd256/phase17c_plan/primary.json outputs/external_minenetcd256/phase17c_acquired
```

Use a new directory for planning. If acquisition is interrupted, repeat the same acquisition command. The local journal verifies cached ranges by SHA-256 and conservatively charges each attempted network range before requesting it. A failed acquisition has no completed dataset manifest. A later fit must use only a complete, hash-verified cache with adequate positive support in both development splits. Preserve the 100-tree RF and three-channel RGB Siamese baseline settings and keep official test sealed. Indian supervised training remains NO-GO.

## Verified acquisition

Actual transfer was 299,740,770 acquisition bytes and 142,268 metadata bytes, totaling 299,883,038. The independent read-back verified all 320 patch hashes, exact row identities, RGB/mask dimensions, binary values and duplicate checks. No exact RGB pair was repeated and no decoded observation crossed the splits. Spatial overlap within a mine remains unverified without crop geometry.

| Split | Sites with change / total sites | Patches with change / total patches | Changed pixels | Unchanged pixels |
| --- | ---: | ---: | ---: | ---: |
| TRAIN | 18 / 20 | 69 / 240 | 1,538,891 | 14,189,749 |
| Validation | 10 / 10 | 24 / 80 | 535,534 | 4,707,346 |

The completed ignored cache includes the patch manifest, range journal and read-back support receipt. Next implement a manifest-driven offline training entry point for this cache and verify both baselines consume the same frozen validation rows before fitting. Original RGB assets were decoded and saved as arrays without recompression. The Parquet delivery's source encoding determines their original fidelity.
