"""Phase25C.1 metadata-only expansion planner; no acquisition or raster reads."""
import argparse
import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path

from scripts.phase25b_cached import backup_gate,frozen,guarded,digest,save,PLAN,BANDS
from src.phase25.dataset import spatial_check,windows
from src.phase25.review_import import reconcile

OUT=Path('outputs/phase25/datasets/25c1-plan-v1')
REVIEW=Path('outputs/phase23i_review')


def candidate(key,row,meta,follow,files,guard):
    if meta['bands']!=BANDS:raise ValueError('Unexpected legacy cache schema')
    seasons={}
    for name,start,end in [('before','2023-11-01','2024-04-01'),('after','2024-11-01','2025-04-01')]:
        m=meta['meta'][name];dates=[datetime.fromtimestamp(int(t)/1000,timezone.utc).date().isoformat() for t in m['s2_days']]
        if any(not start<=d<end for d in dates):raise ValueError('Metadata dates outside frozen season')
        if m['s1_scenes']<1 or not dates:raise ValueError('Missing source-scene support')
        seasons[name]=dict(s1_scene_count=m['s1_scenes'],s2_items=len(dates),s2_independent_days=len(set(dates)),
            s2_first_date=min(dates),s2_last_date=max(dates),exact_original_ids='INCOMPLETE',valid_pixel_coverage='UNMEASURED_METADATA_ONLY')
    if not isinstance(follow.get('joined'),int) or follow['joined']<1:raise ValueError('Missing follow-up metadata support')
    return dict(aoi=key,split=row['split'],district=row['district'],bounds=row['bounds'],guard=guard,
        seasons=seasons,follow=dict(window=['2025-11-01','2026-04-01'],items=follow['joined'],exact_ids_and_dates='INCOMPLETE',valid_coverage='UNMEASURED'),
        caches=files,pseudo_positive_support='UNMEASURED; no masks or outcome tables read',
        intended_hypotheses=['mining-context disturbance where independently documented','potential stable background','challenging non-mining explanations'],
        hypothesis_admission='UNKNOWN until evidence; strata do not create labels')


def acquisition_contract(plan_sha):
    return dict(schema='minechange-missing-context-contract/1',plan_sha256=plan_sha,authorized=False,
        reference_contract=dict(path='docs/reports/phase25b1-preregistration.json',sha256=digest('docs/reports/phase25b1-preregistration.json')),
        sources=dict(elevation='USGS/SRTMGL1_003',land_cover='ESA/WorldCover/v200/2021',rain='UCSB-CHG/CHIRPS/DAILY',surface_water='JRC/GSW1_4/GlobalSurfaceWater'),
        seasons=dict(before=['2023-11-01','2024-04-01'],after=['2024-11-01','2025-04-01'],follow=['2025-11-01','2026-04-01']),
        grid='Each preregistered64x64 AOI,30m north-up EPSG32646, exact bounds/affine from plan; no replacement locations',
        support='SRTM~30m/2000; WorldCover10m/2021; CHIRPS0.05degree seasonal totals152/151days; JRC30m/1984-2021; native-support nearest sampling is not new30m information',
        metadata='Current before/after S1/S2 and follow-up S2 IDs/timestamps/settings; requery corroborates but cannot certify original cache membership',
        sar='Metadata only: existing descending relative-orbit77 filters; no new SAR imagery or mixing',
        quality='Reuse B1 count/mask/class checks unchanged; missing JRC stays missing; no new thresholds or pseudo replay',
        caps=dict(requests=60,response_body_bytes=100_000_000,per_response_bytes=2_000_000,all_attempts_counted=True),
        rights='Copernicus/SRTM/WorldCoverCCBY4/CHIRPS/JRC conditions retained; private use only, no release approval',
        stop='Separate acquisition approval required; preserve meter/lock across retries; no fallback AOIs or known failed source repeats')


