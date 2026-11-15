# Phase 14A — Indian reference acquisition checklist

**NO-GO for real training.** The real annotation ledger exported zero accepted positive and zero accepted negative polygons in each split. Phase 11C contains six UNKNOWN screening leads. No real manifest was generated. The Phase 11A entry point, `python -m src.phase3.india_data`, revalidates ledger decisions before building the registered 14-band dataset. The Siamese U-Net consumes paired temporal observations and validity flags, while the 100-tree RF experiments use signed changes and optional terrain. Both require admitted labels on matching feature pixels.

## Request these files

| Priority | Ask | Evidence to request |
| --- | --- | --- |
| Gevra | CMPDI Geomatics / SECL | Survey-controlled actual-work excavation outlines and source observations for both seasons. |
| Bhubaneswari | CMPDI Geomatics / MCL | Equivalent files, with mine identity and adjacent works distinguished. |
| Nigahi | CMPDI Geomatics / NCL | Equivalent files, with excavation distinguished from spoil and quarry water. |
| Meghalaya controls and change leads | Existing Phase 11B packets and licensed archive | Independently dated image pairs for documented change leads and for stable or independently explained non-mining interiors. Start with R008 for a potential control. |

1. Request original date-stamped actual-work GIS files (GeoPackage or GeoJSON plus CRS) or independent orthorectified before/after GeoTIFFs with native quality masks. Request observation/survey dates and exact scene IDs, acquisition footprints, documented independent positional error at or below 30 m, and written rights for analysis and reviewer access. The dates must fall within 1 Nov 2023–31 Mar 2024 and 1 Nov 2024–31 Mar 2025. Require visible common coverage over each proposed polygon, with ambiguous edges excluded. The CMPDI report year alone cannot establish a capture date. [CMPDI Geomatics](https://www.cmpdi.co.in/en/geomatics-1) · [Bhoonidhi guidance](https://bhoonidhi.nrsc.gov.in/bhoonidhi/htmls/FAQ2.html).
2. Prepare a WGS84 polygon GeoJSON and evidence ledger containing actual dates, independent source URLs or identifiers, provenance, positional quality, rights, interpretation, confidence, group ID and two distinct independent decisions. Use neutral IDs for reviewers and keep Sentinel screening indicators out of their packets. Keep disagreement and unresolved evidence UNKNOWN. Collect both classes across sufficient independent blocks in each split. [Existing protocol](../reference/REAL_REFERENCE_PROTOCOL.md).
3. For a first manifest, use the frozen Meghalaya GAUL boundary, 5 km blocks, 120 m buffered cores, seed 42 and verified coverage receipt. Supply registered north-up EPSG:32646, 30 m, 14-band rasters with valid-data masks, coverage and provenance hashes. Gevra, Bhubaneswari and Nigahi are outside the current study geometry. Keep their evidence separate until a distinct regional boundary, grid and spatial split design are frozen; preserve all Meghalaya assignments. Start with an admission-only dry run and enumerate usable pixels, patches, groups and blocks by class and split before considering fitting.

## Previously identified public datasets

- [Tropical mining panel](https://www.nature.com/articles/s41893-025-01668-9) ([Zenodo DOI](https://doi.org/10.5281/zenodo.17034288)). Annual georeferenced GeoPackage mining predictions, 2016–2024, with separate hand-validated test evidence. Database ODbL, contents DbCL. No verified site-specific independent seasonal pair for these candidates. The existence of a 2024 layer does not establish capture within the after window.
- [Maus et al. v2](https://doi.pangaea.de/10.1594/PANGAEA.942325). WGS84 GeoPackage footprints from a 2019 Sentinel-2 mosaic, CC BY-SA 4.0. Historical location context only.

No new imagery or model fitting was needed for this audit.
