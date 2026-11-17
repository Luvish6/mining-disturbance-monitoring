# Phase 22B — Maus v2 static pilot readiness

**CONDITIONAL. Training is NO-GO.** The 2019 static footprint design and spatial roster are frozen for review and QA. The selected validation window passed fused-input QA. The selected TRAIN window had no qualifying descending dual-polarization radar scenes. Independent dated reference imagery, two independent review decisions and positive/background support are missing. No model was fitted and no TEST imagery, labels or metrics were accessed.

## Frozen geography

Authentication reused the Phase 22A PANGAEA SHA-256 and the pinned geoBoundaries ADM1 release. The boundary file SHA-256 is `4c63fe43294a391e8f2de4e9f86f3edb60f8688275b9fee90c61fb2aa0c26061`. The local split SHA-256 is `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`.

| Assignment | Groups | Maus candidates | Development windows | Admitted positive / negative |
|---|---:|---:|---:|---:|
| TRAIN | 244 | 675 | 16 | 0 / 0 |
| Validation (Odisha) | 45 | 200 | 8 | 0 / 0 |
| Sealed TEST (Jharkhand) | 53 | 231 | 0 | Sealed |
| Excluded | 13 | 98 | 0 | Ineligible |

The 16 TRAIN windows span 16 states. The nearest two selected development windows are approximately 15.0 km apart in the grouping projection. Windows were screened against any other group, including excluded and TEST candidate footprints. State and 2 km edge grouping limit spatial leakage; independently verified mine-complex identity remains outstanding. A draft roster exposed a diacritic mismatch in the publisher Jharkhand spelling. The final generator normalizes state names and refuses an empty required partition. The draft did not reach satellite export and is excluded from the pilot.

The ignored local directory `outputs/phase22b_maus_frozen/` holds `split.json`, `development.json`, `sealed_test.json` (group and source IDs only), `development_overlay.geojson` (locator outlines) and `review.csv`. The CSV has 72 blank interpretation rows, covering interiors, boundaries and hard-negative searches at each site. Image/date/rights fields await independent evidence. The source polygons are historical locators. Their interiors, boundaries and unlabeled surroundings are ineligible as training masks until review supplies verified polygons. [Phase 22A provenance and license](phase22a-indian-label-feasibility.md)

## Bounded Earth Engine QA

| Window | S2 scenes joined to cloud probability | S1 scenes in selected orbit | Common valid cells |
|---|---:|---:|---:|
| TRAIN | 36 | 0, no eligible orbit | Unmeasured, export withheld |
| Validation | 34 | 7, descending orbit 121 | 4,096 / 4,096 |

The validation GeoTIFF passed the 64 × 64 EPSG:32645, 30 m affine, band order, NoData and count/validity checks. Optical counts were 2–31 per cell and radar counts were 7 per cell. Earth Engine returned unnamed TIFF bands. The exporter verified graph order before delivery, then assigned band descriptions and NoData locally. Raw and final pixel arrays agreed exactly. Two validation responses of 80,643 bytes each included the band-metadata retry and had the same raw SHA-256. The cached QA receipt contains ordered scene IDs and acquisition times, CRS, affine and raw, normalized-container and preview hashes. The optical false-colour overlay uses B4/B8/B3 at a common 0–0.30 stretch and shows the historical candidate edge in amber. Its 1,624 rasterized locator cells check rendering in the common grid and do not certify ground-truth alignment. Radar VV/VH units are dB according to the collection documentation and existing power-domain smoothing implementation. [S1 GRD catalog](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD) · [S2 harmonized SR catalog](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)

Reproduce from the repository root with the existing Python environment. Freeze requires a fresh local target directory. QA verifies existing receipts and hashes before reusing cached outputs.

```powershell
python -B -m scripts.phase22b_maus freeze
python -B -m scripts.phase22b_maus qa
python -B -m pytest -q -p no:cacheprovider tests/test_phase22b_maus.py
```

## Diagnostic deferred until admission

Use the first hash-ordered admitted TRAIN patch containing both classes under a shared validity mask. On that single patch only, use seed 42 and the preregistered U-Net/Adam settings. Run at most 20 repeated optimizer steps and record initial and final masked BCE, finite logits and gradients, foreground-pixel count and foreground/background scores. The diagnostic passes the engineering gate if array shapes agree, loss and gradients remain finite and final loss is below initial loss. Discard diagnostic weights. The threshold and all validation settings remain untouched.

The next gate requires a prespecified TRAIN-only coverage amendment or a supported optical-only design, independently dated imagery and clear reuse rights for the planned review windows, and both classes with suitable position and valid sensor support across multiple development groups. Do not interpret the single validation QA result as experiment-wide coverage. The existing Indian temporal training decision remains NO-GO.
