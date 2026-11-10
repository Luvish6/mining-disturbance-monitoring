"""Source KML geometry verification for candidates, never disturbance labels."""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon,MultiPolygon,mapping,shape
from .annotation import boundary_geometry

KML_NAMESPACE='http://www.opengis.net/kml/2.2'


def coordinate_ring(text):
    values=[]
    for token in (text or '').split():
        components=token.split(',')
        if len(components) not in (2,3): raise ValueError('KML coordinates need longitude,latitude[,altitude]')
        lon,lat=map(float,components[:2])
        if not (-180<=lon<=180 and -90<=lat<=90): raise ValueError('Invalid geographic coordinate range')
        values.append((lon,lat))
    if len(values)<4 or values[0]!=values[-1]: raise ValueError('Closed coordinate ring with at least four positions required')
    return values


def verify_kml(path,boundary,candidate_id,source_url,document_title,site_name,district):
    """Preserve original polygon vertices and unknown positional accuracy.

    Source-to-site identity must be checked against the original application.
    Containment and format checks do not prove mine activity or survey accuracy.
    """
    raw=Path(path).read_bytes()
    if len(raw)>5*1024*1024: raise ValueError('Candidate KML exceeds bounded 5 MiB size')
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('External/entity XML declarations are not accepted')
    tree=ET.fromstring(raw);ns={'k':KML_NAMESPACE}
    if tree.tag!=f'{{{KML_NAMESPACE}}}kml': raise ValueError('OGC KML 2.2 namespace required')
    if tree.findall('.//k:NetworkLink',ns): raise ValueError('External network references are not geometry evidence')
    geometries=[]
    for polygon in tree.findall('.//k:Polygon',ns):
        shell=coordinate_ring(polygon.findtext('k:outerBoundaryIs/k:LinearRing/k:coordinates',namespaces=ns))
        holes=[coordinate_ring(n.text) for n in polygon.findall('k:innerBoundaryIs/k:LinearRing/k:coordinates',ns)]
        g=Polygon(shell,holes)
        if not g.is_valid or g.is_empty or g.area<=0: raise ValueError('Invalid source polygon; no automatic repair')
        geometries.append(g)
    if not geometries: raise ValueError('No original polygon geometry in KML')
    geometry=geometries[0] if len(geometries)==1 else MultiPolygon(geometries)
    if not geometry.is_valid or not boundary_geometry(boundary).covers(geometry):
        raise ValueError('Source geometry must be valid and wholly within original study districts')
    containing={f['properties']['GAUL2_NAME'] for f in boundary['features'] if shape(f['geometry']).covers(geometry)}
    if district not in containing: raise ValueError('Claimed district does not contain the source geometry')
    first=list(geometries[0].exterior.coords)[0]
    return dict(type='Feature',geometry=mapping(geometry),properties=dict(
        candidate_id=candidate_id,site_name=site_name,district=district,
        source_organization='MoEFCC environmental clearance portal',source_url=source_url,
        document_title=document_title,source_sha256=hashlib.sha256(raw).hexdigest(),
        coordinate_crs='EPSG:4326',source_crs='OGC:CRS84 (WGS84 longitude/latitude, KML 2.2)',
        crs_basis='OGC KML standard geographic horizontal CRS; not an assumed pit-grid projection',
        transformation_method='Preserve KML longitude/latitude as GeoJSON; discard altitude, no datum shift',
        map_anchor=list(first),map_anchor_method='Original KML boundary ring vertex 1, not a centroid',
        geographic_uncertainty_m=None,uncertainty_note='Source does not provide measured positional accuracy; decimal digits are not accuracy',
        geometry_role='Published application boundary; not a verified disturbed-surface polygon',
        verification_status='verified_geographic_location',seasonal_verification_status='awaiting_independent_imagery',
        seasonal_change_evidence=False,review_status='awaiting_evidence',category='uncertain',
        intersects_study_area=True,contained_in_original_study_area=True,
        source_observation_date=None,source_publication_date=None,
        license_restrictions='Publicly linked application attachment. No explicit open redistribution license established; retain citation, no imagery included',
        evidence='Geographic application boundary located and source-linked. Surface mining activity and new/expanded 2023–2025 disturbance are not verified.'))
