"""Private NRSC LISS-III BOA evidence helpers; no reference-label admission."""
import hashlib,json,shutil,stat,zipfile
from pathlib import Path,PurePosixPath
import numpy as np

BANDS={'BAND2.tif':'green','BAND3.tif':'red','BAND4.tif':'nir','BAND5.tif':'swir'}
SPECTRAL_REFERENCE='https://bhoonidhi.nrsc.gov.in/bhoonidhi_resources/help/docs/R2_data_user_handbook.pdf'


def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def member_path(root,name):
 p=PurePosixPath(name.replace('\\','/'))
 if p.is_absolute() or '..' in p.parts or ':' in name:raise ValueError('Unsafe archive path')
 target=(Path(root)/str(p)).resolve()
 if not target.is_relative_to(Path(root).resolve()):raise ValueError('Archive traversal')
 return target


def extract(archive,dest,max_bytes=1500000000):
 archive=Path(archive);dest=Path(dest).resolve();original=sha(archive);dest.mkdir(parents=True,exist_ok=True);hashes={}
 with zipfile.ZipFile(archive) as z:
  infos=z.infolist()
  if sum(i.file_size for i in infos)>max_bytes or shutil.disk_usage(dest).free<sum(i.file_size for i in infos)+2*2**30:raise ValueError('Extraction storage/size gate')
  seen=set()
  for info in infos:
   key=info.filename.replace('\\','/').casefold()
   if key in seen or stat.S_ISLNK(info.external_attr>>16):raise ValueError('Duplicate/symlink ZIP member')
   seen.add(key);p=member_path(dest,info.filename)
   if info.is_dir():p.mkdir(parents=True,exist_ok=True);continue
   p.parent.mkdir(parents=True,exist_ok=True);size=0
   import contextlib
   exists=p.exists();stream_hash=hashlib.sha256()
   with z.open(info) as src,(contextlib.nullcontext(None) if exists else p.open('xb')) as target:
    while chunk:=src.read(1024*1024):
     size+=len(chunk);stream_hash.update(chunk)
     if size>info.file_size:raise ValueError('ZIP member exceeds advertised size')
     if target is not None:target.write(chunk)
   if exists and (p.stat().st_size!=size or sha(p)!=stream_hash.hexdigest()):raise ValueError('Existing partial extraction mismatch; no overwrite')
   if size!=info.file_size:raise ValueError('Truncated ZIP member')
   hashes[p.relative_to(dest).as_posix()]=dict(sha256=sha(p),bytes=size,crc32=f'{info.CRC:08x}')
 if sha(archive)!=original:raise ValueError('Original archive changed')
 return dict(archive_name=archive.name,archive_sha256=original,archive_bytes=archive.stat().st_size,member_crc='all checked while reading ZIP members to EOF',members=hashes)


def metadata(path):
 result={}
 for line in Path(path).read_text(encoding='utf-8').splitlines():
  if '=' not in line:continue
  k,v=line.split('=',1)
  if k.strip() in result:raise ValueError('Duplicate metadata field')
  result[k.strip()]=v.strip()
 if result.get('Sensor')!='L3' or result.get('BandNumbers')!='2345' or result.get('ProcessingLevel')!='AtmosphericallyCorrectedProduct' or result.get('ValidRange')!='0-10000' or float(result.get('ScaleFactor','nan'))!=.0001:raise ValueError('Unsupported sensor/radiometry; do not guess')
 return result


def reflectance(raw,valid_masks,meta):
 if float(meta['ScaleFactor'])!=.0001 or meta['ValidRange']!='0-10000':raise ValueError('Unverified scale')
 raw=np.asarray(raw)
 if raw.ndim!=3 or raw.shape[0]!=4 or np.shape(valid_masks)!=raw.shape:raise ValueError('Four aligned LISS-III bands and masks required')
 valid=np.asarray(valid_masks,bool).all(0)&np.isfinite(raw).all(0)&((raw>=0)&(raw<=10000)).all(0)
 # NoData may be undeclared. All-band-zero padding is excluded explicitly; single-band zero is not automatically invalid.
 valid &= np.any(raw>0,axis=0)
 x=raw.astype('float32')*.0001;x[:,~valid]=np.nan
 return x,valid


def indices(x):
 g,r,n,s=x
 def ratio(a,b):
  den=a+b;return np.divide(a-b,den,out=np.full_like(a,np.nan),where=np.isfinite(den)&(den!=0))
 return dict(NDVI=ratio(n,r),NDWI=ratio(g,n),MNDWI=ratio(g,s),NDBI=ratio(s,n),brightness=np.mean(x,axis=0))


def flags(x,valid):
 g,r,n,s=x
 # Descriptive inspection flags ONLY: bright soil can resemble cloud, dark water can resemble shadow.
 return dict(valid_support=valid,bright_neutral_proxy=valid&(g>.3)&(r>.3)&(n>.3)&(abs(g-r)<.05),dark_surface_proxy=valid&(np.mean(x[:3],axis=0)<.05),water_spectral_proxy=valid&(g>s))


def relative_match(before,after,valid,radius=3):
 """Integer-lag gradient correlation: relative texture QA, never absolute accuracy."""
 if min(before.shape)<12 or valid.sum()<100:return dict(status='INSUFFICIENT_TEXTURE_SUPPORT')
 def highpass(a):
  from scipy.ndimage import gaussian_filter
  filled=np.where(np.isfinite(a),a,np.nanmedian(a));return filled-gaussian_filter(filled,1)
 a=highpass(before);b=highpass(after);scores=[]
 for dy in range(-radius,radius+1):
  for dx in range(-radius,radius+1):
   ya=slice(max(0,dy),min(a.shape[0],a.shape[0]+dy));yb=slice(max(0,-dy),min(a.shape[0],a.shape[0]-dy));xa=slice(max(0,dx),min(a.shape[1],a.shape[1]+dx));xb=slice(max(0,-dx),min(a.shape[1],a.shape[1]-dx))
   mask=valid[ya,xa]&valid[yb,xb];u=a[ya,xa][mask];v=b[yb,xb][mask]
   if len(u)<100 or u.std()<1e-6 or v.std()<1e-6:continue
   scores.append((float(np.corrcoef(u,v)[0,1]),dy,dx))
 if not scores:return dict(status='INSUFFICIENT_TEXTURE_SUPPORT')
 c,dy,dx=max(scores,key=lambda z:(z[0],-abs(z[1])-abs(z[2]),-z[1],-z[2]));zero=next((z[0] for z in scores if z[1:]==(0,0)),None)
 return dict(status='INTERNAL_RELATIVE_TEXTURE_ONLY',best_correlation=c,zero_lag_correlation=zero,after_shift_rows=dy,after_shift_columns=dx,image_column_row_shift_metres=[dx*24,dy*24],map_east_north_shift_metres=[dx*24,-dy*24],search_boundary=abs(dx)==radius or abs(dy)==radius,absolute_accuracy_m=None,independent_controls=False,limitations='Vegetation,illumination,clouds and real change can move the correlation peak; not RMSE/CE90; no image shift applied')
