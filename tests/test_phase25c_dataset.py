import copy
import json
from pathlib import Path

import numpy as np
import pytest
from affine import Affine

from scripts.phase25b_cached import save,tif
from src.phase25.features import Grid
from src.phase25.dataset import (BANDS,COUNTS,LABELS,SCHEMA,sha,windows,spatial_check,
    read_patch,load_manifest,require_verified_references,within)


def row():
    return dict(patch_id='fixture',group_id='88:556',split='train',row_offset=0,col_offset=0,
        crs='EPSG:32646',affine=[30,0,441540,0,-30,2783460],shape=[32,32],
        bounds=[441540,2782500,442500,2783460],parent_bounds=[441540,2781540,443460,2783460])


def seal(root,m):
    m['artifacts']={p.name:sha(p) for p in root.glob('*.tif')}
    (root/'manifest.json').write_text(json.dumps(m),encoding='utf-8')
    (root/'manifest.sha256').write_text(sha(root/'manifest.json'))


@pytest.fixture
def dataset(tmp_path):
    r=row();g=Grid(r['crs'],r['affine'],(32,32));r['files']={}
    y=np.zeros((32,32),dtype='uint8');y[0,0]=1;y[0,1]=255
    arrays={'features':(np.zeros((len(BANDS),32,32)),BANDS,'float32',-9999),
        'validity':(np.ones((len(BANDS),32,32)),BANDS,'uint8',None),
        'counts':(np.ones((5,32,32))*2,COUNTS,'float32',-9999),
        'pseudo_states':(y,['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE'],'uint8',255),
        'pseudo_masks':(np.stack([y==k for k in (0,1,255)]),list(LABELS.values()),'uint8',None)}
    for n,(a,b,d,no) in arrays.items():
        tif(tmp_path/(n+'.tif'),a,g,b,dtype=d,nodata=no);r['files'][n]=n+'.tif'
    m=dict(schema=SCHEMA,bands=BANDS,label_semantics=LABELS,verified_reference_labels=0,patches=[r])
    seal(tmp_path,m);return tmp_path,m


def test_crop_windows_cover_parent_once():
    hits=np.zeros((64,64),int)
    for r,c,h,w in windows():hits[r:r+h,c:c+w]+=1
    assert np.all(hits==1) and len(windows())==4


def test_pseudo_opt_in_and_no_supervised_truth(dataset):
    p,m=dataset;x=read_patch(p,'fixture')
    assert x['pseudo_states'] is None and x['verified_reference_labels'] is None
    x=read_patch(p,'fixture',allow_pseudo=True)
    assert x['pseudo_states'][0,1]==255 and x['pseudo_states'][0,0]==1
    with pytest.raises(ValueError):require_verified_references(x)


def test_duplicate_geometry_and_partition_leakage():
    a=row();b=copy.deepcopy(a);b['patch_id']='other'
    with pytest.raises(ValueError,match='Overlapping'):spatial_check([a,b])
    b['split']='validation'
    with pytest.raises(ValueError,match='Group'):spatial_check([a,b])
    a['split']='test'
    with pytest.raises(ValueError,match='TEST'):spatial_check([a])


def test_grid_and_parent_containment():
    a=row();a['affine'][2]+=1
    with pytest.raises(ValueError):spatial_check([a])
    a=row();a['parent_bounds']=[0,0,1,1]
    with pytest.raises(ValueError):spatial_check([a])


def test_tampering_and_reference_promotion_rejected(dataset):
    p,m=dataset;(p/'features.tif').write_bytes(b'altered')
    with pytest.raises(ValueError,match='integrity'):load_manifest(p)
    m['verified_reference_labels']=1;seal(p,m)
    with pytest.raises(ValueError,match='reference'):load_manifest(p)


def test_nodata_not_zero_and_validity_inconsistency(dataset):
    import rasterio
    p,m=dataset
    with rasterio.open(p/'features.tif','r+') as d:
        x=d.read();x[BANDS.index('elevation'),0,0]=-9999;d.write(x)
    seal(p,m)
    with pytest.raises(ValueError,match='Validity'):read_patch(p,'fixture')
    with rasterio.open(p/'validity.tif','r+') as d:
        x=d.read();x[BANDS.index('elevation'),0,0]=0;d.write(x)
    seal(p,m);assert np.isnan(read_patch(p,'fixture')['features'][BANDS.index('elevation'),0,0])


def test_affine_band_order_and_change_arithmetic(dataset):
    import rasterio
    p,m=dataset
    with rasterio.open(p/'features.tif','r+') as d:d.descriptions=tuple(reversed(BANDS))
    seal(p,m)
    with pytest.raises(ValueError,match='contract'):read_patch(p,'fixture')
    with rasterio.open(p/'features.tif','r+') as d:
        d.descriptions=tuple(BANDS);x=d.read();x[BANDS.index('dVV'),0,0]=1;d.write(x)
    seal(p,m)
    with pytest.raises(ValueError,match='arithmetic'):read_patch(p,'fixture')


def test_paths_and_unchecked_manifest(dataset):
    p,m=dataset
    with pytest.raises(ValueError,match='escapes'):within(p,'../outside')
    with pytest.raises(ValueError,match='replacement'):read_patch(p,'fixture',manifest={})


def test_frozen_assignment_and_pixel_offset_identity():
    a=row();a['split']='validation'
    with pytest.raises(ValueError,match='seed42'):spatial_check([a])
    a=row();a['row_offset']=32
    with pytest.raises(ValueError,match='identity'):spatial_check([a])


def test_required_payload_cannot_escape_hash_inventory(dataset):
    p,m=dataset
    del m['artifacts']['features.tif']
    (p/'manifest.json').write_text(json.dumps(m),encoding='utf-8')
    (p/'manifest.sha256').write_text(sha(p/'manifest.json'))
    with pytest.raises(ValueError,match='integrity inventory'):load_manifest(p)
