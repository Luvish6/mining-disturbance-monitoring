"""Offline private interpretation handoff; no registration correction or label promotion."""
import json,html,os
from pathlib import Path
import numpy as np
import rasterio
from src.phase25.liss3_evidence import sha
from src.phase25.nrsc_readiness import quality_summary,registration_summary,readiness
from src.phase25.competing_data import load_extension
from scripts.phase25_liss3_review import finalize

ROOT=Path('outputs/phase25/datasets/nrsc-liss3-evidence-v1')
OUT=Path('outputs/phase25/qa/nrsc-review-readiness-v1')
POLICY=Path('config/phase25_nrsc_permissions_v1.json')


def save(path,data):
 with Path(path).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def run():
 if (OUT/'readiness.json').exists():raise ValueError('Completed readiness run exists; preserve it')
 s=json.loads((ROOT/'summary.json').read_bytes());finalize(ROOT,s);load_extension('outputs/phase25/datasets/competing-supplement-v1')
 for name,digest in json.loads((ROOT/'integrity.json').read_bytes()).items():
  if sha(ROOT/name)!=digest:raise ValueError('Original evidence changed')
 forms={name:sha(ROOT/name) for name in ['independent_review_empty.csv','independent_control_empty.csv']}
 permissions=json.loads(POLICY.read_bytes());references=json.loads((OUT/'cached_reference_inventory.json').read_bytes())
 if any(any(v['full_aoi_bbox_coverage'].values()) for v in references['planet'].values()):raise ValueError('Planet footprint inventory changed; inspect metadata before any payload access')
 result=[];cards=[];empty_controls=[]
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 for i,row in enumerate(s['aois'],1):
  pid=row['aoi_id'];src=ROOT/'aois'/pid;dest=OUT/pid;dest.mkdir(exist_ok=True);quality=quality_summary(row['coverage']);reg=registration_summary(row['relative_registration'],[]);gates=readiness(quality,reg,permissions)
  ref={season:next(r for r in rows if r['aoi_id']==pid) for season,rows in references['liss4'].items()}
  ref_status='REJECTED_FOR_CONTROL:afterimage visibly obscured/strong dark region,beforelowcontrast;no independently surveyed accuracy' if i==1 else 'REJECTED_FOR_CONTROL:no paired valid signal/full footprint'
  record=dict(aoi_id=pid,registration=reg,quality=quality,cached_liss4=ref,reference_assessment=ref_status,review_readiness=gates,stable_landmarks_accepted=[],sun_elevation_before_after=[row['coverage'][k]['sun_elevation'] for k in ['before','after']],rights=permissions)
  save(dest/'readiness.json',record);result.append(record)
  # Paired spectra remain unshifted; no delta/model/pseudo-label map in the blinded interpretation panel.
  fig,axes=plt.subplots(3,2,figsize=(9,12),layout='constrained');images=[]
  for j,season in enumerate(['before','after']):
   with rasterio.open(src/(season+'_native_sr.tif')) as ds:
    a=ds.read();a=np.where(a==ds.nodata,np.nan,a);extent=[ds.bounds.left,ds.bounds.right,ds.bounds.bottom,ds.bounds.top]
   with rasterio.open(src/(season+'_native_indices.tif')) as ds:
    ix=ds.read();ix=np.where(ix==ds.nodata,np.nan,ix);names=list(ds.descriptions)
   rgb=np.clip(a[[2,1,0]].transpose(1,2,0)/.5,0,1);axes[0,j].imshow(np.nan_to_num(rgb,nan=1),extent=extent,interpolation='nearest');axes[0,j].set_title(s['scenes'][season]['date']+' FCC NIR/red/green',fontsize=10)
   images.append(axes[1,j].imshow(np.ma.masked_invalid(ix[names.index('NDVI')]),extent=extent,vmin=-.1,vmax=1,cmap='RdYlGn',interpolation='nearest'));axes[1,j].set_title('NDVI (not a land-use label)',fontsize=10)
   im=axes[2,j].imshow(np.ma.masked_invalid(ix[names.index('NDBI')]),extent=extent,vmin=-.5,vmax=.5,cmap='RdBu_r',interpolation='nearest');axes[2,j].set_title('SWIR/NIR contrast (NDBI), not built-up truth',fontsize=9)
  fig.colorbar(images[0],ax=list(axes[1]),label='NDVI');fig.colorbar(im,ax=list(axes[2]),label='NDBI')
  for ax in axes.flat:ax.set_xlabel('UTM46N easting(m)',fontsize=8);ax.set_ylabel('Northing(m)',fontsize=8);ax.tick_params(labelsize=8);ax.ticklabel_format(style='plain',useOffset=False)
  fig.suptitle(f'PRIVATE LOCAL INSPECTION ONLY | TRAIN{i:02d}\n24moutput/23.5mnative; FCCfixed0..0.5reflectance stretch\n100%valid signal is NOT a clear-ground estimate. Registration unverified.\nNo accepted control; unknown cloud/haze/shadow fraction; no attributed labels.',fontsize=10)
  fig.savefig(dest/'blinded_paired_panel_v3.png',dpi=140);plt.close(fig)
  q=quality['after'];lag=reg['diagnostic_only'];image=(dest/'blinded_paired_panel_v3.png').relative_to(OUT).as_posix()
  cards.append(f'<section><h2>TRAIN{i:02d}: independent interpretation pending</h2><p>Valid signal:before100%,after100%; bright-neutral flags0. After dark flags:{q["dark_proxy_cells"]}({q["dark_proxy_percent"]:.3f}%). These are NOT validated cloud/shadow counts. Clear/haze/shadow percentages unknown.</p><p>Accepted independent landmarks:0. Offset/uncertainty unknown. Existing texture lag:{lag["image_column_row_lag_pixels"]}pixels; correlation{lag["best_correlation"]:.3f}; NOT an accuracy estimate. No shift applied.</p><img src="{html.escape(image)}" alt="Unshifted paired false-colour,NDVI and SWIR/NIR panels"/><p>Do not attribute spatial differences until stable controls and quality are verified.</p></section>')
  for direction in ['northwest','northeast','southwest','southeast','interior1','interior2']:empty_controls.append(dict(aoi_id=pid,intended_distribution=direction,control_description='',independent_source='',reference_date='',reference_crs='',reference_coordinates='',documented_uncertainty_m='',before_landmark='',after_landmark='',reviewer='',acceptance=''))
 save(OUT/'readiness.json',dict(schema='nrsc-interpretation-readiness/1',parent_summary_sha256=sha(ROOT/'summary.json'),cached_reference_inventory_sha256=sha(OUT/'cached_reference_inventory.json'),policy_sha256=sha(POLICY),original_forms_sha256=forms,aois=result,automatic_corrections=0,verified_controls=0,model_input_layers_added=0,labels_added=0,external_reviewer_release=False,test_access=False))
 import csv
 with (OUT/'external_control_requirements_empty.csv').open('x',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(empty_controls[0]));w.writeheader();w.writerows(empty_controls)
 (OUT/'external_requirements.md').write_text('''# Exact unresolved prerequisites

All three AOIs: independently georeferenced, distributed permanent landmarks visible in both LISS3dates. Prefer surveyed points or an orthophoto with documented date,datum/CRS and positional error suitable for the existing<=30madmission gate. Plan six candidate checkpoints perAOI across quadrants/interior (a proposed collection plan,not a relaxed/new admission standard); reserve checks independent of any fitted correction. Coordinates and reviewer decisions remain blank. Stable road junctions/rock outcrops may be candidates only after verifying they are unchanged and outside cloud/shadow. Vegetation-only texture is not a stable control. No accepted landmarks exist in the inspected caches; no offset or statistical uncertainty can currently be estimated. Do not widen/force a correlation search or warp these scenes to improve appearance.

TRAIN01:cachedMarch/November2024LISS4has signal,butafterpreviewhas broad bright obscuration/dark region consistent with clouds/shadows,beforeis lowcontrast; no geographically distributed qualifying tie set. TRAIN02:beforeLISS4allzero;afterdoes not fully cover AOI. TRAIN03:bothLISS4cropsallzero. KnownPlanetfootprints miss allthree; protected pixels were not opened. ExistingSentinel30mseasonalinputs are contextual sensor data,not surveyed absolute controls. The inspected reference-annotation folders contain metadata/plans,not a qualifying new reference image. No new imagery downloaded.

Quality:provider cloud/quality fields blank,no QA mask,blue/cirrus unavailable,metadata accuracyzerois not a measured error. Quantify no clear/cloud/haze/shadow fraction from unvalidated proxies. Need provider scene/product quality information or documented,independent visual assessment of unoccluded ground and residual haze/shadow. Sun-elevation difference3.090187degrees is illumination context,not a correction or measured shadow extent.

Permissions:obtain the accepted terms/order record for the two supplied LISS3BOAproducts,confirm local reviewer viewing,restricted copies,public noncommercial imagery/derivatives and attribution separately. Ask NRSC to clarify the two ProductIDs recorded privately in archive_receipts.json and the zeroaccuracyfields. Current general EULA supports lawful registered research/value addition and bars commercial original-data redistribution; it is not the missing exact-product sharing record. No request was sent. Source:https://bhoonidhi.nrsc.gov.in/bhoonidhi/registration.html

All82patches,labels,originalreviewforms and frozenVAL/TESTremain unchanged. This package supports local owner qualitative inspection only; independent reference review/admission remains blocked. No algorithm predictions,weak masks,model scores or threshold maps are in the new panels.
''',encoding='utf-8')
 (OUT/'index.html').write_text('<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' file:; style-src \'unsafe-inline\'"><title>Private NRSC interpretation</title><style>body{font:16px sans-serif;max-width:1100px;margin:auto;padding:20px}section{border-top:2px solid #789;margin-top:30px}img{max-width:100%}.warning{background:#fff1c2;padding:20px}</style></head><body><h1>Private NRSC interpretation package</h1><p class="warning">LOCAL OWNER INSPECTION ONLY. External sharing and verified reference decisions BLOCKED pending permissions,quality and independent registration controls. Not approved labels or model inputs.</p>'+''.join(cards)+'</body></html>',encoding='utf-8')
 if any(sha(ROOT/name)!=digest for name,digest in forms.items()):raise ValueError('Blinded forms changed')
 save(OUT/'integrity.json',{p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()})
 print('Three private panels;0verified controls;no corrections; original forms preserved')

if __name__=='__main__':run()
