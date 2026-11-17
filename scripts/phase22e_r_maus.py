"""Recover the exact Phase 22E plan in a separate, bounded output directory."""

import argparse
import json
from pathlib import Path

from affine import Affine
import numpy as np
import rasterio

from scripts.phase22b_maus import ROOT, digest, write_json
from scripts.phase22e_maus import DEST as ORIGINAL, SIZE, exclusion_sources, label_mask, reproject
from scripts.phase22e_maus_export import build, check_images, check_plan_geometry, debug, export_all, read_plan
from scripts.phase22e_maus import source_context
from src.gee_setup import initialize

DEST = Path("outputs/phase22e_r_maus")
PLAN_SHA = "b3aecfd62e4e7d838430b4ca60f15c11e3b71ce7add8db0c2a4287e43f04b459"
RESPONSE_CAP = 45


def frozen_plan(root, original, dest):
    raw = (original / "plan.json").read_bytes()
    if digest(raw) != PLAN_SHA:
        raise ValueError("Original acquisition-plan hash mismatch")
    plan, _ = read_plan(root, original)
    if len(plan["patches"]) != 39 or len(plan["patches"]) > RESPONSE_CAP:
        raise ValueError("Recovery exceeds frozen response cap or plan size")
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / "plan.json"
    if not target.exists():
        with target.open("xb") as stream:
            stream.write(raw)
    elif target.read_bytes() != raw:
        raise ValueError("Recovery plan differs from original bytes")
    return plan


def first_train(plan):
    return next(row for row in plan["patches"] if row["split"] == "train")


def smoke_gate(receipt, image, mask, row, maus):
    if receipt["state_of_patch"] != "QA_ACCEPTED_WEAK":
        raise ValueError("Smoke export rejected: " + receipt["reason"])
    _, valid, labels = check_images(image, mask, row)
    with rasterio.open(image) as ds, rasterio.open(mask) as ms:
        bounds = np.asarray(ds.bounds)
        if not np.array_equal(bounds, ms.bounds) or not np.array_equal(bounds, row["bounds"]):
            raise ValueError("Image and mask footprints differ from the frozen footprint")
    geoms = [reproject(maus[fid], 4326, row["crs"]) for fid in row["label_source_fids"]]
    expected = label_mask(geoms, row["affine"], valid, bool(row["negative_stratum"]))
    if not np.array_equal(labels, expected) or valid.mean() < .70:
        raise ValueError("Smoke mask content or valid-cell support mismatch")
    return dict(patch_id=row["patch_id"], plan_sha256=PLAN_SHA, status="PASS",
                shape=[SIZE, SIZE], crs=row["crs"], affine=list(Affine(*row["affine"]))[:6],
                bounds=bounds.tolist(), valid_pixels=int(valid.sum()), total_pixels=valid.size,
                raw_sha256=receipt["raw_sha256"], image_sha256=receipt["image_sha256"],
                mask_sha256=receipt["mask_sha256"], bytes=receipt["bytes"],
                provenance_hash=receipt["provenance_hash"])


def run_smoke(root, original, dest):
    plan = frozen_plan(root, original, dest)
    _, split, _, maus, geometry, states = source_context(root)
    project, hashes = exclusion_sources()
    if hashes != plan["project_exclusions"]:
        raise ValueError("Frozen project exclusion hashes changed")
    check_plan_geometry(plan, split, geometry, states, project)
    row = first_train(plan)
    directory = dest / "patches"
    directory.mkdir(exist_ok=True)
    initialize()
    receipt = build(row, maus, directory, PLAN_SHA)
    key = row["patch_id"]
    result = smoke_gate(receipt, directory / f"{key}_image.tif",
                        directory / f"{key}_weak_mask.tif", row, maus)
    write_json(dest / "smoke.json", result)
    print("Smoke PASS", result, flush=True)


def run_batch(root, original, dest):
    plan = frozen_plan(root, original, dest)
    smoke = json.loads((dest / "smoke.json").read_bytes())
    row = first_train(plan)
    key = row["patch_id"]
    if smoke.get("status") != "PASS" or smoke.get("plan_sha256") != PLAN_SHA or smoke.get("patch_id") != key:
        raise ValueError("Verified smoke receipt required before batch export")
    directory = dest / "patches"
    receipt = json.loads((directory / f"{key}.json").read_bytes())
    for field, suffix in (("image_sha256", "image"), ("mask_sha256", "weak_mask")):
        if smoke[field] != receipt[field] or smoke[field] != digest((directory / f"{key}_{suffix}.tif").read_bytes()):
            raise ValueError("Smoke artifact checksum mismatch")
    export_all(root, dest)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=("smoke", "batch", "debug"))
    action = cli.parse_args().action
    if action == "smoke":
        run_smoke(ROOT, ORIGINAL, DEST)
    elif action == "batch":
        run_batch(ROOT, ORIGINAL, DEST)
    else:
        frozen_plan(ROOT, ORIGINAL, DEST)
        debug(ROOT, DEST)
