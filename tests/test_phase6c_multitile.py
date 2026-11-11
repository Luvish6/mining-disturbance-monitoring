"""Synthetic multi-source software fixtures. No scientific reference claims."""
import json
import shutil

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer
from shapely import transform
from shapely.geometry import box, mapping

from src.phase3.data import BANDS, BAND_UNITS, digest, read_manifest, save_json
from src.phase3.evaluate import require_matching_support
from src.phase3.multitile import inspect_sources, prepare_tiles
from src.phase3.rf_experiments import evaluate, fit, samples
from src.phase3.run import infer, train
from src.phase3.spatial import partition


@pytest.fixture
def inputs(tmp_path):
    blocks = {}
    for bx in range(70, 150):
        blocks.setdefault(partition(f'{bx}:550'), bx)
    project = Transformer.from_crs(32646, 4326, always_xy=True).transform
    paths, features = [], []
    for split, bx in sorted(blocks.items()):
        x = ((bx * 5000 + 600) // 30) * 30
        y = 2751000
        path = tmp_path / f'{split}.tif'
        with rasterio.open(path, 'w', driver='GTiff', crs='EPSG:32646',
                           width=8, height=8, count=14, dtype='float32', nodata=-9999,
                           transform=from_origin(x, y, 30, 30)) as dst:
            data = np.random.default_rng(bx).normal(size=(14, 8, 8)).astype('float32')
            data[0, 0, 0] = -9999
            data[1, 0, 1] = np.nan
            dst.write(data)
            # A dataset mask can override GDAL's generated NoData mask.
            dst.write_mask(np.full((8, 8), 255, dtype='uint8'))
            dst.descriptions = BANDS
            dst.units = BAND_UNITS
            dst.update_tags(data_kind='synthetic')
        paths.append(path)
        for label in (0, 1):
            props = dict(label_id=f'{split}-{label}', label=label, source='software fixture',
                         provenance='generated', interpretation_date='2026-01-01', reviewer='fixture',
                         confidence='high', reviewed=True, synthetic=True,
                         evidence_group_id=f'{split}-{label}')
            polygon = box(x+120*label+1, y-239, x+120*(label+1)-1, y-1)
            features.append(dict(type='Feature', properties=props,
                                 geometry=mapping(transform(polygon, project, interleaved=False))))
    labels = tmp_path / 'labels.geojson'
    save_json(labels, dict(type='FeatureCollection', features=features))
    return paths, labels


def build(inputs, output, paths=None):
    rasters, labels = inputs
    return prepare_tiles(paths if paths is not None else rasters, labels, output,
                         patch_size=8, synthetic=True)


def test_distinct_ids_reproducible_order_and_validity(inputs, tmp_path):
    m = build(inputs, tmp_path / 'dataset')
    other = build(inputs, tmp_path / 'other', inputs[0][::-1])
    assert m == other
    assert m == read_manifest(tmp_path / 'dataset/manifest.json', require_splits=True)
    assert len({row['patch_id'] for row in m['records']}) == 3
    assert {(row['row'], row['col']) for row in m['records']} == {(0, 0)}
    assert m['quality']['invalid_labeled_pixels'] == 6
    for row in m['records']:
        with np.load(tmp_path / 'dataset' / row['path']) as patch:
            assert not patch['mask'][0, :2].any()
            assert patch['mask'][0, 2]


def test_overlap_different_files_and_hashes(inputs, tmp_path):
    duplicate = tmp_path / 'another.tif'
    shutil.copyfile(inputs[0][0], duplicate)
    with rasterio.open(duplicate, 'r+') as dst:
        dst.update_tags(distinct='yes')
    assert digest(duplicate) != digest(inputs[0][0])
    with pytest.raises(ValueError, match='overlapping'):
        build(inputs, tmp_path / 'dataset', [*inputs[0], duplicate])


@pytest.mark.parametrize(('mutation', 'message'), [
    ('crs', 'EPSG'), ('origin', 'lattice'), ('order', 'band order'),
    ('units', 'units'), ('nodata', 'NoData'),
])
def test_inconsistent_source_contract(inputs, mutation, message):
    with rasterio.open(inputs[0][0], 'r+') as dst:
        if mutation == 'crs':
            dst.crs = 'EPSG:4326'
        elif mutation == 'origin':
            dst.transform = from_origin(dst.transform.c + 1, dst.transform.f, 30, 30)
        elif mutation == 'order':
            dst.descriptions = BANDS[::-1]
        elif mutation == 'units':
            dst.set_band_unit(13, 'feet')
        else:
            dst.nodata = 0
    with pytest.raises(ValueError, match=message):
        inspect_sources(inputs[0], synthetic=True)


@pytest.mark.parametrize('key', ['evidence_group_id', 'site_id'])
def test_group_leakage_across_blocks(inputs, tmp_path, key):
    path = inputs[1]
    doc = json.loads(path.read_text())
    doc['features'][0]['properties'][key] = ' COMMON GROUP '
    doc['features'][2]['properties'][key] = 'common group'
    save_json(path, doc)
    with pytest.raises(ValueError, match='crosses frozen partitions'):
        build(inputs, tmp_path / 'dataset')
    assert not (tmp_path / 'dataset').exists()


@pytest.mark.parametrize('override', [dict(block_m=6000), dict(buffer_m=0), dict(seed=43)])
def test_real_overrides_rejected_at_prepare_and_read(inputs, tmp_path, override):
    output = tmp_path / 'dataset'
    with pytest.raises(ValueError, match='frozen'):
        prepare_tiles(*inputs, output, **override)
    m = build(inputs, output)
    m.update(data_kind='real', **override)
    save_json(output / 'manifest.json', m)
    with pytest.raises(ValueError, match='frozen'):
        read_manifest(output / 'manifest.json', require_splits=True)


@pytest.mark.parametrize(('keep', 'message'), [
    (lambda props: not props['label_id'].startswith('test-'), 'No independent test'),
    (lambda props: props['label_id'] != 'test-1', 'test requires both'),
])
def test_missing_support(inputs, tmp_path, keep, message):
    doc = json.loads(inputs[1].read_text())
    doc['features'] = [f for f in doc['features'] if keep(f['properties'])]
    save_json(inputs[1], doc)
    build(inputs, tmp_path / 'dataset')
    with pytest.raises(ValueError, match=message):
        read_manifest(tmp_path / 'dataset/manifest.json', require_splits=True)


def test_rehashed_patch_cannot_change_reference(inputs, tmp_path):
    output = tmp_path / 'dataset'
    m = build(inputs, output)
    record = m['records'][0]
    path = output / record['path']
    with np.load(path) as original:
        arrays = dict(original)
    arrays['label'][arrays['mask']] ^= 1
    np.savez_compressed(path, **arrays)
    record['sha256'] = digest(path)
    save_json(output / 'manifest.json', m)
    with pytest.raises(ValueError, match='differ from verified sources'):
        read_manifest(output / 'manifest.json', require_splits=True)


@pytest.mark.parametrize('field', ['ids', 'label', 'blocks', 'tiles'])
def test_support_order_and_identity(field):
    common = dict(ids=['t0:0', 't1:0'], label=[0, 1], blocks=['0:1', '0:2'], tiles=['t0', 't1'])
    changed = dict(common, **{field: common[field][::-1]})
    with pytest.raises(ValueError, match=field):
        require_matching_support(common, changed)


def test_both_model_paths_use_same_held_out_pixels(inputs, tmp_path):
    build(inputs, tmp_path / 'dataset')
    manifest = tmp_path / 'dataset/manifest.json'
    forest, paired = tmp_path / 'forest', tmp_path / 'paired'
    rf_test, paired_test = tmp_path / 'rf_test', tmp_path / 'paired_test'
    fit(manifest, forest, synthetic_smoke=True)
    evaluate(manifest, forest, rf_test)
    train(manifest, paired, epochs=1, width=2, synthetic_smoke=True)
    report = infer(manifest, paired, paired_test, rf_evaluation=rf_test)
    assert report['standalone_rf_support_verified']
    with np.load(rf_test / 'common_test_pixels.npz') as rf, np.load(
        paired_test / 'common_pixels.npz'
    ) as both:
        require_matching_support(rf, both)
        data = dict(rf)
    data['ids'] = data['ids'][::-1]
    np.savez_compressed(rf_test / 'common_test_pixels.npz', **data)
    receipt = json.loads((rf_test / 'evaluation.json').read_text())
    receipt['common_pixels_sha256'] = digest(rf_test / 'common_test_pixels.npz')
    save_json(rf_test / 'evaluation.json', receipt)
    with pytest.raises(ValueError, match='support mismatch: ids'):
        infer(manifest, paired, tmp_path / 'rejected', rf_evaluation=rf_test)
    assert not (tmp_path / 'rejected').exists()
    data['ids'] = data['ids'][::-1]
    data['mask_hashes'][0] = 'different'
    np.savez_compressed(rf_test / 'common_test_pixels.npz', **data)
    receipt['common_pixels_sha256'] = digest(rf_test / 'common_test_pixels.npz')
    save_json(rf_test / 'evaluation.json', receipt)
    with pytest.raises(ValueError, match='support mismatch: masks'):
        infer(manifest, paired, tmp_path / 'rejected_masks', rf_evaluation=rf_test)
    assert len(samples(manifest, 'test')[2]) == 62
