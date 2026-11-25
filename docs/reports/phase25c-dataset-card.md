# Draft dataset card — MineChange-India private pilot v1

**Status:** PRIVATE ENGINEERING PILOT; NOT A PUBLIC DATASET. Mining attribution UNKNOWN. No admitted reference labels. No accuracy claim or training authorization.

## Purpose and scope

Package existing Meghalaya S1/S2 seasonal observations and partial environmental context into a reproducible offline development contract. It is a retrospective exploratory land-change pilot, not a verified mining-change benchmark, legality product, river-impact assessment or India-wide sample.

16 non-overlapping32×32 patches at30m, cropped from four frozen1.92km development AOIs:12 TRAIN patches/three blocks and4 VAL patches/one block. Adjacent patches share source scenes and spatial dependence. TEST is sealed. Sampling reuses the metadata-selected Phase25B roster, without foreground-based selection.

BEFORE `[2023-11-01,2024-04-01)`; AFTER `[2024-11-01,2025-04-01)`. Pseudo-state persistence also uses `[2025-11-01,2026-04-01)` follow-up: retrospective evidence, not an early prediction feature.

## Data and annotation

29 feature slots: paired VV/VH, B2/B3/B4, NDVI/BSI/NDWI; four signed changes; slope/elevation/WorldCover/CHIRPS/JRC; four unsupported context slots (fire, roads, geology, mining context). Native spatial/temporal support varies and is specified in `schema.json`; the common30m grid does not equalize information resolution. VAL lacks acquired elevation/WorldCover/CHIRPS/JRC context.

Three pseudo states:1 potential disturbance;0 potentially stable background;255 uncertain/ignore. Counts:36 /4,837 /11,511 respectively. Shared-sensor rules provide no independent reference truth. VAL contains zero pseudo-disturbance cells. Unknown is not a negative. Human review remains separate and pending; no reviewer decisions were altered.

## Quality and provenance

Georeferenced GeoTIFFs, explicit validity, QA counts, pixel CSVs, immutable manifests and per-patch receipts. Source hashes, global pixel IDs, canonical spatial splits and change arithmetic are validated. Original legacy scene identities/follow-up provenance remain incomplete; reconstructed current-query IDs are not certified original source membership. Georeferencing inherited from the frozen exporter is not independent absolute positional accuracy.

Cloud/shadow residuals, terrain illumination, seasonal vegetation, roads/construction, erosion, coarse contextual sources, missing values, small geographic sample and pseudolabel circularity limit interpretation. Missing JRC or fire support never means absence. No calibrated probabilities, mining precision/recall, causal river effect or operational alerts are supplied.

## Access and rights

Private output location: `outputs/phase25/datasets/25c-v1/`. No imagery, tables, source metadata or geodata is included in Git. Attribution: Copernicus Sentinel, NASA/USGS/JPL SRTM, ESA WorldCover CC-BY4.0, CHIRPS public-domain citation, ECJRC/Google surface water under applicable Copernicus terms. Confirm complete redistribution conditions before any release. No Planet or LISS-IV assets are used. No public dataset license is granted by this draft card.

## Loading and reproduction

```python
from src.phase25.dataset import load_manifest, read_patch
root = 'outputs/phase25/datasets/25c-v1'
manifest = load_manifest(root)
x = read_patch(root, manifest['patches'][0]['patch_id'])
# Explicit exploratory-only opt-in; never independent training truth:
p = read_patch(root, manifest['patches'][0]['patch_id'], allow_pseudo=True)
```

On a fresh output target with the verified original private caches and backup available:

```powershell
python -B -m scripts.phase25c_dataset --backup (Read-Host 'Verified private backup root')
```

Existing output is rejected rather than overwritten. No normalization is fitted and no online fallback exists. This29-band schema must not be passed as a registered14-band model input. Independent interpretation must remain blinded to these pseudo states and rankings.

Next gate: independent source/date/registration/rights evidence, two-reviewer admission, geographically distributed positive and negative support, explicit future acquisition/training/release approval. [Measured results](phase25c-private-pilot.md).
