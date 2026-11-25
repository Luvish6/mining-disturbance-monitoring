# Phase 25 — MineChange-India progress

| Phase | Actual status | Evidence / next gate |
|---|---|---|
| 25A | Complete: focused implementation inventory, verified literature, model/input/rights and hardware feasibility | [Report](reports/phase25a-feasibility.md), [evidence](reports/phase25a-evidence.json); 35 offline tests passed |
| 25B | NOT STARTED | Await approval for cached-only feature and three-state pseudo-label design; acquisition requires separate approval |
| 25C | NOT STARTED | Requires eligible unique patches, source rights, provenance and separate pseudo/reference manifests |
| 25D | NOT STARTED | U-Net/modern comparison requires data and approved isolated TerraMind smoke test; no historical RF deletion |
| 25E | NOT STARTED | Preserve existing portal; analyzer changes await approval |
| 25F | NOT STARTED | No public dataset, DOI reservation or upload authorized |
| 25G | NOT STARTED | Integration after preceding gates; no current result replaced |

Updated 2026-11-25 from baseline 08604dea. No Earth Engine request, image/weight acquisition, research training, TEST payload access or new label in 25A. Pseudo-labels are not independent mining ground truth. Indian verified supervised training remains NO-GO, attribution UNKNOWN and operational alerts zero. Stop at this boundary for approval.

## Mandatory backup gate — VERIFIED 2026-11-25

Stable tag `pre-minechange-india` is pushed at 08604dea. Existing `phase22-label-sources` is preserved; development is isolated on `phase25-minechange-india`. The full private project-parent snapshot passed size, inventory and SHA-256 verification for 72,005 files (7,918,850,848 bytes), zero mismatches. See [rollback instructions](reports/phase25-backup-rollback.md). Separate ignored Phase 25 directories are reserved; 25B is still NOT STARTED. No merge, acquisition or training approval is implied.
