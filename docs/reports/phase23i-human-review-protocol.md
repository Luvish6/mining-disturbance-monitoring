# Phase 23I — Independent before/after visual review: protocol, sample and validation plan

This phase starts from `941b535`. It made **zero Earth Engine requests, no downloads and no labels**. Claude performed no review. TEST blocks and tiles are never in the frame. The frozen 22X/22Y/22Z results are unchanged.

**Code and records.**
- Code: `scripts/phase23i_review.py` (`--sample`, `--render`, `--sheet`), tested in `tests/test_phase23i_review.py`.
- Sample design: [phase23i-sample-design.json](phase23i-sample-design.json).
- Manifest: [phase23i-sample-manifest.csv](phase23i-sample-manifest.csv). It lists neutral IDs, strata and weights, with no coordinates.
- Local only, in `outputs/phase23i_review/`:
  - `crosswalk.json`: neutral ID → cluster or cell and position, for the coordinator only;
  - `chips/`: blinded images;
  - `adjudication/`: chips with candidate boundaries;
  - `chip_quality.json`;
  - `review_sheet_A.csv` and `review_sheet_B.csv`;
  - `review_A.html` and `review_B.html`.

## 1. Sample (preregistered: seed `23I`, committed before any review)

**Frame.** The Phase 22X systematic sample: 20 AOIs (17 TRAIN, 3 VAL), each passing the full-footprint TEST guard. It contains the 174 SAR-tested clusters with their Phase 22Y classes. Controls are drawn from the Phase 22X background cells (eligible, more than 60 m from any candidate, land).

**Selection.**
- Order: sha256(seed:key).
- Draws are sequential, rejecting any item **less than 640 m** (one chip width) from an already-selected item in the same AOI, so review sites never overlap.
- The nominal inclusion probability is n_h/N_h. The separation rule makes it approximate.

| Stratum | Design | Frame N_h | Sampled n_h | Rejected for separation | Nominal weight |
|---|---|---|---|---|---|
| PERSISTENT clusters | probability | 53 | 8 | 2 | 6.63 |
| PARTIAL clusters | probability | 77 | 6 | 5 | 12.83 |
| RECOVERING clusters | probability | 44 | 6 | 8 | 7.33 |
| CONTROL (non-detection cells) | probability | 75,618 | 10 | 4 | 7,562 |
| Tier-1 high-priority (22Z) | **purposive** | 14 eligible | **0** | 14 | not used |

**Total: 30 items** (23 TRAIN, 7 VAL).

**Purposive stratum.** It is empty: every remaining Tier-1 cluster lies within 640 m of an already-selected item, which is unavoidable in dense Lumshnong. The rule was **not** relaxed after seeing this. Two Tier-1 clusters are already in the PERSISTENT probability stratum and are tagged in the crosswalk as high-priority examples. Purposive items, if added later, would **never** enter rate estimates.

## 2. Imagery (existing cache, zero requests)

For each item, there is one 5-panel chip of **630 m × 630 m** (21 × 21 cells), north-up, at the identical extent:
- Sentinel-2 true colour (B4/B3/B2) for 2023–24, 2024–25 and 2025–26;
- Sentinel-1 VV for 2023–24 and 2024–25.

**Rendering rules.**
- Every chip uses the same **fixed linear stretch, 0–0.30 reflectance**, with no per-image enhancement and nearest-neighbour display.
- Invalid pixels are shown **mid-grey** and never filled from elsewhere.
- Every item, detected or control, gets an identical **90 m yellow marker**, so detections and controls look the same (blinding).
- The adjudication copy adds the candidate boundaries in cyan and is for the coordinator only.

**Provenance and limits.**
- These are **30 m seasonal median composites**, not single scenes. They come from the Phase 22X and 22Y caches, with ≥ 2 observations per pixel.
- Contributing acquisition timestamps are recorded per AOI in the 22X metadata (e.g. 47/57 joined scenes). Individual scene IDs were not cached, so "exact date and source ID" is available only as composite windows plus timestamp lists.
- Valid-pixel fraction per chip is at least 0.96 in every season (median 1.0).
- **At 30 m, 1–3-cell clusters occupy only a few pixels, so many items will be hard to interpret.**

**Missing imagery: approval needed, not acquired.** The recommended option is **10 m Sentinel-2 chips** for the same 30 extents (64 × 64 pixels, 640 m), with the same seasonal-median graph. Each item is one stack of 3 seasons × 3 bands.

| Option | Earth Engine requests | Data |
|---|---|---|
| **A** (recommended): 10 m seasonal-median chips | about 61 (1 metadata + 30 × URL/download) | about 2.5 MB |
| **B** (optional, in addition): single best-clear-scene chips with exact scene IDs and dates | about 181 (1 + 30 × 3 dates × 2) | about 3 MB |

Both would run under the existing exclusive lock and ledger.

## 3. Human-review instructions and schema

**Reviewers.** Two independent reviewers (A and B), preferably one with remote-sensing or geology expertise. Each gets their own randomized item order (`review_A.html` / `review_B.html`, or the CSV sheets).
- They see only blinded chips and neutral IDs.
- They see no stratum, model score, cluster boundary or the other reviewer's answers.
- No AI-generated labels are used.

**Per item, judge only what is visible inside the marker:**

| Field | Values |
|---|---|
| `visible_disturbance` | YES / NO / UNCERTAIN, comparing 2023–24 with 2024–25 |
| `change_type` | vegetation_removal / exposed_soil / excavation_like / construction / agriculture / other / unclear |
| `image_quality` | GOOD / LIMITED / UNUSABLE |
| `reviewer_confidence` | HIGH / MEDIUM / LOW |
| `mining_attribution` | fixed **UNKNOWN** (no independent documentation) |
| `notes` | optional, free text |

The 2025–26 panel is used only to describe persistence, not to decide `visible_disturbance`.

**Disagreements.** A third person (the adjudicator or supervisor) resolves them using the adjudication chips. The original A and B answers are kept unchanged. The adjudicated label is recorded separately, following the Phase 22J template conventions.

## 4. Validation methodology (for the paper)

1. **Inter-reviewer agreement.** Cohen's κ on `visible_disturbance`, both 3-class and collapsed to YES vs not-YES, with a bootstrap 95% CI over items. Report also the percentage agreement and the confusion matrix.
2. **Visual confirmation rate per probability stratum** = YES / (items with image_quality ≠ UNUSABLE), with a Wilson 95% CI.
   - Report per stratum (PERSISTENT, PARTIAL, RECOVERING).
   - Report a **weighted** detected-cluster rate using the nominal weights, labelled approximate because of the separation rule.
3. **Control disturbance rate** = YES among CONTROL items, with a Wilson CI. This indicates visible change *not* flagged by the rule. It is **not recall**, because a random-cell sample of 10 is far too small to estimate omission over 75,618 cells.
4. **Error categories:**
   - detected but NO: likely commission (haze, shadow, phenology, registration);
   - detected but UNCERTAIN: resolution-limited;
   - control but YES: possible omission or sub-threshold change;
   - UNUSABLE imagery.

   Change-type distributions are reported per stratum.
5. **Not computed:** recall, F1 and overall or mining accuracy. There is no independent reference, and visual change is not mining.
6. **Limitations to state:**
   - 30 m composites, unless option A is approved;
   - optical interpretation cannot separate quarrying from jhum, construction or landslides;
   - reviewer expertise and anchoring;
   - small n, with wide CIs.

## Status

The workflow is ready for reviewers. The 30 m chips exist now, and option A would add the 10 m chips once approved. No review has been performed.
