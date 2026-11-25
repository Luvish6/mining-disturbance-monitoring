import csv
import copy
import json
from pathlib import Path

import pytest

from src.phase25.review_import import FIELDS,reconcile
from scripts.phase25c1_readiness import candidate
from scripts.phase25b_cached import BANDS


def sheet(path,person='A',complete=False,visible='YES'):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
        for rid in ['R1','R2']:
            r=dict.fromkeys(FIELDS,'');r.update(review_id=rid,reviewer_id=person,mining_attribution='UNKNOWN')
            if complete:r.update(review_time_utc='2026-01-01T00:00:00Z',visible_disturbance=visible,change_type='excavation_like',image_quality='GOOD',reviewer_confidence='HIGH')
            w.writerow(r)


def test_original_blanks_stay_pending_and_unchanged(tmp_path):
    a=tmp_path/'a.csv';b=tmp_path/'b.csv';sheet(a);sheet(b,'B');raw=a.read_bytes()
    x=reconcile(a,b,['R1','R2'])
    assert x['pending']==2 and x['verified_labels']==0 and a.read_bytes()==raw
    assert all(r['reference_label'] is None and not r['verified_reference'] for r in x['rows'])
    assert x['rows'][0]['adjudication']['decision']==''


def test_agreement_never_promotes_mining_and_identity_independence(tmp_path):
    a=tmp_path/'a.csv';b=tmp_path/'b.csv';sheet(a,'Person One',True);sheet(b,'Person Two',True)
    x=reconcile(a,b,['R1','R2']);assert x['interpretation_agreements']==2 and x['verified_labels']==0
    assert all(r['mining_attribution']=='UNKNOWN' for r in x['rows'])
    sheet(b,'person one',True)
    with pytest.raises(ValueError,match='independent'):reconcile(a,b,['R1','R2'])


def test_disagreement_needs_adjudication_and_no_fabricated_decision(tmp_path):
    a=tmp_path/'a.csv';b=tmp_path/'b.csv';sheet(a,'Person One',True);sheet(b,'Person Two',True,'NO')
    x=reconcile(a,b,['R1','R2']);assert x['disagreements']==2
    assert all(r['adjudication']['decision']=='' for r in x['rows'])


def test_bad_ids_attribution_and_placeholder_rejected(tmp_path):
    a=tmp_path/'a.csv';b=tmp_path/'b.csv';sheet(a,'A',True);sheet(b)
    with pytest.raises(ValueError,match='identity'):reconcile(a,b,['R1','R2'])
    sheet(a)
    with pytest.raises(ValueError,match='IDs'):reconcile(a,b,['R1','foreign'])
    a.write_text(a.read_text().replace('UNKNOWN','MINING'))
    with pytest.raises(ValueError,match='attribution'):reconcile(a,b,['R1','R2'])


def test_metadata_only_support_does_not_certify_pixels_or_labels():
    meta=dict(bands=BANDS,meta={s:dict(s2_days=[1704067200000 if s=='before' else 1735689600000],s1_scenes=3) for s in ['before','after']})
    row=dict(split='train',district='fixture',bounds=[0,0,1920,1920])
    x=candidate('1:1',row,meta,dict(joined=4),{},dict(eligible=True))
    assert x['pseudo_positive_support'].startswith('UNMEASURED')
    assert x['seasons']['before']['valid_pixel_coverage']=='UNMEASURED_METADATA_ONLY'
    bad=copy.deepcopy(meta);bad['meta']['before']['s2_days']=[1735689600000]
    with pytest.raises(ValueError,match='outside'):candidate('1:1',row,bad,dict(joined=4),{}, {})


def test_planner_has_no_acquisition_or_raster_decode_interface():
    import ast
    text=Path('scripts/phase25c1_readiness.py').read_text(encoding='utf-8-sig');tree=ast.parse(text)
    forbidden={'load','read_grid','read_development','getInfo','getDownloadURL','Initialize','request','acquire_lock'}
    for n in ast.walk(tree):
        if isinstance(n,ast.Call):
            name=n.func.id if isinstance(n.func,ast.Name) else n.func.attr if isinstance(n.func,ast.Attribute) else ''
            assert name not in forbidden
    assert '--acquire' not in text
