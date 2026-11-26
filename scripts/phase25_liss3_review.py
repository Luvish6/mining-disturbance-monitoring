"""Offline, TRAIN-only native LISS-III BOA review and annotation-only evidence attachment."""
import argparse,json,math,csv
from pathlib import Path
import numpy as np
import rasterio
from affine import Affine
from rasterio.windows import Window,from_bounds
from rasterio.features import geometry_mask
from rasterio.warp import reproject,Resampling
from shapely.geometry import box,mapping
from src.phase25.liss3_evidence import BANDS,extract,metadata,sha,reflectance,indices,flags,relative_match,SPECTRAL_REFERENCE
from src.phase25.features import Grid
from scripts.phase25b_cached import backup_gate,guarded,tif
from src.phase25.competing_data import load_extension

OUT=Path('outputs/phase25/datasets/nrsc-liss3-evidence-v1')
PARENT=Path('outputs/phase25/datasets/competing-supplement-v1')
AOIS=PARENT/'manual_aoi.geojson'


def save(path,value):
 with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def inspect_source(folder,meta):
 info={};first=None
 for file in BANDS:
  with rasterio.open(folder/file) as ds:
   signature=(ds.crs.to_string(),ds.transform,ds.shape)
   if first is None:first=signature
   if signature!=first or ds.count!=1 or ds.dtypes!=('uint16',) or ds.crs.to_epsg()!=32646 or ds.res!=(24.,24.):raise ValueError('Unexpected source band/grid')
   if ds.width!=int(meta['NoPixels']) or ds.height!=int(meta['NoScans']):raise ValueError('Metadata dimension mismatch')
   center=ds.transform*(.5,.5)
   if not np.allclose(center,[float(meta['ProdULMapX']),float(meta['ProdULMapY'])],atol=1e-5,rtol=0):raise ValueError('Metadata center/grid mismatch')
   info[file]=dict(shape=list(ds.shape),crs=ds.crs.to_string(),affine=list(ds.transform)[:6],bounds=list(ds.bounds),nodata=ds.nodata,tiff_scale=ds.scales[0],tiff_offset=ds.offsets[0],actual_reflectance_scale=float(meta['ScaleFactor']))
 return info


def crop(folder,meta,bounds):
 arrays=[];masks=[];grid=None
 for file in BANDS:
  with rasterio.open(folder/file) as ds:
   w=from_bounds(*bounds,ds.transform);c0=math.floor(w.col_off);r0=math.floor(w.row_off);w=Window(c0,r0,math.ceil(w.col_off+w.width)-c0,math.ceil(w.row_off+w.height)-r0)
   if c0<0 or r0<0 or c0+w.width>ds.width or r0+w.height>ds.height:raise ValueError('Requested TRAIN AOI outside source bounds')
   a=ds.read(1,window=w);arrays.append(a);masks.append(ds.read_masks(1,window=w)>0);g=Grid(ds.crs.to_string(),tuple(ds.window_transform(w))[:6],a.shape)
   if grid is not None and g!=grid:raise ValueError('Crop band alignment')
   grid=g
 inside=geometry_mask([mapping(box(*bounds))],out_shape=grid.shape,transform=Affine(*grid.affine),invert=True,all_touched=False)
 raw=np.stack(arrays);x,valid=reflectance(raw,np.stack(masks),meta);valid&=inside;x[:,~valid]=np.nan
 return x,valid,inside,grid,dict(aoi_native_pixel_centres=int(inside.sum()),valid_signal_cells=int(valid.sum()),valid_signal_percent=float(100*valid.sum()/inside.sum()),all_band_zero_cells=int((inside&np.all(raw==0,axis=0)).sum()),out_of_range_cells=int((inside&np.any((raw<0)|(raw>10000),axis=0)).sum()))


def aligned(x,grid,bounds):
 dst=np.full((4,32,32),np.nan,'float32');transform=Affine(30,0,bounds[0],0,-30,bounds[3])
 for b in range(4):reproject(np.where(np.isfinite(x[b]),x[b],-9999),dst[b],src_transform=Affine(*grid.affine),src_crs=grid.crs,src_nodata=-9999,dst_transform=transform,dst_crs=grid.crs,dst_nodata=np.nan,resampling=Resampling.average)
 return dst,Grid(grid.crs,tuple(transform)[:6],(32,32))


