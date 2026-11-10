"""All imagery and labels in this module are SYNTHETIC software fixtures."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer
from shapely.geometry import box, mapping
from shapely import transform
import torch
from src.phase3.labels import load_labels
from src.phase3.spatial import block_for, partition
from src.phase3.data import BANDS, prepare, read_manifest, fit_stats, normalized, digest, save_json
from src.phase3.model import SiameseUNet, masked_loss
from src.phase3.evaluate import metrics, shared_evaluation
from src.phase3.run import train, infer


@pytest.fixture(scope='module')
def fixture_data(tmp_path_factory):
    root = tmp_path_factory.mktemp('synthetic_phase3')
    raster = root / 'synthetic.tif'
    grid = from_origin(500000, 2820000, 30, 30)
    rng = np.random.default_rng(3)
    x = rng.normal(size=(14, 640, 640)).astype('float32')
    x[:, 0:10, 0:10] = -9999
    with rasterio.open(raster, 'w', driver='GTiff', width=640, height=640, count=14,
                       dtype='float32', crs='EPSG:32646', transform=grid, nodata=-9999) as ds:
        ds.write(x); ds.descriptions = BANDS; ds.update_tags(data_kind='synthetic')
    to_geo = Transformer.from_crs(32646, 4326, always_xy=True).transform
    features = []
    for bx in range(100, 103):
        for by in range(561, 564):
            for label in (0, 1):
                g = box(bx*5000+500+label*2100, by*5000+500,
                        bx*5000+2400+label*2100, by*5000+4500)
                features.append(dict(type='Feature', geometry=mapping(transform(g, to_geo, interleaved=False)),
                    properties=dict(label_id=f'{bx}_{by}_{label}', label=label, source='synthetic fixture',
                    provenance='Generated for software testing, not satellite evidence',
                    interpretation_date='2026-11-08', reviewer='test fixture', reviewed=True,
                    confidence='high', synthetic=True)))
    labels = root / 'synthetic.geojson'
    save_json(labels, dict(type='FeatureCollection', features=features))
    prepare(raster, labels, root / 'dataset', synthetic=True)
    return root


def test_ingestion_shapes_masks_and_partition_independence(fixture_data):
    path = fixture_data / 'dataset/manifest.json'
    m = read_manifest(path, require_splits=True)
    assert m['data_kind'] == 'synthetic'
    assert all(min(c) > 0 for c in m['counts'].values())
    groups = {s: {r['block'] for r in m['records'] if r['split']==s} for s in m['counts']}
    assert not groups['train'] & groups['test']
    assert not groups['validation'] & groups['test']
    r = m['records'][0]
    with np.load(path.parent / r['path']) as z:
        assert z['before'].shape == (4,64,64) and z['features'].shape == (6,64,64)
        assert not np.any(z['mask'] & (z['label']==255))
        a, b = normalized(z, fit_stats(path))
        assert a.shape == b.shape == (8,64,64) and np.isfinite(a).all()


@pytest.mark.parametrize('field,value', [('label',2),('reviewed',False),('source',''),('confidence','low'),('interpretation_date','bad')])
def test_label_metadata_rejected(fixture_data, field, value):
    data = json.loads((fixture_data/'synthetic.geojson').read_text())
    data['features'][0]['properties'][field] = value
    with pytest.raises(ValueError):
        load_labels(data)


def test_overlap_and_duplicate_labels_rejected(fixture_data):
    data = json.loads((fixture_data/'synthetic.geojson').read_text())
    data['features'].append(copy.deepcopy(data['features'][0]))
    with pytest.raises(ValueError, match='Duplicate'):
        load_labels(data)
    data['features'][-1]['properties']['label_id'] = 'other'
    with pytest.raises(ValueError, match='Overlapping'):
        load_labels(data)


def test_spatial_buffers_and_reproducibility():
    assert block_for((200,200,2000,2000)) == '0:0'
    assert block_for((4900,200,5100,1000)) is None
    assert block_for((10,200,1000,1000)) is None
    assert partition('100:562') == partition('100:562')
    with pytest.raises(ValueError):
        block_for((0,0,100,100), buffer_m=3000)


def test_normalization_ignores_test_and_missing_values(tmp_path):
    # Hand-constructed synthetic manifest to isolate train-only scaling.
    records = []
    for name, split, val in [('a','train',2.),('b','test',1e8)]:
        x = np.full((4,8,8),val,dtype='float32')
        valid = np.ones((14,8,8), dtype=bool); valid[:8,0,0]=False
        x[:,0,0] = np.nan
        p = tmp_path/f'{name}.npz'
        np.savez(p,before=x,after=x,valid=valid)
        records.append(dict(path=p.name,sha256=digest(p),split=split,block=name))
    save_json(tmp_path/'manifest.json',dict(schema=1,channels=list(BANDS),records=records))
    stats = fit_stats(tmp_path/'manifest.json')
    assert stats['mean'] == [2.]*4
    with np.load(tmp_path/'a.npz') as z:
        a,b = normalized(z,stats)
        assert np.isfinite(a).all() and (a[:,0,0]==0).all()


def test_model_forward_backward_and_empty_positive_loss():
    torch.set_num_threads(2)
    model = SiameseUNet(width=4)
    a = torch.randn(2,8,17,19)
    out = model(a, a+1)
    assert out.shape == (2,1,17,19)
    y = torch.zeros_like(out); mask = torch.ones_like(out,dtype=torch.bool)
    y[:,:,0,0] = 255; mask[:,:,0,0] = False
    loss = masked_loss(out,y,mask); loss.backward()
    assert torch.isfinite(loss) and model.e1[0].weight.grad is not None
    with pytest.raises(ValueError,match='No valid'):
        masked_loss(out,y,torch.zeros_like(mask))


def test_metrics_and_paired_common_set():
    result = metrics(np.array([0,0,1,1]),np.array([.1,.8,.7,.9]))
    assert result['confusion_matrix'] == [[1,1],[0,2]]
    assert result['classes'][1]['iou'] == pytest.approx(2/3)
    assert metrics([0,0],[.1,.1])['classes'][1]['recall'] is None
    with pytest.raises(ValueError):
        shared_evaluation([0,1],[.1],[.2,.3],['a','b'])
    with pytest.raises(ValueError):
        metrics([0,1],[.1,np.nan])
    assert shared_evaluation([0,1],[.1,.9],[.2,.8],['a','a'])['paired_f1_difference_95pct'] is None


def test_corrupt_patch_fails_before_training(fixture_data, tmp_path):
    source = fixture_data/'dataset/manifest.json'
    data = json.loads(source.read_text())
    data['records'][0]['path'] = '../escape.npz'
    save_json(tmp_path/'manifest.json', data)
    with pytest.raises(ValueError,match='Unsafe'):
        read_manifest(tmp_path/'manifest.json')


def test_real_mode_rejects_synthetic_labels(fixture_data, tmp_path):
    with pytest.raises(ValueError,match='Synthetic'):
        prepare(fixture_data/'synthetic.tif',fixture_data/'synthetic.geojson',tmp_path/'bad')


@pytest.mark.parametrize('bad', ['bands', 'crs'])
def test_bad_grid_or_channels_rejected(fixture_data, tmp_path, bad):
    path = tmp_path/'bad.tif'
    with rasterio.open(path,'w',driver='GTiff',width=64,height=64,count=14,
            dtype='float32',crs='EPSG:4326' if bad=='crs' else 'EPSG:32646',
            transform=from_origin(500000,2820000,30,30)) as ds:
        ds.write(np.zeros((14,64,64),dtype='float32'))
        ds.descriptions = ('wrong',)*14 if bad=='bands' else BANDS
        ds.update_tags(data_kind='synthetic')
    with pytest.raises(ValueError, match='EPSG|band'):
        prepare(path, fixture_data/'synthetic.geojson', tmp_path/'output', synthetic=True)


def test_patch_checksum_detects_mutation(fixture_data):
    manifest = fixture_data/'dataset/manifest.json'
    m = read_manifest(manifest)
    patch = manifest.parent/m['records'][0]['path']
    original = patch.read_bytes()
    try:
        patch.write_bytes(original+b'corruption')
        with pytest.raises(ValueError, match='checksum'):
            read_manifest(manifest)
    finally:
        patch.write_bytes(original)


def test_cpu_synthetic_training_checkpoint_rf_and_geotiff(fixture_data):
    manifest = fixture_data/'dataset/manifest.json'
    with pytest.raises(ValueError,match='synthetic-smoke'):
        train(manifest, fixture_data/'must_not_train', epochs=1)
    meta = train(manifest,fixture_data/'run',epochs=1,width=2,batch_size=8,synthetic_smoke=True)
    report = infer(manifest,fixture_data/'run',fixture_data/'predictions')
    assert meta['device'] == 'cpu' and report['data_kind'] == 'synthetic'
    assert report['rf']['classes'][1]['support'] == report['siamese']['classes'][1]['support']
    p = next((fixture_data/'predictions').glob('*.tif'))
    with rasterio.open(p) as ds:
        assert ds.count == 8 and ds.crs.to_epsg() == 32646
        assert ds.tags()['data_kind'] == 'synthetic'
    assert (fixture_data/'run/loss.png').exists()


def test_manifest_rejects_nonfinite_valid_features(fixture_data, tmp_path):
    import shutil
    dataset = tmp_path / 'dataset'
    shutil.copytree(fixture_data / 'dataset', dataset)
    manifest = dataset / 'manifest.json'
    m = json.loads(manifest.read_text())
    record = m['records'][0]
    patch = dataset / record['path']
    with np.load(patch) as z:
        arrays = {key: z[key].copy() for key in z.files}
    row, col = np.argwhere(arrays['mask'])[0]
    arrays['features'][0, row, col] = np.nan
    np.savez_compressed(patch, **arrays)
    record['sha256'] = digest(patch)
    save_json(manifest, m)
    with pytest.raises(ValueError, match='Nonfinite feature'):
        read_manifest(manifest, require_splits=True)


@pytest.mark.parametrize('split', ['validation', 'test'])
def test_manifest_rejects_single_class_heldout(fixture_data, tmp_path, split):
    import shutil
    dataset = tmp_path / 'dataset'
    shutil.copytree(fixture_data / 'dataset', dataset)
    manifest = dataset / 'manifest.json'
    m = json.loads(manifest.read_text())
    for record in m['records']:
        if record['split'] != split:
            continue
        patch = dataset / record['path']
        with np.load(patch) as z:
            arrays = {key: z[key].copy() for key in z.files}
        arrays['label'][arrays['mask']] = 0
        np.savez_compressed(patch, **arrays)
        record['sha256'] = digest(patch)
    m['counts'][split] = [sum(m['counts'][split]), 0]
    save_json(manifest, m)
    with pytest.raises(ValueError, match=f'{split} requires both'):
        read_manifest(manifest, require_splits=True)
