"""Train bounded weak-supervision experiments offline; never TEST or independent accuracy."""
import json
import math
import sys
import time
from pathlib import Path
import numpy as np
import rasterio
from affine import Affine
import torch
from scripts.phase25b_cached import backup_gate,digest
from src.phase25.unet_experiment import load_data,fit,evaluate,metrics,MANIFEST_SHA,CLAIM
from src.phase25.learning import CONTRACT_SHA,load_evaluation_frame,compare_contract


def save_predictions(records,frame,out):
    out.mkdir()
    for r in records:
        row=r['row'];p=frame['images'][row['patch_id']];support=r['adapted']['token_common_valid']
        with rasterio.open(out/(row['patch_id']+'.tif'),'w',driver='GTiff',height=32,width=32,count=2,dtype='float32',crs=row['crs'],transform=Affine(*row['affine']),nodata=-9999) as ds:
            ds.write(np.stack([np.where(support,p,-9999),np.where(support,(p>=.5).astype(float),-9999)]).astype('float32'))
            ds.set_band_description(1,'UNVALIDATED_PSEUDO_MODEL_PROBABILITY');ds.set_band_description(2,'FIXED_0_5_PSEUDO_MODEL_PREDICTION')
            ds.update_tags(model_validation_status='NOT_VALIDATED',operational_alerts='0',claim=CLAIM)


