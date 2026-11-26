# Cached Investigation V3.1 scientific sensitivity evaluation

2026-11-26. Descriptive robustness analysis, not mining accuracy. No parameter selection, downloads, GEE, fitting, new labels or TEST payload access. Original observations, labels, dataset manifest and frozen 17 TRAIN / 3 VAL groups remain unchanged.

## Design

All 82 patches (70 TRAIN / 12 VAL), two timing modes, three original weight presets and seven individual weight-zero ablations plus intact baseline: 3,936 patch/configuration cases and 125,952 patch/threshold/component-size cases. Thresholds 20–90 every 10; 4-neighbor minimum components 1/2/4/8 cells (0.09/0.18/0.36/0.72 ha). No connected-component stitching across patch boundaries; cluster counts are patch-local, not independently identified mines.

Ablation zeroes one family weight and renormalizes the remainder. It is **not** input removal: vegetation>=0.25 AND soil>=0.25 prerequisites remain even when those weights are zero. Core sensor validity, >=60% available weight and >=10-point competing margin remain unchanged. Missing evidence remains missing. Weight renormalization can increase scores; reduced candidate area does not imply improved accuracy. Pair-only persistence is absent: its adaptive ablation is a no-op; equal/physical missing-weight removal can affect the coverage gate. Terrain is neutral context, not an exclusion of steep mining.

Each CSV reports supported cells so coverage changes remain visible. Overlap uses full spatial unions; unsupported cells have no candidate and are not certified negatives. No significance tests or independent-pixel claims. Retrospective mode uses 2025–26 follow-up and cannot represent prospective early warning.

## Default-setting results

Threshold60, minimum4 cells.

| Split | Timing | Weighting | Cells | Area ha | Patch-local clusters |
|---|---|---|---:|---:|---:|
|validation|pair|equal|514|46.26|25|
|validation|pair|physical|666|59.94|33|
|validation|pair|adaptive|660|59.40|33|
|validation|retrospective|equal|400|36.00|25|
|validation|retrospective|physical|553|49.77|29|
|validation|retrospective|adaptive|536|48.24|27|
|train|pair|equal|1516|136.44|125|
|train|pair|physical|2029|182.61|166|
|train|pair|adaptive|1981|178.29|163|
|train|retrospective|equal|1008|90.72|80|
|train|retrospective|physical|1657|149.13|128|
|train|retrospective|adaptive|1655|148.95|132|

## Sensitivity and spatial variation

Adaptive pair-only VAL candidates fall from660 to426 cells with soil weight zero (Jaccard0.6355), rise to720 with vegetation weight zero (Jaccard0.8182), and change to662 with geology weight zero (Jaccard0.9970). The spectral prerequisites remain active in every case. Retrospective persistence ablation increases VAL candidates536→659 cells; this is follow-up evidence sensitivity, not a measured detection benefit.

| Timing | VAL minimum cells | Adaptive area ha at60 | Clusters |
|---|---:|---:|---:|
|pair|1|77.67|181|
|pair|2|68.22|76|
|pair|4|59.40|33|
|pair|8|51.84|16|
|retrospective|1|64.62|165|
|retrospective|2|55.08|59|
|retrospective|4|48.24|27|
|retrospective|8|43.65|17|

Adaptive default pair-only TRAIN block candidate counts range0–554 (2/17 zero); VAL45–512 across3 blocks. Retrospective TRAIN0–523 (2/17 zero), VAL42–407. This concentration limits generalization claims; 82 spatially clustered patches are not82 independent sites.

| Timing | VAL overlap comparison at60/min4 | Jaccard |
|---|---|---:|
|pair|equal vs physical|0.771772|
|pair|equal vs adaptive|0.778788|
|pair|physical vs adaptive|0.982063|
|retrospective|equal vs physical|0.723327|
|retrospective|equal vs adaptive|0.746269|
|retrospective|physical vs adaptive|0.969259|

| Timing | VAL weighting | Score median | Score q95 | Supported cells |
|---|---|---:|---:|---:|
|pair|equal|37.500|61.359|12286|
|pair|physical|28.764|68.542|12286|
|pair|adaptive|30.559|68.003|12286|
|retrospective|equal|32.143|57.828|12286|
|retrospective|physical|25.306|63.200|12286|
|retrospective|adaptive|27.352|62.959|12286|

Full TRAIN/VAL score distributions, all threshold/size/ablation combinations, default block variability and preset overlaps are in the adjacent CSVs. Legacy overlap is with the existing shared-source rule, not independent ground truth or the exact historical Phase15C experiment. Physical/adaptive similarity and larger area do not establish superiority.

## Independent evidence and validation

Existing [completed human review](../human-review-integration.md) reports30 matched items,29 complete pairs,10YES/YES but **zero admitted mining positives and zero admitted negatives**. Five disturbance-priority leads do not establish mining attribution. Shared Sentinel source imagery, missing admitted polygon interiors, attribution, positional evidence, independent reviewer authentication/adjudication and rights prevent valid mining precision/recall/F1/accuracy here. NGDR lease/lithology context and weak/pseudo labels are not independent mining-change labels. No accuracy metrics were computed.

Actual frontend calculate function matched Python across3,936 cases at threshold60/min4: identical finite support and candidate masks; maximum per-cell score error2.84e-14. The eight-threshold/four-component sweep is Python; frontend filtering stays its historical four-cell setting.12focused Python tests and16frontend tests passed. Evaluation runtime76.39s (includes integrity/parity/I/O/plotting, not model compute). Figures visually inspected; source publication audit required before commit.

## Outputs and reproduction

Private immutable run: `outputs/phase25/experiments/investigation-evaluation-v1/`. Figures `threshold_comparison.png`, `ablation_comparison.png`; all patch/block tables, hashes and receipt retained privately. Only aggregate numeric tables and source code are committed; no source geodata, imagery, reviewer identities, private geometry or model artifacts. Figures remain private under existing publication policy.

```powershell
python -B -m scripts.investigation_evaluate --output outputs/phase25/experiments/<new-run-directory>
```

The command refuses existing targets, verifies backup and dataset/source hashes and uses the real TypeScript scorer via existing Node. No training, network calls or TEST access. Frozen dataset SHA256: `ce8279c4cab99b9295b2cafa31eff298fea24abeee648eaa64982606403a3106`. Candidate attribution UNKNOWN; operational alerts0.

Next evidence requirement: independent dated mining/non-mining polygon interpretation and unchanged admission gates. Do not optimize weights against these descriptive VAL outputs.
