"""Versioned manual reference annotations; no model fitting or inferred labels."""
import argparse
import copy
import csv
from datetime import datetime,timezone,date
import hashlib
import json
from pathlib import Path
import numpy as np
from pyproj import Transformer
from shapely import transform,union_all
from shapely.geometry import shape,mapping
from .admission import validate_references,TARGET
from .labels import load_labels
from .spatial import block_for,partition

STATES=('draft','awaiting_evidence','awaiting_second_review','disagreement','rejected','accepted')
CATEGORIES=('known_mining_location','potential_new_disturbance','potential_expanded_disturbance',
            'historical_unchanged_mining_area','possible_non_mining_reference','uncertain')
GAUL='FAO/GAUL/2025/level2'
DISTRICTS={'East Jaintia Hills','West Jaintia Hills'}


def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream: json.dump(value,stream,indent=2,allow_nan=False)


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def collection(features=()): return dict(type='FeatureCollection',features=list(features))


def boundary_geometry(document):
    provenance=document.get('provenance',{})
    features=document.get('features',[])
    if (provenance.get('source')!=GAUL or provenance.get('simplified') is not False
            or len(features)!=2 or {f.get('properties',{}).get('GAUL2_NAME') for f in features}!=DISTRICTS):
        raise ValueError('Original unsimplified GAUL district features required')
    geometries=[shape(f['geometry']) for f in features]
    if any(g.is_empty or not g.is_valid for g in geometries): raise ValueError('Invalid district geometry')
    return union_all(geometries)


def exact_boundary():
    from src.gee_setup import initialize
    from src.study_area import get_study_area,verify_boundary
    initialize();fc=get_study_area();verify_boundary(fc)
    doc=fc.getInfo()
    doc['provenance']=dict(source=GAUL,simplified=False,retrieved_at=now())
    boundary_geometry(doc)
    return doc


def validate_candidates(rows,boundary):
    seen=set();region=boundary_geometry(boundary)
    for row in rows:
        for key in ('candidate_id','source_organization','source_url','document_title','evidence','license_restrictions'):
            if not isinstance(row.get(key),str) or not row[key].strip(): raise ValueError(f'Missing candidate {key}')
        if row['candidate_id'] in seen: raise ValueError('Duplicate candidate ID')
        seen.add(row['candidate_id'])
        if not row['source_url'].startswith('https://'): raise ValueError('Genuine source URL required')
        if row.get('category') not in CATEGORIES or row.get('review_status')!='awaiting_evidence':
            raise ValueError('Discovery candidates must await evidence, never be accepted')
        if row.get('date') is not None: date.fromisoformat(row['date'])
        if 'geographic_uncertainty_m' not in row or 'seasonal_change_evidence' not in row:
            raise ValueError('Explicit uncertainty and seasonal relevance required')
        uncertainty=row['geographic_uncertainty_m']
        if uncertainty is not None and (isinstance(uncertainty,bool) or not isinstance(uncertainty,(int,float)) or not np.isfinite(uncertainty) or uncertainty<0):
            raise ValueError('Candidate uncertainty must be unknown or a documented finite nonnegative error')
        if type(row['seasonal_change_evidence']) is not bool: raise ValueError('Seasonal evidence flag must be explicit true/false')
        if row.get('geometry') is None: row['intersects_study_area']=None
        else:
            if row.get('coordinate_crs')!='EPSG:4326': raise ValueError('Record candidate geographic CRS explicitly')
            g=shape(row['geometry']);bounds=g.bounds
            if g.is_empty or not g.is_valid or not (-180<=bounds[0]<=bounds[2]<=180 and -90<=bounds[1]<=bounds[3]<=90):
                raise ValueError('Candidate geometry must be valid WGS84')
            row['intersects_study_area']=bool(g.intersects(region))
    return rows


