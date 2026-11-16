# Phase 17B — MineNetCD256 multi-shard planning

Run from the project root with the existing Python environment:

```powershell
python -B -m scripts.minenetcd256_planner plan outputs/external_minenetcd256/phase10c.json outputs/external_minenetcd256/phase17b_plan
```

The planner pins the four development shards to the existing release revision, checks every domain row against the saved official split roster and freezes each row by shard, group and group-local index. Seed 42 hashes order publisher domain-name prefixes and sites within each prefix. Prefixes are grouping identifiers without inferred country assignments. Each selected site's rows use equally spaced integer ranks including both endpoints. Primary and fallback retain the same mines and have separate manifest hashes; neither uses cached patch substitutions. The test roster is checked from the saved metadata for disjointness. No test shard is opened.

The real metadata-only run used **142,268 bytes** and verified 47,743 TRAIN rows from 60 mines and 4,613 validation rows from ten. Both choices touch 27 TRAIN and five validation row groups. Each estimates **849,766,808 acquisition bytes**, plus metadata for **849,909,076 total bytes**, above the **536,870,912-byte cap**. Both frozen manifests are **blocked**. Fewer selected rows did not reduce the number of required compressed chunks. The estimates include complete physical chunks (including domain and nested image fields) for selected row groups, plus exact reopened headers and footers, with PyArrow prebuffering disabled. No image or mask chunks were fetched for the plan.

Ignored local outputs are `primary.json`, `fallback.json`, `transfer.json` and `summary.txt` in the planner output directory.

The future acquisition interface accepts only a cap-compliant frozen manifest. The following command refuses the current primary manifest before making network requests. A new selection strategy that reduces row-group coverage would require a separately frozen plan.

```powershell
python -B -m scripts.minenetcd256_planner acquire outputs/external_minenetcd256/phase17b_plan/primary.json outputs/external_minenetcd256/phase17b_acquired
```

No model was fitted. Indian supervised training remains NO-GO.
