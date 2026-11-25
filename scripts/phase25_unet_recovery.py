"""Two prespecified TRAIN-only sampling recoveries; no TEST, tuning or acquisition."""
import json,time,random
from pathlib import Path
import numpy as np
import torch
from src.phase25.unet_experiment import load_data,load_model,payload_metadata,evaluate,metrics,CLAIM
from src.phase25.learning import masked_bce_dice,metric_counts
from src.phase3.model import SiameseUNet
from src.phase25.dataset import sha
from scripts.phase25_unet_pilot import save_predictions,panels
from scripts.phase25b_cached import backup_gate

BASE=Path('outputs/phase25/experiments/25e2-unet-pseudo-v1')
OUT=Path('outputs/phase25/experiments/25e3-recovery-v1')


def schedule(train,positive_per_four,rng):
    if any(r['row']['split']!='train' for r in train):raise ValueError('TRAIN-only sampling')
    pos=[i for i,r in enumerate(train) if ((r['adapted']['target']==1)&r['adapted']['mask']).any()]
    neg=[i for i,r in enumerate(train) if r['adapted']['mask'].any() and i not in pos]
    if not pos or not neg:raise ValueError('Both TRAIN patch strata required')
    pos=list(rng.permutation(pos));neg=list(rng.permutation(neg));batches=[];cursor=0
    for start in range(0,len(neg),4-positive_per_four):
        group=[pos[(cursor+i)%len(pos)] for i in range(positive_per_four)];cursor+=positive_per_four
        batches.append(group+neg[start:start+4-positive_per_four])
    return batches


def sensitivity(frame):
    y=np.array(frame['labels']);p=np.array(frame['probabilities']);v=np.array(frame['valid'],bool);g=np.array(frame['group_ids'])
    return {str(t):dict(pooled=metric_counts(y,p,v,t),per_group={key:metric_counts(y[g==key],p[g==key],v[g==key],t) for key in sorted(set(g))}) for t in [.25,.5,.75]}


def distributions(frame):
    y=np.array(frame['labels']);p=np.array(frame['probabilities']);v=np.array(frame['valid'],bool)
    quant=lambda z:np.quantile(z,[0,.25,.5,.75,1]).tolist() if z.size else None
    p=np.clip(p,1e-7,1-1e-7)
    return dict(quantiles_min_q25_median_q75_max={str(c):quant(p[v&(y==c)]) for c in [0,1]},weighted_positive_bce_sum=float((-10*np.log(p[v&(y==1)])).sum()),negative_bce_sum=float((-np.log1p(-p[v&(y==0)])).sum()))


