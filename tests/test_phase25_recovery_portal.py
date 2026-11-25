import json
from pathlib import Path
from types import SimpleNamespace
from http.client import HTTPConnection
from threading import Thread
import numpy as np
import torch
import pytest
from scripts.phase25_unet_recovery import schedule,sensitivity
from scripts.phase25_model_portal import experimental_files
from scripts.phase8_planet_portal import handler,ThreadingHTTPServer
from src.phase25.dataset import sha


def test_schedule_train_only_deterministic_positive_exposure():
    def record(y,split='train'):return dict(row=dict(split=split),adapted=dict(target=torch.tensor([y]),mask=torch.tensor([True])))
    rows=[record(1)]+[record(0) for _ in range(5)]
    a=schedule(rows,3,np.random.default_rng(42));b=schedule(rows,3,np.random.default_rng(42))
    assert a==b and all(batch[:3]==[0,0,0] for batch in a)
    assert sorted(batch[3] for batch in a)==[1,2,3,4,5]
    rows[0]['row']['split']='validation'
    with pytest.raises(ValueError,match='TRAIN-only'):schedule(rows,3,np.random.default_rng(42))


def test_fixed_sensitivity_excludes_unknown():
    frame=dict(labels=[0,1,255],probabilities=[.4,.6,.9],valid=[True,True,False],group_ids=['a','a','a'])
    m=sensitivity(frame)
    assert set(m)=={'0.25','0.5','0.75'}
    assert m['0.5']['pooled']['confusion_matrix']==[[1,0],[0,1]]


def test_private_static_route_has_no_raw_or_cross_origin_access(tmp_path):
    files={'snapshot.json':('application/json',b'{}')}
    with ThreadingHTTPServer(('127.0.0.1',0),handler(tmp_path,{},'127.0.0.1',files)) as server:
        thread=Thread(target=server.serve_forever);thread.start()
        def get(path,**headers):
            c=HTTPConnection('127.0.0.1',server.server_port);c.request('GET',path,headers={'Host':'127.0.0.1',**headers});r=c.getresponse();status=r.status;r.read();c.close();return status
        try:
            assert get('/__experimental__/snapshot.json')==403
            assert get('/__experimental__/snapshot.json',**{'Sec-Fetch-Site':'same-origin'})==200
            assert get('/__experimental__/model.pt',**{'Sec-Fetch-Site':'same-origin'})==404
            assert get('/__experimental__/snapshot.json',**{'Sec-Fetch-Site':'same-origin','Origin':'https://elsewhere.invalid'})==403
        finally:server.shutdown();thread.join()


def test_missing_or_altered_snapshot_fails_closed(tmp_path):
    from scripts.phase25_model_portal import CACHE
    assert experimental_files(tmp_path)=={}
    cache=tmp_path/CACHE;cache.mkdir(parents=True);p=cache/'snapshot.json';p.write_text('{}')
    (cache/'integrity.json').write_text(json.dumps({'snapshot.json':sha(p)}));p.write_text('changed')
    with pytest.raises(ValueError,match='integrity'):experimental_files(tmp_path)
