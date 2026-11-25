"""One offline synthetic-only Tiny smoke, with externally monitored resource caps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

SHA='e56ea9ebcd4451078b9ca4893d5cd8a89bbee376ae16829c3e7fbbbc76de0eba'
SIZE=211873402


def verify_checkpoint(path):
    p=Path(path)
    if p.stat().st_size!=SIZE:raise ValueError('Checkpoint size mismatch')
    with p.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=SHA:raise ValueError('Checkpoint SHA mismatch')


def child(checkpoint,out):
    verify_checkpoint(checkpoint)
    import torch
    import numpy as np
    from src.phase25.learning import adapt_patch,masked_bce_dice,MEAN,STD,SCALE
    from src.phase25.dataset import BANDS
    from terratorch.models.backbones.terramind.model.terramind_register import terramind_v1_tiny,select_modality_patch_embed_weights,PRETRAINED_BANDS
    torch.manual_seed(42);torch.set_num_threads(1)
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
    torch.cuda.set_per_process_memory_fraction(0.70,0)
    torch.cuda.reset_peak_memory_stats()
    model=terramind_v1_tiny(pretrained=False,modalities=['S2L2A','S1GRD'])
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    expected=model.state_dict()
    missing=[k for k in expected if k not in state or state[k].shape!=expected[k].shape]
    if missing:raise ValueError('Missing/mismatched encoder keys: '+str(missing))
    ignored=[k for k in state if k not in expected]
    model.load_state_dict({k:state[k] for k in expected},strict=True)
    model=select_modality_patch_embed_weights(model,{'S2L2A':['BLUE','GREEN','RED'],'S1GRD':['VV','VH']},PRETRAINED_BANDS)
    del state,expected
    model.requires_grad_(False).eval().cuda()
    x=np.full((len(BANDS),32,32),np.nan,dtype='float32')
    for season in ['before','after']:
        for band,value in zip(['B2','B3','B4','VV','VH'],[.12,.16,.18,-12.,-20.]):
            i=BANDS.index(season+'_'+band);x[i]=value+(0.01 if season=='after' and band.startswith('B') else 0.)
    x[BANDS.index('before_B2'),:16,:16]=np.nan
    y=np.zeros((32,32),dtype='uint8');y[16:,16:]=1;y[:16,:16]=255
    record=dict(features=x,validity=np.isfinite(x),pseudo_states=y)
    a=adapt_patch(record)
    assert a['before'].shape==(1,5,32,32) and int(a['mask'].sum())==768
    actual=a['before'][0,:,20,20].numpy();raw=np.array([.12,.16,.18,-12.,-20.],dtype='float32')
    assert np.allclose(actual,(raw*SCALE-MEAN)/STD,atol=1e-6)
    assert a['terramind_before']['S2L2A'].shape==(1,3,32,32)
    assert a['terramind_before']['S1GRD'].shape==(1,2,32,32)
    x2=x.copy();x2[~np.isfinite(x2)]=np.inf
    b=adapt_patch(dict(features=x2,validity=np.isfinite(x2),pseudo_states=y))
    assert torch.equal(a['before'],b['before']) and torch.equal(a['mask'],b['mask'])
    def encode(d):
        with torch.no_grad():return model({k:v.cuda() for k,v in d.items()})
    before=encode(a['terramind_before']);after=encode(a['terramind_after'])
    assert len(before)==12 and before[-1].shape==(1,4,192) and after[-1].shape==before[-1].shape
    assert all(torch.isfinite(v).all() for v in before+after)
    # Output-head interpolation only; original inputs remain native32x32 without padding/resizing.
    head=torch.nn.Linear(192,1).cuda()
    logits=head((after[-1]-before[-1]).abs()).transpose(1,2).reshape(1,1,2,2)
    logits=torch.nn.functional.interpolate(logits,size=(32,32),mode='bilinear',align_corners=False)
    logits.retain_grad();mask=a['mask'].cuda();target=a['target'].cuda()
    loss=masked_bce_dice(logits,target,mask,pos_weight=1.)
    assert torch.isfinite(loss)
    loss.backward();torch.cuda.synchronize()
    assert logits.shape==(1,1,32,32) and torch.all(logits.grad[~mask]==0)
    assert all(p.grad is None and not p.requires_grad for p in model.parameters())
    assert head.weight.grad is not None and torch.isfinite(head.weight.grad).all()
    peak=max(torch.cuda.max_memory_allocated(),torch.cuda.max_memory_reserved())
    if peak>6*2**30:raise RuntimeError('CUDA memory cap')
    result=dict(status='PASS_SYNTHETIC_ONLY',checkpoint_sha256=SHA,checkpoint_bytes=SIZE,input_shape=[1,5,32,32],modalities={'S2L2A':['BLUE','GREEN','RED'],'S1GRD':['VV','VH']},feature_shape=list(before[-1].shape),feature_layers=len(before),output_shape=list(logits.shape),masked_valid_cells=768,normalization_once=True,nonfinite_fill_equivalence=True,ignored_logit_gradient_zero=True,encoder_frozen=True,head_backward_finite=True,optimizer_steps=0,loss=float(loss.detach()),cuda_peak_allocated=torch.cuda.max_memory_allocated(),cuda_peak_reserved=torch.cuda.max_memory_reserved(),ignored_checkpoint_keys=len(ignored),ignored_checkpoint_prefixes=sorted({k.split('.')[0] for k in ignored}),mask_limitation='Computational fill and loss exclusion; encoder has no explicit spatial attention mask. This does not prove invalid tokens cannot affect valid embeddings.',spatial_limitation='Native32x32 at30m; checkpoint pretraining spatial-domain shift remains. Output head interpolates logits only.',research_training=False,test_access=False)
    Path(out).write_text(json.dumps(result,indent=2))


def process_tree_memory(root):
    """Include Windows venv launcher descendants; peak working-set is conservative."""
    import psutil
    total=0
    for process in [root]+root.children(recursive=True):
        try:
            info=process.memory_info()
            total+=max(info.rss,getattr(info,'peak_wset',info.rss))
        except psutil.NoSuchProcess:continue
    return total


def stop_owned_tree(root):
    import psutil
    try:children=root.children(recursive=True)
    except psutil.NoSuchProcess:children=[]
    for process in reversed(children+[root]):
        try:process.kill()
        except psutil.NoSuchProcess:pass


def run(checkpoint):
    from scripts.phase25d2_setup import resource_gate,ENV
    from src.phase25.setup_transfer import ROOT
    import psutil
    resource_gate();verify_checkpoint(checkpoint)
    free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())
    if free<7*1024:raise RuntimeError('VRAM gate')
    dest=Path('outputs/phase25/experiments/25d2-synthetic-smoke-v1')
    dest.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HOME=str(ROOT/'hf'),TORCH_HOME=str(ROOT/'torch'),TEMP=str(ROOT/'tmp'),TMP=str(ROOT/'tmp'),PYTHONUNBUFFERED='1',WANDB_MODE='disabled')
    start=time.monotonic();peak=0;failure=None
    with (dest/'smoke.log').open('x') as log:
        p=subprocess.Popen([str(ENV/'Scripts/python.exe'),'-B','-m',__name__ if __name__!='__main__' else 'scripts.phase25d2_smoke','--child',str(checkpoint),str(dest/'result.json')],env=env,stdout=log,stderr=subprocess.STDOUT)
        monitor=psutil.Process(p.pid)
        try:
            while p.poll() is None:
                try:peak=max(peak,process_tree_memory(monitor))
                except psutil.NoSuchProcess:break
                if peak>6*2**30:failure='PROCESS_RAM_CAP';break
                if time.monotonic()-start>300:failure='WALL_CAP';break
                time.sleep(.1)
        finally:
            if p.poll() is None:stop_owned_tree(monitor)
            p.wait()
    receipt=dict(returncode=p.returncode,failure=failure,wall_seconds=time.monotonic()-start,process_tree_peak_working_set_upper_bound=peak,accounting='launcher plus recursive descendants; conservative sum of sampled peak working sets',checkpoint_sha256=SHA,model_transfers_not_performed=True,synthetic_only=True)
    (dest/'monitor.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
    if failure or p.returncode:raise RuntimeError('Smoke failed; stop and inspect retained log')


if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='--child':child(sys.argv[2],sys.argv[3])
    else:run(sys.argv[1])
