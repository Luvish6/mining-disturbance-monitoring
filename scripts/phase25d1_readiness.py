"""Phase25D.1 offline data/contract/hardware readiness. No fitting or weight loading."""
import argparse
import ast
import ctypes
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
import torch

from scripts.phase25b_cached import digest,save
from scripts.phase25b1_recover import save_verified
from scripts.phase25c2_expand import verify,checked_qa,D
from src.phase25.dataset import load_manifest,BANDS
from src.phase25.learning import adapt_patch,CONTRACT,CONTRACT_SHA,MEAN,STD

OUT=Path('outputs/phase25/qa/25d1-readiness-v1')
MANIFEST_SHA='3e3794f9fde5a9c1a22c265ae86f1d8b3553d524eb7c4403e02f050d52d1b7aa'
REGISTER_SHA='01ccbea7cc7ed0f49482427dbddd42e9a47d12fe1edd51ae980c9069718b1c2d'


def registration_constants():
    p=Path('outputs/phase25a_feasibility/terramind_register.py.txt')
    if digest(p)!=REGISTER_SHA:raise ValueError('Cached publisher source changed')
    data={}
    for n in ast.parse(p.read_text()).body:
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['PRETRAINED_BANDS','v1_pretraining_mean','v1_pretraining_std']:
            data[n.targets[0].id]=ast.literal_eval(n.value)
    names=data['PRETRAINED_BANDS']['untok_sen2l2a@224'];indices=[names.index(n) for n in ['BLUE','GREEN','RED']]
    for key,expected in [('v1_pretraining_mean',MEAN),('v1_pretraining_std',STD)]:
        v=[data[key]['untok_sen2l2a@224'][i] for i in indices]+data[key]['untok_sen1grd@224']
        if not np.allclose(v,expected):raise ValueError('Publisher normalization mismatch')


def hardware():
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total','available','page_total','page_available','virtual_total','virtual_available','extended']]
    m=Memory();m.length=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise ValueError('Memory probe failed')
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.free,driver_version','--format=csv,noheader'],text=True).strip()
    return dict(python=sys.version.split()[0],torch=torch.__version__,torch_cuda_build=torch.version.cuda,cuda_available=torch.cuda.is_available(),
        terratorch_installed=importlib.util.find_spec('terratorch') is not None,gpu=gpu,ram_total_gib=m.total/2**30,ram_available_gib=m.available/2**30,
        disk_free_gib={d:shutil.disk_usage(d+':/').free/2**30 for d in ['C','D']})


