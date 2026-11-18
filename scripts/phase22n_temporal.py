"""Offline replay of preregistered eligible Phase 22N development AOIs."""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from scipy.ndimage import label
from shapely.geometry import box, shape, Point
from shapely.ops import unary_union
from shapely import transform as geometry_transform
from rasterio.features import shapes
from rasterio.warp import transform_geom

from scripts.phase22l_temporal import select_candidates, render, FIELDS
from src.phase3.spatial import block_for, partition

PLAN = Path("docs/reports/phase22n-preregistration.json")
OUT = Path("outputs/phase22n_temporal")
CACHE = Path("outputs/phase22l_temporal_pilot")
DISTRICTS = Path("outputs/phase6b_multitile/districts.json")
ROSTER = Path("outputs/phase6b_multitile/roster.json")
CRS = "EPSG:32646"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")


def rectangle(lon, lat):
    x,y = Transformer.from_crs(4326, CRS, always_xy=True).transform(lon,lat)
    left,top = round(x/30)*30-960,round(y/30)*30+960
    return box(left,top-1920,left+1920,top)


def guards():
    roster=json.loads(ROSTER.read_bytes())
    if sha(DISTRICTS)!=roster["geometry_sha256"]:
        raise ValueError("Frozen district hash mismatch")
    t=Transformer.from_crs(4326,CRS,always_xy=True)
    area=unary_union([geometry_transform(shape(f["geometry"]),t.transform,interleaved=False)
                     for f in json.loads(DISTRICTS.read_bytes())["features"]])
    x0,y0,x1,y1=area.bounds
    protected=[]
    for x in range(math.floor(x0/5000)-1,math.ceil(x1/5000)+1):
        for y in range(math.floor(y0/5000)-1,math.ceil(y1/5000)+1):
            key=f"{x}:{y}"
            if partition(key)=="test":
                protected.append((key,box(x*5000,y*5000,(x+1)*5000,(y+1)*5000).buffer(120,join_style=2)))
    return area,protected


def check(lon,lat,area,protected):
    p=rectangle(lon,lat)
    hits=[(k,g) for k,g in protected if p.intersects(g)]
    key=block_for(p.bounds)
    center=Point(*Transformer.from_crs(4326,CRS,always_xy=True).transform(lon,lat))
    nearest=min(protected,key=lambda item:center.distance(item[1].boundary))
    return dict(bounds=list(p.bounds),block=key,split=partition(key) if key else None,
                district_contained=area.covers(p),test_intersections=[k for k,g in hits],
                test_buffer_overlap_m2=sum(p.intersection(g).area for k,g in hits),
                rectangle_test_buffer_distance_m=min(p.distance(g) for k,g in protected),
                center_nearest_test_buffer=nearest[0],
                center_distance_to_test_buffer_boundary_m=center.distance(nearest[1].boundary),
                center_inside_nearest_test_buffer=nearest[1].covers(center),
                eligible=area.covers(p) and not hits and key is not None and partition(key)!="test")


def cluster_stats(b,a,eligible,candidates,slope):
    ids,n=label(candidates,structure=np.ones((3,3),dtype=int))
    rows=[]
    for i in range(1,n+1):
        m=ids==i
        rows.append(dict(cluster=i,cells=int(m.sum()),hectares=float(m.sum()*.09),
            before_ndvi_mean=float(b[3][m].mean()),after_ndvi_mean=float(a[3][m].mean()),
            before_bsi_mean=float(b[4][m].mean()),after_bsi_mean=float(a[4][m].mean()),
            before_ndvi_lt_020_fraction=float((b[3][m]<.20).mean()),
            slope_range_deg=[float(slope[m].min()),float(slope[m].max())]))
    fraction=float((b[3][eligible]<.20).mean()) if eligible.any() else None
    return ids,rows,fraction