def candidate_seed():
    common=dict(geometry=None,coordinate_crs=None,geographic_uncertainty_m=None,seasonal_change_evidence=False,
                review_status='awaiting_evidence',category='known_mining_location',
                license_restrictions='Public document; explicit open redistribution license not established')
    records=[
      ('saryngkham-a','Ministry of Coal','https://www.coal.nic.in/sites/default/files/2025-08/PIB2153719.pdf',
       'Production commences in two coal blocks','2025-08-07','Production reported from 2025-06-03, outside the target after season. No verified geographic footprint.'),
      ('brishyrnot-i','Indian Bureau of Mines','https://ibm.gov.in/writereaddata/files/173028842167221b2556cb8Brishyrnot.pdf',
       'Brishyrnot Limestone Mine-I inspection report','2024-09-10','Inspection 10–11 September 2024. Document contains pit grid numbers but their CRS is not established here; no geographic conversion performed.'),
      ('mynkree','Indian Bureau of Mines','https://ibm.gov.in/writereaddata/files/174065170867c03cbc8fd51Mynkree_Limestone_Mine.pdf',
       'Mynkree Limestone Mine inspection report','2024-12-05','Dated inspection record is a candidate lead, not a paired seasonal disturbance mask.'),
      ('amsyndui','Meghalaya State Pollution Control Board','https://megspcb.gov.in/public%20hearing%20compressed/Amynsyndui_limestone_quarry_deia_17th_sep_2024_compressed.pdf',
       'Amsyndui Limestone Mine draft EIA',None,'Previously documented indexed EIA lead in West Jaintia Hills. Original geographic interpretation and dates still need verification.'),
      ('korpet','Environmental clearance portal','https://environmentclearance.nic.in/state/FB_ECGeneral_Report.aspx?pid=197899',
       'KORPET limestone mining project application',None,'Previously documented 2021 proposal; permit geography and 2023–2025 surface change require independent verification.')]
    return [dict(common,candidate_id=i,source_organization=o,source_url=u,document_title=t,date=d,
                 date_role='inspection_start' if i in ('brishyrnot-i','mynkree') else 'publication' if d else 'not_verified',evidence=e)
            for i,o,u,t,d,e in records]


def candidates(root):
    revisions=sorted((Path(root)/'candidates').glob('revision_*.json'))
    return read(revisions[-1] if revisions else Path(root)/'candidates/inventory.json')


def import_candidates(root,inventory):
    _,boundary=latest(root);existing=candidates(root);incoming=read(inventory)
    if not isinstance(incoming,list): raise ValueError('Candidate inventory must be a JSON list')
    combined=validate_candidates(existing+incoming,boundary)
    number=len(list((Path(root)/'candidates').glob('revision_*.json')))+1
    path=Path(root)/'candidates'/f'revision_{number:06d}.json';write_new(path,combined)
    return path


