"""Small offline multi-layer pilot; reusable GEE graph exists but no online execution."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from scripts.phase25b_cached import backup_gate,digest,save,tif,CONFIG
from src.phase25.dataset import load_manifest,read_patch,BANDS
from src.phase25.features import Grid
from src.phase25.methodology import score_cached

ROOT=Path('outputs/phase25/datasets/25c2-v1')
MANIFEST_SHA='3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa'
RULE_SHA='f59a7d08541103f33fb28d8da7815ed13c1e3d1ee41dd3a4b9a9a9a58ac89186'


def run(destination):
    start=time.perf_counter();backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    if digest(ROOT/'manifest.json')!=MANIFEST_SHA or digest(CONFIG)!=RULE_SHA:raise ValueError('Frozen dataset/rules changed')
    if Path('outputs/phase25/receipts/.acquire.lock').exists():raise ValueError('Active acquisition lock')
    manifest=load_manifest(ROOT)
    # Hash order independent of labels, scores, reviewer outcomes and held-out performance.
    row=min((r for r in manifest['patches'] if r['split']=='train'),key=lambda r:hashlib.sha256(('42:25E1:'+r['patch_id']).encode()).hexdigest())
    record=read_patch(ROOT,row['patch_id'],allow_pseudo=True)
    cfg=json.loads(CONFIG.read_bytes());result=score_cached(record,cfg['rules'])
    review=Path('outputs/phase25/experiments/human-review-integration-v1');receipt=json.loads((review/'receipt.json').read_bytes())
    for name in ['consensus_summary.json','interpretation_records.json']:
        if digest(review/name)!=receipt['outputs'][name]:raise ValueError('Human-review receipt changed')
    human=json.loads((review/'consensus_summary.json').read_bytes());observations=json.loads((review/'interpretation_records.json').read_bytes())['rows']
    leads=[dict(review_id=r['review_id'],candidate_key=r['candidate']['key'],aoi=r['candidate']['aoi'],split=r['candidate']['split'],human_observation='CONSENSUS_VISIBLE_DISTURBANCE',mining_attribution='UNKNOWN',independent_reference_label=None,algorithm_score_at_review_location='NOT_EVALUATED_BY_THIS_SINGLE_PATCH_PILOT',excavation_like_flag=r['excavation_like_flag']) for r in observations if r['review_id'] in human['priority_ids']]
    if len(leads)!=5:raise ValueError('Preserve exactly five priority inspection leads')
    out=Path(destination)
    if not out.resolve().is_relative_to(Path('outputs/phase25/experiments').resolve()):raise ValueError('Isolated Phase25 output required')
    out.mkdir(parents=True,exist_ok=False)
    grid=Grid(row['crs'],tuple(row['affine']),tuple(row['shape']))
    tif(out/'evidence_count.tif',result['score'],grid,['EXPLORATORY_EVIDENCE_COUNT_NOT_MINING_PROBABILITY'])
    tif(out/'score_components.tif',result['components'],grid,result['component_names'])
    tif(out/'validity.tif',result['valid'].astype('uint8'),grid,['COMMON_SIGNAL_VALID'],dtype='uint8',nodata=255)
    summary=dict(version='25e1/1',selection='sha256(42:25E1:<patch_id>) minimum among frozen TRAIN patches; label-blind',patch_id=row['patch_id'],group_id=row['group_id'],split=row['split'],crs=row['crs'],affine=row['affine'],shape=row['shape'],eligible_cells=int(result['valid'].sum()),total_cells=int(result['valid'].size),eligible_percent=float(result['valid'].mean()*100),score_distribution={str(k):int((result['score']==k).sum()) for k in range(4)},score_semantics=result['score_semantics'],contexts=result['contexts'],alternative_explanations=result['alternatives'],preserved_pseudo_state_counts={str(k):int((record['pseudo_states']==k).sum()) for k in [0,1,255]},persistence='Existing retrospective pseudo-states kept separate. Follow-up NDVI/BSI are not stored as pilot input bands; no persistence inference from missing channels.',priority_review_leads=leads,independently_verified_references=0,human_reviewed_disturbance_leads=len(leads),operational_alerts=0,requests=0,download_bytes=0,training=False,elapsed_seconds=time.perf_counter()-start)
    save(out/'summary.json',summary)
    save(out/'source_provenance.json',json.loads((ROOT/row['provenance']).read_bytes()))
    save(out/'receipt.json',dict(manifest_sha256=MANIFEST_SHA,rules_sha256=RULE_SHA,human_review_receipt_sha256=digest(review/'receipt.json'),source_feature_sha256=digest(ROOT/row['files']['features']),source_counts_sha256=digest(ROOT/row['files']['counts']),outputs={p.name:digest(p) for p in out.iterdir() if p.is_file()},reference_labels_created=False,test_access=False))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');run(p.parse_args().output)
