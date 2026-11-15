"""Bounded real Sentinel cache augmentation and scene-disjoint replica acquisition."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

import ee
import numpy as np
import rasterio
from rasterio.io import MemoryFile
import requests

from config.phase2_settings import Phase2Config
from scripts import phase6b_multitile as phase6
from src import optical_preprocessing as optical, sar_preprocessing as sar
from src.change_features import build_stack
from src.coverage_diagnostics import COUNT_BANDS, validity_image
from src.phase3.data import BANDS, BAND_UNITS, digest, save_json
from src.phase3.regional_inference import NODATA, write_tile

SITES = ("gevra", "bhubaneswari")
RAW_LIMIT = 2*1024**2


def day(ms):
    return datetime.fromtimestamp(ms/1000, timezone.utc).date().isoformat()


def divide(rows, season, minimum, stride=1):
    grouped = {}
    for scene_id, time in rows:
        key = day(time)
        if not scene_id or not season.start <= key < season.end:
            raise ValueError("Invalid scene provenance")
        grouped.setdefault(key, []).append((scene_id,time))
    if len({sid for sid,_ in rows}) != len(rows):
        raise ValueError("Duplicate source product")
    groups = [[], []]
    for index, date in enumerate(sorted(grouped)):
        groups[(index//stride)%2].extend(sorted(grouped[date]))
    if any(len({day(t) for _,t in r}) < minimum for r in groups):
        raise ValueError("Insufficient independent acquisition dates per replica")
    return groups


def inventory(region,cfg):
    def rows(col):
        col = col.sort("system:index")
        return col.aggregate_array("system:index").zip(col.aggregate_array("system:time_start"))

    return ee.List([ee.Dictionary(dict(
        s1=rows(sar.collection(region, season, cfg).filter(ee.Filter.eq("relativeOrbitNumber_start",cfg.relative_orbit))),
        s2=rows(optical.collections(region,season,cfg)[1])))
        for season in phase6.SEASONS]).getInfo()


def replicas(sources,cfg,stride=1):
    result = [[],[]]
    for season,rows in zip(phase6.SEASONS,sources,strict=True):
        radar,optical_rows = (divide(rows[key],season,cfg.min_observations,stride) for key in ("s1","s2"))
        for index in (0,1):
            result[index].append(dict(s1=radar[index],s2=optical_rows[index],s2_cloud=optical_rows[index]))
    for sensor in ("s1","s2","s2_cloud"):
        a,b = ({sid for season in r for sid,_ in season[sensor]} for r in result)
        if a & b:
            raise ValueError("Shared source scene between replicas")
    return result


def replica_image(region,cfg,manifest):
    radar, optical_images, rc, oc, verification = [],[],[],[],[]
    for season,source in zip(phase6.SEASONS,manifest,strict=True):
        r = sar.collection(region,season,cfg).filter(ee.Filter.eq("relativeOrbitNumber_start",cfg.relative_orbit))
        r = r.filter(ee.Filter.inList("system:index",[i for i,_ in source["s1"]]))
        o = optical.collections(region,season,cfg)[1].filter(
            ee.Filter.inList("system:index",[i for i,_ in source["s2"]]))
        image,count = sar.seasonal(r,cfg.relative_orbit,region,cfg)
        radar.append(image)
        rc.append(count)
        image,count = optical.seasonal(o,region,cfg)
        optical_images.append(image)
        oc.append(count)
        cloud = ee.ImageCollection(o.map(lambda im: ee.Image(im.get("clouds"))))
        verification.append(ee.Dictionary(dict(s1=r.aggregate_array("system:index"),s2=o.aggregate_array("system:index"),
                                               s2_cloud=cloud.aggregate_array("system:index"))))
    actual = ee.List(verification).getInfo()
    for expected, observed in zip(manifest,actual,strict=True):
        if any(sorted(i for i,_ in expected[k]) != sorted(observed[k]) for k in expected):
            raise ValueError("Earth Engine used a different scene inventory")
    s0,s1 = radar
    o0,o1 = optical_images
    pair = ee.Image.cat([s0,o0,s1,o1,build_stack(s0,s1,o0,o1,region)]).rename(list(BANDS))
    counts = ee.Image.cat(rc+oc).rename(list(COUNT_BANDS)).unmask(0,False)
    return ee.Image.cat([pair,counts,validity_image(pair.select(list(BANDS[8:])),counts,cfg)]).toFloat().unmask(NODATA,False)


def export(image, output, bounds, cfg, size, scenes):
    affine = rasterio.Affine(30,0,bounds[0],0,-30,bounds[3])
    url = image.getDownloadURL(dict(format="GEO_TIFF",crs=cfg.analysis_crs,
                                    crs_transform=list(affine)[:6],dimensions=[size,size]))
    payload = bytearray()
    with requests.get(url,timeout=(15,120),stream=True) as response:
        if response.status_code!=200:
            raise RuntimeError(f"Earth Engine HTTP {response.status_code}")
        for chunk in response.iter_content(65536):
            if len(payload)+len(chunk)>RAW_LIMIT:
                raise ValueError("Raster byte budget exceeded")
            payload.extend(chunk)
    with MemoryFile(bytes(payload)) as mem, mem.open() as src:
        if ((str(src.crs),src.transform,src.shape,src.count)!=(cfg.analysis_crs,affine,(size,size),len(phase6.SCHEMA))
                or any(src.descriptions) and src.descriptions!=phase6.SCHEMA):
            raise ValueError("Unexpected export grid or bands")
        data,profile = src.read(),src.profile
    limits = [len(season[sensor]) for sensor in ("s1","s2") for season in scenes]
    qa = phase6.validate_pixels(data,limits,size=size,cfg=cfg)
    denom = qa["denominator"]
    valid = qa["valid_cells"]
    qa["passes"] = (valid["common_valid"]/denom>=cfg.min_common_coverage
                    and all(valid[k]/denom>=cfg.min_sar_coverage for k in ("sar_before_valid","sar_after_valid")))
    qa["slope_percentiles"] = np.percentile(data[13][data[13]!=NODATA],[10,50,90]).tolist()
    output.mkdir()
    write_tile(output/"features.tif",profile,BANDS,data[:14],dict(data_kind="real"),BAND_UNITS)
    write_tile(output/"diagnostics.tif",profile,phase6.DIAGNOSTICS,data[14:],dict(data_kind="real"))
    qa.update(crs=cfg.analysis_crs, transform=list(affine)[:6], counts=limits, scenes=scenes,
              settings=asdict(cfg), seasons=[asdict(s) for s in phase6.SEASONS],collections=phase6.COLLECTIONS,
              raw_bytes=len(payload),hashes={name:digest(output/name) for name in ("features.tif","diagnostics.tif")})
    save_json(output/"receipt.json",qa)
    return qa, data[-1]==1


def new_blocks(cache):
    original = json.loads((cache/"roster.json").read_bytes())
    if digest(cache/"districts.json")!=original["geometry_sha256"]:
        raise ValueError("Frozen district geometry changed")
    old = original["selected"]
    candidates = json.loads((cache/"geometry_preflight.json").read_bytes())
    candidates = candidates["shortlist"] + [r for r in candidates["rejected"] if r["reason"]=="outside first three hash ranks"]
    districts = phase6.geometry(cache)
    excluded = {r["block"] for r in old}
    options = []
    for row in old:
        if row["split"]=="test":
            continue
        matching = [r for r in candidates if r["district"]==row["district"] and r["split"]==row["split"]
                    and r["block"] not in excluded]
        options.extend(sorted(matching,key=lambda r:r["rank"])[:3])
    for row in options:
        if (phase6.block_for(row["bounds"])!=row["block"] or phase6.partition(row["block"])!=row["split"]
                or not districts[row["district"]].covers(phase6.box(*row["bounds"]))):
            raise ValueError("Window violates frozen buffered district design")
    qa = phase6.preflight(options)
    selected = []
    for base in old:
        if base["split"]=="test":
            continue
        eligible = [row for row in options if row["split"]==base["split"] and row["district"]==base["district"]
                    and qa[row["id"]]["slope"] is not None and min(qa[row["id"]]["sar_scenes"])>=2
                    and (qa[row["id"]]["paired_count"] or 0)>=2]
        if eligible:
            winner = max(eligible,key=lambda row:(abs(qa[row["id"]]["slope"]-base["preflight"]["slope"]),row["rank"]))
            selected.append(dict(winner,preflight=qa[winner["id"]],contrast_anchor=base["id"]))
    return selected, [dict(row,preflight=qa[row["id"]]) for row in options], old


def export_pair(site,item,out):
    cfg = Phase2Config(**item["settings"])
    region = ee.Geometry.Rectangle(item["bounds"],cfg.analysis_crs,False)
    masks, checks = [],[]
    for index,scenes in enumerate(item["replicas"],1):
        qa,mask = export(replica_image(region,cfg,scenes),out/f"{site}-r{index}",item["bounds"],cfg,32,scenes)
        checks.append(qa)
        masks.append(mask)
        print(site,index,qa["counts"],qa["valid_cells"],flush=True)
    common = masks[0]&masks[1]
    intersection = int(common.sum())
    path = out/f"{site}-intersection.tif"
    with rasterio.open(out/f"{site}-r1/diagnostics.tif") as template:
        write_tile(path,template.profile,("replica_common_intersection",),common[None].astype("float32"),
                   dict(data_kind="real"))
    return dict(replicas=[dict(counts=q["counts"],valid=q["valid_cells"],passes=q["passes"]) for q in checks],
                intersection=intersection,intersection_sha256=digest(path),
                passes=all(q["passes"] for q in checks) and intersection/1024>=cfg.min_common_coverage)


def retry_bhubaneswari(previous,out):
    site = "bhubaneswari"
    from_path = previous/"roster.json"
    item = json.loads(from_path.read_bytes())["comparison"][site]
    if json.loads((previous/"summary.json").read_bytes())[site]["passes"]:
        raise ValueError("Retry is reserved for a failed coverage gate")
    original = [{sensor: a[sensor]+b[sensor] for sensor in ("s1","s2")}
                for a,b in zip(*item["replicas"],strict=True)]
    item["replicas"] = replicas(original,Phase2Config(**item["settings"]),stride=2)
    out.mkdir()
    save_json(out/"roster.json",dict(site=site,comparison=item,original_sha256=digest(from_path),
                                     rule="alternate successive two-UTC-date groups; coverage-only retry"))
    phase6.initialize()
    ee.data.setDeadline(120000)
    save_json(out/"summary.json",{site:export_pair(site,item,out)})


def run(outputs,out):
    cache = outputs/"phase6b_multitile"
    phase6.initialize()
    ee.data.setDeadline(120000)
    out.mkdir()
    selected,options,original = new_blocks(cache)
    discovery = json.loads((outputs/"phase11c_india_discovery/inventory.json").read_bytes())
    comparison = {}
    for site in SITES:
        existing, = [row["screen"] for row in discovery if row["id"]==site]
        cfg = Phase2Config(**existing["config"])
        bounds = existing["bounds"]
        region = ee.Geometry.Rectangle(bounds,cfg.analysis_crs,False)
        # Freeze the same exact scene roster used by the saved Phase 11C site.
        full = inventory(region,cfg)
        for original_season, current in zip(existing["sources"],full,strict=True):
            for key in ("s1","s2"):
                saved = sorted(zip(original_season[key+"_ids"],original_season[key+"_time_start_ms"],strict=True))
                if saved!=sorted(tuple(row) for row in current[key]):
                    raise ValueError(f"Live and cached full-season inventories disagree: {site}/{key}")
        comparison[site] = dict(bounds=bounds,settings=asdict(cfg),replicas=replicas(full,cfg))
    roster = dict(existing=original,additional=selected,preflight=options,comparison=comparison,
                  block_m=5000,buffer_m=120,seed=42,source_roster_sha256=digest(cache/"roster.json"),
                  source_discovery_sha256=digest(outputs/"phase11c_india_discovery/inventory.json"))
    save_json(out/"roster.json",roster)
    results = {}
    for site,item in comparison.items():
        results[site] = export_pair(site,item,out)
        save_json(out/"summary.json",results)
    for row in selected:
        image, metadata = phase6.tile_graph(phase6.region_for(row["bounds"]))
        scenes = ee.List(metadata).getInfo()
        phase6.validate_scene_rows(scenes)
        qa,_ = export(image,out/row["id"],row["bounds"],phase6.CFG,phase6.SIZE,scenes)
        results[row["id"]] = dict(split=row["split"],block=row["block"],counts=qa["counts"],
                                   valid=qa["valid_cells"],slope=qa["slope_percentiles"],passes=qa["passes"])
        save_json(out/"summary.json",results)
        print(row["id"],results[row["id"]],flush=True)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs",type=Path,default=Path("outputs"))
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--retry-bhubaneswari",type=Path)
    args=parser.parse_args()
    if args.retry_bhubaneswari:
        retry_bhubaneswari(args.retry_bhubaneswari,args.out)
    else:
        run(args.outputs,args.out)
