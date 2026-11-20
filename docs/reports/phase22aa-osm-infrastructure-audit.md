# Phase 22AA — OpenStreetMap infrastructure alternative-explanation audit

The preregistration was committed as `4924414` before download ([phase22aa-preregistration.json](phase22aa-preregistration.json)). Results are in [phase22aa-summary.json](phase22aa-summary.json). Code is in `scripts/phase22aa_osm.py` and tests in `tests/test_phase22aa_osm.py`.

**Decision: NO-GO.** Infrastructure explanations cannot be meaningfully assessed with current OSM coverage. All clusters remain **UNKNOWN**.

## Data and provenance

| Item | Value |
|---|---|
| Source | Overpass API (`overpass-api.de`): **1 request**, 723,413 bytes, 329 ways |
| OSM snapshot | `timestamp_osm_base` 2026-11-20T18:27:06Z |
| Query | `highway` and `building` ways, `out geom`, over the 20 guarded Phase 22X AOIs, each expanded by 500 m |
| Licence | **ODbL 1.0, © OpenStreetMap contributors.** Raw data is cached locally in `outputs/phase22aa_osm/` and not published. |
| TEST check | Every WGS84 query envelope was verified outside the TEST buffers (at least about 0.9 km clear) and inside the districts |
| Earth Engine | 0 requests |

## Protocol (fixed in advance)

- **Clusters.** The 174 frozen 22X clusters, with their 22Y classes and 22Z tiers.
- **Distances.** Measured from each cluster polygon (the union of its 30 m cells) to the nearest mapped road and building, right-censored at 500 m.
- **Adjacency.** A cluster is *adjacent* if a road or building lies within 60 m (2 cells).
- **Tests.**
  - Each class against shape-preserving translations within its AOI's background (Phase 22R null, 10,000 draws).
  - PERSISTENT against other classes, permuting labels within AOIs (Phase 22Y).
- **OSM-SPARSE rule.** An AOI is sparse if it has 0 buildings and less than 1 km of road. Results are rerun excluding sparse AOIs and excluding Lumshnong.
- **GO rule.** At least 12 of the 18 cluster-bearing AOIs must be not sparse.

## Results

**Coverage.** The query returned 133 road ways and 196 building ways, but only **3 buildings fall inside the 20 AOIs**. The rest lie in the 500 m margins. **7 of the 18 cluster-bearing AOIs are OSM-SPARSE**, with no mapped road or building at all, so only 11 are usable. That is below the GO threshold of 12, and the building comparison is uninformative everywhere. Mapped road length inside the non-sparse AOIs ranges from 1.0 to 7.1 km.

**Adjacency to mapped roads or buildings (within 60 m).**

Two definitions are reported:
- *Polygon:* cluster-polygon distance ≤ 60 m.
- *Cell-centre:* any cluster cell centre inside the 60 m buffer. This is the definition the translation test uses.

| Class | Adjacent (polygon) | Adjacent share (cell-centre) | Background translation null: median [95% range] | p |
|---|---|---|---|---|
| PERSISTENT | 10 / 53 | 17.0% | 18.9% [9.4, 28.3] | 0.73 |
| PARTIAL | 17 / 77 | 18.2% | 10.4% [5.2, 18.2] | 0.04 |
| RECOVERING | 5 / 44 | 9.1% | 11.4% [2.3, 20.5] | 0.80 |

- **Persistent vs other, within AOIs:** adjacency p = 0.49; minimum distance p = 0.43.
- **Excluding sparse AOIs:** persistent 18.8% against a null of 20.8% (p = 0.73).
- **Excluding Lumshnong:** persistent 20% against 16% (p = 0.78).

**Lumshnong locality (87:556 + 87:557).** 5 of 28 persistent clusters and 5 of 26 other clusters are adjacent to roads. The locality has 9.5 km of mapped road and only **1 mapped building**, despite its cement plants and settlement. That alone shows how incomplete OSM building coverage is here.

**Review tiers.** Adjacency is 1 of 16 for Tier 1, 3 of 13 for Tier 2 and 6 of 24 for Tier 3. Four Tier-1/2 clusters are flagged **INFRASTRUCTURE_ADJACENT**, all on or within 39 m of a mapped road: 87:557/C025 (Tier 1), and 87:556/C017, 88:556/C001 and 89:557/C007 (Tier 2).
- These four should be checked for roads first.
- Tiers are not changed and nothing is relabelled.

## Interpretation

Where roads are mapped, persistent clusters are **not** more road-adjacent than random placements of the same shapes. So *mapped* roads do not explain persistence. Partially recovered clusters lie near roads somewhat more often than chance (p = 0.04, descriptive).

This is weak evidence, because OSM is incomplete:
- buildings are essentially unmapped;
- 7 cluster AOIs have no mapped infrastructure at all;
- unmapped tracks, mine roads, plant yards and settlements are invisible to the test.

**A missing OSM feature does not show that infrastructure is absent.** The infrastructure alternative therefore remains **open**, not rejected.

## What would resolve it

A dated, independent infrastructure layer at 30 m or finer would resolve it, for example:
- Microsoft or Google open building footprints;
- a Bhuvan settlement or road layer;
- the DMR/MBDA survey outputs, which have already been requested.

Re-running this same preregistered test on such a layer would answer the question.