def plan(backup):
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='phase25-minechange-india':raise ValueError('Wrong branch')
    subprocess.run(['git','merge-base','--is-ancestor','60fdc9b','HEAD'],check=True)
    if subprocess.check_output(['git','rev-parse','pre-minechange-india^{commit}'],text=True).strip()!='08604dea4fe39641ea32ebda8a37532669b52933':raise ValueError('Stable tag changed')
    if OUT.exists():raise ValueError('No overwrite')
    if Path('outputs/phase25/receipts/.acquire.lock').exists():raise ValueError('Acquisition active; stop')
    hashes=backup_gate(backup);frozen(PLAN,hashes);original=json.loads(PLAN.read_bytes())
    from scripts.phase22n_temporal import guards
    area,protected=guards();rows=[];metadata_hashes={};rejected=[]
    # Full roster from prior preregistration, not ordered/filtered by foreground or outcomes.
    for key,row in sorted(original['aois'].items()):
        if row['split'] not in ('train','validation'):continue
        try:g=guarded(key,row,area,protected)
        except ValueError:
            rejected.append(dict(aoi=key,reason='FROZEN_FULL_FOOTPRINT_GUARD'));continue
        stem=key.replace(':','_');xm=Path('outputs/phase22x_landscape')/(stem+'_meta.json');ym=Path('outputs/phase22y_persistence')/(stem+'_meta.json')
        xp=xm.with_name(stem+'.npy');yp=ym.with_name(stem+'.npy')
        if not all(p.exists() for p in [xm,ym,xp,yp]):
            rejected.append(dict(aoi=key,reason='MISSING_CACHE_OR_SIDECAR'));continue
        for p in [xm,ym]:
            frozen(p,hashes)
            copy=Path(backup)/'project_parent'/'mining_monitor_phase1'/p
            if digest(copy)!=digest(p):raise ValueError('Backup metadata copy mismatch')
            metadata_hashes[p.as_posix()]=digest(p)
        files={p.as_posix():dict(bytes=p.stat().st_size,payload_status='NOT_OPENED') for p in [xp,yp]}
        rows.append(candidate(key,row,json.loads(xm.read_bytes()),json.loads(ym.read_bytes()),files,g))
    patches=[]
    for a in rows:
        left,bottom,right,top=a['bounds']
        for r,c,h,w in windows():
            x=left+c*30;y=top-r*30
            patches.append(dict(patch_id='planned_'+a['aoi'].replace(':','_')+f'_r{r}_c{c}',group_id=a['aoi'],split=a['split'],
                shape=[h,w],crs='EPSG:32646',affine=[30,0,x,0,-30,y],bounds=[x,y-960,x+960,y],parent_bounds=a['bounds'],row_offset=r,col_offset=c))
    spatial_check(patches)
    old=json.loads(Path('outputs/phase25/experiments/25b-v1/selection.json').read_bytes())['aois']
    for a in rows:
        receipt=Path('outputs/phase25/datasets/25b1-v1')/a['aoi'].replace(':','_')/'integrated/receipt.json'
        if receipt.exists():
            from scripts.phase25b1_recover import cached_json
            r=cached_json(receipt);a['existing_context']={k:r['valid_cells'][k] for k in ['elevation','land_cover','rainfall','surface_water','fire_history','roads']}
        else:a['existing_context']='MISSING; no context acquired for this AOI'
    missing=[a for a in rows if not isinstance(a['existing_context'],dict)]
    missing.sort(key=lambda a:(0 if a['split']=='validation' else 1,__import__('hashlib').sha256(('42:25C1:'+a['aoi']).encode()).hexdigest()))
    frozen(REVIEW/'crosswalk.json',hashes)
    ids=json.loads((REVIEW/'crosswalk.json').read_bytes())
    if len(ids)!=30 or len({x['review_id'] for x in ids})!=30 or any(x['split'] not in ('train','validation') for x in ids):raise ValueError('Unexpected blinded review metadata')
    source_rows=[r for r in rows if r['aoi'] in {x['aoi'] for x in ids}]
    if {x['aoi'] for x in ids}-{r['aoi'] for r in source_rows}:raise ValueError('Review item outside eligible development roster')
    OUT.mkdir(parents=True,exist_ok=False)
    per_response=2_000_000;chunks=(len(rows)+1)//2
    request_estimate=4+chunks+len(missing)*2+10
    if request_estimate>60:raise ValueError('Proposed request budget infeasible; do not silently shrink roster')
    receipt=dict(schema='minechange-india-expansion-plan/1',status='PLAN_ONLY_NOT_AUTHORIZATION',seed=42,
        selection='ALL eligible existing frozen development AOIs; no mask/prediction/outcome reads',aois=rows,rejections=rejected,proposed_patches=patches,
        original_plan_sha256=digest(PLAN),metadata_hashes=metadata_hashes,existing_25c_parent_groups=old,
        priority=[a['aoi'] for a in missing],context_bands=['elevation','land_cover','rain_before_mm','rain_after_mm','rain_before_count','rain_after_count','water_occurrence'],
        proposed_acquisition=dict(authorized=False,context_exports=len(missing),source_metadata_chunks=chunks,
            estimated_requests_including_initialization_and_10_retry_reserve=request_estimate,
            raw_float32_context_bytes=len(missing)*64*64*7*4,
            planning_response_body_estimate_bytes=30_000_000,proposed_hard_requests=60,proposed_hard_bytes=100_000_000,per_response_cap=per_response,
            prerequisites='Separate approval, committed exact source/orbit/mask plan, one persistent metered lock; stop before caps; no replacements',
            no_retries_for='Known unsupported MODIS/roads/geology/mining-context layers; no repeat requests without new source evidence'),
        development_positive_support='UNKNOWN; neither VAL masks nor outcome tables inspected; includes all original VAL groups',
        grouping='Frozen seed42 5km/120m cores and protected TEST geometries; exhaustive non-overlapping32x32 crops',
        review=dict(items=len(ids),neutral_ids=sorted(x['review_id'] for x in ids),source_crosswalk_sha256=digest(REVIEW/'crosswalk.json'),
            interface='src.phase25.review_import.reconcile; interpretation only, no reference admission'),
        verified_labels=0,requests=0,downloads=0,training=0,release='NO-GO')
    save(OUT/'plan.json',receipt);(OUT/'plan.sha256').write_text(digest(OUT/'plan.json')+'\n',encoding='utf-8')
    summary=dict(eligible_aois=len(rows),by_split={s:dict(aois=sum(a['split']==s for a in rows),planned_patches=sum(a['split']==s for a in rows)*4,
        added_aois=sum(a['split']==s and a['aoi'] not in old for a in rows)) for s in ['train','validation']},
        context_cached_aois=sum(isinstance(a['existing_context'],dict) for a in rows),missing_context_aois=len(missing),
        metadata_source_bytes=sum(p.stat().st_size for p in [Path(x) for x in metadata_hashes]),
        unopened_cache_bytes=sum(x['bytes'] for a in rows for x in a['caches'].values()),rejected=len(rejected),
        estimated_requests=request_estimate,estimated_body_bytes=30_000_000,plan_sha256=digest(OUT/'plan.json'),requests=0)
    save(OUT/'acquisition-contract.json',acquisition_contract(digest(OUT/'plan.json')))
    (OUT/'acquisition-contract.sha256').write_text(digest(OUT/'acquisition-contract.json')+'\n',encoding='utf-8')
    save(OUT/'summary.json',summary);print(json.dumps(summary))


