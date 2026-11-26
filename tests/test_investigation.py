import json,io,zipfile
import numpy as np
import pytest
from affine import Affine
from rasterio.io import MemoryFile
from src.phase25.investigation import components,combine,fit_scales,adaptive_weights
from src.phase25.ngdr_context import archives
from scripts.investigation_portal import inspect_upload,exported


def fields():
 shape=(4,4);v={}
 for s in ['before','after']:
  for b,value in [('NDVI',.8 if s=='before' else .2),('BSI',0 if s=='before' else .3),('VV',-10 if s=='before' else -14),('VH',-15 if s=='before' else -19),('NDWI',-.3),('optical_count',3),('sar_count',3)]:v[s+'_'+b]=np.full(shape,value)
 v.update(dNDVI=v['after_NDVI']-v['before_NDVI'],dBSI=v['after_BSI']-v['before_BSI'],dVV=v['after_VV']-v['before_VV'],rainfall=np.full(shape,np.nan),slope=np.full(shape,10.),surface_water=np.zeros(shape));return v


def test_train_only_scale_fit_and_no_future_leakage():
 v=fields();s=fit_scales([(dict(split='train'),v)]);a=components(v,s)
 v.update(follow_NDVI=np.ones((4,4))*.1,follow_BSI=np.ones((4,4))*.5,follow_count=np.ones((4,4))*3)
 b=components(v,s);assert np.array_equal(a['values'],b['values'],equal_nan=True) and np.isnan(b['values'][3]).all()
 assert np.isfinite(components(v,s,retrospective=True)['values'][3]).all()
 with pytest.raises(ValueError):fit_scales([(dict(split='validation'),v)])


def test_missingness_and_zero_weights_never_create_certainty():
 v=fields();p=components(v,dict(ndvi=.3,soil=.1,sar=1.,rain=100.));z=combine(p,[1]*7)
 assert np.isfinite(z['score']).all() and ((z['score']>=0)&(z['score']<=100)).all()
 p['values'][:6]=np.nan;assert np.isnan(combine(p,[1]*7)['score']).all()
 with pytest.raises(ValueError):combine(p,[0]*7)


def test_competing_crop_evidence_prevents_automatic_mining_attribution():
 v=fields();v.update(before_crops=np.ones((4,4)),after_crops=np.ones((4,4)));p=components(v,dict(ndvi=.3,soil=.1,sar=1.,rain=100.));z=combine(p,[1,1,1,0,0,0,0],40)
 assert not z['candidate'].any()


def test_geology_crs_and_nested_archive_limits(tmp_path):
 p=tmp_path/'LITHOLOGY_bad.zip'
 with zipfile.ZipFile(p,'w') as z:z.writestr('bad.geojson',json.dumps(dict(type='FeatureCollection',features=[],crs={'properties':{'name':'UNKNOWN'}})))
 with pytest.raises(ValueError,match='CRS'):archives(tmp_path)


def upload_bytes(bounds=(100000,100000,100960,100960),dtype='uint8',names=None):
 names=names or [s+'_'+b for s in ['before','after'] for b in ['R','G','B']]
 with MemoryFile() as m:
  with m.open(driver='GTiff',width=32,height=32,count=len(names),dtype=dtype,crs='EPSG:32646',transform=Affine(30,0,bounds[0],0,-30,bounds[3])) as ds:ds.write(np.ones((len(names),32,32),dtype=dtype)*50);ds.descriptions=names
  return m.read()


def test_unknown_or_test_upload_area_rejected_before_pixel_inference(tmp_path):
 from scripts.investigation_dataset import OUT
 p=tmp_path/OUT;p.mkdir(parents=True);(p/'manifest.json').write_text(json.dumps(dict(patches=[])));(p/'config.json').write_text(json.dumps(dict(scales={})))
 with pytest.raises(ValueError,match='outside approved'):inspect_upload(tmp_path,upload_bytes())


def test_rgb_compatible_upload_does_not_invent_spectral_bands(tmp_path):
 from scripts.investigation_dataset import OUT
 p=tmp_path/OUT;p.mkdir(parents=True);(p/'manifest.json').write_text(json.dumps(dict(patches=[dict(split='train',group_id='a',crs='EPSG:32646',bounds=[100000,100000,100960,100960])])));(p/'config.json').write_text(json.dumps(dict(scales={})))
 d=inspect_upload(tmp_path,upload_bytes());assert d['modes']=={} and d['rgb_probabilities'] is None and d['status']=='UNKNOWN' and d['images']['before']


def test_export_unknown_status_and_controls_preserved():
 v=fields();p=components(v,dict(ndvi=.3,soil=.1,sar=1.,rain=100.));
 def safe(a):return np.where(np.isfinite(a),a,None).tolist()
 d=dict(id='synthetic',modes={'pair':dict(contributions=safe(p['values']),valid=p['valid'].tolist(),competitors=safe(p['competitors']))},affine=[30,0,400000,0,-30,2800000],crs='EPSG:32646',source_sha256='synthetic',dates={})
 r=exported(d,dict(mode='pair',weights=[1,1,1,0,0,0,0],threshold=40))
 assert r['clusters']==1 and r['geojson']['features'][0]['properties']['mining_attribution']=='UNKNOWN' and r['geojson']['features'][0]['properties']['operational_alerts']==0


def test_post_routes_reject_cross_origin_and_oversize(tmp_path,monkeypatch):
 from scripts.phase8_planet_portal import handler,ThreadingHTTPServer
 from threading import Thread
 from http.client import HTTPConnection
 import scripts.investigation_portal as portal
 monkeypatch.setattr(portal,'studio_post',lambda *args,**kwargs:dict(status='synthetic only'))
 with ThreadingHTTPServer(('127.0.0.1',0),handler(tmp_path,{},'127.0.0.1',{})) as server:
  t=Thread(target=server.serve_forever);t.start()
  def request(headers):
   c=HTTPConnection('127.0.0.1',server.server_port);c.request('POST','/__studio__/export',body=b'{}',headers={'Host':'127.0.0.1',**headers});r=c.getresponse();code=r.status;r.read();c.close();return code
  try:
   assert request({})==403
   assert request({'Sec-Fetch-Site':'same-origin','Origin':'https://external.invalid'})==403
   assert request({'Sec-Fetch-Site':'same-origin','Content-Length':'99999999'})==413
   assert request({'Sec-Fetch-Site':'same-origin'})==200
  finally:server.shutdown();t.join()


def test_steep_slope_alone_never_forces_all_change_into_non_mining():
 v=fields();v['slope'][:]=45;p=components(v,dict(ndvi=.3,soil=.1,sar=1.,rain=100.));r=combine(p,[1,1,1,0,0,0,0],60)
 assert r['candidate'].all() and (p['competitors'][2]<=.5).all()
 assert np.allclose(r['score'],100)
