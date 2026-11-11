"""Aligned, bounded raster ingestion and immutable content-addressed manifests."""
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window, bounds as window_bounds
from rasterio.transform import Affine
from pyproj import Transformer
from shapely import transform
from .labels import load_labels
from .spatial import block_for, partition

TEMPORAL = ('VV', 'VH', 'NDVI', 'NDTI')
FEATURES = ('dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope')
BAND_UNITS = ('dB', 'dB', '1', '1') * 3 + ('m', 'degree')
BANDS = tuple(f'{t}_{b}' for t in ('before', 'after') for b in TEMPORAL) + FEATURES


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def prepare(raster, labels, output, patch_size=64, block_m=5000, buffer_m=120,
            seed=42, synthetic=False, max_pixels=4_000_000, boundary=None, coverage=None):
    """One bounded north-up UTM tile. No resampling or implicit nodata filling.

    Edge/cross-block polygons and patches are excluded. All temporal channels
    plus RF features must be valid for the main common-footprint experiment.
    """
    if not isinstance(patch_size, int) or patch_size < 8 or patch_size % 4:
        raise ValueError('patch_size must be a multiple of 4, at least 8')
    if not synthetic:
        from .multitile import prepare_tiles
        return prepare_tiles([raster], labels, output, patch_size, block_m, buffer_m,
                             seed, synthetic, max_pixels, boundary, coverage)
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new output directory; datasets are immutable')
    refs = load_labels(labels)
    if any(bool(p.get('synthetic', False)) != synthetic for _, p in refs):
        raise ValueError('Synthetic label provenance must match dataset mode')
    with rasterio.open(raster) as ds:
        if ds.crs is None or ds.crs.to_epsg() != 32646:
            raise ValueError('Expected metric EPSG:32646 grid')
        a = ds.transform
        if a.b or a.d or a.a <= 0 or a.e >= 0 or abs(a.a + a.e) > 1e-6:
            raise ValueError('Expected north-up square pixels')
        if ds.count != len(BANDS) or tuple(ds.descriptions) != BANDS:
            raise ValueError(f'Exact band descriptions/order required: {BANDS}')
        if ds.width * ds.height > max_pixels:
            raise ValueError('Tile exceeds bounded initial experiment size')
        if ds.tags().get('data_kind') != ('synthetic' if synthetic else 'real'):
            raise ValueError('Raster must declare data_kind real/synthetic')
        project = Transformer.from_crs('EPSG:4326', ds.crs, always_xy=True).transform
        shapes, excluded_labels = [], []
        for geometry, props in refs:
            projected = transform(geometry, project, interleaved=False)
            if block_for(projected.bounds, block_m, buffer_m) is None:
                excluded_labels.append(props['label_id'])
            else:
                shapes.append((projected, props['label']))
        if not shapes:
            raise ValueError('No reference polygons remain inside buffered blocks')
        output.mkdir(parents=True)
        records, counts, quality = tile_patches(ds, shapes, patch_size, block_m, buffer_m, seed, output)
        quality['excluded_label_ids'] = excluded_labels
        manifest = dict(schema=1, data_kind='synthetic' if synthetic else 'real',
                        raster_sha256=digest(raster), labels_sha256=digest(labels),
                        label_provenance=[props for _, props in refs],
                        raster_metadata=ds.tags(),
                        channels=list(BANDS), crs=str(ds.crs), resolution_m=a.a,
                        patch_size=patch_size, block_m=block_m, buffer_m=buffer_m,
                        seed=seed, counts=counts, quality=quality, records=records)
        save_json(output / 'manifest.json', manifest)
    return manifest


def tile_patches(ds, shapes, patch_size, block_m, buffer_m, seed, output, tile_id=None, expected_root=None):
    a = ds.transform
    target = (rasterize(shapes, out_shape=ds.shape, transform=a, fill=255,
                        dtype='uint8', all_touched=False) if shapes
              else np.full(ds.shape, 255, dtype='uint8'))
    records, counts = [], {s: [0, 0] for s in ('train', 'validation', 'test')}
    quality = dict(unlabeled_pixels=int((target == 255).sum()), invalid_labeled_pixels=0,
                   excluded_patch_labeled_pixels=0, edge_labeled_pixels=0)
    for row in range(0, ds.height, patch_size):
        for col in range(0, ds.width, patch_size):
            y = target[row:row+patch_size, col:col+patch_size]
            if y.shape != (patch_size, patch_size):
                quality['edge_labeled_pixels'] += int((y != 255).sum())
                continue
            if not (y != 255).any():
                continue
            w = Window(col, row, patch_size, patch_size)
            block = block_for(window_bounds(w, a), block_m, buffer_m)
            if block is None:
                quality['excluded_patch_labeled_pixels'] += int((y != 255).sum())
                continue
            x = ds.read(window=w).astype('float32')
            valid = (ds.read_masks(window=w) > 0) & np.isfinite(x)
            if ds.nodata is not None:
                valid &= x != ds.nodata
            common = valid.all(axis=0)
            quality['invalid_labeled_pixels'] += int(((y != 255) & ~common).sum())
            mask = common & (y != 255)
            if not mask.any():
                continue
            split = partition(block, seed)
            name = f'r{row}_c{col}'
            if tile_id:
                name = f'{tile_id}_{name}'
            record = dict(path=f'{name}.npz', split=split, block=block, row=row, col=col,
                          transform=list(ds.window_transform(w))[:6])
            if tile_id:
                record.update(tile_id=tile_id, patch_id=name)
            arrays = dict(before=x[:4], after=x[4:8], features=x[8:], valid=valid, label=y, mask=mask)
            root = expected_root if output is None else output
            if output is None:
                with np.load(root / record['path']) as saved:
                    if set(saved.files) != set(arrays) or any(
                        saved[k].dtype != v.dtype or not np.array_equal(saved[k], v, equal_nan=True)
                        for k, v in arrays.items()
                    ):
                        raise ValueError('Patch values, labels or masks differ from verified sources')
            else:
                np.savez_compressed(root / record['path'], **arrays)
            counts[split] = (np.array(counts[split]) + np.bincount(y[mask], minlength=2)).tolist()
            records.append(dict(record, sha256=digest(root / record['path'])))
    return records, counts, quality