def import_reviews(a,b,out):
    out=Path(out)
    if not out.resolve().is_relative_to(Path('outputs/phase25').resolve()) or out.exists():raise ValueError('New private Phase25 output directory required')
    expected=json.loads((OUT/'plan.json').read_bytes())
    if digest(OUT/'plan.json')!=(OUT/'plan.sha256').read_text().strip():raise ValueError('Plan integrity failure')
    if digest(REVIEW/'crosswalk.json')!=expected['review']['source_crosswalk_sha256']:raise ValueError('Original review roster changed')
    cross=json.loads((REVIEW/'crosswalk.json').read_bytes())
    if len(cross)!=30 or any(x['split'] not in ('train','validation') for x in cross):raise ValueError('Development-only30-item roster required')
    result=reconcile(a,b,[x['review_id'] for x in cross])
    out.mkdir(parents=True,exist_ok=False);save(out/'interpretation_import.json',result)
    for name,path in [('submitted_A.csv',a),('submitted_B.csv',b)]:
        with (out/name).open('xb') as f:f.write(Path(path).read_bytes())
        if digest(out/name)!=result['originals']['A' if name=='submitted_A.csv' else 'B']['sha256']:raise ValueError('Review submission changed during import')
    save(out/'receipt.json',dict(import_sha256=digest(out/'interpretation_import.json'),source_crosswalk_sha256=digest(REVIEW/'crosswalk.json'),
        original_sheets=result['originals'],verified_labels=0,labels_created=False,blinded_review_ids_only=True))
    print(json.dumps({k:result[k] for k in ['pending','interpretation_agreements','disagreements','verified_labels']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--plan',action='store_true');g.add_argument('--import-reviews',nargs=2,metavar=('A_CSV','B_CSV'))
    p.add_argument('--backup');p.add_argument('--out');a=p.parse_args()
    if a.plan:
        if not a.backup:p.error('--backup required')
        plan(a.backup)
    else:
        if not a.out:p.error('--out required')
        import_reviews(*a.import_reviews,a.out)