def run():
    plan=json.loads(PLAN.read_bytes())
    if OUT.exists():
        raise ValueError("Preserve existing results")
    for path,expected in plan["source_hashes"].items():
        if sha(path)!=expected:
            raise ValueError("Changed frozen input: "+path)
    area,protected=guards()
    accepted=[]
    for row in plan["eligible_aois"]:
        actual=check(*row["anchor"],area,protected)
        if actual!=row["guard"] or not actual["eligible"]:
            raise ValueError("AOI guard mismatch")
        p=box(*actual["bounds"])
        if any(p.intersects(q) for q in accepted):
            raise ValueError("Overlapping eligible AOIs")
        accepted.append(p)
    if len(accepted)!=1 or plan["eligible_aois"][0]["id"]!="east-94-559-c74":
        raise ValueError("This replay supports only the frozen cached AOI")
    r=json.loads((CACHE/"receipt.json").read_bytes())
    with rasterio.open(CACHE/"seasonal.tif") as ds:
        expected=tuple(["before_"+k for k in FIELDS]+["before_count"]+["after_"+k for k in FIELDS]+["after_count","slope"])
        if ds.shape!=(64,64) or ds.count!=15 or ds.crs.to_string()!=CRS or ds.descriptions!=expected:
            raise ValueError("Cache grid/bands invalid")
        if list(ds.bounds)!=plan["eligible_aois"][0]["guard"]["bounds"] or ds.nodata!=-9999:
            raise ValueError("Cache bounds/NoData mismatch")
        if ds.transform!=Affine(30,0,ds.bounds.left,0,-30,ds.bounds.top):
            raise ValueError("Cache affine mismatch")
        values=ds.read().astype(float); affine=ds.transform; bounds=list(ds.bounds)
    values[values==-9999]=np.nan
    b,a=values[:6],values[7:13]; bc,ac=values[6],values[13]; slope=values[14]
    for im,c in ((b,bc),(a,ac)):
        if not np.isfinite(c).all() or (c<0).any() or (c!=np.floor(c)).any() or not np.array_equal(np.isfinite(im).all(axis=0),c>=2):
            raise ValueError("Invalid counts/seasonal support")
    valid,mask,dv,db=select_candidates(b,a,bc,ac,slope)
    ids,stats,background=cluster_stats(b,a,valid,mask,slope)
    if (int(valid.sum()),int(mask.sum()),len(stats))!=(r["eligible_cells"],r["candidate_cells"],r["candidates"]):
        raise ValueError("Frozen result replay mismatch")
    OUT.mkdir(parents=True)
    features=[]; review=[]
    for geom,i in shapes(ids.astype("int32"),mask=mask,transform=affine,connectivity=8):
        row=stats[int(i)-1]; cid=f"east-94-559-c74-C{int(i):03d}"
        geo=transform_geom(CRS,"EPSG:4326",geom)
        centroid=shape(geo).centroid
        features.append(dict(type="Feature",geometry=geo,properties=dict(row,cluster_id=cid,status="candidate disturbance, UNKNOWN - not validated.")))
        review.append(dict(cluster_id=cid,aoi_id="east-94-559-c74",latitude=centroid.y,longitude=centroid.x,
            polygon_file="clusters.geojson#"+cid,satellite_acquisition_date_range="2023-11-01/2024-03-31;2024-11-01/2025-03-31",
            reviewer_id="",imagery_date_reviewed="",verdict="",notes=""))
    save(OUT/"clusters.geojson",dict(type="FeatureCollection",features=features))
    with (OUT/"review.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(review[0]) if review else ["cluster_id"]);writer.writeheader();writer.writerows(review)
    render(b,a,valid,dv,mask,bounds,OUT/"comparison.png")
    days={k:len({int(v)//86400000 for v in src["dates_ms"]}) for k,src in r["sources"].items()}
    result=dict(aoi_id="east-94-559-c74",anchor=r["anchor"],block=r["block"],eligible_cells=int(valid.sum()),coverage_percent=float(valid.mean()*100),
        candidate_cells=int(mask.sum()),candidate_clusters=len(stats),candidate_hectares=float(mask.sum()*.09),
        slope_range_deg=r["slope_context_candidate_deg"],independent_capture_days=days,
        eligible_before_ndvi_lt_020_fraction=background,
        candidate_before_ndvi_lt_020_fraction=float((b[3][mask]<.20).mean()) if mask.any() else None,
        clusters=stats,control_status="INELIGIBLE; no measurements",control_metrics=None,
        earth_engine_requests=0,response_body_bytes=0,cache_receipt_sha256=sha(CACHE/"receipt.json"),
        cache_raster_sha256=sha(CACHE/"seasonal.tif"),plan_sha256=sha(PLAN),
        quality=r["quality"],status="candidate disturbance, UNKNOWN - not validated.",
        review_verdicts=["excavation","other","uncertain"])
    save(OUT/"results.json",result)
    save(OUT/"product_hashes.json",{p.name:sha(p) for p in OUT.iterdir() if p.is_file()})
    print(json.dumps(result,allow_nan=False))


if __name__=="__main__":
    run()
