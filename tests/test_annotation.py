"""All geometry, reviewers and evidence in these tests are synthetic fixtures."""
import copy
import json
from pathlib import Path
import pytest
from pyproj import Transformer
from shapely import transform
from shapely.geometry import box,mapping,Point
from src.phase3.annotation import (init,read,write_new,collection,boundary_geometry,validate_candidates,
 candidate_seed,import_drafts,review,export,latest,validate_points,import_candidates)
from src.phase3.annotation_map import review_map,bounded_region
from ee.apitestcase import ApiTestCase
from unittest.mock import patch


class AnnotationGraphTests(ApiTestCase):
    def test_rgb_context_preserves_cloud_mask_and_channel_order(self):
        import ee
        from config.phase2_settings import Phase2Config
        from src.phase3.annotation_map import rgb_context
        image=ee.Image.constant([1000]*8).rename(['B2','B3','B4','B8','B8A','B9','SCL','other']).set('clouds',ee.Image.constant(0).rename('probability'))
        graph=rgb_context(image,Phase2Config()).serialize()
        assert 'B2' in graph and 'Image.updateMask' in graph and 'probability' in graph

    def test_unsubmitted_export_plan_matches_existing_raster_contract(self):
        import tempfile
        from dataclasses import asdict
        from config.settings import BEFORE,AFTER
        from config.phase2_settings import Phase2Config
        from src.phase3.annotation_map import paired_export_plan
        cfg=Phase2Config(relative_orbit=77)
        boundary=dict(collection([dict(type='Feature',geometry=mapping(box(92,25,92.5,25.5)),properties={'GAUL2_NAME':'East Jaintia Hills'}),
                                  dict(type='Feature',geometry=mapping(box(92.5,25,93,25.5)),properties={'GAUL2_NAME':'West Jaintia Hills'})]),
                      provenance=dict(source='FAO/GAUL/2025/level2',simplified=False,synthetic_fixture=True))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);write_new(root/'boundary.json',boundary);init(root/'session',root/'boundary.json')
            write_new(root/'coverage.json',dict(config=asdict(cfg),metadata={'selected_relative_orbit':77},seasons=[asdict(BEFORE),asdict(AFTER)]))
            with patch('src.gee_setup.initialize'),patch('src.phase3.ee_inputs.export_task') as task:
                path=paired_export_plan(root/'session',root/'coverage.json',root/'plan',[92.35,25.35],100)
                assert task.call_count==1
                assert not task.return_value.start.called
            plan=read(path)
            assert plan['status']=='prepared_not_submitted' and len(plan['band_order'])==14
            assert plan['crs_transform']==[30,0,0,0,-30,0] and plan['nodata']==-9999
            assert plan['export_id'] is None and plan['raster_sha256'] is None


@pytest.fixture
def session(tmp_path):
    inverse=Transformer.from_crs(32646,4326,always_xy=True).transform
    polygon=lambda bounds:mapping(transform(box(*bounds),inverse,interleaved=False))
    boundary=dict(collection([dict(type='Feature',geometry=polygon((500000,2800000,505000,2805000)),properties={'GAUL2_NAME':'East Jaintia Hills'}),
                             dict(type='Feature',geometry=polygon((505000,2800000,510000,2805000)),properties={'GAUL2_NAME':'West Jaintia Hills'})]),
                  provenance=dict(source='FAO/GAUL/2025/level2',simplified=False,synthetic_fixture=True))
    source=tmp_path/'boundary.geojson';write_new(source,boundary);root=tmp_path/'workspace';init(root,source)
    feature=dict(type='Feature',geometry=polygon((500500,2800500,500800,2800800)),properties=dict(
        label_id='fixture-1',candidate_id='saryngkham-a',site_id='fixture-site',label=1,source='synthetic test',
        provenance='Synthetic software fixture only',interpretation_date='2026-11-08',reviewer='fixture-first',
        reviewed=False,confidence='high',synthetic=False,independent_reference=True,
        target_definition='new_mining_related_disturbance_2023_2025',before_evidence_date='2024-01-15',
        after_evidence_date='2025-01-15',spatial_accuracy_m=10,evidence_urls=['https://example.org/synthetic-fixture'],
        independent_evidence_note='Synthetic contract test; not research evidence',
        evidence_license_note='Synthetic fixture; no real imagery used'))
    return root,feature,boundary


def import_one(root,feature,tmp_path):
    path=tmp_path/'draft.geojson';write_new(path,collection([feature]));import_drafts(root,path)


def test_empty_workspace_and_candidate_inventory(session):
    root,_,boundary=session
    rows=validate_candidates(candidate_seed(),boundary)
    assert len(rows)==5 and all(r['intersects_study_area'] is None for r in rows)
    assert read(root/'reports/initial/accepted.geojson')['features']==[]
    assert read(root/'reports/initial/admission_report.json')['real_dataset_ready'] is False
    with pytest.raises(ValueError):validate_candidates(rows+rows,boundary)
    bad=copy.deepcopy(boundary);bad['provenance']['simplified']=True
    with pytest.raises(ValueError,match='unsimplified'):boundary_geometry(bad)


