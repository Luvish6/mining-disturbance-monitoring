"""SYNTHETIC RF and admission tests; never scientific reference samples."""
import json
import sqlite3
import struct
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box,mapping
from src.phase3.data import BANDS,FEATURES,digest,read_manifest
from src.phase3.spatial import partition
from src.phase3.rf_experiments import fit,evaluate,map_tile,load_model,indices
from src.phase3.admission import validate_references,validate_real_manifest,TARGET
from src.phase3.reference_sources import gpkg_geometry,subset


def manifest(tmp_path):
    dataset=tmp_path/'synthetic';dataset.mkdir();records=[];counts={}
    used=set()
    for split in ('train','validation','test'):
        bx=next(x for x in range(100,200) if partition(f'{x}:561')==split and x not in used);used.add(bx)
        y=np.indices((8,8)).sum(axis=0)%2
        x=np.stack([y*(c+1) for c in range(6)]).astype('float32')
        p=dataset/f'{split}.npz'
        np.savez(p,before=np.zeros((4,8,8),dtype='float32'),after=np.zeros((4,8,8),dtype='float32'),
                 features=x,valid=np.ones((14,8,8),dtype=bool),label=y.astype('uint8'),mask=np.ones((8,8),dtype=bool))
        records.append(dict(path=p.name,sha256=digest(p),split=split,block=f'{bx}:561',row=0,col=(bx-100)*168,
                            transform=[30,0,bx*5000+300,0,-30,2805600]))
        counts[split]=[32,32]
    # Realistic one-source pixel alignment: use tile columns from a 5 km block
    # lattice compatible with a 30 m grid (blocks every 15 km).
    records=[];used=set()
    for split in ('train','validation','test'):
        bx=next(x for x in range(102,300,3) if partition(f'{x}:561')==split and x not in used);used.add(bx)
        p=dataset/f'{split}.npz'
        col=(bx-102)*5000//30
        col=(col//8)*8
        east=510240+col*30
        # keep all patches within block cores, on the same 30 m source lattice
        records.append(dict(path=p.name,sha256=digest(p),split=split,block=f'{bx}:561',row=0,col=col,
                            transform=[30,0,east,0,-30,2805600]))
    m=dict(schema=1,data_kind='synthetic',channels=list(BANDS),records=records,counts=counts,
           patch_size=8,block_m=5000,buffer_m=120,seed=42,resolution_m=30,crs='EPSG:32646',quality={})
    p=dataset/'manifest.json';p.write_text(json.dumps(m));read_manifest(p,require_splits=True)
    return p


def test_four_models_reload_reproducibility_common_ids_and_raster(tmp_path):
    path=manifest(tmp_path)
    with pytest.raises(ValueError,match='Synthetic'): fit(path,tmp_path/'forbidden')
    a=fit(path,tmp_path/'run_a',synthetic_smoke=True)
    b=fit(path,tmp_path/'run_b',synthetic_smoke=True)
    assert a['config']['n_estimators']==100 and a['test_used_for_selection'] is False
    for name in ('sar','optical','fused','fused_terrain'):
        ma,_=load_model(tmp_path/'run_a',name);mb,_=load_model(tmp_path/'run_b',name)
        x=np.zeros((3,len(indices(name))))
        assert np.array_equal(ma.predict_proba(x),mb.predict_proba(x))
        assert a['experiments'][name]['features']==[FEATURES[i] for i in indices(name)]
    report=evaluate(path,tmp_path/'run_a',tmp_path/'evaluation')
    assert all(sum(sum(row) for row in r['overall']['confusion_matrix'])==64 for r in report['experiments'].values())
    with np.load(tmp_path/'evaluation/common_test_pixels.npz') as z:
        assert len(np.unique(z['ids']))==64
    raster=tmp_path/'synthetic.tif'
    values=np.zeros((14,8,8),dtype='float32');values[:,0,0]=-9999
    with rasterio.open(raster,'w',driver='GTiff',width=8,height=8,count=14,dtype='float32',crs='EPSG:32646',
                       transform=from_origin(510240,2805600,30,30),nodata=-9999) as ds:
        ds.write(values);ds.descriptions=BANDS;ds.update_tags(data_kind='synthetic')
    output=tmp_path/'map.tif';map_tile(raster,tmp_path/'run_a',output)
    with rasterio.open(output) as ds:
        assert ds.crs.to_epsg()==32646 and ds.res==(30,30) and ds.count==4
        assert ds.read(1)[0,0]==-9999 and ds.read(3).sum()==63
        assert ds.tags()['data_kind']=='synthetic'


def test_geotransform_cannot_spoof_spatial_partition(tmp_path):
    path=manifest(tmp_path);m=json.loads(path.read_text());m['records'][0]['transform'][2]+=5000
    path.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='spatial block'): read_manifest(path,require_splits=True)


def test_unknown_dataset_identity_cannot_train(tmp_path):
    path=manifest(tmp_path);m=json.loads(path.read_text());m['data_kind']='unverified'
    path.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='identity'): read_manifest(path,require_splits=True)


def reference():
    return dict(synthetic=False,independent_reference=True,target_definition=TARGET,
        before_evidence_date='2024-01-15',after_evidence_date='2025-01-15',spatial_accuracy_m=10,
        reviewer='a',second_reviewer='b',evidence_urls=['https://example.org/synthetic-unit-test-only'])


@pytest.mark.parametrize('key,value',[('independent_reference',False),('after_evidence_date','2025-06-03'),
    ('target_definition','known_mine'),('spatial_accuracy_m',None),('spatial_accuracy_m',100),('second_reviewer','a')])
def test_inadmissible_real_reference_metadata(key,value):
    r=reference();r[key]=value
    with pytest.raises(ValueError): validate_references([r])


def test_registered_real_provenance_cannot_be_bypassed():
    with pytest.raises(ValueError,match='provenance'):
        validate_real_manifest(dict(resolution_m=30,crs='EPSG:32646',label_provenance=[reference()],raster_metadata={}))


def test_historical_reference_import_never_creates_labels(tmp_path):
    geometry=box(92.2,25.2,92.3,25.3)
    blob=b'GP'+bytes([0,1])+struct.pack('<i',4326)+geometry.wkb
    assert gpkg_geometry(blob).equals(geometry)
    path=tmp_path/'reference.gpkg';db=sqlite3.connect(path)
    db.execute('create table gpkg_geometry_columns (table_name text,column_name text,srs_id integer)')
    db.execute("insert into gpkg_geometry_columns values ('mines','geom',4326)")
    db.execute('create table mines(fid integer,geom blob)');db.execute('insert into mines values(1,?)',(blob,));db.commit();db.close()
    boundary=tmp_path/'boundary.geojson';boundary.write_text(json.dumps(mapping(box(92,25,93,26))))
    output=tmp_path/'candidates.geojson';assert subset(path,boundary,output)==1
    p=json.loads(output.read_text())['features'][0]['properties']
    assert 'label' not in p and p['temporal_match_2023_2025'] is False