def panels(records,frame,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from src.phase25.dataset import BANDS
    # Label-defined illustrative strata only, after model/threshold freezing; never selection/tuning.
    positive=[r for r in records if ((r['raw']['pseudo_states']==1)&r['adapted']['mask'].numpy()[0,0]).any()]
    positive_ids={r['row']['patch_id'] for r in positive}
    background=[r for r in records if r['row']['patch_id'] not in positive_ids]
    selected=[]
    for candidates in [positive,background,records]:
        for r in candidates:
            if all(x['row']['patch_id']!=r['row']['patch_id'] for x in selected):selected.append(r);break
    out.mkdir()
    for r in selected:
        pid=r['row']['patch_id'];x=r['raw']['features'];y=r['raw']['pseudo_states'];p=frame['images'][pid]
        fig,axes=plt.subplots(1,4,figsize=(11,3))
        for ax,season in zip(axes[:2],['before','after']):
            rgb=np.stack([x[BANDS.index(season+'_'+b)] for b in ['B4','B3','B2']],-1)
            ax.imshow(np.clip(np.nan_to_num(rgb)/.3,0,1));ax.set_title(season+' RGB (0–0.30)')
        axes[2].imshow(np.where(y==255,np.nan,y),vmin=0,vmax=1,cmap='viridis');axes[2].set_title('Pseudo target; blank=ignore')
        axes[3].imshow(np.where(r['adapted']['token_common_valid'],p>=.5,np.nan),vmin=0,vmax=1,cmap='viridis');axes[3].set_title('Prediction at0.50')
        for ax in axes:ax.axis('off')
        fig.suptitle(pid+' — pseudo-label agreement, NOT verified mining accuracy',fontsize=9);fig.tight_layout();fig.savefig(out/(pid+'.png'),dpi=130);plt.close(fig)


def run(output):
    start=time.monotonic();backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    if Path('outputs/phase25/receipts/.acquire.lock').exists():raise ValueError('Active acquisition lock')
    out=Path(output)
    if not out.resolve().is_relative_to(Path('outputs/phase25/experiments').resolve()):raise ValueError('Isolated run directory required')
    out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    if device=='cuda':
        free,_=torch.cuda.mem_get_info()
        if free<2*2**30:device='cpu'
        else:torch.cuda.set_per_process_memory_fraction(.5,0)
    cfg=json.loads(Path('config/phase25d1_comparison.json').read_bytes())
    if cfg['input_contract_sha256']!=CONTRACT_SHA:raise ValueError('D.1 normalization/input contract changed')
    root=Path('outputs/phase25/datasets/25c2-v1');manifest,data=load_data(root)
    train=[r for r in data if r['row']['split']=='train'];val=[r for r in data if r['row']['split']=='validation']
    if {r['row']['group_id'] for r in train}&{r['row']['group_id'] for r in val}:raise ValueError('Spatial leakage')
    def support(records):
        return dict(patches=len(records),usable_patches=sum(bool(r['adapted']['mask'].any()) for r in records),positive=sum(int(((r['adapted']['target']==1)&r['adapted']['mask']).sum()) for r in records),negative=sum(int(((r['adapted']['target']==0)&r['adapted']['mask']).sum()) for r in records),groups=len({r['row']['group_id'] for r in records}),positive_groups=len({r['row']['group_id'] for r in records if ((r['adapted']['target']==1)&r['adapted']['mask']).any()}))
    counts={s:support(r) for s,r in [('train',train),('validation',val)]}
    if counts['train']['positive']==0 or counts['train']['negative']==0:raise ValueError('Missing TRAIN pseudo-class support')
    pos_weight=min(10,counts['train']['negative']/counts['train']['positive'])
    config=dict(claim=CLAIM,seeds=[42,43,44],device=device,torch_version=str(torch.__version__),max_epochs=5,per_seed_seconds=300,total_training_seconds=1200,batch_size=1,gradient_accumulation=4,optimizer='AdamW',lr=.0003,weight_decay=.0001,gradient_clip_norm=1.,augmentation='NONE',checkpoint_selection='minimum mean VAL masked D.1 loss; patience2; ties earlier epoch',threshold=.5,positive_weight=pos_weight,normalization='Frozen D.1 constants; no statistics fitted',contract_sha256=CONTRACT_SHA,dataset_sha256=MANIFEST_SHA,support=counts,test_access=False,human_review_labels_used=False,supervised_mining_validation='NO-GO',operational_alerts=0)
    (out/'run_config.json').write_text(json.dumps(config,indent=2))
    expected=load_evaluation_frame('outputs/phase25/qa/25d1-readiness-v1/validation-frame.json',cfg['validation_frame_sha256'])
    results=[];total_training=0
    for seed in config['seeds']:
        remaining=1200-total_training
        if remaining<300:break
        dest=out/f'seed_{seed}';dest.mkdir()
        result,frame=fit(seed,train,val,dest,device,pos_weight,remaining)
        candidate=dict(frame,contract_sha256=CONTRACT_SHA,dataset_sha256=MANIFEST_SHA,split='validation');compare_contract(candidate,candidate,expected)
        total_training+=result['training_wall_seconds'];results.append(result)
        np.savez_compressed(dest/'validation_predictions.npz',probabilities=np.array(frame['probabilities'],dtype='float32'),labels=np.array(frame['labels'],dtype='uint8'),valid=np.array(frame['valid'],bool),pixel_ids=np.array(frame['pixel_ids']),group_ids=np.array(frame['group_ids']))
        save_predictions(val,frame,dest/'georeferenced_predictions')
        if seed==42:
            panels(val,frame,dest/'comparison_images')
            baseline=dict(frame,probabilities=[0.]*len(frame['probabilities']));baseline_metrics=metrics(baseline)
        # No seed re-selection: report every completed fit at the same fixed threshold.
        if result['stop']=='TIME_CAP':break
    if digest(root/'manifest.json')!=MANIFEST_SHA:raise ValueError('Dataset changed during experiment')
    summary=dict(claim=CLAIM,models=results,constant_background=baseline_metrics,support=counts,total_training_wall_seconds=total_training,total_run_wall_seconds=time.monotonic()-start,device=device,completed_seeds=[r['seed'] for r in results],selection_bias='VAL used for checkpoint selection; agreement with pseudo-labels is not independent accuracy',requests=0,downloads=0,verified_reference_labels=0,operational_alerts=0)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    (out/'receipt.json').write_text(json.dumps({str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()},indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='models'},indent=2));print(json.dumps([dict(seed=r['seed'],epochs=r['completed_epochs'],metrics=r['validation']['pooled']) for r in results],indent=2))


if __name__=='__main__':run(sys.argv[1])
