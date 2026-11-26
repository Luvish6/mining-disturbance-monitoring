import zipfile,json
import numpy as np
import pytest
from src.phase25.liss3_evidence import member_path,extract,metadata,reflectance,indices,relative_match


def test_zip_traversal_and_source_preservation(tmp_path):
 for name in ['../outside','/absolute','C:\\outside','a\\..\\outside']:
  with pytest.raises(ValueError):member_path(tmp_path,name)
 z=tmp_path/'valid.zip'
 with zipfile.ZipFile(z,'w') as a:a.writestr('scene/meta.txt',b'original')
 original=z.read_bytes();r=extract(z,tmp_path/'private')
 assert z.read_bytes()==original and r['members']['scene/meta.txt']['bytes']==8
 assert extract(z,tmp_path/'private')==r
 (tmp_path/'private/scene/meta.txt').write_text('altered')
 with pytest.raises(ValueError,match='no overwrite'):extract(z,tmp_path/'private')
 assert (tmp_path/'private/scene/meta.txt').read_text()=='altered'


def test_zip_oversize_and_symlink_rejected(tmp_path):
 z=tmp_path/'oversize.zip'
 with zipfile.ZipFile(z,'w') as a:a.writestr('large',b'abcd')
 with pytest.raises(ValueError,match='size gate'):extract(z,tmp_path/'oversize',max_bytes=3)
 z=tmp_path/'link.zip';i=zipfile.ZipInfo('link');i.create_system=3;i.external_attr=0o120777<<16
 with zipfile.ZipFile(z,'w') as a:a.writestr(i,b'outside')
 with pytest.raises(ValueError,match='symlink'):extract(z,tmp_path/'link')


def test_declared_boa_required_no_radiance_guess(tmp_path):
 p=tmp_path/'product.meta';p.write_text('Sensor=L3\nBandNumbers=2345\nProcessingLevel=AtmosphericallyCorrectedProduct\nValidRange=0-10000\nScaleFactor=0.0001\nCloudPercent=\nAcrossTrackAccuracy=0.0\n')
 m=metadata(p);assert m['CloudPercent']=='' and m['AcrossTrackAccuracy']=='0.0'
 p.write_text(p.read_text().replace('0.0001','0.001'))
 with pytest.raises(ValueError):metadata(p)


def test_scaling_padding_valid_zero_and_range_masks():
 raw=np.array([[[0,0,10001]],[[1000,0,1000]],[[4000,0,4000]],[[3000,0,3000]]],dtype='uint16')
 x,v=reflectance(raw,np.ones_like(raw,bool),{'ScaleFactor':'.0001','ValidRange':'0-10000'})
 assert v.tolist()==[[True,False,False]] and x[0,0,0]==0 and np.isclose(x[2,0,0],.4)
 assert np.isnan(x[:,0,1:]).all()
 with pytest.raises(ValueError):reflectance(raw[:3],np.ones_like(raw[:3],bool),{'ScaleFactor':'.0001','ValidRange':'0-10000'})


def test_indices_use_real_green_red_nir_swir_no_blue():
 x=np.array([.2,.1,.4,.3],dtype='float32')[:,None,None];r=indices(x)
 assert np.isclose(r['NDVI'][0,0],.6) and np.isclose(r['NDBI'][0,0],-1/7) and np.isclose(r['MNDWI'][0,0],-.2)
 assert 'BSI' not in r and 'RGB' not in r
 assert np.isnan(indices(np.zeros((4,1,1),'float32'))['NDVI']).all()


def test_relative_texture_never_absolute_accuracy_and_coordinates():
 a=np.random.default_rng(42).normal(size=(40,40));b=np.roll(a,(1,-2),(0,1));r=relative_match(a,b,np.ones_like(a,bool))
 assert r['after_shift_rows']==-1 and r['after_shift_columns']==2
 assert r['map_east_north_shift_metres']==[48,24] and r['image_column_row_shift_metres']==[48,-24]
 assert r['absolute_accuracy_m'] is None and r['independent_controls'] is False
 assert relative_match(a,b,np.zeros_like(a,bool))['status']=='INSUFFICIENT_TEXTURE_SUPPORT'


def test_unapproved_attachment_cannot_promote_to_model_input(tmp_path):
 from scripts.phase25_liss3_review import finalize
 p=tmp_path/'evidence_manifest.json';p.write_text(json.dumps(dict(parent_integrity_sha256='x',original_patches_unchanged=82,model_input_layers_added=0,verified_labels_added=0,attachments=[dict(model_input_eligible=True,reference_admitted=False)])))
 with pytest.raises(ValueError,match='Unapproved'):finalize(tmp_path,dict(parent82_inventory_sha256='x'))