def run(before,after):
 backup_gate('D:/ResearchBackups/mining-monitoring/pre-minechange-india-20261125');load_extension(PARENT)
 if (OUT/'summary.json').exists():raise ValueError('Completed evidence package exists; never overwrite')
 OUT.mkdir(parents=True,exist_ok=True);base_hash=sha(PARENT/'integrity.json');aoi_hash=sha(AOIS);features=json.loads(AOIS.read_bytes())['features']
 from scripts.phase22n_temporal import guards
 area,protected=guards()
 for f in features:
  p=f['properties'];guarded(p['block'],dict(split=p['split'],bounds=p['bounds_utm46n']),area,protected)
 sources={};receipts=json.loads((OUT/'archive_receipts.json').read_bytes()) if (OUT/'archive_receipts.json').exists() else {}
 for season,archive in [('before',Path(before)),('after',Path(after))]:
  if season not in receipts:receipts[season]=extract(archive,OUT/'raw'/season)
  elif sha(archive)!=receipts[season]['archive_sha256']:raise ValueError('Archive changed')
  for relative,value in receipts[season]['members'].items():
   if sha(OUT/'raw'/season/relative)!=value['sha256']:raise ValueError('Extracted file changed')
  folder=OUT/'raw'/season/archive.stem;meta=metadata(next(folder.glob('*.meta')))
  if metadata(folder/'BAND_META.txt')!=meta:raise ValueError('Contradictory product metadata')
  from datetime import datetime
  date=datetime.strptime(meta['DateOfPass'],'%d-%b-%Y').date().isoformat();start,end={'before':('2023-11-01','2024-04-01'),'after':('2024-11-01','2025-04-01')}[season]
  if not start<=date<end:raise ValueError('Acquisition outside frozen season')
  sources[season]=dict(folder=folder,meta=meta,date=date,grid=inspect_source(folder,meta))
 if not (OUT/'archive_receipts.json').exists():save(OUT/'archive_receipts.json',receipts)
 summaries=[];review=[];parent_manifest=json.loads((PARENT/'extension_manifest.json').read_bytes());v2=Path('outputs/phase25/datasets/minechange-india-multiclass-v2');v2m=json.loads((v2/'manifest.json').read_bytes())
 for number,f in enumerate(features,1):
  p=f['properties'];pid=p['aoi_id'];folder=OUT/'aois'/pid;folder.mkdir(parents=True,exist_ok=False);bounds=p['bounds_utm46n'];data={};result={}
  for season in ['before','after']:
   s=sources[season];x,valid,inside,grid,coverage=crop(s['folder'],s['meta'],bounds);ix=indices(x);quality=flags(x,valid);data[season]=dict(x=x,valid=valid,inside=inside,grid=grid,indices=ix)
   tif(folder/(season+'_native_sr.tif'),x,grid,list(BANDS.values()));tif(folder/(season+'_native_indices.tif'),np.stack(list(ix.values())),grid,list(ix))
   qa=np.stack([q.astype('uint8') for q in quality.values()]);qa[:,~inside]=255;tif(folder/(season+'_diagnostic_flags.tif'),qa,grid,list(quality),dtype='uint8',nodata=255)
   # Explicit unknown cloud/shadow/haze status, never masquerading as a clear-data mask.
   tif(folder/(season+'_unverified_quality.tif'),np.full(grid.shape,255,'uint8'),grid,['CLOUD_HAZE_TERRAIN_SHADOW_UNVERIFIED'],dtype='uint8',nodata=255)
   target,target_grid=aligned(x,grid,bounds);tif(folder/(season+'_30m_sr_DIAGNOSTIC.tif'),target,target_grid,list(BANDS.values()));data[season]['aligned']=target
   result[season]=dict(date=s['date'],**coverage,descriptive_flags={name:int(q.sum()) for name,q in quality.items() if name!='valid_support'},qa='NO_PROVIDER_QA; flags are not cloud/shadow classification',ndvi_median=float(np.nanmedian(ix['NDVI'])),ndbi_median=float(np.nanmedian(ix['NDBI'])),sun_elevation=float(s['meta']['SunElevationAtCenter']))
  b,a=data['before'],data['after']
  if b['grid'].shape!=a['grid'].shape or not np.allclose(b['grid'].affine,a['grid'].affine,atol=1e-6,rtol=0):raise ValueError('Native date grids differ: explicit resampling design needed')
  common=b['valid']&a['valid'];delta={n:a['indices'][n]-b['indices'][n] for n in ['NDVI','NDBI','MNDWI']};tif(folder/'native_differences_DIAGNOSTIC.tif',np.stack(list(delta.values())),b['grid'],['d'+n for n in delta])
  matching=relative_match(b['x'][2],a['x'][2],common)
  matching['native_grid_alignment']='same lattice, date origins differ by integer24m pixels; not proof of registration accuracy'
  # Analysts only: seasonal Sentinel vs independently acquired single-date NRSC; not a reviewer label source.
  if pid.startswith('mci_supp_'):
   row=next(r for r in parent_manifest['new_train_patches'] if r['patch_id']==pid);source=PARENT/row['folder']/'source_stack.tif';meta=json.loads((PARENT/row['folder']/'source_receipt.json').read_bytes());names=meta['bands']
  else:
   row=next(r for r in v2m['patches'] if r['patch_id']==pid);source=v2/row['output_folder']/'observations.tif';names=v2m['bands']
  with rasterio.open(source) as ds:
   if ds.transform!=Affine(30,0,bounds[0],0,-30,bounds[3]) or ds.crs.to_epsg()!=32646:raise ValueError('Sentinel evidence grid mismatch')
   sentinel=ds.read([names.index('before_NDVI')+1,names.index('after_NDVI')+1]);sentinel=np.where(sentinel==-9999,np.nan,sentinel)
  ni=[indices(data[s]['aligned'])['NDVI'] for s in ['before','after']];nrsc_delta=ni[1]-ni[0];sentinel_delta=sentinel[1]-sentinel[0];same=np.isfinite(nrsc_delta)&np.isfinite(sentinel_delta)
  from scipy.stats import spearmanr
  rho=float(spearmanr(nrsc_delta[same],sentinel_delta[same]).statistic) if same.sum()>2 and np.std(nrsc_delta[same]) and np.std(sentinel_delta[same]) else None
  # Native review panel excludes all Sentinel/pseudo/model predictions and source-type roles.
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  fig,axes=plt.subplots(2,3,figsize=(12,8),layout='constrained');extent=[b['grid'].affine[2],b['grid'].affine[2]+b['grid'].shape[1]*24,b['grid'].affine[5]-b['grid'].shape[0]*24,b['grid'].affine[5]]
  for j,s in enumerate(['before','after']):
   x=data[s]['x'];rgb=np.clip(np.moveaxis(x[[2,1,0]],0,-1)/.5,0,1);axes[0,j].imshow(np.nan_to_num(rgb,nan=1),extent=extent,interpolation='nearest');axes[0,j].set_title(sources[s]['date']+'\nFCC NIR/red/green',fontsize=10)
   rgb=np.clip(np.moveaxis(x[[3,2,0]],0,-1)/.5,0,1);axes[1,j].imshow(np.nan_to_num(rgb,nan=1),extent=extent,interpolation='nearest');axes[1,j].set_title('SWIR/NIR/green false colour\n(not true RGB)',fontsize=10)
  im=axes[0,2].imshow(np.ma.masked_invalid(delta['NDVI']),vmin=-.5,vmax=.5,cmap='RdYlGn',extent=extent,interpolation='nearest');fig.colorbar(im,ax=axes[0,2],label='After-minus-before NDVI');axes[0,2].set_title('Descriptive NDVI difference')
  im=axes[1,2].imshow(np.ma.masked_invalid(delta['NDBI']),vmin=-.5,vmax=.5,cmap='RdBu_r',extent=extent,interpolation='nearest');fig.colorbar(im,ax=axes[1,2],label='After-minus-before NDBI');axes[1,2].set_title('SWIR/NIR indicator\nnot built-up truth',fontsize=10)
  for ax in axes.flat:ax.set_xlabel('UTM46N easting (m)');ax.set_ylabel('Northing (m)');ax.ticklabel_format(style='plain',useOffset=False)
  fig.suptitle(f'TRAIN review{number:02d}: {p["longitude"]:.7f}E,{p["latitude"]:.7f}N;24m output/23.5m native\nUnknown clouds/haze/shadows and absolute registration; no attributed labels. Fixed0-0.5stretch.')
  fig.savefig(folder/'private_review_panel.png',dpi=150);plt.close(fig)
  row=dict(aoi_id=pid,block=p['block'],split='train',coverage=result,common_valid_cells=int(common.sum()),common_valid_percent=float(common.sum()/b['inside'].sum()*100),native_grid=dict(crs=b['grid'].crs,affine=list(b['grid'].affine),shape=list(b['grid'].shape)),paired_ndvi_change=dict(median=float(np.nanmedian(delta['NDVI'])),q05_q95=np.nanquantile(delta['NDVI'],[.05,.95]).tolist()),paired_ndbi_change_median=float(np.nanmedian(delta['NDBI'])),relative_registration=matching,sentinel_comparison=dict(common_30m_cells=int(same.sum()),ndvi_delta_spearman=rho,interpretation='Single-date independent sensor versus seasonal Sentinel composite; not equal temporal estimands or validated change accuracy'),evidence_status='STRUCTURALLY_COMPATIBLE_PRIVATE_DIAGNOSTIC_REVIEW_PENDING',mining_attribution='UNKNOWN',reference_labels=None,permissions='PRIVATE_ONLY_TERMS_UNCONFIRMED')
  summaries.append(row);save(folder/'receipt.json',row)
  for reviewer in ['first','second']:review.append(dict(review_item=f'TRAIN{number:02d}',reviewer_slot=reviewer,reviewer_id='',before_interpretation='',after_interpretation='',agriculture_evidence='',construction_evidence='',other_explanations='',quality='',positional_evidence='',rights_confirmation='',verdict='',notes='',adjudication=''))
  print(json.dumps(dict(aoi=pid,before=result['before']['valid_signal_percent'],after=result['after']['valid_signal_percent'],common=row['common_valid_percent'],dNDVI=row['paired_ndvi_change']['median'],matching=matching)),flush=True)
 with (OUT/'independent_review_empty.csv').open('x',newline='',encoding='utf-8') as f:
  writer=csv.DictWriter(f,fieldnames=list(review[0]));writer.writeheader();writer.writerows(review)
 summary=dict(schema='nrsc-liss3-evidence/1',aoi_sha256=aoi_hash,parent82_inventory_sha256=base_hash,scenes={s:dict(date=v['date'],product_id=v['meta']['ProductID'],metadata=v['meta'],grid=v['grid'],archive_sha256=receipts[s]['archive_sha256']) for s,v in sources.items()},aois=summaries,original_patch_count=82,verified_labels_admitted=0,new_class_labels=0,operational_alerts=0,band_mapping=BANDS,band_reference=SPECTRAL_REFERENCE,true_rgb='UNAVAILABLE:no blue band',bsi='UNAVAILABLE:standard BSI requires blue',indices=list(indices(np.ones((4,2,2),'float32'))),quality='No cloud/shadow/haze QA supplied; blank quality fields and zero accuracy placeholders do not prove clear imagery or absolute accuracy',no_new_downloads=True,no_gee=True)
 if sha(PARENT/'integrity.json')!=base_hash or sha(AOIS)!=aoi_hash:raise ValueError('Parent/AOI changed')
 for s,path in [('before',Path(before)),('after',Path(after))]:
  if sha(path)!=receipts[s]['archive_sha256']:raise ValueError('ZIP changed')
 save(OUT/'summary.json',summary);finalize(OUT,summary);save(OUT/'integrity.json',{p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and not p.is_relative_to(OUT/'raw')})

