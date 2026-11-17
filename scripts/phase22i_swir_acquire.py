"""Same-footprint B2/B11/B12 acquisition for the lean Phase 22I ablation."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from threading import Lock
from time import sleep
from unittest.mock import patch

import ee
import numpy as np
import rasterio
from affine import Affine

from scripts import phase22e_maus_export as exporter
from scripts.phase22b_maus import ROOT, digest, stable, write_json
from scripts.phase22c_maus import NODATA, WINDOW
from scripts.phase22h_maus_acquire import SHA
from scripts.phase22h_maus_train import training_data, SPLIT_SHA
from src.gee_setup import initialize

DEST = Path("outputs/phase22i_maus")
EXTRA = ("B2","B11","B12")
BODY_LIMIT = 500_000_000
CAP = 170
MAX_BODY = 2 * 1024**2


class Transfer:
    def __init__(self,path):
        self.path = path
        self.lock = Lock()
        self.count = 0
        self.bytes = 0
        self.reserved = 0
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                self.count += int(record["event"] == "request")
                self.bytes += record.get("bytes",0)

    def log(self,event,**data):
        with self.path.open("a",encoding="utf-8") as stream:
            stream.write(json.dumps(dict(event=event,**data))+"\n")

    def wrapped(self,fetch):
        def fetch_budgeted(url,max_size):
            with self.lock:
                if self.count >= CAP or self.bytes+self.reserved+max_size > BODY_LIMIT:
                    raise ValueError("STOP before response or 500 MB cap; obtain approval for any budget increase")
                self.count += 1
                number = self.count
                self.reserved += max_size
                self.log("request",number=number)
            try:
                body=fetch(url,max_size)
            except Exception:
                with self.lock:
                    self.reserved -= max_size
                    self.log("failed",number=number)
                raise
            with self.lock:
                self.reserved -= max_size
                self.bytes += len(body)
                self.log("body",number=number,bytes=len(body))
            return body
        return fetch_budgeted


def extra_image(row):
    """Use exactly the frozen joined asset IDs and the frozen 10 m grid."""
    ids, dates = row["source_ids"], row["source_dates_ms"]
    if len(ids)<2 or len(ids)!=len(dates) or len(ids)!=len(set(ids)):
        raise ValueError("Invalid frozen joined-scene provenance")
    from datetime import datetime,timezone
    start,end = [datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp()*1000
                 for d in (WINDOW.start,WINDOW.end)]
    if any(not start<=d<end for d in dates):
        raise ValueError("Frozen optical timestamps outside Q1 2019")
    crs=f"EPSG:{row['crs']}"
    affine=row["affine"]
    def prepare(key):
        sr=ee.Image(f"COPERNICUS/S2_SR_HARMONIZED/{key}")
        prob=ee.Image(f"COPERNICUS/S2_CLOUD_PROBABILITY/{key}").select("probability")
        scl=sr.select("SCL")
        visible=sr.select(["B3","B4","B8"])
        valid=(prob.lt(40).And(scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)))
                .And(sr.select("B8A").mask()).And(sr.select("B9").mask())
                .And(visible.mask().reduce(ee.Reducer.min())))
        blue=sr.select("B2").updateMask(valid).reproject(crs,affine)
        swir=(sr.select(["B11","B12"]).updateMask(valid)
              .resample("bilinear").reproject(crs,affine))
        union=blue.addBands(swir).updateMask(valid.reproject(crs,affine))
        return union.updateMask(union.mask().reduce(ee.Reducer.min())).divide(10000)
    stack=ee.ImageCollection.fromImages([prepare(key) for key in ids])
    return stack.median().updateMask(stack.select("B2").count().gte(2)).select(list(EXTRA))


def read_extra(path,row):
    with rasterio.open(path) as ds:
        if (ds.shape!=(128,128) or ds.count!=3 or ds.crs is None
                or ds.crs.to_epsg()!=row["crs"] or ds.transform!=Affine(*row["affine"])
                or tuple(ds.bounds)!=tuple(row["bounds"]) or ds.descriptions!=EXTRA
                or ds.dtypes!=("float32",)*3 or ds.nodata!=NODATA):
            raise ValueError("Extra-band raster does not match the frozen grid")
        x=ds.read()
    valid=np.isfinite(x)&(x!=NODATA)
    if not np.array_equal(valid,np.broadcast_to(valid[0],valid.shape)):
        raise ValueError("Extra bands have inconsistent joint support")
    return x,valid[0]


def common_support(old,new,y):
    common=old&new
    if common.mean()<.70 or int((common&(y!=255)).sum())<32:
        raise ValueError("Patch fails preregistered common support gate")
    return common


def obtain(sample,dest):
    row,_,old,y=sample
    key=row["patch_id"]
    path=dest/"bands"/f"{key}.tif"
    result=path.with_suffix(".json")
    if result.exists():
        receipt=json.loads(result.read_bytes())
        if (receipt["parent_image_sha256"]!=row["image_sha256"]
                or receipt["parent_mask_sha256"]!=row["mask_sha256"]
                or receipt["tiff_sha256"]!=digest(path.read_bytes())
                or receipt["source_ids"]!=row["source_ids"]
                or receipt["source_dates_ms"]!=row["source_dates_ms"]):
            raise ValueError("Cached extra-band provenance mismatch")
        _,valid=read_extra(path,row)
        common=common_support(old,valid,y)
        if receipt["common_valid_cells"]!=int(common.sum()):
            raise ValueError("Cached common support receipt mismatch")
        return receipt
    if path.exists():
        raise ValueError("Unreceipted extra-band export")
    try:
        _,transfer=exporter.download(extra_image(row),EXTRA,row,path)
    except ee.EEException as exc:
        if "memory capacity exceeded" not in str(exc) or path.exists():
            raise
        print("Retrying a transient Earth Engine resource failure on the same window",flush=True)
        sleep(2)
        _,transfer=exporter.download(extra_image(row),EXTRA,row,path)
    _,valid=read_extra(path,row)
    common=common_support(old,valid,y)
    receipt=dict(patch_id=key,split=row["split"],parent_image_sha256=row["image_sha256"],
                 parent_mask_sha256=row["mask_sha256"],source_ids=row["source_ids"],
                 source_dates_ms=row["source_dates_ms"],bands=EXTRA,
                 old_valid_cells=int(old.sum()),common_valid_cells=int(common.sum()),
                 lost_known_cells=int((old&~common&(y!=255)).sum()),grid=[row["crs"],row["affine"]]) | transfer
    write_json(result,receipt)
    return receipt


def run(action):
    samples,_,_,_=training_data()
    planned=samples["train"]+samples["validation"]
    first=planned[0]
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/"bands").mkdir(exist_ok=True)
    ledger=Transfer(DEST/"transfer.jsonl")
    if action=="batch":
        saved=json.loads((DEST/"smoke.json").read_bytes())
        if (saved["status"]!="PASS" or saved["patch_id"]!=first[0]["patch_id"]
                or saved["tiff_sha256"]!=digest((DEST/"bands"/f"{saved['patch_id']}.tif").read_bytes())):
            raise ValueError("Passing same-footprint smoke receipt required")
    initialize()
    if hasattr(ee.data,"setMaxRetries"):
        ee.data.setMaxRetries(0)
    with patch.object(exporter,"fetch",ledger.wrapped(exporter.fetch)):
        if action=="smoke":
            result=obtain(first,DEST)
            write_json(DEST/"smoke.json",result|dict(status="PASS",manifest_sha256=SHA,
                                                     split_sha256=SPLIT_SHA))
            print("SWIR smoke PASS",result["old_valid_cells"],result["common_valid_cells"],
                  result["tiff_sha256"],ledger.bytes,flush=True)
            return
        results=[]
        with ThreadPoolExecutor(max_workers=2) as pool:
            for start in range(0,len(planned),2):
                results.extend(pool.map(lambda v:obtain(v,DEST),planned[start:start+2]))
                if start%20==0:
                    print("SWIR receipts",len(results),ledger.count,ledger.bytes,flush=True)
    if digest((ROOT/"split.json").read_bytes())!=SPLIT_SHA:
        raise ValueError("Frozen split changed")
    write_json(DEST/"acquisition.json",dict(split_sha256=SPLIT_SHA,manifest_sha256=SHA,
        test_sealed=True,responses=ledger.count,response_body_bytes=ledger.bytes,
        patches=len(results),loss={role:dict(
            valid_cells=sum(r["old_valid_cells"]-r["common_valid_cells"] for r in results if r["split"]==role),
            known_cells=sum(r["lost_known_cells"] for r in results if r["split"]==role),
            changed_patches=sum(r["old_valid_cells"]!=r["common_valid_cells"] for r in results if r["split"]==role))
            for role in ("train","validation")}))
    print("SWIR acquisition complete",len(results),ledger.count,ledger.bytes,flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("smoke","batch"))
    run(parser.parse_args().action)