def init(root,boundary_file=None):
    root=Path(root)
    if root.exists(): raise ValueError('Choose a new versioned annotation workspace')
    boundary=read(boundary_file) if boundary_file else exact_boundary()
    boundary_geometry(boundary);rows=validate_candidates(candidate_seed(),boundary)
    root.mkdir(parents=True)
    for folder in ('candidates','imagery_review','drafts','reviews','accepted','rejected','reports'):
        (root/folder).mkdir()
    write_new(root/'boundary_original.geojson',boundary)
    write_new(root/'workspace.json',dict(schema=1,boundary_sha256=sha(boundary),block_m=5000,buffer_m=120,seed=42,crs='EPSG:32646',resolution_m=30))
    write_new(root/'candidates/inventory.json',rows)
    with (root/'candidates/inventory.csv').open('x',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write_new(root/'drafts/revision_000000.geojson',dict(collection(),revision=0,events=[]))
    export(root,root/'reports/initial')
    return root


def latest(root):
    root=Path(root);config=read(root/'workspace.json');boundary=read(root/'boundary_original.geojson')
    if sha(boundary)!=config['boundary_sha256']: raise ValueError('Boundary changed since session creation')
    return read(sorted((root/'drafts').glob('revision_*.geojson'))[-1]),boundary


def commit(root,document,event):
    document=copy.deepcopy(document);document['revision']+=1
    event=dict(event,at=now(),revision=document['revision'])
    document['events'].append(event)
    path=Path(root)/'drafts'/f"revision_{document['revision']:06d}.geojson"
    write_new(path,document)
    return path


def geometry_check(feature,boundary):
    g=shape(feature.get('geometry'))
    if g.is_empty or not g.is_valid or g.geom_type not in ('Polygon','MultiPolygon'): raise ValueError('Valid Polygon/MultiPolygon required')
    a,b,c,d=g.bounds
    if not (-180<=a<=c<=180 and -90<=b<=d<=90): raise ValueError('Coordinates must be WGS84 longitude/latitude')
    if not boundary_geometry(boundary).covers(g): raise ValueError('Annotation is outside the original district boundary')
    project=Transformer.from_crs(4326,32646,always_xy=True).transform
    metric=transform(g,project,interleaved=False);block=block_for(metric.bounds,5000,120)
    if block is None: raise ValueError('Polygon crosses a block core or its 120 m buffer')
    return dict(block=block,partition=partition(block,42),area_m2=metric.area)


def import_drafts(root,geojson):
    document,boundary=latest(root);incoming=read(geojson)
    if incoming.get('type')!='FeatureCollection' or incoming.get('crs'): raise ValueError('RFC 7946 FeatureCollection required')
    candidate_ids={r['candidate_id'] for r in candidates(root)}
    by_id={f['properties']['label_id']:f for f in document['features']}
    seen=set()
    for f in incoming['features']:
        p=f.setdefault('properties',{});identity=p.get('label_id')
        if not isinstance(identity,str) or not identity.strip() or identity in seen: raise ValueError('Unique stable label_id required')
        if p.get('candidate_id') not in candidate_ids: raise ValueError('Associate a recorded candidate ID first')
        seen.add(identity);geometry_check(f,boundary)
        # Edits always invalidate past acceptance; no state is imported from a browser.
        p['annotation_state']='draft';p['reviewed']=False;p.pop('second_reviewer',None)
        p.pop('review_snapshot',None)
        by_id[identity]=f
    values=list(by_id.values())
    for i,f in enumerate(values):
        for other in values[:i]:
            if shape(f['geometry']).intersection(shape(other['geometry'])).area>0: raise ValueError('Duplicate or overlapping polygons')
    document['features']=values
    return commit(root,document,dict(action='import_drafts',labels=sorted(seen),note='Prior review invalidated for edited labels'))


def evidence_errors(feature):
    """First-review readiness, without inventing a second reviewer to satisfy admission."""
    from config.settings import BEFORE,AFTER
    p=feature['properties'];issues=[]
    check=copy.deepcopy(feature);check['properties']['reviewed']=True
    try: load_labels(collection([check]))
    except (ValueError,KeyError,TypeError) as exc: issues.append(str(exc))
    if p.get('synthetic') is not False or p.get('independent_reference') is not True or p.get('target_definition')!=TARGET:
        issues.append('Explicit real independent target-aligned evidence required')
    for key,season in (('before_evidence_date',BEFORE),('after_evidence_date',AFTER)):
        try:
            d=p.get(key,'');date.fromisoformat(d)
            if not season.start<=d<season.end: issues.append(f'{key}: outside seasonal window')
        except (ValueError,TypeError): issues.append(f'{key}: actual acquisition date required')
    accuracy=p.get('spatial_accuracy_m')
    if isinstance(accuracy,bool) or not isinstance(accuracy,(int,float)) or not np.isfinite(accuracy) or not 0<=accuracy<=30:
        issues.append('Document positional error <=30 m; unknown is not zero')
    urls=p.get('evidence_urls')
    if not isinstance(urls,list) or not urls or any(not isinstance(u,str) or not u.startswith(('http://','https://')) for u in urls):
        issues.append('Independent evidence URLs required')
    if not p.get('independent_evidence_note'): issues.append('Explain independent evidence and interpretation method')
    if not p.get('evidence_license_note'): issues.append('Record evidence access and redistribution restrictions')
    return issues


def review(root,label_id,action,reviewer,notes,independent=False):
    if not reviewer.strip() or not notes.strip(): raise ValueError('Actual reviewer identifier and decision notes required')
    document,boundary=latest(root)
    feature=next((f for f in document['features'] if f['properties']['label_id']==label_id),None)
    if feature is None: raise ValueError('Unknown annotation ID')
    p=feature['properties'];state=p.get('annotation_state','draft')
    event=dict(label_id=label_id,action=action,reviewer=reviewer.strip(),notes=notes,independent=independent,
               feature_sha256=sha(dict(geometry=feature['geometry'],properties={k:v for k,v in p.items() if k not in ('annotation_state','review_snapshot','second_reviewer','reviewed')})))
    if action=='submit':
        if state not in ('draft','awaiting_evidence','disagreement'): raise ValueError('Cannot submit from current state')
        if not independent: raise ValueError('Attest actual independent evidence review with --independent')
        p['reviewer']=reviewer.strip();p['reviewed']=True
        geometry_check(feature,boundary);issues=evidence_errors(feature)
        p['annotation_state']='awaiting_evidence' if issues else 'awaiting_second_review'
        p['review_snapshot']=sha(dict(geometry=feature['geometry'],evidence={k:v for k,v in p.items() if k not in ('annotation_state','review_snapshot','second_reviewer','reviewed')}))
        event['issues']=issues
    elif action in ('approve','disagree'):
        if state!='awaiting_second_review': raise ValueError('First review must complete before second review')
        if not independent or reviewer.strip().casefold()==p['reviewer'].strip().casefold(): raise ValueError('Different independently reviewing second reviewer required')
        current=sha(dict(geometry=feature['geometry'],evidence={k:v for k,v in p.items() if k not in ('annotation_state','review_snapshot','second_reviewer','reviewed')}))
        if current!=p.get('review_snapshot'): raise ValueError('Geometry or evidence changed after first review')
        if action=='disagree': p['annotation_state']='disagreement'
        else:
            p['second_reviewer']=reviewer.strip();p['reviewed']=True
            load_labels(collection([feature]));validate_references([p]);geometry_check(feature,boundary)
            p['annotation_state']='accepted'
    elif action=='reject':
        if state=='accepted': raise ValueError('Import a revised draft to reopen an accepted annotation')
        p['annotation_state']='rejected'
    else: raise ValueError('Unknown review action')
    event.update(from_state=state,to_state=p['annotation_state'])
    return commit(root,document,event)


def export(root,output):
    document,boundary=latest(root);output=Path(output)
    if output.exists(): raise ValueError('Choose a new export/report directory')
    accepted=[];issues=[];counts={s:[0,0] for s in ('train','validation','test')};blocks={s:set() for s in counts}
    seen_sites={};states={s:0 for s in STATES}
    for f in document['features']:
        p=f['properties'];state=p.get('annotation_state','draft');states[state]+=1
        if state!='accepted': continue
        try:
            info=geometry_check(f,boundary);load_labels(collection([f]));validate_references([p])
            events=[e for e in document['events'] if e.get('label_id')==p['label_id']]
            if not events or events[-1].get('action')!='approve' or events[-1].get('to_state')!='accepted':
                raise ValueError('Missing completed second-review decision')
            current=sha(dict(geometry=f['geometry'],evidence={k:v for k,v in p.items() if k not in ('annotation_state','review_snapshot','second_reviewer','reviewed')}))
            if current!=p.get('review_snapshot'): raise ValueError('Accepted evidence changed')
            site=p.get('site_id') or p['candidate_id']
            if site in seen_sites and seen_sites[site]!=info['partition']: raise ValueError('Same site spans data partitions')
            seen_sites[site]=info['partition'];accepted.append(f)
            counts[info['partition']][p['label']]+=1;blocks[info['partition']].add(info['block'])
        except (ValueError,KeyError,TypeError) as exc: issues.append(dict(label_id=p['label_id'],error=str(exc)))
    if accepted: load_labels(collection(accepted))
    # Fail closed for the entire accepted export if any claimed acceptance is invalid.
    if issues: accepted=[];counts={s:[0,0] for s in counts};blocks={s:set() for s in blocks}
    output.mkdir(parents=True)
    write_new(output/'accepted.geojson',collection(accepted))
    write_new(output/'drafts.geojson',collection(document['features']))
    write_new(output/'reviewer_decisions.json',document['events'])
    write_new(output/'rejected.json',[f for f in document['features'] if f['properties'].get('annotation_state')=='rejected'])
    summary=dict(revision=document['revision'],accepted_polygons=len(accepted),states=states,
        accepted_by_class_partition=counts,independent_blocks={s:sorted(b) for s,b in blocks.items()},
        independent_site_count=len(seen_sites) if accepted else 0,issues=issues,
        boundary_sha256=sha(boundary),boundary_source=GAUL,boundary_simplified=False,
        real_dataset_ready=bool(accepted) and not issues and all(min(c)>0 for c in counts.values()),
        note='Counts are polygons/sites/blocks, not independent pixels. Human identity and evidence truth are not authenticated.')
    write_new(output/'admission_report.json',summary)
    write_new(output/'evidence_summary.json',[dict(label_id=f['properties']['label_id'],candidate_id=f['properties']['candidate_id'],
        evidence_urls=f['properties'].get('evidence_urls',[]),before=f['properties'].get('before_evidence_date'),
        after=f['properties'].get('after_evidence_date'),state=f['properties'].get('annotation_state')) for f in document['features']])
    return summary


def validate_points(points,min_distance_m=60):
    project=Transformer.from_crs(4326,32646,always_xy=True).transform;values=[]
    for f in points['features']:
        g=shape(f['geometry'])
        if g.geom_type!='Point' or g.is_empty or not (-180<=g.x<=180 and -90<=g.y<=90): raise ValueError('Valid WGS84 points required')
        p=transform(g,project,interleaved=False)
        if any(p.distance(other)<min_distance_m for other in values): raise ValueError('Duplicate or too-close sampled points')
        values.append(p)
    return len(values)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('init');a.add_argument('root');a.add_argument('--boundary-file')
    a=sub.add_parser('import-drafts');a.add_argument('root');a.add_argument('geojson')
    a=sub.add_parser('import-candidates');a.add_argument('root');a.add_argument('inventory')
    a=sub.add_parser('review');a.add_argument('root');a.add_argument('label_id');a.add_argument('action',choices=['submit','approve','disagree','reject'])
    a.add_argument('--reviewer',required=True);a.add_argument('--notes',required=True);a.add_argument('--independent',action='store_true')
    a=sub.add_parser('export');a.add_argument('root');a.add_argument('output')
    a=sub.add_parser('map');a.add_argument('root');a.add_argument('output');a.add_argument('--point',nargs=2,type=float);a.add_argument('--radius-m',type=int,default=300);a.add_argument('--live',action='store_true')
    a=sub.add_parser('export-plan');a.add_argument('root');a.add_argument('coverage');a.add_argument('output');a.add_argument('--point',nargs=2,type=float,required=True);a.add_argument('--radius-m',type=int,default=300)
    args=vars(p.parse_args());command=args.pop('command')
    if command in ('map','export-plan'):
        from .annotation_map import review_map,paired_export_plan
        result={'map':review_map,'export-plan':paired_export_plan}[command](**args)
    else: result={'init':init,'import-drafts':import_drafts,'import-candidates':import_candidates,'review':review,'export':export}[command](**args)
    print(result)


if __name__=='__main__':main()
