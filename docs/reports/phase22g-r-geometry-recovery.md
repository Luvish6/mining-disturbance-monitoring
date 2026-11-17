# Phase 22G-R — Same-group positive-window geometry recovery

**NO-GO for the 162-slot plan.** Gujarat recovered within its original TRAIN group. Andhra Pradesh, West Bengal and Odisha exhausted the preregistered 10 m lattice-center candidates without a passing positive window. The separate 153-slot proposal passed joint geometry checks. It was not adopted as the Phase 22G acquisition plan.

The [dated amendment](../preregistration-phase22g-r-v1.md) was committed at `7ba0e66ec26aa742d084daaff0c2d29b38844c9e` before relocation. The original rejection receipt, its coordinates and reasons remain intact. The original split stayed byte-identical at SHA-256 `603bcaf9a2aa817dd42d7cdd7a09906c6f8bd80e3bba58da00f8cdf75baebb60`. No group or split was reassigned. The cached 39 patch records were unchanged. TEST imagery and labels stayed sealed. No Earth Engine request, satellite download or fitting occurred.

| Group / role | Interior lattice centers | Excluded by necessary ADM1 center guard | Full-window attempts | Result |
|---|---:|---:|---:|---|
| Andhra Pradesh / TRAIN | 1,931 | 1,931 | 0 | Exhausted |
| Gujarat / TRAIN | 23,848 | 13,110 | 1,790 | Recovered, 6,111 Maus pixel centers |
| West Bengal / TRAIN | 1,448 | 1,448 | 0 | Exhausted |
| Odisha / validation | 4,647 | 4,599 | 48 | Exhausted |

All 1,789 failed full-window attempts before the Gujarat success and all 48 Odisha full-window attempts violated the full footprint plus 2,050 m guard containment. The guard was never relaxed. For a failed group, impossibility applies to the specified same-group, interior, grid-centered search and frozen geometry. It does not establish that no different sampling design could work.

## Joint verification

| Split | Required slots | Passing geometry | Missing slots |
|---|---:|---:|---:|
| TRAIN | 126 | 120 | 6 |
| Validation | 36 | 33 | 3 |

The missing slots are the positive and two background slots in each of the three blocked groups. The remaining 153 slots were checked jointly for unique IDs, full footprints, exact 10 m 128 × 128 grids, 2,050 m state and opposing-group guards, and patch overlap. Proposed background windows excluded all Maus polygons and the frozen project candidate geometries. Group roles were inherited from the frozen roster. Geometry reservations for hard backgrounds carry no verified optical-hardness or scene-validity judgment. Validation remains Odisha-only.

The reduced local proposal is `outputs/phase22g_r_maus/proposed-geometry.json`, SHA-256 `00f87cbbe5f26a5166165582bacff8492f89f928d13750b5f991d01bbcc503ea`. Its 120 TRAIN and 33 validation slots keep complete one-positive/two-background triples. The local `required-slots.json` enumerates all 162 original requirements and their resolution, including explicit missing slots. `recovery.json` retains old/new geometries and rejection counts. Only the sanitized summary is published.

The 162-slot acquisition remains blocked. The reduced plan requires a separate decision before any acquisition. Agreement with Maus v2 annotations would remain weak-label agreement. Twelve focused tests passed.
