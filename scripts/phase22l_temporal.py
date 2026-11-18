"""One small temporal optical land-change pilot at an existing Meghalaya TRAIN lead."""

import json
from pathlib import Path

from affine import Affine
import ee
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom
from shapely.geometry import shape

from config.phase2_settings import Phase2Config
from config.settings import BEFORE, AFTER
from scripts.phase22b_maus import digest, fetch, write_json
from src.gee_setup import initialize
from src.optical_preprocessing import collections
from src.study_area import get_study_area

OUT=Path("outputs/phase22l_temporal_pilot")
SOURCE=Path("outputs/phase11b_reference_packages/east-94-559-c74.json")
CRS="EPSG:32646"
SIZE=64
SCALE=30
NODATA=-9999
FIELDS=("B4","B3","B2","NDVI","BSI","NDWI")


def select_candidates(before,after,counts_before,counts_after,slope):
    finite=np.isfinite(before).all(axis=0)&np.isfinite(after).all(axis=0)&np.isfinite(slope)
    eligible=finite&(counts_before>=2)&(counts_after>=2)&(before[5]<0)&(after[5]<0)
    delta=after[3]-before[3]
    exposed=after[4]-before[4]
    result=eligible&(delta<=-.30)&(exposed>.10)
    return eligible,result,delta,exposed


def seasonal_graph(region,season,cfg):
    raw,joined=collections(region,season,cfg)
    def prepare(img):
        cloud=ee.Image(img.get("clouds")).select("probability")
        scl=img.select("SCL")
        needed=img.select(["B2","B3","B4","B8","B11"])
        mask=(cloud.lt(cfg.cloud_probability).And(scl.eq(4).Or(scl.eq(5)))
              .And(img.select("B8A").mask()).And(img.select("B9").mask())
              .And(needed.mask().reduce(ee.Reducer.min())))
        sr=needed.divide(10000).updateMask(mask)
        blue,green,red,nir,swir=[sr.select(k) for k in ("B2","B3","B4","B8","B11")]
        def ratio(a,b,name):
            den=a.add(b)
            return a.subtract(b).divide(den).updateMask(den.neq(0)).rename(name)
        ndvi=ratio(nir,red,"NDVI")
        ndwi=ratio(green,nir,"NDWI")
        bsi=ratio(swir.add(red),nir.add(blue),"BSI")
        # Additional conservative water and very-dark surface screening.
        land=ndwi.lt(0).And(green.add(red).add(nir).divide(3).gte(.04))
        out=sr.select(["B4","B3","B2"]).addBands(ndvi).addBands(bsi).addBands(ndwi)
        return out.updateMask(land).updateMask(out.mask().reduce(ee.Reducer.min()))
    daily=joined.map(prepare)
    count=daily.select("NDVI").count().unmask(0).rename("count")
    return daily.median().updateMask(count.gte(2)),count,raw,joined


def render(b,a,valid,dv,mask,bounds,target):
    extent=(bounds[0],bounds[2],bounds[1],bounds[3])
    fig,axes=plt.subplots(1,3,figsize=(12,4),layout="constrained")
    for ax,img,title in zip(axes[:2],(b,a),("Before Nov 2023–Mar 2024","After Nov 2024–Mar 2025"),strict=True):
        rgb=np.clip(img[:3].transpose(1,2,0)/.3,0,1)
        ax.imshow(rgb,extent=extent)
        ax.set_title(title,fontsize=10)
    im=axes[2].imshow(np.ma.masked_where(~valid,dv),vmin=-.6,vmax=.6,cmap="RdYlGn",extent=extent)
    axes[2].set_title("NDVI difference; valid land",fontsize=10)
    if mask.any():
        for ax in axes:
            ax.contour(mask.astype(float),levels=[.5],colors=["magenta"],extent=extent,origin="upper",linewidths=.8)
    for ax in axes:
        ax.set_xlabel("UTM easting (m)")
        ax.set_ylabel("UTM northing (m)")
        ax.ticklabel_format(style="plain",useOffset=False)
    fig.colorbar(im,ax=axes[2],label="NDVI difference")
    fig.suptitle("Exploratory land change; magenta outlines are review candidates")
    fig.savefig(target,dpi=150)
    plt.close(fig)


