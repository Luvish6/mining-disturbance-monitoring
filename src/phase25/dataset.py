"""Private MineChange-India/1 offline patch contract; pseudo states are not truth."""
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from shapely.geometry import box
from src.phase3.spatial import partition

SCHEMA='minechange-india-private/1'
OPTICAL=['B2','B3','B4','NDVI','BSI','NDWI']
BANDS=[f'{s}_{b}' for s in ('before','after') for b in ['VV','VH']+OPTICAL]+['dVV','dVH','dNDVI','dBSI','slope','elevation','land_cover','rainfall','surface_water','fire_history','roads','geology','mining_context']
COUNTS=['before_optical_count','after_optical_count','before_sar_count','after_sar_count','follow_optical_count']
LABELS={'0':'potentially_stable_background','1':'potential_disturbance','255':'uncertain_ignore'}


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def within(root,name):
    p=(Path(root)/name).resolve()
    if not p.is_relative_to(Path(root).resolve()):raise ValueError('Artifact path escapes dataset')
    return p


def windows():
    return [(r,c,32,32) for r in (0,32) for c in (0,32)]


def spatial_check(rows):
    seen=set();groups={};shapes=[]
    for row in rows:
        if row['split'] not in ('train','validation'):raise ValueError('TEST/unknown partition prohibited')
        if row['patch_id'] in seen:raise ValueError('Duplicate patch ID')
        seen.add(row['patch_id'])
        group=row['group_id']
        if group in groups and groups[group]!=row['split']:raise ValueError('Group crosses partitions')
        groups[group]=row['split']
        if partition(group,seed=42)!=row['split']:raise ValueError('Frozen seed42 assignment mismatch')
        if row['crs']!='EPSG:32646' or row['shape']!=[32,32]:raise ValueError('Wrong patch grid')
        a=Affine(*row['affine'])
        if (a.a,a.b,a.d,a.e)!=(30,0,0,-30) or a.c%30 or a.f%30:raise ValueError('Wrong lattice/affine')
        geom=box(a.c,a.f-960,a.c+960,a.f)
        if list(geom.bounds)!=row['bounds'] or not box(*row['parent_bounds']).covers(geom):raise ValueError('Patch footprint outside parent')
        r,c=row['row_offset'],row['col_offset'];p=row['parent_bounds']
        if (r,c,32,32) not in windows() or a.c!=p[0]+c*30 or a.f!=p[3]-r*30:raise ValueError('Row/column identity mismatch')
        bx,by=map(int,group.split(':'));core=box(bx*5000+120,by*5000+120,(bx+1)*5000-120,(by+1)*5000-120)
        if not core.covers(geom):raise ValueError('Patch violates frozen buffered core')
        for old,split in shapes:
            if geom.intersection(old).area>0:raise ValueError('Overlapping/duplicate spatial windows')
            if split!=row['split'] and geom.distance(old)<240:raise ValueError('Cross-split buffer violation')
        shapes.append((geom,row['split']))


def load_manifest(root):
    root=Path(root);path=root/'manifest.json'
    if sha(path)!=(root/'manifest.sha256').read_text().strip():raise ValueError('Manifest integrity failure')
    m=json.loads(path.read_bytes())
    if m['schema']!=SCHEMA or m['bands']!=BANDS or m['verified_reference_labels']!=0 or m['label_semantics']!=LABELS:
        raise ValueError('Unsupported schema/reference claim')
    spatial_check(m['patches'])
    for row in m['patches']:
        if set(row['files'])!={'features','validity','counts','pseudo_states','pseudo_masks'} or not set(row['files'].values()).issubset(m['artifacts']):
            raise ValueError('Required raster absent from integrity inventory')
    for name,h in m['artifacts'].items():
        if sha(within(root,name))!=h:raise ValueError('Artifact integrity failure')
    return m


def read_patch(root,patch_id,*,allow_pseudo=False,manifest=None):
    # Always authenticate the manifest; callers cannot supply an unchecked replacement.
    m=load_manifest(root)
    if manifest is not None and manifest!=m:raise ValueError('Unchecked manifest replacement')
    row=next((r for r in m['patches'] if r['patch_id']==patch_id),None)
    if row is None:raise ValueError('Unknown patch')
    arrays={}
    for name,bands in [('features',BANDS),('validity',BANDS),('counts',COUNTS),('pseudo_states',['RETROSPECTIVE_PSEUDO_STATE_NOT_REFERENCE']),('pseudo_masks',list(LABELS.values()))]:
        with rasterio.open(within(root,row['files'][name])) as ds:
            if ds.crs.to_string()!=row['crs'] or list(ds.transform)[:6]!=row['affine'] or list(ds.shape)!=row['shape'] or list(ds.descriptions)!=bands:
                raise ValueError('Raster contract mismatch')
            a=ds.read();arrays[name]=a
            if name in ('features','counts'):
                if ds.nodata!=-9999:raise ValueError('Wrong NoData contract')
                arrays[name]=np.where(a==ds.nodata,np.nan,a)
    v=arrays['validity']
    if not np.isin(v,[0,1]).all() or not np.array_equal(v.astype(bool),np.isfinite(arrays['features'])):
        raise ValueError('Validity/nonfinite mismatch')
    y=arrays['pseudo_states'][0]
    if not np.isin(y,[0,1,255]).all():raise ValueError('Invalid pseudo states')
    if not np.array_equal(arrays['pseudo_masks'],np.stack([y==k for k in (0,1,255)])):raise ValueError('Pseudo masks mismatch')
    for a,b,d in [('before_VV','after_VV','dVV'),('before_VH','after_VH','dVH'),('before_NDVI','after_NDVI','dNDVI'),('before_BSI','after_BSI','dBSI')]:
        x0,x1,dx=[arrays['features'][BANDS.index(n)] for n in (a,b,d)]
        ok=np.isfinite(dx)
        if not np.allclose(dx[ok],(x1-x0)[ok],rtol=1e-5,atol=1e-6):raise ValueError('Change arithmetic mismatch')
    if np.any((y!=255)&~np.all(v[:20].astype(bool),axis=0)):raise ValueError('Pseudo state lacks valid paired signals')
    counts=arrays['counts'];valid=np.isfinite(counts)
    if np.any(counts[valid]<0) or np.any(counts[valid]!=np.floor(counts[valid])):raise ValueError('Invalid observation counts')
    return dict(features=arrays['features'],validity=v.astype(bool),counts=counts,
                pseudo_states=y if allow_pseudo else None,label_semantics=LABELS,verified_reference_labels=None,row=row)


def require_verified_references(_dataset):
    raise ValueError('No admitted independent mining reference labels; supervised Indian training NO-GO')