def finalize(root,summary):
    root=Path(root);path=root/'evidence_manifest.json'
    if path.exists():
        current=json.loads(path.read_bytes())
        if current['parent_integrity_sha256']!=summary['parent82_inventory_sha256'] or current['original_patches_unchanged']!=82 or current['model_input_layers_added']!=0 or current['verified_labels_added']!=0:raise ValueError('Evidence attachment changed')
        for row in current['attachments']:
            if row['model_input_eligible'] or row['reference_admitted']:raise ValueError('Unapproved evidence promotion')
            for name,digest in row['layers'].items():
                if sha(root/row['directory']/name)!=digest:raise ValueError('Evidence layer changed')
        return current
    attachments=[]
    for row in summary['aois']:
        pid=row['aoi_id'];folder=root/'aois'/pid
        attachments.append(dict(aoi_id=pid,block=row['block'],split='train',directory=folder.relative_to(root).as_posix(),layers={p.name:sha(p) for p in folder.glob('*.tif')},model_input_eligible=False,reference_admitted=False,quality_gate=dict(radiometry='DECLARED_BOA_SCALE_VALID',valid_support=row['common_valid_percent'],cloud_shadow_haze='UNVERIFIED',independent_registration='UNVERIFIED',permission='PRODUCT_TERMS_UNCONFIRMED'),interpretation='UNKNOWN; no automatic agriculture/construction/mining label; single-date vs seasonal evidence not equivalent'))
    value=dict(schema='mci-nrsc-diagnostic-evidence/1',parent_path='../competing-supplement-v1',parent_integrity_sha256=summary['parent82_inventory_sha256'],original_patches_unchanged=82,model_input_layers_added=0,verified_labels_added=0,weak_labels_added=0,operational_alerts=0,test_access=False,attachments=attachments)
    save(path,value);return value


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--after',required=True);a=p.parse_args();run(a.before,a.after)
