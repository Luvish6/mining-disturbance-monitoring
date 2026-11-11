"""Schema 2 preparation and verification for bounded, non-overlapping raster sources."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import math
import shutil

from pyproj import Transformer
import rasterio
from shapely import transform
from shapely.geometry import box, shape

from config.settings import AFTER, BEFORE
from .admission import validate_real_manifest
from .annotation import boundary_geometry
from .data import BANDS, BAND_UNITS, digest, save_json, tile_patches
from .labels import load_labels
from .spatial import block_for, partition

CRS = 'EPSG:32646'
SETTINGS = (5000, 120, 42)
PARTITIONS = ('train', 'validation', 'test')
MAX_PIXELS = 4_000_000
MAX_TILES = 64


def settings(patch_size, block_m, buffer_m, seed, synthetic, max_pixels):
    if type(patch_size) is not int or patch_size < 8 or patch_size % 4:
        raise ValueError('patch_size must be a multiple of 4, at least 8')
    if type(max_pixels) is not int or not 0 < max_pixels <= MAX_PIXELS:
        raise ValueError('Invalid total source pixel budget')
    if not synthetic and (block_m, buffer_m, seed) != SETTINGS:
        raise ValueError('Real datasets require frozen block/buffer/seed settings')
    block_for((1, 1, 2, 2), block_m, buffer_m)


def inspect_sources(rasters, synthetic=False, max_pixels=MAX_PIXELS, registered=True):
    """Read-only grid/schema inspection. Structural checks never admit real evidence."""
    paths = sorted(Path(raster).resolve(strict=True) for raster in rasters)
    if not 1 <= len(paths) <= MAX_TILES or len(set(paths)) != len(paths):
        raise ValueError('Expected unique source paths within the tile limit')
    sources, total = [], 0
    for path in paths:
        with rasterio.open(path) as src:
            affine = src.transform
            if (src.crs is None or src.crs.to_epsg() != 32646
                    or (affine.a, affine.b, affine.d, affine.e) != (30, 0, 0, -30)
                    or any(not math.isfinite(v) or v % 30 for v in (affine.c, affine.f))):
                raise ValueError('Expected EPSG:32646 and a north-up global 30 m lattice')
            if src.descriptions != BANDS:
                raise ValueError('Exact feature band order required')
            if any(dtype != 'float32' for dtype in src.dtypes) or src.nodata != -9999:
                raise ValueError('Expected float32 and explicit NoData -9999')
            if any(actual is not None and actual != expected
                   for actual, expected in zip(src.units, BAND_UNITS)):
                raise ValueError('Inconsistent feature band units')
            if registered and not synthetic and src.units != BAND_UNITS:
                raise ValueError('Explicit registered feature band units required')
            tags = src.tags()
            if tags.get('data_kind') != ('synthetic' if synthetic else 'real'):
                raise ValueError('Source real/synthetic identity mismatch')
            total += src.width * src.height
            if total > max_pixels:
                raise ValueError('Total source pixels exceed bounded experiment budget')
            bounds = list(src.bounds)
            sha = digest(path)
            if any(sha == row['sha256'] or box(*bounds).intersection(box(*row['bounds'])).area > 0
                   for row in sources):
                raise ValueError('Duplicate or spatially overlapping raster sources')
            sources.append(dict(tile_id=f'tile_{sha}', path=str(path), sha256=sha,
                                crs=CRS, transform=list(affine)[:6], bounds=bounds,
                                width=src.width, height=src.height, nodata=src.nodata,
                                units=list(src.units), metadata=tags))
    return sorted(sources, key=lambda row: row['tile_id'])


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def real_evidence(boundary, coverage):
    if boundary is None or coverage is None:
        raise ValueError('Real ingestion requires original district and successful coverage evidence')
    document = read_json(boundary)
    boundary_geometry(document)
    districts = [shape(feature['geometry']) for feature in document['features']]
    project = Transformer.from_crs(4326, CRS, always_xy=True).transform
    districts = [transform(geom, project, interleaved=False) for geom in districts]
    report = read_json(coverage)
    if (report.get('status') != 'district_coverage_passed'
            or report.get('district_coverage_checked') is not True
            or report.get('district_coverage', {}).get('coverage_gate_passed') is not True
            or report.get('seasons') != [vars(BEFORE), vars(AFTER)]):
        raise ValueError('Successful matching seasonal district coverage required')
    return districts, report


def reference_shapes(refs, block_m, buffer_m, seed, synthetic, districts):
    project = Transformer.from_crs(4326, CRS, always_xy=True).transform
    shapes, excluded, groups = [], [], {}
    for geom, props in refs:
        if bool(props.get('synthetic', False)) != synthetic:
            raise ValueError('Synthetic label provenance must match dataset mode')
        projected = transform(geom, project, interleaved=False)
        if not synthetic and sum(district.covers(projected) for district in districts) != 1:
            raise ValueError('Reference polygon must be contained in one original GAUL district')
        group = props.get('evidence_group_id', props['label_id'] if synthetic else None)
        if not isinstance(group, str) or not group.strip():
            raise ValueError('Independent evidence_group_id is required')
        block = block_for(projected.bounds, block_m, buffer_m)
        if block is None:
            excluded.append(props['label_id'])
            continue
        split = partition(block, seed)
        site = props.get('site_id') or props.get('candidate_id')
        keys = [('group', group.strip().casefold())]
        if isinstance(site, str) and site.strip():
            keys.append(('site', site.strip().casefold()))
        if any(groups.setdefault(key, split) != split for key in keys):
            raise ValueError('Independent evidence group or site crosses frozen partitions')
        shapes.append((projected, props['label']))
    if not shapes:
        raise ValueError('No reference polygons remain inside buffered blocks')
    return shapes, excluded


def build(root, sources, patch_size, block_m, buffer_m, seed, synthetic, max_pixels, writing):
    refs = load_labels(root / 'references.geojson')
    provenance = [props for _, props in refs]
    districts, coverage = ([], None) if synthetic else real_evidence(
        root / 'districts.geojson', root / 'coverage.json')
    shapes, excluded = reference_shapes(refs, block_m, buffer_m, seed, synthetic, districts)
    records, counts = [], {s: [0, 0] for s in PARTITIONS}
    quality = dict(excluded_label_ids=excluded, unlabeled_pixels=0, invalid_labeled_pixels=0,
                   excluded_patch_labeled_pixels=0, edge_labeled_pixels=0)
    coverage_hash = None if synthetic else digest(root / 'coverage.json')
    orbit = None
    for source in sources:
        if not synthetic:
            if sum(district.covers(box(*source['bounds'])) for district in districts) != 1:
                raise ValueError('Source tile must be contained in one original GAUL district')
            validate_real_manifest(dict(resolution_m=30, crs=CRS,
                                        label_provenance=provenance, raster_metadata=source['metadata']))
            meta = json.loads(source['metadata']['provenance'])
            if (meta.get('band_order') != list(BANDS) or meta['coverage_report_sha256'] != coverage_hash
                    or meta['relative_orbit'] != coverage.get('metadata', {}).get('selected_relative_orbit')
                    or meta['orbit_pass'] != coverage.get('config', {}).get('orbit_pass')):
                raise ValueError('Registered source provenance differs from coverage or band schema')
            current = (meta['relative_orbit'], meta['orbit_pass'])
            if orbit is not None and current != orbit:
                raise ValueError('Mixed SAR orbit or pass')
            orbit = current
        with rasterio.open(source['path']) as src:
            tile_records, tile_counts, tile_quality = tile_patches(
                src, shapes, patch_size, block_m, buffer_m, seed, root if writing else None,
                source['tile_id'], expected_root=root)
        records.extend(tile_records)
        for split in counts:
            counts[split] = [a + b for a, b in zip(counts[split], tile_counts[split])]
        for key, value in tile_quality.items():
            quality[key] += value
    return dict(schema=2, data_kind='synthetic' if synthetic else 'real', channels=list(BANDS),
                band_units=list(BAND_UNITS), crs=CRS, resolution_m=30, patch_size=patch_size,
                block_m=block_m, buffer_m=buffer_m, seed=seed, max_pixels=max_pixels,
                labels_sha256=digest(root / 'references.geojson'), label_provenance=provenance,
                district_sha256=None if synthetic else digest(root / 'districts.geojson'),
                coverage_sha256=coverage_hash, sources=sources, records=records, counts=counts,
                quality=quality)


def prepare_tiles(rasters, labels, output, patch_size=64, block_m=5000, buffer_m=120,
                  seed=42, synthetic=False, max_pixels=MAX_PIXELS, boundary=None, coverage=None):
    """Create a schema 2 dataset atomically from existing reviewed labels and local sources."""
    settings(patch_size, block_m, buffer_m, seed, synthetic, max_pixels)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Choose a new output directory; datasets are immutable')
    # Preserve the established real/synthetic error at the existing prepare entry point.
    refs = load_labels(labels)
    if any(bool(props.get('synthetic', False)) != synthetic for _, props in refs):
        raise ValueError('Synthetic label provenance must match dataset mode')
    if not synthetic:
        real_evidence(boundary, coverage)
    sources = inspect_sources(rasters, synthetic, max_pixels)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.phase3-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'dataset'
        stage.mkdir()
        shutil.copyfile(labels, stage / 'references.geojson')
        if not synthetic:
            shutil.copyfile(boundary, stage / 'districts.geojson')
            shutil.copyfile(coverage, stage / 'coverage.json')
        manifest = build(stage, sources, patch_size, block_m, buffer_m, seed, synthetic, max_pixels, True)
        if inspect_sources(rasters, synthetic, max_pixels) != sources:
            raise ValueError('Source changed during preparation')
        save_json(stage / 'manifest.json', manifest)
        stage.rename(output)
    return manifest


def verify_manifest(path, manifest, require_splits):
    if manifest.get('data_kind') not in ('synthetic', 'real'):
        raise ValueError('Explicit real/synthetic dataset identity required')
    synthetic = manifest['data_kind'] == 'synthetic'
    controls = [manifest[key] for key in ('patch_size', 'block_m', 'buffer_m', 'seed')]
    budget = manifest['max_pixels']
    settings(*controls, synthetic, budget)
    sources = inspect_sources([source['path'] for source in manifest['sources']], synthetic, budget)
    if sources != manifest['sources']:
        raise ValueError('Source hash, grid or provenance changed')
    reconstructed = build(path.parent, sources, *controls, synthetic, budget, False)
    if reconstructed != manifest:
        raise ValueError('Manifest differs from reconstructed sources, references or patches')
    if require_splits:
        for split in PARTITIONS:
            if not any(row['split'] == split for row in reconstructed['records']):
                raise ValueError(f'No independent {split} patches; acquire more spatial labels')
            if min(reconstructed['counts'][split]) == 0:
                raise ValueError(f'{split} requires both reference classes')
    return manifest
