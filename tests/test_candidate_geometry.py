"""Synthetic KML fixtures only; no test geometry is research reference data."""
import copy
import pytest
from shapely.geometry import box,mapping
from src.phase3.candidate_geometry import coordinate_ring,verify_kml


def boundary():
    return dict(type='FeatureCollection',provenance=dict(source='FAO/GAUL/2025/level2',simplified=False,synthetic_fixture=True),features=[
        dict(type='Feature',geometry=mapping(box(92,25,92.5,25.5)),properties={'GAUL2_NAME':'East Jaintia Hills'}),
        dict(type='Feature',geometry=mapping(box(92.5,25,93,25.5)),properties={'GAUL2_NAME':'West Jaintia Hills'})])


def test_source_vertices_preserved_and_no_training_labels(tmp_path):
    p=tmp_path/'fixture.kml';p.write_text('''<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>92.1,25.1,0 92.2,25.1,0 92.2,25.2,0 92.1,25.1,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Document></kml>''')
    f=verify_kml(p,boundary(),'synthetic-only','https://example.org/synthetic-fixture','Synthetic fixture','Synthetic site','East Jaintia Hills')
    assert f['geometry']['coordinates'][0][0]==(92.1,25.1)
    assert f['properties']['map_anchor']==[92.1,25.1]
    assert f['properties']['geographic_uncertainty_m'] is None
    assert 'label' not in f['properties'] and f['properties']['seasonal_change_evidence'] is False
    with pytest.raises(ValueError,match='district'):verify_kml(p,boundary(),'id','https://example.org','title','site','West Jaintia Hills')
    outside=boundary();outside['features'][0]['geometry']=mapping(box(90,20,91,21))
    with pytest.raises(ValueError,match='within'):verify_kml(p,outside,'id','https://example.org','title','site','district')


@pytest.mark.parametrize('coordinates',['92,25 92.1,25 92.1,25.1','200,25 92.1,25 92.1,25.1 200,25','NaN,25 92.1,25 92.1,25.1 NaN,25'])
def test_bad_coordinates_fail(coordinates):
    with pytest.raises(ValueError):coordinate_ring(coordinates)


def test_kml_network_links_do_not_count_as_evidence(tmp_path):
    p=tmp_path/'fixture.kml';p.write_text('<kml xmlns="http://www.opengis.net/kml/2.2"><NetworkLink/></kml>')
    with pytest.raises(ValueError,match='network'):verify_kml(p,boundary(),'id','https://example.org','title','site','district')


def test_candidate_map_shows_site_name_and_original_source(tmp_path):
    import json
    from src.phase3.annotation import init,import_candidates
    from src.phase3.annotation_map import review_map
    path=tmp_path/'boundary.geojson';path.write_text(json.dumps(boundary()))
    session=tmp_path/'session';init(session,path)
    row=dict(candidate_id='synthetic-map-only',site_name='Synthetic source-verified fixture',
       geometry=mapping(box(92.1,25.1,92.101,25.101)),coordinate_crs='EPSG:4326',source_organization='Synthetic test',
       source_url='https://example.org/synthetic-map-source',document_title='Synthetic fixture',date=None,
       geographic_uncertainty_m=None,seasonal_change_evidence=False,review_status='awaiting_evidence',category='uncertain',
       license_restrictions='Synthetic fixture only',evidence='Not real mining data')
    path=tmp_path/'candidate.json';path.write_text(json.dumps([row]));import_candidates(session,path)
    html=review_map(session,tmp_path/'map').read_text(encoding='utf-8')
    assert row['site_name'] in html and row['source_url'] in html
    assert 'not disturbance labels' in html