def run(backup):
    if OUT.exists():raise ValueError('New readiness output required; no overwrite')
    p,c,cfg,hashes,original,area,protected,preserved=verify(backup);q=checked_qa()
    if digest(D/'manifest.json')!=MANIFEST_SHA:raise ValueError('Expanded manifest changed')
    manifest=load_manifest(D);registration_constants()
    # Selected development backup bytes only; frozen TEST is not opened.
    for path,h in q['source_hashes'].items():
        copy=Path(backup)/'project_parent'/'mining_monitor_phase1'/path
        if digest(copy)!=h:raise ValueError('Development backup integrity failed')
    stats={};groups={};patches=[];expected=dict(contract_sha256=CONTRACT_SHA,dataset_sha256=MANIFEST_SHA,split='validation',pixel_ids=[],group_ids=[],labels=[],valid=[])
    for row in manifest['patches']:
        record={}
        for name in ['features','validity','pseudo_states']:
            with rasterio.open(D/row['files'][name]) as ds:
                if list(ds.transform)[:6]!=row['affine'] or ds.crs.to_string()!=row['crs']:raise ValueError('Input grid mismatch')
                a=ds.read()
                if name=='features':a=np.where(a==ds.nodata,np.nan,a)
                record[name]=a[0] if name=='pseudo_states' else a.astype(bool) if name=='validity' else a
        d=adapt_patch(record);mask=d['mask'].numpy()[0,0];y=record['pseudo_states'];s=row['split'];key=row['group_id']
        st=stats.setdefault(s,dict(patches=0,usable_patches=0,raw_positive=0,raw_stable=0,raw_uncertain=0,usable_positive=0,usable_stable=0,
            token_valid_cells=0,excluded_labeled_by_token=0,positive_patches=0))
        st['patches']+=1;st['usable_patches']+=int(mask.any());st['raw_positive']+=int((y==1).sum());st['raw_stable']+=int((y==0).sum());st['raw_uncertain']+=int((y==255).sum())
        pos=int(((y==1)&mask).sum());neg=int(((y==0)&mask).sum())
        st['usable_positive']+=pos;st['usable_stable']+=neg;st['positive_patches']+=int(pos>0);st['token_valid_cells']+=int(d['token_common_valid'].sum())
        st['excluded_labeled_by_token']+=int((np.isin(y,[0,1])&~mask).sum())
        g=groups.setdefault(key,dict(split=s,positive=0,stable=0));g['positive']+=pos;g['stable']+=neg
        patches.append(dict(patch_id=row['patch_id'],group_id=key,split=s,usable_positive=pos,usable_stable=neg))
        if s=='validation':
            for i in range(32):
                for j in range(32):
                    expected['pixel_ids'].append(key+f":r{row['row_offset']+i}:c{row['col_offset']+j}")
                    expected['group_ids'].append(key);expected['labels'].append(int(y[i,j]));expected['valid'].append(bool(mask[i,j]))
    for s,st in stats.items():
        st['positive_groups']=sum(g['split']==s and g['positive']>0 for g in groups.values())
        st['usable_groups']=sum(g['split']==s and g['positive']+g['stable']>0 for g in groups.values())
        st['usable_foreground_prevalence']=st['usable_positive']/(st['usable_positive']+st['usable_stable']) if st['usable_positive']+st['usable_stable'] else None
    tm=json.loads(Path('docs/reports/phase25a-evidence.json').read_bytes())['terramind']
    known=[Path('outputs/phase25/models')/tm['checkpoint']['path'],Path.home()/'.cache/huggingface/hub/models--ibm-esa-geospatial--TerraMind-1.0-tiny/snapshots'/tm['model_revision']/tm['checkpoint']['path']]
    present=[x for x in known if x.is_file()]
    for path in present:
        if path.stat().st_size!=tm['checkpoint']['size'] or digest(path)!=tm['checkpoint']['lfs']['sha256']:raise ValueError('Local checkpoint identity mismatch; no weights loaded')
    OUT.mkdir(parents=True,exist_ok=False);save_verified(OUT/'validation-frame.json',expected)
    result=dict(status='INPUT_ADAPTER_READY; TERRAMIND_RUNTIME_AND_30M_TOKEN_CONTRACT_UNVERIFIED',contract=CONTRACT,contract_sha256=CONTRACT_SHA,
        dataset_manifest_sha256=MANIFEST_SHA,validation_frame_sha256=digest(OUT/'validation-frame.json'),stats=stats,groups=groups,patches=patches,
        hardware=hardware(),checkpoint=dict(model=tm['model'],revision=tm['model_revision'],expected_sha256=tm['checkpoint']['lfs']['sha256'],expected_bytes=tm['checkpoint']['size'],
            license=tm['license'],present_in_known_caches=bool(present),actual_hash_verified=bool(present),weights_loaded=False),
        cached_source_sha256=REGISTER_SHA,backup_development_files_verified=len(q['source_hashes']),
        proposed_positive_weight_train_only=min(10,stats['train']['usable_stable']/stats['train']['usable_positive']) if stats['train']['usable_positive'] else None,
        verified_reference_labels=0,model_fits=0,downloads=0,requests=0,operational_alerts=0)
    for path,h in {**preserved,**q['source_hashes']}.items():
        if digest(path)!=h:raise ValueError('Historical inputs changed')
    if digest(D/'manifest.json')!=MANIFEST_SHA:raise ValueError('Dataset manifest changed')
    save_verified(OUT/'readiness.json',result);print(json.dumps({k:result[k] for k in ['status','stats','hardware','checkpoint','proposed_positive_weight_train_only']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--backup',required=True);a=p.parse_args();run(a.backup)
