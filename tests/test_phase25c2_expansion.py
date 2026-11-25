import copy
import json
from pathlib import Path

import ee
import numpy as np
import pytest
from affine import Affine
from ee.apitestcase import ApiTestCase
from rasterio.io import MemoryFile

from scripts.phase25c2_expand import checked,signals,validate_raw,validate_metadata,graph,NAMES
from scripts.phase25c1_readiness import acquisition_contract


def raw(*,bands=7,crs='EPSG:32646',affine=Affine(30,0,441540,0,-30,2783460),order=None):
    a=np.ones((bands,64,64),dtype='float32')
    if bands==7:a[4]=152;a[5]=151
    with MemoryFile() as m:
        with m.open(driver='GTiff',height=64,width=64,count=bands,dtype='float32',crs=crs,transform=affine,nodata=-9999) as d:
            d.write(a)
            if order:d.descriptions=tuple(order)
        return m.read()


def test_plan_hash_mismatch_stops_before_parse(tmp_path):
    p=tmp_path/'plan.json';p.write_text('{}')
    with pytest.raises(ValueError,match='SHA256'):checked(p,'0'*64)


def test_exact_context_grid_band_order_and_counts():
    row=dict(bounds=[441540,2781540,443460,2783460])
    assert validate_raw(raw(order=NAMES),row).shape==(7,64,64)
    for body in [raw(bands=6),raw(affine=Affine(30,0,441550,0,-30,2783460)),raw(order=list(reversed(NAMES))),raw(crs='EPSG:32645')]:
        with pytest.raises(ValueError):validate_raw(body,row)


def test_signal_common_support_and_signed_changes():
    v={s+'_'+b:np.ones((2,2))*10 for s in ['before','after'] for b in ['VV','VH','B2','B3','B4','NDVI','BSI','NDWI','count','sar_count']}
    v['after_VV'][:]=8;v['before_count'][0,0]=0
    x=signals(v)
    assert np.all(x['dVV']==-2) and np.isnan(x['before_NDVI'][0,0]) and np.isnan(x['dNDVI'][0,0])


def test_incomplete_metadata_chunk_or_duplicate_ids_rejected():
    one={s:dict(s1_ids=['a'],s1_dates_ms=[1],s2_ids=['b'],s2_dates_ms=[1],rain_ids=list(range(n)),rain_count=n) for s,n in [('before',152),('after',151)]}
    one['follow']=dict(s2_ids=['c'],s2_dates_ms=[2]);one['native']=dict.fromkeys(['elevation','land_cover','water','rain'],{})
    validate_metadata({'k':one},['k'])
    with pytest.raises(ValueError):validate_metadata({'k':one},['k','other'])
    bad=copy.deepcopy(one);bad['follow']['s2_ids']=['c','c'];bad['follow']['s2_dates_ms']=[1,2]
    with pytest.raises(ValueError):validate_metadata({'k':bad},['k'])


def test_new_writer_preserves_existing_target(tmp_path):
    from scripts.phase25c_dataset import package
    with pytest.raises(ValueError,match='Existing'):
        package([],[],{}, {},{},out=tmp_path,version='fixture',start=0,cpu=0)


class GraphContract(ApiTestCase):
    def test_offline_context_graph_is_frozen_and_follow_provenance_only(self):
        contract=acquisition_contract('fixture');image,info=graph(ee,dict(bounds=[441540,2781540,443460,2783460]),contract)
        text=image.serialize()
        for n in NAMES:assert n in text
        assert 'MCD64A1' not in text and 'roads' not in text
        assert set(info)=={'before','after','follow','native'}
        _,empty=graph(ee,dict(bounds=[441540,2781540,443460,2783460]),contract,metadata=False)
        assert empty=={}
