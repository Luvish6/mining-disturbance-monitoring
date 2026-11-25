import csv
import copy
import pytest
from src.phase25.review_import import FIELDS
from src.phase25.review_analysis import read_submission,analyze


def sheet(path,person,values):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
        for rid,value in values:
            w.writerow(dict(review_id=rid,reviewer_id=person,review_time_utc='2026-01-01T00:00:00Z',visible_disturbance=value,change_type='excavation_like',image_quality='GOOD',reviewer_confidence='MEDIUM',mining_attribution='UNKNOWN',notes=''))


def test_join_by_id_preserves_original_and_incomplete(tmp_path):
    a=tmp_path/'A.csv';b=tmp_path/'B.csv';ids=['R1','R2','R3']
    sheet(a,'A',[('R1','YES'),('R2','NO'),('R3','')]);sheet(b,'B',[('R3','YES'),('R2','NO'),('R1','YES')]);raw=a.read_bytes()
    A,_=read_submission(a,ids);B,_=read_submission(b,ids)
    rows,s=analyze(A,B,[dict(review_id=k) for k in ids]);r={x['review_id']:x for x in rows}
    assert s['complete_disturbance_pairs']==2 and s['cohens_kappa']==1
    assert r['R1']['consensus']=='CONSENSUS_DISTURBANCE' and r['R2']['consensus']=='CONSENSUS_NO_DISTURBANCE'
    assert r['R3']['consensus']=='INCOMPLETE' and r['R3']['review_A']['visible_disturbance']==''
    assert s['priority_ids']==['R1'] and a.read_bytes()==raw
    assert all(x['reference_label'] is None and x['admission_status']=='NOT_ADMITTED' for x in rows)


@pytest.mark.parametrize('values',[[('R1','YES'),('R1','NO')],[('R1','YES')],[('R1','YES'),('foreign','NO')]])
def test_duplicate_missing_foreign_ids_rejected(tmp_path,values):
    p=tmp_path/'bad.csv';sheet(p,'A',values)
    with pytest.raises(ValueError,match='IDs'):read_submission(p,['R1','R2'])


def test_unknown_category_attribution_and_future_time_rejected(tmp_path):
    p=tmp_path/'bad.csv';sheet(p,'A',[('R1','MAYBE')])
    with pytest.raises(ValueError,match='category'):read_submission(p,['R1'])
    sheet(p,'A',[('R1','YES')]);p.write_text(p.read_text().replace('UNKNOWN','MINING'))
    with pytest.raises(ValueError,match='attribution'):read_submission(p,['R1'])
    sheet(p,'A',[('R1','YES')]);p.write_text(p.read_text().replace('2026-01-01','9999-01-01'))
    with pytest.raises(ValueError,match='timestamp'):read_submission(p,['R1'])


def test_unusable_and_low_confidence_never_admitted_or_prioritized(tmp_path):
    a=tmp_path/'A.csv';b=tmp_path/'B.csv';sheet(a,'A',[('R1','YES'),('R2','NO')]);sheet(b,'B',[('R1','YES'),('R2','NO')])
    A,_=read_submission(a,['R1','R2']);B,_=read_submission(b,['R1','R2'])
    A['R1']['reviewer_confidence']='LOW';B['R2']['image_quality']='UNUSABLE'
    rows,s=analyze(A,B,[dict(review_id='R1'),dict(review_id='R2')])
    assert s['priority_ids']==[] and s['admitted_negative_labels']==s['admitted_positive_labels']==0
    assert all(r['reference_label'] is None and r['mining_attribution']=='UNKNOWN' and r['excavation_like_flag'] for r in rows)
    assert 'IMAGERY_NOT_USABLE_BY_BOTH_REVIEWERS' in rows[1]['blockers']


def test_same_reviewer_rejected_and_undefined_kappa_kept(tmp_path):
    a=tmp_path/'A.csv';b=tmp_path/'B.csv';sheet(a,'A',[('R1','NO')]);sheet(b,'B',[('R1','NO')])
    A,_=read_submission(a,['R1']);B,_=read_submission(b,['R1'])
    _,s=analyze(A,B,[dict(review_id='R1')]);assert s['cohens_kappa'] is None
    B['R1']['reviewer_id']='a'
    with pytest.raises(ValueError,match='Same submitted'):analyze(A,B,[dict(review_id='R1')])
