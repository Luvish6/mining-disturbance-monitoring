"""Offline coordinator-only join of completed blinded reviews; no labels or imagery acquisition."""
import argparse
import csv
import json
import math
from pathlib import Path
from scripts.phase25b_cached import backup_gate,digest,save
from src.phase25.review_analysis import read_submission,analyze
from src.phase25.review_import import FIELDS
from src.phase3.spatial import partition,block_for


def write_csv(path,rows,fields):
    with path.open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def run(a,b,destination):
    backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    plan=Path('outputs/phase25/datasets/25c1-plan-v1/plan.json')
    if digest(plan)!=plan.with_suffix('.sha256').read_text().strip():raise ValueError('Frozen plan changed')
    expected=json.loads(plan.read_bytes());review=Path('outputs/phase23i_review');crosspath=review/'crosswalk.json'
    if digest(crosspath)!=expected['review']['source_crosswalk_sha256']:raise ValueError('Candidate crosswalk changed')
    cross=json.loads(crosspath.read_bytes());ids=[r['review_id'] for r in cross]
    if len(ids)!=30 or set(ids)!=set(expected['review']['neutral_ids']):raise ValueError('Original 30-item roster required')
    frozen=json.loads(Path('docs/reports/phase22x-preregistration.json').read_bytes())['aois']
    for r in cross:
        if r['split'] not in ['train','validation'] or partition(r['aoi'])!=r['split']:raise ValueError('Frozen split/TEST guard failure')
        if r['aoi'] not in frozen or frozen[r['aoi']]['split']!=r['split'] or not frozen[r['aoi']]['guard']['eligible']:raise ValueError('Unverified frozen AOI')
        x,y=r['x'],r['y']
        if not all(isinstance(z,(int,float)) and math.isfinite(z) for z in [x,y]) or block_for([x-.01,y-.01,x+.01,y+.01])!=r['aoi']:raise ValueError('Candidate/block location mismatch')
    original_hashes={role:digest(p) for role,p in [('A',a),('B',b)]}
    A,_=read_submission(a,ids);B,_=read_submission(b,ids);rows,summary=analyze(A,B,cross)
    metadata=review/'s2_10m/metadata.json';sources=json.loads(metadata.read_bytes())
    if set(sources)!=set(ids):raise ValueError('Scene metadata mapping mismatch')
    for row in rows:
        rid=row['review_id'];png=review/'chips10'/f'{rid}.png'
        if not png.is_file() or any(not sources[rid].get(s,{}).get('ids') for s in ['before','after']):raise ValueError('Missing original reviewer image/source metadata')
        row['imagery']=dict(source='SHARED_SENTINEL_2_INPUT',png_path=png.as_posix(),png_sha256=digest(png),source_metadata_path=metadata.as_posix(),source_metadata_sha256=digest(metadata),independent_reference=False)
    out=Path(destination)
    if not out.resolve().is_relative_to(Path('outputs/phase25').resolve()):raise ValueError('Private Phase25 output required')
    out.mkdir(parents=True,exist_ok=False)
    for role,p in [('A',a),('B',b)]:
        with (out/f'original_review_{role}.csv').open('xb') as f:f.write(Path(p).read_bytes())
        if digest(p)!=original_hashes[role] or digest(out/f'original_review_{role}.csv')!=original_hashes[role]:raise ValueError('Original CSV changed during import')
    merged=[];queue=[]
    for r in rows:
        c=r['candidate'];flat=dict(review_id=r['review_id'],candidate_key=c['key'],aoi=c['aoi'],block_id=c['aoi'],split=c['split'],x=c['x'],y=c['y'],crs='EPSG:32646',source_type='SHARED_SENTINEL_2_INPUT',consensus=r['consensus'],priority_disturbance_review=r['priority_disturbance_review'],excavation_like_flag=r['excavation_like_flag'],mining_attribution='UNKNOWN',reference_label='',admission_status=r['admission_status'],blockers=';'.join(r['blockers']),preview_path=r['imagery']['png_path'])
        for role in ['A','B']:
            flat.update({role+'_'+k:r['review_'+role][k] for k in FIELDS if k!='review_id'})
            flat[role+'_missing_fields']=';'.join(r['review_'+role]['missing_fields'])
        merged.append(flat)
        rank=1 if r['priority_disturbance_review'] else 2 if r['excavation_like_flag'] else 3 if r['consensus']=='INCOMPLETE' else 4 if r['consensus'] in ['CONFLICTING','CONSENSUS_UNCERTAIN'] else 5
        queue.append(dict(review_id=r['review_id'],priority=rank,candidate_key=c['key'],block_id=c['aoi'],split=c['split'],consensus=r['consensus'],excavation_like_flag=r['excavation_like_flag'],blockers=';'.join(r['blockers']),next_action='Complete missing response' if r['consensus']=='INCOMPLETE' else 'Obtain independent dated evidence and mining attribution; adjudicate without scores',adjudicator_id='',decision='',independent_evidence_urls='',before_evidence_date='',after_evidence_date='',polygon_path='',positional_uncertainty_m='',rights_confirmation='',reviewer_identity_confirmation='',notes=''))
    queue.sort(key=lambda r:(r['priority'],not r['excavation_like_flag'],r['review_id']))
    write_csv(out/'merged_reviews.csv',merged,list(merged[0]));write_csv(out/'adjudication_queue.csv',queue,list(queue[0]))
    save(out/'interpretation_records.json',dict(rows=rows,verified_labels=0))
    summary['priority_blocks']={r['review_id']:dict(block=r['candidate']['aoi'],split=r['candidate']['split']) for r in rows if r['priority_disturbance_review']}
    summary['reviewed_block_counts']={s:len({r['candidate']['aoi'] for r in rows if r['candidate']['split']==s}) for s in ['train','validation']}
    save(out/'consensus_summary.json',summary)
    save(out/'receipt.json',dict(original_sha256=original_hashes,crosswalk_sha256=digest(crosspath),plan_sha256=digest(plan),outputs={p.name:digest(p) for p in out.iterdir() if p.is_file()},originals_unchanged=True,labels_created=False,test_access=False))
    (out/'README.md').write_text('Coordinator-only review integration. Preserve originals. Join is by review_id. All mining attribution UNKNOWN; no reference labels admitted. A/B identities are unconfirmed pseudonyms. LIMITED imagery is usable-rated with limitations, not certified reference quality. Do not send unblinded candidate/block mappings or adjudication material to new blinded reviewers.\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('review_a');p.add_argument('review_b');p.add_argument('output');args=p.parse_args();run(args.review_a,args.review_b,args.output)
