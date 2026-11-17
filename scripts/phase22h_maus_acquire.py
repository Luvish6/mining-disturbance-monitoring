"""Acquire only the approved Phase 22H development geometries."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
from threading import Lock
from time import sleep
from unittest.mock import patch

import ee
import numpy as np
from PIL import Image

from scripts import phase22e_maus_export as exports
from scripts.phase22b_maus import ROOT, digest, stable, train_normalization, write_json
from scripts.phase22e_maus import exclusion_sources, label_mask, reproject, source_context
from scripts.phase22e_r_maus import smoke_gate
from scripts.phase22f_maus import CACHE, cached_inputs
from scripts.phase22g_maus_preflight import authenticated

DEST = Path("outputs/phase22h_maus")
MANIFEST = Path("outputs/phase22g_r_maus/proposed-geometry.json")
SHA = "00f87cbbe5f26a5166165582bacff8492f89f928d13750b5f991d01bbcc503ea"
CAPS = {"metadata":400,"tiff":130}


class Journal:
    def __init__(self,path):
        self.path = path
        self.lock = Lock()
        self.counts = Counter()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                self.counts[json.loads(line)["kind"]] += 1

    def charge(self,kind):
        with self.lock:
            if self.counts[kind] >= CAPS[kind]:
                raise ValueError(f"Phase 22H {kind} request cap reached")
            self.counts[kind] += 1
            with self.path.open("a",encoding="utf-8") as out:
                out.write(json.dumps(dict(kind=kind,request=self.counts[kind]))+"\n")

    def wrap(self,kind,fn):
        def call(*args,**kwargs):
            self.charge(kind)
            return fn(*args,**kwargs)
        return call


@contextmanager
def requests_limited(dest):
    journal = Journal(dest/"requests.jsonl")
    with ExitStack() as stack:
        for field in ("computeValue","getDownloadId"):
            stack.enter_context(patch.object(ee.data,field,journal.wrap("metadata",getattr(ee.data,field))))
        stack.enter_context(patch.object(exports,"fetch",journal.wrap("tiff",exports.fetch)))
        if hasattr(ee.data,"setMaxRetries"):
            ee.data.setMaxRetries(0)
        exports.initialize()
        yield journal


def input_plan():
    old_samples, _, norm, verified_hashes = cached_inputs()
    manifest = authenticated(MANIFEST,SHA)
    original, split, _, maus, geo, states = source_context(ROOT)
    project, exclusion_hashes = exclusion_sources()
    old_plan = json.loads((CACHE/"plan.json").read_bytes())
    if (manifest["split_sha256"] != digest(original) or manifest["test_sealed"] is not True
            or manifest["patches"][:39] != old_plan["patches"]
            or old_plan["project_exclusions"] != exclusion_hashes):
        raise ValueError("Approved manifest or exclusions differ from immutable inputs")
    rows = manifest["patches"]
    roles = Counter(row["split"] for row in rows)
    if roles != {"train":120,"validation":33} or len({r["patch_id"] for r in rows}) != 153:
        raise ValueError("Exact 153 approved windows are required")
    triples = Counter()
    for row in rows:
        group = split["groups"][row["group_id"]]
        if (row["split"] != group["split"] or row["state"] not in group["states"]
                or not set(row["label_source_fids"]) <= set(group["ids"])
                or bool(row["negative_stratum"]) == bool(row["label_source_fids"])):
            raise ValueError("Split, group, state or label source mismatch")
        triples[row["group_id"],bool(row["negative_stratum"])] += 1
    if any(n != (2 if bg else 1) for (_,bg),n in triples.items()) or len(triples)!=102:
        raise ValueError("Frozen groups must each have one positive and two background slots")
    exports.check_plan_geometry(manifest,split,geo,states,project)
    return old_samples,norm,verified_hashes,rows[39:],maus,original


def rendition(row):
    return row | dict(weak_label_type="WEAK_UNVERIFIED_BACKGROUND" if row["negative_stratum"]
                      else "WEAK_UNVERIFIED_POSITIVE")


def data_paths(row):
    return tuple(DEST/"patches"/f"{row['patch_id']}_{k}.tif" for k in ("image","weak_mask"))


def fit_ready(receipt):
    return receipt["state_of_patch"] == "QA_ACCEPTED_WEAK"


def fetch_patch(row,maus):
    try:
        receipt = exports.build(rendition(row),maus,DEST/"patches",SHA)
    except ee.EEException as exc:
        if "memory capacity exceeded" not in str(exc) or any(path.exists() for path in data_paths(row)):
            raise
        print("Transient Earth Engine metadata resource error; retrying the same window",flush=True)
        sleep(2)
        receipt = exports.build(rendition(row),maus,DEST/"patches",SHA)
    if not fit_ready(receipt) and receipt["reason"] not in {
            "Insufficient eligible optical source records",
            "Optical valid-cell coverage below 70 percent",
            "Insufficient eligible weak target cells"}:
        raise ValueError("Integrity stop: "+receipt["reason"])
    return receipt


def request(action):
    old_samples,norm,hashes,rows,maus,original = input_plan()
    first = next(r for r in rows if r["split"] == "train" and r["label_source_fids"])
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/"patches").mkdir(exist_ok=True)
    if not (DEST/"normalization-phase22f.json").exists():
        write_json(DEST/"normalization-phase22f.json",norm)
    if action == "smoke":
        with requests_limited(DEST) as journal:
            result = fetch_patch(first,maus)
        receipt = smoke_gate(result,*data_paths(first),first,maus) | dict(
            plan_sha256=SHA,requests=dict(journal.counts))
        write_json(DEST/"smoke.json",receipt)
        print("Smoke passed",receipt["valid_pixels"],receipt["raw_sha256"],dict(journal.counts),flush=True)
        return
    smoke = json.loads((DEST/"smoke.json").read_bytes())
    if (smoke["status"] != "PASS" or smoke["plan_sha256"] != SHA
            or smoke["patch_id"] != first["patch_id"]
            or any(digest(f.read_bytes()) != smoke[k] for f,k in zip(
                data_paths(first),("image_sha256","mask_sha256"),strict=True))):
        raise ValueError("Frozen Phase 22H passing smoke artifact required")
    received = []
    with requests_limited(DEST) as journal, ThreadPoolExecutor(max_workers=2) as pool:
        for offset in range(0,len(rows),3):
            received.extend(pool.map(lambda row:fetch_patch(row,maus),rows[offset:offset+3]))
            if offset % 15 == 0:
                print("New patch receipts",len(received),dict(journal.counts),flush=True)
    if (ROOT/"split.json").read_bytes() != original or digest(MANIFEST.read_bytes())!=SHA:
        raise ValueError("Frozen input changed during acquisition")
    summarise(old_samples,received,maus,hashes,journal.counts)


def summarise(cached,received,maus,hashes,charges):
    rejected_groups = {row["group_id"] for row in received if not fit_ready(row)}
    accepted = [r for r in received if r["group_id"] not in rejected_groups]
    records = {role:[r[0] for r in seq] for role,seq in cached.items()}
    for r in accepted:
        records[r["split"]].append(r | dict(cache="phase22h"))
    for role in records:
        records[role].sort(key=lambda r:stable(r["patch_id"]))
    selected = sorted(accepted,key=lambda r:stable(r["patch_id"]))
    sample = np.random.default_rng(42).choice(len(selected),min(20,len(selected)),replace=False)
    overlays = DEST/"overlays"
    overlays.mkdir(exist_ok=True)
    flags, panels = [], []
    for i in sorted(sample):
        row = selected[i]
        image,mask = data_paths(row)
        _,valid,y = exports.check_images(image,mask,row)
        expected = label_mask([reproject(maus[fid],4326,row["crs"]) for fid in row["label_source_fids"]],
                              row["affine"],valid,bool(row["negative_stratum"]))
        if not np.array_equal(expected,y):
            flags.append(row["patch_id"])
        panel = exports.preview(DEST/"patches",row)
        panel.save(overlays/f"{row['patch_id']}.png")
        panels.append(panel)
    if panels:
        sheet = Image.new("RGB",(4*256,((len(panels)+3)//4)*155))
        for i,p in enumerate(panels):
            sheet.paste(p,((i%4)*256,(i//4)*155))
        sheet.save(overlays/"sample-contact.png")
    summary = {}
    for role,seq in records.items():
        summary[role] = dict(patches=len(seq),groups=len({r["group_id"] for r in seq}),
            positive_patches=sum(bool(r["positive_pixels"]) for r in seq),
            background_patches=sum(bool(r["background_pixels"]) for r in seq),
            weak_positive=sum(r["positive_pixels"] for r in seq),
            weak_background=sum(r["background_pixels"] for r in seq),
            states={s:dict(patches=sum(r["state"]==s for r in seq),
                groups=len({r["group_id"] for r in seq if r["state"]==s}))
                    for s in sorted({r["state"] for r in seq})})
    go = len(panels)>=20 and len(flags)/len(panels)<=.10 and all(
        r["positive_patches"]>=2 and r["background_patches"]>=2 for r in summary.values())
    stats = [("train",x,v) for _,x,v,_ in cached["train"]]
    for r in accepted:
        if r["split"]=="train":
            x,v,_ = exports.check_images(*data_paths(r),r)
            stats.append(("train",x,v))
    mean,sd = train_normalization(stats)
    for role,seq in records.items():
        write_json(DEST/f"{role}_manifest.json",dict(approved_sha256=SHA,patches=seq))
    write_json(DEST/"dataset.json",dict(dataset_go=go,test_sealed=True,approved_sha256=SHA,
        acquired=len(received),accepted_new=len(accepted),requests=dict(charges),
        tiff_body_bytes=sum(r["bytes"] for r in received),
        rejected=[dict(patch_id=r["patch_id"],reason=r["reason"],group=r["group_id"])
                  for r in received if not fit_ready(r)], excluded_groups=sorted(rejected_groups),summary=summary,
        normalization=dict(mean=mean.tolist(),sd=sd.tolist(),bands=["B3","B4","B8"]),
        original_manifest_hashes=hashes,inspected_new=len(panels),geometric_flags=flags,
        visual_interpretation="HUMAN REVIEW PENDING"))
    print("DATASET",go,json.dumps(summary),dict(charges),flush=True)


if __name__=="__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action",choices=("smoke","batch"))
    request(cli.parse_args().action)
