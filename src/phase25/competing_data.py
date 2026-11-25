"""Load an append-only private TRAIN supplement, preserving the immutable V2 parent."""
import json
from pathlib import Path
import numpy as np
import rasterio
from affine import Affine
from shapely.geometry import box
from src.phase25.dataset import sha,within
from src.phase25.multiclass_data import load_dataset
from src.phase25.competing_classes import competing_evidence
from src.phase3.spatial import partition


def read_export_values(ds):
    # GEE unmask(-9999) does not guarantee a TIFF NoData tag. The frozen export contract does.
    a=ds.read().astype('float32');invalid=(a==-9999)
    if ds.nodata is not None:invalid|=a==ds.nodata
    return np.where(invalid,np.nan,a)


def load_extension(root):
    root=Path(root);inventory=json.loads((root/'integrity.json').read_bytes())
    for path,digest in inventory.items():
        if sha(within(root,path))!=digest:raise ValueError('Extension integrity mismatch')
    manifest=json.loads((root/'extension_manifest.json').read_bytes());parent=(root/manifest['parent_path']).resolve()
    if parent.parent!=root.resolve().parent or manifest['schema']!='mci-multiclass-extension/1' or manifest['reference_labels'] is not None or manifest['operational_alerts']!=0 or not manifest['test_sealed']:raise ValueError('Extension semantics/path')
    if sha(parent/'integrity.json')!=manifest['parent_integrity_sha256']:raise ValueError('Parent integrity mismatch')
    base=load_dataset(parent);thresholds=json.loads((parent/'generation_config.json').read_bytes())['thresholds'];seen={r['patch_id'] for r in base['patches']};occupied=[(box(*r['bounds']),r['split']) for r in base['patches']]
    for row in manifest['new_train_patches']:
        if row['split']!='train' or partition(row['group_id'],seed=42)!='train' or row['patch_id'] in seen:raise ValueError('Split/duplicate violation')
        seen.add(row['patch_id']);g=box(*row['bounds']);bx,by=map(int,row['group_id'].split(':'))
        if not box(bx*5000+120,by*5000+120,(bx+1)*5000-120,(by+1)*5000-120).covers(g):raise ValueError('Frozen core violation')
        if any(g.distance(p)<(240 if s!='train' else 120) for p,s in occupied):raise ValueError('Overlap/spatial buffer violation')
        occupied.append((g,'train'));folder=within(root,row['folder']);receipt=json.loads((folder/'source_receipt.json').read_bytes());names=receipt['bands']
        with rasterio.open(folder/'source_stack.tif') as ds:
            if ds.shape!=(32,32) or ds.crs.to_string()!=row['crs'] or ds.transform!=Affine(*row['affine']):raise ValueError('Supplement grid mismatch')
            a=read_export_values(ds)
        with np.load(folder/'model_ready.npz',allow_pickle=False) as z:
            expected=a[[names.index(n) for n in manifest['model_input_bands']]]
            if not np.array_equal(expected,z['features'],equal_nan=True) or not np.array_equal(np.isfinite(expected),z['validity']):raise ValueError('Feature/mask alignment')
            if not np.array_equal(z['weak_labels']!=255,z['label_valid']):raise ValueError('Unknown mask mismatch')
            replay=competing_evidence(dict(zip(names,a)),thresholds)['labels']
            if not np.array_equal(replay,z['weak_labels']):raise ValueError('Class-rule replay mismatch')
            with rasterio.open(folder/'weak_classes.tif') as ds:
                if ds.transform!=Affine(*row['affine']) or not np.array_equal(ds.read(1),replay):raise ValueError('Label raster mismatch')
    if set(manifest['model_input_bands'])&set(manifest['annotation_only_bands']+manifest['quality_only_bands']):raise ValueError('Annotation leakage')
    return manifest
