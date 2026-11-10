"""Synthetic-only checks for reference labeling and raster readiness tools."""
import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer
from shapely import transform
from shapely.geometry import box, mapping
from src.phase3.data import BANDS,digest
from src.phase3.spatial import partition
from src.phase3.workflow import init_labels,check_labels,block_grid,audit_raster,register_raster


def write(path,data):
    path.write_text(json.dumps(data))
    return path


def source(tmp_path, descriptions=True):
    path=tmp_path/'synthetic.tif'
    x=np.zeros((14,8,8),dtype='float32')
    x[6,0,0]=-9999; x[2,1,1]=np.nan
    with rasterio.open(path,'w',driver='GTiff',width=8,height=8,count=14,dtype='float32',
            transform=from_origin(500010,2810010,30,30),crs='EPSG:32646',nodata=-9999) as ds:
        ds.write(x); ds.update_tags(data_kind='synthetic')
        if descriptions: ds.descriptions=BANDS
    return path


def metadata(path):
    return dict(source='synthetic software fixture',export_id='fixture-only',operator='test',
                retrieved_date='2026-11-08',data_kind='synthetic',band_order=list(BANDS),
                raster_sha256=digest(path),seasons=[['2023-11-01','2024-04-01'],['2024-11-01','2025-04-01']])


def test_empty_label_starter_never_claims_ready(tmp_path):
    path=tmp_path/'labels.geojson'; init_labels(path)
    assert json.loads(path.read_text())['features']==[]
    report=check_labels(path,tmp_path/'report.json')
    assert report['status']=='blocked' and report['training_ready'] is False
    with pytest.raises(FileExistsError): init_labels(path)


def test_grid_has_splits_but_no_labels(tmp_path):
    inverse=Transformer.from_crs(32646,4326,always_xy=True).transform
    aoi=write(tmp_path/'aoi.geojson',mapping(transform(box(500000,2805000,510000,2815000),inverse,interleaved=False)))
    output=tmp_path/'cores.geojson'
    assert block_grid(aoi,output)==4
    features=json.loads(output.read_text())['features']
    assert all('label' not in f['properties'] for f in features)
    assert all(f['properties']['split']==partition(f['properties']['block']) for f in features)


def test_label_check_reports_partition_counts_and_crossing(tmp_path):
    inverse=Transformer.from_crs(32646,4326,always_xy=True).transform
    features=[]
    for bx in range(100,104):
        for label in (0,1):
            g=box(bx*5000+500+1000*label,2805500,bx*5000+1000+1000*label,2806000)
            features.append(dict(type='Feature',geometry=mapping(transform(g,inverse,interleaved=False)),
                properties=dict(label_id=f'{bx}_{label}',label=label,source='synthetic',provenance='test only',
                    reviewer='test',reviewed=True,interpretation_date='2026-11-08',confidence='high',synthetic=True)))
    path=write(tmp_path/'labels.geojson',dict(type='FeatureCollection',features=features))
    report=check_labels(path,tmp_path/'report.json')
    assert sum(sum(c) for c in report['counts'].values())==8
    assert report['data_kind']=='synthetic'
    assert report['training_ready'] is False
    g=box(499900,2806000,500500,2806500)
    features[0]['geometry']=mapping(transform(g,inverse,interleaved=False))
    write(path,dict(type='FeatureCollection',features=features))
    report=check_labels(path,tmp_path/'report2.json')
    assert any('crosses' in issue for issue in report['issues'])


def test_raster_audit_counts_missing_and_valid_zeros(tmp_path):
    path=source(tmp_path)
    report=audit_raster(path,tmp_path/'report.json')
    assert report['common_valid_pixels']==62
    assert report['bands'][0]['valid_pixels']==64
    assert report['bands'][0]['mean']==0
    assert report['bands'][2]['valid_pixels']==63
    assert report['status']=='raster_checks_passed'


def test_registration_preserves_nodata_masks_and_raw_source(tmp_path):
    path=source(tmp_path,descriptions=False); before=digest(path)
    meta=write(tmp_path/'metadata.json',metadata(path))
    registered=tmp_path/'registered.tif'
    register_raster(path,meta,registered)
    assert digest(path)==before
    with rasterio.open(registered) as ds:
        assert ds.descriptions==BANDS
        assert ds.read_masks()[6,0,0]==0
        assert ds.read_masks()[0,0,0]==255
    assert audit_raster(registered,tmp_path/'report.json')['common_valid_pixels']==62
    with pytest.raises(ValueError,match='new'): register_raster(path,meta,registered)


@pytest.mark.parametrize('bad',['hash','kind','seasons'])
def test_provenance_mismatches_rejected(tmp_path,bad):
    path=source(tmp_path); meta=metadata(path)
    if bad=='hash': meta['raster_sha256']='wrong'
    if bad=='kind': meta['data_kind']='real'
    if bad=='seasons': meta['seasons']=[]
    metadata_path=write(tmp_path/'metadata.json',meta)
    with pytest.raises(ValueError): register_raster(path,metadata_path,tmp_path/'out.tif')
    assert not (tmp_path/'out.tif').exists()
