# Phase 22K preregistration — 18 November 2026

Agreement with unverified Maus v2 weak labels - NOT independently verified Indian accuracy.

Use the original Phase 22H 153 B3/B4/B8 patches, masks and geographic assignments. Pin split 603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60 and manifest 00f87cbbe5f26a5166165582bacff8492f89f928d13750b5f991d01bbcc503ea. TEST remains sealed. Compute indices on raw reflectance, with valid finite cells and known binary weak masks only. If an index denominator is zero on that support, fail before reporting comparison metrics to avoid silently changing support.

NDVI=(B8-B4)/(B8+B4); NDWI=(B3-B8)/(B3+B8); brightness=(B3+B4+B8)/3. Rule A uses NDVI<t1. Rule B adds brightness>t2. Rule C also requires NDWI<t3. t1 grid is -0.20 through 0.80 at 0.10 steps. t2 grid is 0.02 through 0.30 at 0.02 steps. t3 grid is -0.60 through 0.40 at 0.10 steps. Enumerate ascending grid order, maximize all eligible TRAIN pixel foreground F1 and retain the first combination on an exact tie. No component filtering or normalization. No validation-driven parameter choice.

Freeze all three selected rules before evaluating validation once. Reuse the Phase 22H metric functions and group/state handling. Report TRAIN and validation precision, recall, F1, IoU, FPR, confusion and background-only false positives, including null undefined denominators. Compare descriptively with frozen Phase 22H RF-A/RF-B and U-Net three-seed means/sample SD. No model refitting or TEST evaluation is authorized.
