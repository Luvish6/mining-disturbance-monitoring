"""Private multiclass packaging from frozen caches; no fitting or reference promotion."""
import json,time
from collections import Counter
from pathlib import Path
import numpy as np
import rasterio
from scripts.phase25b_cached import backup_gate,digest,save,tif
from scripts.phase25_multiclass_acquire import CONFIG,OUT as ACQ,NAMES,validate
from scripts.phase25b1_recover import cached_json
from src.phase25.dataset import load_manifest,BANDS,COUNTS
from src.phase25.features import Grid
from src.phase25.multiclass import evidence
ROOT=Path('outputs/phase25/datasets/25c2-v1')
OUT=Path('outputs/phase25/datasets/minechange-india-multiclass-v2')
FOLLOW=['follow_B4','follow_B3','follow_B2','follow_NDVI','follow_BSI','follow_NDWI','follow_count']

def build():
    start=time.perf_counter();backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125');cfg=json.loads(CONFIG.read_bytes())
    if digest(ROOT/'manifest.json')!=cfg['base_manifest_sha256']:raise ValueError('Original dataset changed')
    m=load_manifest(ROOT);rows={r['aoi']:r for r in cfg['aois']};bands=BANDS+COUNTS[:4]+FOLLOW+NAMES+['temporal_persistence'];totals={};groups={};patches=[];layers=Counter()
    OUT.mkdir(parents=True,exist_ok=False);hashes={};contexts={};follow={}
    for key,row in rows.items():
        p=Path('outputs/phase22y_persistence')/(key.replace(':','_')+'.npy')
        if digest(p)!=m['source_hashes'][p.as_posix()]:raise ValueError('Follow-up changed')
        f=np.load(p,allow_pickle=False).astype('float32');f[f==-9999]=np.nan
        if f.shape!=(7,64,64):raise ValueError('Follow-up grid shape')
        follow[key]=f;hashes[p.as_posix()]=digest(p)
        p=ACQ/key.replace(':','_')/'context.tif'
        if (p.parent/'receipt.json').exists():
            if digest(p)!=cached_json(p.parent/'receipt.json')['sha256']:raise ValueError('Context hash mismatch')
            contexts[key]=validate(p.read_bytes(),row);hashes[p.as_posix()]=digest(p)
        else:contexts[key]=np.full((len(NAMES),64,64),np.nan,dtype='float32')
    for row in m['patches']:
        key=row['group_id'];r,c=row['row_offset'],row['col_offset'];grid=Grid(row['crs'],tuple(row['affine']),tuple(row['shape']))
        arrays=[]
        for name in ['features','counts']:
            with rasterio.open(ROOT/row['files'][name]) as ds:
                a=ds.read().astype('float32');a[a==ds.nodata]=np.nan;arrays.append(a)
        x,counts=arrays;f=follow[key][:,r:r+32,c:c+32];context=contexts[key][:,r:r+32,c:c+32]
        v=dict(zip(BANDS,x));v.update(dict(zip(COUNTS,counts)));v.update(dict(zip(FOLLOW,f)));v.update(dict(zip(NAMES,context)))
        result=evidence(v,cfg['thresholds']);a=np.concatenate([x,counts[:4],f,context,result['persistence'][None]])
        if a.shape!=(len(bands),32,32):raise ValueError('Unified alignment failure')
        folder=OUT/'patches'/row['patch_id'];folder.mkdir(parents=True)
        tif(folder/'observations.tif',a,grid,bands);tif(folder/'weak_classes.tif',result['labels'],grid,['WEAK_CLASS_NOT_REFERENCE'],dtype='uint8',nodata=255)
        tif(folder/'evidence_scores.tif',result['scores'],grid,[cfg['classes'][str(k)] for k in range(5)])
        tif(folder/'confidence.tif',np.stack([result['confidence'],result['uncertainty']]),grid,['UNCALIBRATED_EVIDENCE_MARGIN','ABSTENTION_UNCERTAINTY'])
        tif(folder/'validity.tif',np.isfinite(a).astype('uint8'),grid,bands,dtype='uint8',nodata=255)
        inputs=[i for i,n in enumerate(bands) if n not in COUNTS[:4]+FOLLOW+['temporal_persistence']]
        np.savez_compressed(folder/'model_ready.npz',features=a[inputs],validity=np.isfinite(a[inputs]),weak_labels=result['labels'],label_valid=result['labels']!=255,confidence=result['confidence'],uncertainty=result['uncertainty'])
        count={str(k):int((result['labels']==k).sum()) for k in [0,1,2,3,4,255]};split=row['split'];totals.setdefault(split,Counter()).update(count)
        for k,n in count.items():
            if n:groups.setdefault(split,{}).setdefault(k,set()).add(key)
        for i,n in enumerate(bands):layers[n]+=int(np.isfinite(a[i]).sum())
        patches.append(dict(**row,multiclass_counts=count,output_folder=folder.relative_to(OUT).as_posix(),independent_reference=False,mining_attribution='UNKNOWN',observation_provenance_sha256=digest(ROOT/row['provenance']),new_files_sha256={p.name:digest(p) for p in folder.iterdir()}))
        target=OUT/'source_provenance'/Path(row['provenance']).name;target.parent.mkdir(exist_ok=True)
        if not target.exists():target.write_bytes((ROOT/row['provenance']).read_bytes())
    target=OUT/'context_provenance';target.mkdir()
    for p in ACQ.glob('metadata_*.json'):cached_json(p);(target/p.name).write_bytes(p.read_bytes())
    summary=dict(version=cfg['version'],patches=len(patches),patch_counts=dict(Counter(r['split'] for r in patches)),class_counts={s:dict(c) for s,c in totals.items()},class_group_support={s:{k:len(g) for k,g in d.items()} for s,d in groups.items()},groups=dict(Counter(r['split'] for r in cfg['aois'])),layer_support_cells=dict(layers),active_class_ids=[k for k in range(5) if sum(t.get(str(k),0) for t in totals.values())],unpopulated_classes=[cfg['classes'][str(k)] for k in range(5) if not sum(t.get(str(k),0) for t in totals.values())],elapsed_seconds=time.perf_counter()-start,verified_mining_labels=0,external_publication=False,operational_alerts=0)
    save(OUT/'summary.json',summary);save(OUT/'manifest.json',dict(schema=cfg['version'],bands=bands,model_input_bands=[bands[i] for i in inputs],package_version='v2-portable-counts-preserved',parent_package='minechange-india-multiclass-v1',annotation_only_bands=FOLLOW+['temporal_persistence'],quality_only_bands=COUNTS[:4],classes=cfg['classes'],patches=patches,source_hashes=hashes,original_manifest_sha256=cfg['base_manifest_sha256'],config_sha256=digest(CONFIG),label_semantics='WEAK_ALGORITHMIC_HYPOTHESES_NOT_REFERENCE',reference_labels=None,human_reviews='Separate immutable review package, not rasterized or used as labels',scene_provenance='Legacy original S1/S2/follow IDs INCOMPLETE; new context IDs are not retroactive original-source certification'))
    (OUT/'generation_config.json').write_bytes(CONFIG.read_bytes())
    card='''# MineChange-India private multiclass candidate

Weak algorithmic hypotheses, NOT verified mining labels or accuracy. Original80patches/20frozen5kmgroups, TRAIN/VAL unchanged; TEST excluded. Observations, masks, class evidence and abstention are separate. Model arrays exclude annotation-only follow-up/persistence bands. Dynamic World10m probabilities are model-derived S2 context, not independent truth. MODIS500m and CHIRPS0.05degree are coarse contextual samples, not independent30m evidence. Evidence margin is uncalibrated, not probability of correctness.

Class1 merges mining-like persistent exposure with unattributed landslide/road/other causes. It does not establish mining or legality. Specific agriculture/construction require strong temporal context. Unpopulated classes are unsupported, excluded from active taxonomy. Stable is not verified mining absence. No class quotas or fabricated missing values. Fire flags trigger abstention; missing fire does not mean no fire.

Feature validity is explicit NaN/mask. Source scene IDs and original legacy certification limitations retained. No independent reference labels exist; human reviews remain outside label generation. Scientific thresholds are fixed exploratory heuristics: inherited NDVI/BSI/SAR gates, strong Dynamic World0.6 context versus0.2before-built, all evidence conditions plus competing margin0.25. These cutoffs have not been field-calibrated.

Rights: Sentinel Copernicus attribution; SRTM NASA/USGS/JPL use policy; WorldCover CC-BY4; CHIRPS public domain/cite; JRC Copernicus/JRC/Google attribution; Dynamic World CC-BY4 Google/National Geographic Society/WRI attribution; MODIS LP DAAC unrestricted/cite. No blanket dataset license is asserted. Excluded: Bhoonidhi/Planet imagery, restricted derivatives/order metadata and reviewer personal information. Bhoonidhi assessments retained only as restricted-evidence references: rights, QA and positioning unresolved; protected TEST payloads unopened.

Release blocked on legacy source certification, independent reference/adjudication, competing-class geographic support and final rights/attribution review. Private candidate only; no external publication or DOI authorization. See redistribution.json and generation_config.json. Georeferenced TIFFs and array files use original32x32/30mEPSG:32646 windows; portable POSIX paths and original observation-count diagnostics retained; no class-rule changes from v1; retain native-support provenance when interpreting all context.
'''
    (OUT/'DATASET_CARD.md').write_text(card,encoding='utf-8')
    save(OUT/'redistribution.json',dict(private_only=True,excluded=['Planet/Bhoonidhi imagery, derivatives, private delivery metadata','reviewer identities/responses'],sources=cfg['rights'],source_contract='Original source_provenance files retain Copernicus/SRTM/WorldCover/CHIRPS/JRC terms; no blanket redistribution grant',blockers=['legacy original IDs incomplete','independent mining reference labels absent','class support and independent geographic validation','final source-specific rights review']))
    save(OUT/'integrity.json',{p.relative_to(OUT).as_posix():digest(p) for p in OUT.rglob('*') if p.is_file()});print(json.dumps(summary,indent=2))

if __name__=='__main__':build()
