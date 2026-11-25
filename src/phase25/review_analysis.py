"""Analysis-only intake of submitted blinded reviews; never reference admission."""
import csv
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from src.phase25.review_import import FIELDS,INTERPRETATION,SCHEMA
from src.phase3.admission import validate_references

CATEGORIES=SCHEMA['visible_disturbance']


def read_submission(path,ids):
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate roster IDs')
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=FIELDS:raise ValueError('Original submission schema required')
        rows=list(reader)
    if len(rows)!=len(ids) or {r.get('review_id') for r in rows}!=set(ids):raise ValueError('Missing, duplicate or foreign review IDs')
    result={};people=set()
    for r in rows:
        if None in r or any(not isinstance(v,str) for v in r.values()):raise ValueError('Malformed row')
        if r['mining_attribution']!='UNKNOWN':raise ValueError('Mining attribution must remain UNKNOWN')
        for k in INTERPRETATION:
            if r[k] and r[k] not in SCHEMA[k]:raise ValueError('Invalid category: '+k)
        missing=[k for k in INTERPRETATION if not r[k]]
        if not r['reviewer_id'].strip():raise ValueError('Missing submitted reviewer identifier')
        people.add(r['reviewer_id'].strip().casefold())
        if r['review_time_utc']:
            try:t=datetime.fromisoformat(r['review_time_utc'].replace('Z','+00:00'))
            except ValueError:raise ValueError('Invalid UTC review timestamp') from None
            if t.tzinfo is None or t.utcoffset().total_seconds()!=0 or t>datetime.now(timezone.utc):raise ValueError('Invalid UTC review timestamp')
        else:missing.append('review_time_utc')
        # Short pseudonyms remain usable for descriptive analysis only, not identity certification.
        result[r['review_id']]=dict(r,missing_fields=missing,complete=not missing)
    if len(people)!=1:raise ValueError('One submitted reviewer identifier per file required')
    return result,people


def analyze(a,b,crosswalk):
    ids=[r['review_id'] for r in crosswalk]
    if set(a)!=set(ids) or set(b)!=set(ids) or len(ids)!=len(set(ids)):raise ValueError('Review-to-candidate mapping mismatch')
    if {r['reviewer_id'].strip().casefold() for r in a.values()} & {r['reviewer_id'].strip().casefold() for r in b.values()}:raise ValueError('Same submitted reviewer in both files')
    matrix=[[0]*len(CATEGORIES) for _ in CATEGORIES];rows=[]
    for c in sorted(crosswalk,key=lambda r:r['review_id']):
        rid=c['review_id'];ra,rb=a[rid],b[rid];va,vb=ra['visible_disturbance'],rb['visible_disturbance']
        if va and vb:matrix[CATEGORIES.index(va)][CATEGORIES.index(vb)]+=1
        complete=ra['complete'] and rb['complete']
        status='INCOMPLETE'
        if complete:
            status={'YES':'CONSENSUS_DISTURBANCE','NO':'CONSENSUS_NO_DISTURBANCE','UNCERTAIN':'CONSENSUS_UNCERTAIN'}[va] if va==vb else 'CONFLICTING'
        usable=all(r['image_quality'] in ['GOOD','LIMITED'] for r in [ra,rb])
        confidence=all(r['reviewer_confidence'] in ['MEDIUM','HIGH'] for r in [ra,rb])
        priority=status=='CONSENSUS_DISTURBANCE' and usable and confidence
        excavation=any(r['change_type']=='excavation_like' for r in [ra,rb])
        try:validate_references([dict(synthetic=False,independent_reference=False)])
        except ValueError as exc:gate_error=str(exc)
        else:raise AssertionError('Shared-input review unexpectedly passed admission')
        reasons=['SHARED_SENTINEL_INPUT_NOT_INDEPENDENT_REFERENCE','MINING_ATTRIBUTION_UNKNOWN','NO_REFERENCE_POLYGON_OR_INDEPENDENT_PAIRED_EVIDENCE','POSITIONAL_ACCURACY_AND_RIGHTS_UNDOCUMENTED','REVIEWER_IDENTITIES_AND_INDEPENDENCE_UNCONFIRMED']
        if not complete:reasons.append('INCOMPLETE_SUBMISSION')
        if not usable:reasons.append('IMAGERY_NOT_USABLE_BY_BOTH_REVIEWERS')
        if not confidence:reasons.append('CONFIDENCE_BELOW_MEDIUM_OR_MISSING')
        if status in ['CONFLICTING','CONSENSUS_UNCERTAIN']:reasons.append('INTERPRETATION_ADJUDICATION_REQUIRED')
        if excavation:reasons.append('EXCAVATION_LIKE_REQUIRES_INDEPENDENT_MINING_ATTRIBUTION')
        rows.append(dict(review_id=rid,candidate=c,review_A=ra,review_B=rb,consensus=status,usable_imagery_reported_by_both=usable,both_confidence_at_least_medium=confidence,priority_disturbance_review=priority,excavation_like_flag=excavation,mining_attribution='UNKNOWN',reference_label=None,admission_status='NOT_ADMITTED',admission_gate_error=gate_error,blockers=reasons))
    n=sum(map(sum,matrix));agree=sum(matrix[i][i] for i in range(len(CATEGORIES)))
    observed=agree/n if n else None
    expected=sum(sum(matrix[i])*sum(row[i] for row in matrix) for i in range(len(CATEGORIES)))/n**2 if n else None
    kappa=(observed-expected)/(1-expected) if n and expected!=1 else None
    distributions={role:{field:dict(Counter(r[field] or 'MISSING' for r in source.values())) for field in INTERPRETATION} for role,source in [('A',a),('B',b)]}
    summary=dict(matched_ids=len(rows),complete_disturbance_pairs=n,fully_complete_pairs=sum(r['review_A']['complete'] and r['review_B']['complete'] for r in rows),agreement_pairs=agree,disagreement_pairs=n-agree,agreement_fraction=observed,expected_chance_agreement=expected,cohens_kappa=kappa,kappa_definition='Unweighted three-category complete-disturbance-pair kappa; neither reviewer is ground truth',categories=CATEGORIES,confusion_matrix_rows_A_columns_B=matrix,consensus_counts=dict(Counter(r['consensus'] for r in rows)),distributions=distributions,priority_ids=[r['review_id'] for r in rows if r['priority_disturbance_review']],excavation_like_ids=[r['review_id'] for r in rows if r['excavation_like_flag']],unusable_by_either=sum(any(s['image_quality']=='UNUSABLE' for s in [r['review_A'],r['review_B']]) for r in rows),incomplete_ids=[r['review_id'] for r in rows if r['consensus']=='INCOMPLETE'],admitted_positive_labels=0,admitted_negative_labels=0,operational_alerts=0,independent_reviewer_identity_status='UNCONFIRMED; submitted A/B are pseudonyms',interpretation='Visible-disturbance agreement only; not mining accuracy or independent reference truth')
    return rows,summary