def run():
    if OUT.exists():
        raise ValueError("Preserve existing pilot outputs; choose a new version explicitly")
    source=SOURCE.read_bytes()
    anchor=json.loads(source)
    if anchor["split"]!="train" or anchor["block"]!="94:559":
        raise ValueError("Expected the existing TRAIN discovery lead")
    lon,lat=anchor["anchor"]
    x,y=Transformer.from_crs(4326,CRS,always_xy=True).transform(lon,lat)
    left,top=round(x/30)*30-960,round(y/30)*30+960
    affine=Affine(30,0,left,0,-30,top)
    bounds=(left,top-SIZE*SCALE,left+SIZE*SCALE,top)
    initialize()
    region=ee.Geometry.Rectangle(list(bounds),CRS,False)
    districts=get_study_area()
    names=districts.aggregate_array("GAUL2_NAME").getInfo()
    if set(names)!={"East Jaintia Hills","West Jaintia Hills"} or not districts.geometry().contains(region,1).getInfo():
        raise ValueError("Pilot rectangle is not contained in the verified district geometry")
    cfg=Phase2Config()
    parts=[]
    scenes={}
    band_names=[]
    for name,season in (("before",BEFORE),("after",AFTER)):
        image,count,raw,joined=seasonal_graph(region,season,cfg)
        metadata=ee.Dictionary(dict(raw_count=raw.size(),joined_count=joined.size(),
            ids=joined.aggregate_array("system:index"),
            dates_ms=joined.aggregate_array("system:time_start"))).getInfo()
        if metadata["joined_count"]<2:
            raise ValueError("Insufficient joined seasonal optical observations")
        scenes[name]=metadata
        names=[f"{name}_{k}" for k in FIELDS]
        parts.append(image.select(list(FIELDS)).rename(names).addBands(count.rename(f"{name}_count")))
        band_names+=names+[f"{name}_count"]
    slope=ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003").select("elevation")).rename("slope")
    stack=parts[0].addBands(parts[1]).addBands(slope).select(band_names+["slope"])
    band_names+=["slope"]
    if stack.bandNames().getInfo()!=band_names:
        raise ValueError("Incorrect graph band order")
    url=stack.toFloat().unmask(NODATA,False).getDownloadURL(dict(
        format="GEO_TIFF",crs=CRS,crs_transform=list(affine)[:6],dimensions=[SIZE,SIZE]))
    raw=fetch(url,2*1024**2)
    from rasterio.io import MemoryFile
    with MemoryFile(raw) as memory,memory.open() as ds:
        if (ds.shape!=(SIZE,SIZE) or ds.count!=15 or ds.crs.to_string()!=CRS
                or ds.transform!=affine or (any(ds.descriptions) and ds.descriptions!=tuple(band_names))):
            raise ValueError("Unexpected seasonal export grid")
        data,profile=ds.read(),ds.profile
    OUT.mkdir(parents=True)
    profile.update(nodata=NODATA,compress="deflate")
    with rasterio.open(OUT/"seasonal.tif","w",**profile) as ds:
        ds.write(data)
        ds.descriptions=tuple(band_names)
    values=data.astype(float)
    values[values==NODATA]=np.nan
    b,a=values[:6],values[7:13]
    bc,ac=values[6],values[13]
    if any(not np.isfinite(c).all() or (c<0).any() or (c!=np.floor(c)).any() for c in (bc,ac)):
        raise ValueError("Invalid observation counts")
    for img,c in ((b,bc),(a,ac)):
        if not np.array_equal(np.isfinite(img).all(axis=0),c>=2):
            raise ValueError("Seasonal values disagree with count masks")
    valid,mask,dv,de=select_candidates(b,a,bc,ac,values[14])
    feats=[]
    for geom,value in shapes(mask.astype("uint8"),mask=mask,transform=affine,connectivity=8):
        poly=shape(geom)
        feats.append(dict(type="Feature",geometry=transform_geom(CRS,"EPSG:4326",geom),
            properties=dict(status="EXPLORATORY_REVIEW_REQUIRED",reference_status="UNKNOWN",
                area_m2=poly.area,pixels=round(poly.area/900))))
    write_json(OUT/"candidates.geojson",dict(type="FeatureCollection",features=feats))
    diag=np.stack([valid,mask,dv,de]).astype("float32")
    diag[~np.isfinite(diag)]=NODATA
    with rasterio.open(OUT/"change.tif","w",driver="GTiff",width=SIZE,height=SIZE,count=4,
                       dtype="float32",crs=CRS,transform=affine,nodata=NODATA) as ds:
        ds.write(diag)
        ds.descriptions=("eligible","exploratory_candidate","dNDVI","dBSI")
    render(b,a,valid,dv,mask,bounds,OUT/"comparison.png")
    report=dict(anchor=[lon,lat],candidate_source_sha256=digest(source),source_split="train",
        block=anchor["block"],grid=dict(crs=CRS,affine=list(affine)[:6],bounds=bounds,size=SIZE),
        seasons=dict(before=[BEFORE.start,BEFORE.end],after=[AFTER.start,AFTER.end]),
        collections=["COPERNICUS/S2_SR_HARMONIZED","COPERNICUS/S2_CLOUD_PROBABILITY","USGS/SRTMGL1_003"],
        sources=scenes,bands=band_names,response_bytes=len(raw),raw_sha256=digest(raw),
        raster_sha256=digest((OUT/"seasonal.tif").read_bytes()),
        eligible_cells=int(valid.sum()),denominator=SIZE*SIZE,
        before_valid_cells=int((bc>=2).sum()),after_valid_cells=int((ac>=2).sum()),
        counts=dict(before=[int(bc.min()),int(bc.max())],after=[int(ac.min()),int(ac.max())]),
        candidates=len(feats),candidate_cells=int(mask.sum()),area_m2=int(mask.sum())*900,
        slope_context_candidate_deg=[float(values[14][mask].min()),float(values[14][mask].max())] if mask.any() else None,
        rule=dict(dNDVI_lte=-.30,dBSI_gt=.10,min_observations=2,min_brightness=.04,NDWI_lt=0),
        bsi="((B11+B4)-(B8+B2))/((B11+B4)+(B8+B2)); B11 native 20m sampled on 30m output",
        quality="SCL 4/5 land, cloud probability<40, scene cloud<=80; dark and water screen; residual terrain shadow unresolved",
        status="EXPLORATORY",reference_status="UNKNOWN")
    write_json(OUT/"receipt.json",report)
    print(json.dumps(report))


if __name__=="__main__":
    run()
