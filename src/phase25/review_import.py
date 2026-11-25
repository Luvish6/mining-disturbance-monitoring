"""Non-destructive import of blinded visible-change reviews, never mining labels."""
import csv
import json
from datetime import datetime,timezone
from pathlib import Path

from scripts.phase23i_review import SCHEMA
from src.phase25.dataset import sha

FIELDS=['review_id','reviewer_id','review_time_utc','visible_disturbance','change_type','image_quality','reviewer_confidence','mining_attribution','notes']
INTERPRETATION=['visible_disturbance','change_type','image_quality','reviewer_confidence']


def parse_sheet(path,ids):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=FIELDS:raise ValueError('Original review-sheet schema required')
        rows=list(reader)
    if len(rows)!=len(ids) or {r['review_id'] for r in rows}!=set(ids):raise ValueError('Missing, duplicate or foreign review IDs')
    result={};people=set()
    for r in rows:
        if None in r or any(not isinstance(v,str) for v in r.values()):raise ValueError('Malformed review row')
        if r['mining_attribution']!='UNKNOWN':raise ValueError('Visible interpretation cannot establish mining attribution')
        filled=any(r[k].strip() for k in INTERPRETATION)
        if filled:
            if any(r[k] not in SCHEMA[k] for k in INTERPRETATION):raise ValueError('Partial/invalid interpretation')
            person=r['reviewer_id'].strip()
            if len(person)<3 or person.upper() in {'UNKNOWN','REVIEWER A','REVIEWER B'}:raise ValueError('Actual reviewer identity required')
            try:t=datetime.fromisoformat(r['review_time_utc'].replace('Z','+00:00'))
            except ValueError:raise ValueError('Actual review timestamp required') from None
            if t.tzinfo is None or t.utcoffset().total_seconds()!=0 or t>datetime.now(timezone.utc):raise ValueError('Valid past UTC timestamp required')
            people.add(person.casefold())
        result[r['review_id']]=dict(**r,completed=filled)
    if len(people)>1:raise ValueError('One independent reviewer per sheet')
    return result,people


def reconcile(path_a,path_b,ids):
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate item roster')
    a,pa=parse_sheet(path_a,ids);b,pb=parse_sheet(path_b,ids)
    if pa&pb:raise ValueError('Reviewers must be independent people')
    rows=[]
    for rid in sorted(ids):
        ra,rb=a[rid],b[rid]
        status='PENDING_INPUT'
        if ra['completed'] and rb['completed']:
            status='INTERPRETATION_AGREEMENT_ONLY' if all(ra[k]==rb[k] for k in INTERPRETATION) else 'ADJUDICATION_REQUIRED'
        rows.append(dict(review_id=rid,review_A=ra,review_B=rb,status=status,
            mining_attribution='UNKNOWN',verified_reference=False,reference_label=None,
            adjudication=dict(adjudicator_id='',decision='',geometry_path='',independent_evidence_urls='',before_date='',after_date='',
                positional_uncertainty_m='',rights_confirmation='',notes=''),
            admission_status='NOT_ADMITTED; independent evidence, geometry and existing protocol gates required'))
    return dict(schema='minechange-blinded-review-import/1',rows=rows,
        originals={role:dict(filename=Path(p).name,sha256=sha(p)) for role,p in [('A',path_a),('B',path_b)]},verified_labels=0,
        pending=sum(r['status']=='PENDING_INPUT' for r in rows),
        interpretation_agreements=sum(r['status']=='INTERPRETATION_AGREEMENT_ONLY' for r in rows),
        disagreements=sum(r['status']=='ADJUDICATION_REQUIRED' for r in rows),
        warning='Shared-Sentinel visible-change review is not independent mining-reference admission')
