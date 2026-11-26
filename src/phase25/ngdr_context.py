"""Private bounded NGDR integration; source attributes are never reference labels."""
import io,json,zipfile,hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import shape
from shapely import make_valid
from rasterio.features import rasterize
from rasterio.warp import transform_geom


def archives(folder):
 records={'lithology':[],'leases':[]};provenance=[];budget=[0]
 def scan(raw,chain,kind):
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   if any(e.file_size>12000000 for e in z.infolist()) or budget[0]+sum(e.file_size for e in z.infolist())>30000000:raise ValueError('Archive size cap')
   if chain.count('/')>6:raise ValueError('Nested archive depth')
   if z.testzip() is not None:raise ValueError('ZIP CRC')
   for entry in z.infolist():
    if entry.is_dir():continue
    if Path(entry.filename).is_absolute() or '..' in Path(entry.filename).parts:raise ValueError('Unsafe archive member')
    budget[0]+=entry.file_size
    if entry.file_size>12000000 or budget[0]>30000000:raise ValueError('Archive size cap')
    data=z.read(entry)
    if entry.filename.lower().endswith('.zip'):scan(data,chain+'/'+entry.filename,kind)
    elif entry.filename.lower().endswith(('.geojson','.json')):
     d=json.loads(data);crs=d.get('crs',{}).get('properties',{}).get('name')
     if crs!='urn:ogc:def:crs:OGC:1.3:CRS84':raise ValueError('Unverified NGDR CRS')
     repaired=0
     for f in d['features']:
      g=shape(f['geometry'])
      if not g.is_valid:g=make_valid(g);repaired+=1
      if g.is_empty or g.geom_type not in ('Polygon','MultiPolygon'):continue
      if not (-180<=g.bounds[0]<=g.bounds[2]<=180 and -90<=g.bounds[1]<=g.bounds[3]<=90):raise ValueError('Coordinate range')
      props=f['properties'];label=str(props.get('lithologic','UNKNOWN')) if kind=='lithology' else str(props.get('mineral_na','UNKNOWN'))
      records[kind].append((g,label))
     provenance.append(dict(member=chain+'/'+entry.filename,sha256=hashlib.sha256(data).hexdigest(),features=len(d['features']),repaired=repaired,crs=crs,scale='NOT_SUPPLIED',observation_date='NOT_SUPPLIED',rights='Product-specific redistribution unconfirmed; authorized private research only; strip contact attributes'))
 for p in sorted(Path(folder).glob('*.zip')):
  kind='lithology' if p.name.startswith('LITHOLOGY_') else 'leases' if p.name.startswith('INDIA_MAJOR_LEASE_') else None
  if kind:
   raw=p.read_bytes();provenance.append(dict(archive=p.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)));scan(raw,p.name,kind)
 if not all(records.values()):raise ValueError('Both actual NGDR sources required')
 return records,provenance


def context(records,row):
 from affine import Affine
 from rasterio.transform import array_bounds
 from shapely.geometry import box
 crs=row['crs'];grid=Affine(*row['affine']);shape_out=tuple(row['shape']);bounds=row['bounds']
 source_window=shape(transform_geom(crs,'EPSG:4326',box(*bounds).__geo_interface__))
 labels=sorted({label for _,label in records['lithology'] if 'UNMAPPED' not in label.upper()})
 codes={label:i+1 for i,label in enumerate(labels)};arrays=[]
 for kind in ['lithology','leases']:
  entries=[]
  for g,label in records[kind]:
   if not g.intersects(source_window) or (kind=='lithology' and label not in codes):continue
   clipped=g.intersection(source_window)
   if clipped.is_empty:continue
   entries.append((transform_geom('EPSG:4326',crs,clipped.__geo_interface__),codes[label] if kind=='lithology' else 1))
  arrays.append(rasterize(entries,out_shape=shape_out,transform=grid,fill=0,all_touched=False).astype('float32') if entries else np.zeros(shape_out,'float32'))
 geo,lease=arrays;geo[geo==0]=np.nan;lease[lease==0]=np.nan
 relevance=np.full(shape_out,np.nan,'float32')
 for label,code in codes.items():relevance[geo==code]=.6 if any(x in label.upper() for x in ['COAL','LIMESTONE']) else .25
 return np.stack([geo,lease,relevance]),codes
