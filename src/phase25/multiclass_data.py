"""Load only the versioned private weak-class schema; never real reference admission."""
import json
from pathlib import Path
import numpy as np
from src.phase25.dataset import spatial_check,sha,within

def load_dataset(root):
    root=Path(root);inventory=json.loads((root/'integrity.json').read_bytes())
    for name,digest in inventory.items():
        if sha(within(root,name))!=digest:raise ValueError('Dataset integrity mismatch')
    m=json.loads((root/'manifest.json').read_bytes())
    if m['schema']!='mci-multiclass/1' or m['label_semantics']!='WEAK_ALGORITHMIC_HYPOTHESES_NOT_REFERENCE' or m['reference_labels'] is not None:raise ValueError('Weak dataset semantics required')
    spatial_check(m['patches'])
    if set(m['model_input_bands'])&set(m['annotation_only_bands']+m.get('quality_only_bands',[])):raise ValueError('Future annotation leakage')
    return m

def load_patch(root,patch_id,manifest=None):
    m=load_dataset(root)
    if manifest is not None and manifest!=m:raise ValueError('Unchecked manifest')
    row=next(r for r in m['patches'] if r['patch_id']==patch_id)
    with np.load(within(root,row['output_folder']+'/model_ready.npz'),allow_pickle=False) as z:data={k:z[k] for k in z.files}
    if data['features'].shape!=(len(m['model_input_bands']),32,32) or not np.array_equal(np.isfinite(data['features']),data['validity']):raise ValueError('Feature validity contract')
    if not np.isin(data['weak_labels'],[0,1,2,3,4,255]).all() or not np.array_equal(data['label_valid'],data['weak_labels']!=255):raise ValueError('Weak class mask contract')
    data['reference_labels']=None;data['row']=row;return data