def read_manifest(path, require_splits=False):
    path = Path(path)
    m = json.loads(path.read_text(encoding='utf-8'))
    if m.get('schema') == 2 and m.get('channels') == list(BANDS):
        from .multitile import verify_manifest
        return verify_manifest(path, m, require_splits)
    if m.get('schema') != 1 or m.get('channels') != list(BANDS):
        raise ValueError('Unsupported manifest schema/channel order')
    if m.get('data_kind') == 'real':
        from .admission import validate_real_manifest
        validate_real_manifest(m)
        if require_splits:
            raise ValueError('Rebuild legacy real manifests with original district and coverage evidence')
    seen, blocks = set(), {}
    for r in m['records']:
        p = (path.parent / r['path']).resolve()
        if not p.is_relative_to(path.parent.resolve()) or r['path'] in seen:
            raise ValueError('Unsafe or duplicate patch path')
        seen.add(r['path'])
        if blocks.setdefault(r['block'], r['split']) != r['split']:
            raise ValueError('Block leakage across partitions')
        if digest(p) != r['sha256']:
            raise ValueError('Patch checksum mismatch')
    if require_splits:
        if m.get('data_kind') not in ('real','synthetic'):
            raise ValueError('Explicit real/synthetic dataset identity required')
        actual_counts = {s: np.zeros(2, dtype=int) for s in ('train', 'validation', 'test')}
        windows = set()
        origins=set()
        for r in m['records']:
            affine=Affine(*r['transform'])
            size=m['patch_size']
            if (affine.a!=m['resolution_m'] or affine.e!=-m['resolution_m'] or affine.b or affine.d
                    or block_for(window_bounds(Window(0,0,size,size),affine),m['block_m'],m['buffer_m'])!=r['block']):
                raise ValueError('Patch transform does not match its spatial block/grid')
            if r['split'] != partition(r['block'], m['seed']):
                raise ValueError('Partition does not match frozen block assignment')
            key = (r['row'], r['col'])
            if key in windows or any(v % m['patch_size'] for v in key):
                raise ValueError('Duplicate or overlapping patch windows')
            windows.add(key)
            origins.add((round(affine.c-r['col']*affine.a,6),round(affine.f-r['row']*affine.e,6)))
            if len(origins)>1:
                raise ValueError('Patch positions do not share one aligned source grid')
            with np.load(path.parent / r['path']) as z:
                size = m['patch_size']
                if (z['before'].shape != (4,size,size) or z['after'].shape != (4,size,size)
                        or z['features'].shape != (6,size,size) or z['valid'].shape != (14,size,size)
                        or z['mask'].shape != (size,size) or z['label'].shape != (size,size)):
                    raise ValueError('Patch array shape mismatch')
                values = np.concatenate([z['before'], z['after'], z['features']], axis=0)
                if np.any(z['valid'] & ~np.isfinite(values)):
                    raise ValueError('Nonfinite feature marked valid')
                expected = z['valid'].all(axis=0) & (z['label'] != 255)
                if not np.array_equal(z['mask'], expected) or not np.isin(z['label'], [0,1,255]).all():
                    raise ValueError('Invalid label/mask contract')
                actual_counts[r['split']] += np.bincount(z['label'][z['mask']], minlength=2)
        if any(actual_counts[s].tolist() != m['counts'][s] for s in actual_counts):
            raise ValueError('Manifest class counts do not match patch labels')
        for s in ('train', 'validation', 'test'):
            if not any(r['split'] == s for r in m['records']):
                raise ValueError(f'No independent {s} patches; acquire more spatial labels')
        for split in ('train', 'validation', 'test'):
            if min(m['counts'][split]) == 0:
                raise ValueError(f'{split} requires both reference classes')
    return m


def fit_stats(path):
    """Shared temporal scaling, separate channel units, TRAIN pixels only."""
    m = read_manifest(path)
    total, squares, n = np.zeros(4), np.zeros(4), np.zeros(4)
    for r in m['records']:
        if r['split'] != 'train':
            continue
        with np.load(Path(path).parent / r['path']) as z:
            for name, offset in (('before', 0), ('after', 4)):
                for c in range(4):
                    values = z[name][c][z['valid'][offset+c]].astype('float64')
                    total[c] += values.sum(); squares[c] += (values**2).sum(); n[c] += values.size
    if (n == 0).any():
        raise ValueError('No valid training observations for a channel')
    mean = total / n
    std = np.maximum(np.sqrt(np.maximum(0, squares/n - mean**2)), 1e-6)
    return dict(mean=mean.tolist(), std=std.tolist(), fit_partition='train')


def normalized(z, stats):
    mean = np.array(stats['mean'], dtype='float32')[:, None, None]
    std = np.array(stats['std'], dtype='float32')[:, None, None]
    out = []
    for name, offset in (('before', 0), ('after', 4)):
        valid = z['valid'][offset:offset+4] & np.isfinite(z[name])
        values = np.where(valid, (z[name]-mean)/std, 0)
        out.append(np.concatenate([values, valid.astype('float32')], axis=0))
    return out
