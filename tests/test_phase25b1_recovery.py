import io
import json
from pathlib import Path

import numpy as np
import pytest
from ee.apitestcase import ApiTestCase
import ee

from src.phase25.acquisition import MeteredHttp, BudgetStop
from src.phase25.features import Grid
from scripts.phase25b1_recover import graphs, road_distance, cached_json


class Raw(io.BytesIO):
    def read(self,n=-1,decode_content=False):return super().read(n)


class Response:
    def __init__(self,body=b'abc',length='3'):
        self.raw=Raw(body);self.status_code=200;self.headers={} if length is None else {'Content-Length':length}
    def close(self):pass


class Session:
    def __init__(self,response):self.response=response;self.calls=0
    def request(self,*args,**kwargs):self.calls+=1;return self.response


def test_counts_transport_and_redacts_credentials(tmp_path):
    session=Session(Response());m=MeteredHttp(tmp_path/'ledger',max_requests=1,max_bytes=20,response_cap=10,session=session)
    response,body=m.request('https://earthengine.googleapis.com/r?token=SECRET',body='SECRET')
    assert response.status==200 and body==b'abc' and m.summary()['received_response_body_bytes']==3
    assert 'SECRET' not in (tmp_path/'ledger').read_text()
    with pytest.raises(BudgetStop):m.request('https://earthengine.googleapis.com/r')
    assert session.calls==1


def test_pending_reservation_survives_resume_and_blocks_overspend(tmp_path):
    p=tmp_path/'ledger';p.write_text(json.dumps(dict(state='PENDING',reserved_bytes=10,response_bytes=0))+'\n')
    s=Session(Response());m=MeteredHttp(p,max_requests=60,max_bytes=15,response_cap=10,session=s)
    with pytest.raises(BudgetStop):m.request('https://earthengine.googleapis.com/r')
    assert s.calls==0 and m.summary()['charged_bytes_including_pending']==10


def test_body_stops_at_cap_and_declared_oversize_is_unread(tmp_path):
    response=Response(b'abcdefghijklmnop',length=None)
    m=MeteredHttp(tmp_path/'ledger',max_bytes=100,response_cap=10,session=Session(response))
    with pytest.raises(BudgetStop):m.request('https://earthengine.googleapis.com/r')
    assert response.raw.tell()==10 and m.summary()['received_response_body_bytes']==10
    r=Response(b'abc','11');m=MeteredHttp(tmp_path/'second',max_bytes=100,response_cap=10,session=Session(r))
    with pytest.raises(BudgetStop):m.request('https://earthengine.googleapis.com/r')
    assert r.raw.tell()==0


def test_unapproved_host_is_not_requested(tmp_path):
    s=Session(Response());m=MeteredHttp(tmp_path/'ledger',session=s)
    with pytest.raises(ValueError):m.request('https://example.invalid')
    assert s.calls==0


def test_osm_missing_road_is_unknown_not_zero_and_remark_rejected():
    g=Grid('EPSG:32646',(30,0,500000,0,-30,2800000),(2,2))
    v,n=road_distance({'elements':[]},g)
    assert n==0 and np.isnan(v).all()
    with pytest.raises(ValueError):road_distance({'remark':'timeout','elements':[]},g)


def test_altered_cached_receipt_rejected(tmp_path):
    p=tmp_path/'a.json';p.write_text('{}');(tmp_path/'a.json.sha256').write_text('0'*64)
    with pytest.raises(ValueError):cached_json(p)


class ContextGraphs(ApiTestCase):
    def test_offline_bounded_graph_has_only_context_no_pseudo_recalibration(self):
        image,metadata=graphs(ee,'synthetic',dict(bounds=[500000,2800000,501920,2801920]))
        text=image.serialize()
        for name in ['elevation','land_cover','water_occurrence','burn_before','rain_before_mm']:
            assert name in text
        assert 'bitwiseAnd' in text and set(metadata)=={'before','after','native'}
