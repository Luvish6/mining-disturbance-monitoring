import json
from pathlib import Path
import numpy as np
import pytest
import torch
from scripts.indian_ssl_pilot import Encoder
from src.phase25.minemind import availability,embed,change,cutoff
from scripts.phase25_minemind_portal import minemind_files,CACHE
from src.phase25.dataset import sha


def test_fully_observed_wrapper_preserves_frozen_encoder():
 torch.manual_seed(42);model=Encoder().eval();x=np.random.default_rng(42).normal(size=(8,4)).astype('float32');m=embed(model,x,np.ones((8,2),bool),np.zeros(4),np.ones(4))
 with torch.no_grad():expected=model.embed(torch.from_numpy(x)).numpy()
 assert np.array_equal(m,expected)


def test_hidden_sensor_values_cannot_change_representation():
 model=Encoder().eval();x=np.ones((3,4));y=x.copy();y[:,:2]=np.nan;observed=np.array([[False,True]]*3)
 assert np.array_equal(embed(model,x,observed,np.zeros(4),np.ones(4)),embed(model,y,observed,np.zeros(4),np.ones(4)))


def test_comparing_different_missing_sensors_is_unavailable_not_change():
 model=Encoder().eval();a=np.array([[1,1,np.nan,np.nan]]);b=np.array([[np.nan,np.nan,1,1]])
 score,valid=change(model,a,b,np.zeros(4),np.ones(4),'both');assert not valid[0] and np.isnan(score[0])
 assert not availability(np.full((1,4),-9999)).any()


def test_withheld_sensors_share_same_temporal_mask():
 model=Encoder().eval();a=np.ones((2,4));b=a.copy();b[0,:2]=np.nan
 score,valid=change(model,a,b,np.zeros(4),np.ones(4),'optical');assert valid.all() and np.all(score==0)
 score,valid=change(model,a,b,np.zeros(4),np.ones(4),'sar');assert not valid[0] and np.isnan(score[0])


def test_quota_threshold_is_deterministic_and_missing_scores_rejected():
 assert cutoff([1,2,3,4],2)==3
 with pytest.raises(ValueError):cutoff([1,np.nan],1)


def test_snapshot_missing_or_corrupt_never_serves_raw(tmp_path):
 assert minemind_files(tmp_path)=={}
 p=tmp_path/CACHE;p.mkdir(parents=True);(p/'model.pt').write_bytes(b'raw');(p/'integrity.json').write_text(json.dumps({'model.pt':sha(p/'model.pt')}))
 with pytest.raises(ValueError):minemind_files(tmp_path)


def test_skip_planet_launch_never_reads_planet_assets(monkeypatch):
 import scripts.phase8_planet_portal as portal
 import scripts.phase25_model_portal as old
 import scripts.phase25_minemind_portal as new
 monkeypatch.setattr('sys.argv',['portal','--without-planet','--port','5199'])
 def forbidden(*args):raise AssertionError('Planet/TESTsource must not open')
 monkeypatch.setattr(portal,'review_files',forbidden);monkeypatch.setattr(old,'experimental_files',lambda root:{});monkeypatch.setattr(new,'minemind_files',lambda root:{})
 class Server:
  def __init__(self,*args):pass
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def serve_forever(self):pass
 monkeypatch.setattr(portal,'ThreadingHTTPServer',Server);portal.main()


def test_observation_counts_gate_missing_sensor_and_context_is_not_fabricated():
 from src.phase25.minemind import tile_change
 model=Encoder().eval();v=np.ones((14,2,2));counts=np.full((4,2,2),3.);counts[[0,1]]=1;v[12:]=np.nan
 result=tile_change(model,dict(values=v,counts=counts),np.zeros(4),np.ones(4))
 assert result['valid'].all() and not result['sensor_observed'][0].any() and result['sensor_observed'][1].all()
 assert not result['context_valid'].any() and np.isnan(result['context']).all()
 counts[2]=.5
 with pytest.raises(ValueError):tile_change(model,dict(values=v,counts=counts),np.zeros(4),np.ones(4))


def test_exploratory_latent_scores_cannot_satisfy_operational_alert_gate(tmp_path):
 from src.phase3.alerts import validation
 assert validation(dict(model_validation='NOT_VALIDATED'),tmp_path,dict(data_kind='exploratory'),'hash')==(False,{})
