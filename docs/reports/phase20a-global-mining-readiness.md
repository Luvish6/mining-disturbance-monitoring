# Phase 20A — Global mining footprint dataset readiness

**NO-GO for fitting on the publisher split.** The archive and imagery route work, and all three development pairs passed structural alignment. The bounded review did not establish usable validation visibility or mine-complex independence. No training, TEST imagery retrieval or TEST label inspection was performed.

## Release and label provenance

Zenodo v1.0.0 declares CC BY-SA 4.0. The 35,577,853-byte archive matched the publisher MD5 `1259ad8045ae648c547ef3db1fccab3b`, passed member CRC checks, and had SHA-256 `c755ee997bfe05bd8fe1f955cea6fade370602b0acc445bc4b3b218980686a16`. It contains the GeoPackage and three documentation images. Imagery is referenced by exact Planetary Computer Sentinel-2 L2A item ID. Only the local ignored workspace contains the download. [Zenodo release](https://zenodo.org/records/14195737) · [Record license metadata](https://zenodo.org/api/records/14195737)

The preferred polygons originate from the Maus or Tang footprint inventories and were manually selected for alignment according to the authors. Rasterization is automatic. The publisher reports separate manual TEST correction, which was not inspected here. Class 1 means inside the preferred mapped footprint and class 0 means outside that annotation on valid imagery. Background does not establish independently verified absence of mining. These are single-date footprint labels. The tiles contain 2024 database timestamps and older sensing IDs. The exact original polygon delineation dates and a pixel-specific reference date were not established, so the database timestamps cannot serve as dates of observed mining change. [Publisher description](https://zenodo.org/records/14195737) · [Publisher rasterization method](https://github.com/SimonJasansky/mine-segmentation/blob/main/src/data/05_persist_pixels_masks.py)

## Development retrieval and alignment

Froze three targets by tile ID and split before inspecting polygon labels: the lowest TRAIN ID, lowest TRAIN ID above 200, and lowest VALIDATION ID. The small sample checks retrieval and alignment, with limited geographic representation. Retrieved only their exact published RGB products, individually windowed from the Planetary Computer L2A assets. Read each 2,048 × 2,048 native 10 m crop on the image CRS, using the publisher's centroid and 10,240 m half-width. Rasterized WGS84 preferred polygons into each actual native image affine using pixel-centre inclusion. Reopened the three pairs and checked dimensions, CRS, affine, encodings and support. The native image areas and raster masks were saved privately alongside RGB overlays and data hashes. Positive RGB signal is a support indicator. It cannot qualify snow, cloud or terrain shadow.

| Tile | Split | Actual acquisition UTC | Paired CRS | Footprint pixels | Background pixels | Visual check |
| --- | --- | --- | --- | ---: | ---: | --- |
| 21 | TRAIN | 2018-09-20 20:41:29.024 | EPSG:32608 | 199,100 | 3,995,204 | Outline includes recognizable workings and darker context. Some adjoining surfaces are uncertain. |
| 201 | TRAIN | 2019-11-13 17:55:59.024 | EPSG:32613 | 171,069 | 4,023,235 | Major pit edges and industrial context broadly coincide. Local attribution remains outside this structural check. |
| 2 | VALIDATION | 2019-04-29 21:00:31.024 | EPSG:32607 | 164,453 | 4,029,851 | Outline follows recognizable valley workings. Extensive bright snow-like cover and deep shadow make scene-wide visibility uncertain. No validity mask was inferred. |

All 12,582,912 sampled cells had positive RGB signal, of which 534,622 (4.25%) are footprint pixels. These counts precede visibility exclusions and are neither certified training inputs nor estimates for the full dataset. Sample raster and mask alignment is structurally verified. Boundary accuracy and actual label completeness were not independently certified. [Publisher Sentinel-2 retrieval code](https://github.com/SimonJasansky/mine-segmentation/blob/main/src/data/get_satellite_images.py)

## Split audit and decision

The GeoPackage has 1,514 tile metadata rows. The released assignment has 890 TRAIN, 201 VALIDATION, 116 TEST and 307 unassigned tiles. The 1,207 assigned IDs are unique. The publication describes 1,210 preferred sites; the difference between that headline and the assigned tile count remains unresolved. A tiles-only positive-area intersection audit found zero cross-split overlaps. **47 exact Sentinel item IDs occur in multiple splits.** That documents repeated acquisition context. Whether any tile pair shares a mining complex remains unknown because the release's tile metadata provides no stable mine-complex grouping key. No TEST labels or pixels were opened for the audit.

**Next action:** Obtain the publisher's tile-to-mine-complex crosswalk and the validity or visibility record for the fixed validation tile, then rerun the split and quality checks without substituting sites or labels. Until both pass, withhold the RF versus single-date U-Net experiment and keep TEST sealed. Indian supervised training remains NO-GO.

The ignored local output directory is `outputs/external_global_mining/phase20a/`. Two focused tests passed for split overlap, shared source scenes, duplicate IDs and malformed metadata.