def test_two_independent_reviews_and_accepted_export(session,tmp_path):
    root,f,_=session;import_one(root,f,tmp_path)
    review(root,'fixture-1','submit','fixture-first','Independent first review performed',True)
    with pytest.raises(ValueError,match='Different'):review(root,'fixture-1','approve','FIXTURE-FIRST','same reviewer',True)
    review(root,'fixture-1','approve','fixture-second','Independent second review performed',True)
    report=export(root,tmp_path/'export')
    assert report['accepted_polygons']==1 and report['independent_site_count']==1
    assert sum(sum(c) for c in report['accepted_by_class_partition'].values())==1
    assert len(read(tmp_path/'export/reviewer_decisions.json'))==3
    assert report['real_dataset_ready'] is False


@pytest.mark.parametrize('field,value',[('after_evidence_date','2025-06-03'),('spatial_accuracy_m',None),('independent_reference',False)])
def test_missing_evidence_never_reaches_second_review(session,tmp_path,field,value):
    root,f,_=session;f['properties'][field]=value;import_one(root,f,tmp_path)
    review(root,'fixture-1','submit','fixture-first','Checked; missing valid evidence',True)
    assert latest(root)[0]['features'][0]['properties']['annotation_state']=='awaiting_evidence'
    with pytest.raises(ValueError):review(root,'fixture-1','approve','fixture-second','Cannot approve',True)


def test_outside_overlap_and_invalid_polygon_rejected(session,tmp_path):
    root,f,_=session;g=copy.deepcopy(f);g['geometry']=mapping(box(10,10,11,11))
    p=tmp_path/'outside.geojson';write_new(p,collection([g]))
    with pytest.raises(ValueError,match='outside'):import_drafts(root,p)
    g=copy.deepcopy(f);g['properties']['label_id']='fixture-2'
    p=tmp_path/'overlap.geojson';write_new(p,collection([f,g]))
    with pytest.raises(ValueError,match='overlapping'):import_drafts(root,p)
    g['geometry']=dict(type='Polygon',coordinates=[[[92,25],[92.1,25.1],[92,25.1],[92.1,25],[92,25]]])
    p=tmp_path/'invalid.geojson';write_new(p,collection([g]))
    with pytest.raises(ValueError,match='Valid'):import_drafts(root,p)


def test_disagreement_rejection_and_edit_invalidate_acceptance(session,tmp_path):
    root,f,_=session;import_one(root,f,tmp_path)
    review(root,'fixture-1','submit','fixture-first','first',True)
    review(root,'fixture-1','disagree','fixture-second','Needs independent adjudication',True)
    assert latest(root)[0]['features'][0]['properties']['annotation_state']=='disagreement'
    review(root,'fixture-1','reject','fixture-first','Cannot resolve uncertainty')
    assert export(root,tmp_path/'export1')['accepted_polygons']==0
    updated=tmp_path/'edited.geojson';write_new(updated,collection([f]));import_drafts(root,updated)
    review(root,'fixture-1','submit','fixture-first','Resolved first review',True)
    review(root,'fixture-1','approve','fixture-second','Resolved independent review',True)
    import_drafts(root,updated)
    assert export(root,tmp_path/'export2')['accepted_polygons']==0


def test_points_distance_and_bounded_map(session,tmp_path):
    root,f,boundary=session
    point=shape_center(f)
    region=bounded_region(boundary,point,100)
    assert region['type']=='Polygon'
    with pytest.raises(ValueError):bounded_region(boundary,[0,0],300)
    pts=collection([dict(type='Feature',geometry=mapping(Point(*point)),properties={})]*2)
    with pytest.raises(ValueError,match='too-close'):validate_points(pts)
    html=review_map(root,tmp_path/'map')
    content=html.read_text(encoding='utf-8')
    assert 'Download drafts' in content and 'L.Control.Draw' in content
    assert 'fixed seed 42' in content
    assert 'second reviewer' not in content.lower() or 'draft' in content
    assert read(tmp_path/'map/imagery_record.json')['annotation_verification'] is False


def shape_center(feature):
    from shapely.geometry import shape
    center=shape(feature['geometry']).centroid
    return [center.x,center.y]


def test_manual_nonmining_candidate_import(session,tmp_path):
    root,_,_=session;row=copy.deepcopy(candidate_seed()[0]);row.update(candidate_id='fixture-background',category='possible_non_mining_reference')
    path=tmp_path/'candidate.json';write_new(path,[row]);import_candidates(root,path)
    with pytest.raises(ValueError,match='Duplicate'):import_candidates(root,path)