def run():
    backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125')
    OUT.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    _,data=load_data('outputs/phase25/datasets/25c2-v1');train=[r for r in data if r['row']['split']=='train'];val=[r for r in data if r['row']['split']=='validation']
    config=dict(seed=42,configs=[dict(id='balanced_2pos_2background',positive_per_four=2),dict(id='positive_3pos_1background',positive_per_four=3)],epochs=10,total_training_cap_seconds=300,lr=.0003,weight_decay=.0001,gradient_clip=1.,positive_weight=10,loss='unchanged D.1 masked BCE+Dice',checkpoint='last completed epoch; no VAL selection',threshold=.5,selection_rule='first listed config with VAL TP>0 and F1>0 is a research candidate; no training/threshold changes based on results',sampling='TRAIN-only cyclic shuffled positive-bearing patches; background patches once/epoch. Repeats are not independent evidence.',claim=CLAIM)
    (OUT/'preregistered_config.json').write_text(json.dumps(config,indent=2))
    device='cuda' if torch.cuda.is_available() else 'cpu'
    if device=='cuda':torch.cuda.set_per_process_memory_fraction(.5,0)
    original,_=load_model(BASE/'seed_42/best.pt',device)
    with np.load(BASE/'seed_42/validation_predictions.npz') as z:base={k:z[k].tolist() for k in ['labels','probabilities','valid','pixel_ids','group_ids']}
    baseline_train=evaluate(original,train,device,10)
    positive=next(r for r in train if ((r['adapted']['target']==1)&r['adapted']['mask']).any());d=positive['adapted']
    original.train();original.zero_grad();logits=original(d['before'].to(device),d['after'].to(device));logits.retain_grad();loss=masked_bce_dice(logits,d['target'].to(device),d['mask'].to(device),10);loss.backward()
    gradient=dict(parameter_gradient_norm=float(torch.sqrt(sum((p.grad.detach()**2).sum() for p in original.parameters() if p.grad is not None))),ignored_gradient_max=float(logits.grad[~d['mask'].to(device)].abs().max()) if (~d['mask']).any() else 0.,optimizer_steps=0)
    diagnosis=dict(training_distribution=distributions(baseline_train),validation_distribution=distributions(base),baseline_sensitivity=sensitivity(base),gradient=gradient,interpretation='Severe TRAIN foreground imbalance and background-dominated exposure; probabilities below0.5 are real. Masks/gradient flow checked, no optimizer used in diagnosis.')
    (OUT/'diagnosis.json').write_text(json.dumps(diagnosis,indent=2));print(json.dumps(diagnosis),flush=True)
    del original;results=[];training_used=0.
    for conf in config['configs']:
        if training_used>=290:break
        random.seed(42);np.random.seed(42);torch.manual_seed(42)
        if device=='cuda':torch.cuda.manual_seed_all(42)
        torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
        model=SiameseUNet(channels=5,width=16).to(device);opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001);rng=np.random.default_rng(42)
        dest=OUT/conf['id'];dest.mkdir();history=[];start=time.monotonic();stop=False;steps=0;exposures=0
        for epoch in range(1,11):
            model.train();losses=[]
            for batch in schedule(train,conf['positive_per_four'],rng):
                if training_used+time.monotonic()-start>=290:stop=True;break
                opt.zero_grad(set_to_none=True)
                for i in batch:
                    d=train[i]['adapted'];loss=masked_bce_dice(model(d['before'].to(device),d['after'].to(device)),d['target'].to(device),d['mask'].to(device),10)
                    if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                    (loss/len(batch)).backward();losses.append(float(loss.detach()));exposures+=1
                torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step();steps+=1
            if stop:break
            history.append(dict(epoch=epoch,training_loss=float(np.mean(losses)),elapsed_seconds=time.monotonic()-start))
            torch.save(dict(state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},metadata=payload_metadata(42),epoch=epoch),dest/f'epoch_{epoch}.pt')
            print(json.dumps(dict(config=conf['id'],**history[-1])),flush=True)
        elapsed=time.monotonic()-start;training_used+=elapsed
        if not history:raise RuntimeError('No completed recovery epoch')
        checkpoint=dest/'best.pt';checkpoint.write_bytes((dest/f"epoch_{history[-1]['epoch']}.pt").read_bytes());checkpoint.with_suffix('.json').write_text(json.dumps(dict(sha256=sha(checkpoint),metadata=payload_metadata(42))))
        selected,_=load_model(checkpoint,device);frame=evaluate(selected,val,device,10);scores=sensitivity(frame);qualifies=scores['0.5']['pooled']['confusion_matrix'][1][1]>0 and scores['0.5']['pooled']['dice_f1']>0
        row=dict(id=conf['id'],epochs=len(history),training_seconds=elapsed,history=history,optimizer_steps=steps,patch_exposures=exposures,metrics=scores,distribution=distributions(frame),qualifies=qualifies,checkpoint_sha256=sha(checkpoint))
        (dest/'metrics.json').write_text(json.dumps(row,indent=2));np.savez_compressed(dest/'validation_predictions.npz',**{k:np.asarray(frame[k]) for k in ['labels','probabilities','valid','pixel_ids','group_ids']})
        save_predictions(val,frame,dest/'georeferenced_predictions');panels(val,frame,dest/'comparison_images');results.append(row)
    selected=next((r['id'] for r in results if r['qualifies']),None)
    (OUT/'summary.json').write_text(json.dumps(dict(config=config,results=results,selected_research_candidate=selected,total_training_seconds=training_used,claim=CLAIM,operational_alerts=0,stop_tuning=True),indent=2))
    print(json.dumps(dict(selected=selected,training_seconds=training_used,results=[dict(id=r['id'],metrics=r['metrics']['0.5']) for r in results]),indent=2))


if __name__=='__main__':run()
