# Phase 22M — Multi-AOI feasibility decision

The requested six-AOI experiment is blocked before preregistration or imagery acquisition. The saved KORPET and Sumon site centers are only about 425 m apart. Exact Phase 22L grid snapping produces overlapping 1.92 km squares. Their shared area is recorded in the [geometry receipt](phase22m-feasibility.json). They cannot be six independent non-overlapping units under the requested design.

Both saved locations are assigned to the frozen Meghalaya TEST partition. Acquiring their temporal imagery would conflict with this task's no-TEST-access instruction. Only existing site locator metadata was inspected. No imagery, labels, predictions or test metrics were opened. No further control selection was performed because it cannot repair the two mandatory overlapping units. Forest and farmland context also require source-backed selection before claims about their role.

The frozen Phase 22H registry requires 128 × 128 input at 10 m, B3/B4/B8, the recorded preprocessing and TRAIN normalization. Phase 22L provides 64 × 64 cells at 30 m, with RGB B4/B3/B2 plus indices. B8 reflectance is absent. Upsampling and inferring B8 would violate that input contract. The requested cross-check is therefore CROSS-CHECK BLOCKED. There are no overlap statistics or U-Net-only areas to report.

No six-AOI centers or boundaries were frozen, and no six-AOI run occurred. No candidate counts, candidate polygons or blinded interpretation rows were fabricated. Candidate counts for each requested AOI are unmeasured. All future candidate records must carry "candidate disturbance, UNKNOWN - not validated." The existing Phase 22L result is preserved and is not a substitute for this run.

A revised task must choose whether KORPET and Sumon are one shared context unit or waive non-overlap for those two and report their dependence. It must also resolve permission to examine existing TEST locations, or replace them explicitly with development locations. A model cross-check requires a separately authorized native-grid export matching the registry and a documented common-grid comparison. Those decisions were not inferred here.

Focused checks verify the two snapped rectangles' overlap and the native input-contract mismatch. Earth Engine requests and imagery transfers were zero. No model fitting, threshold change, split change or dashboard change ran.
