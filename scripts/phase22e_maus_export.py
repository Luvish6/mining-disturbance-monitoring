"""Materialize a frozen Phase 22E development plan and run the gated debug fit."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from time import perf_counter

from affine import Affine
import ee
import numpy as np
from PIL import Image, ImageDraw
import rasterio
from rasterio.io import MemoryFile
from shapely.geometry import box, shape
from shapely.strtree import STRtree

from config.phase2_settings import Phase2Config
from scripts.phase22b_maus import digest, stable, train_normalization, write_json
from scripts.phase22c_maus import NODATA, optical_graph, sensor_support, verify_split
from scripts.phase22e_maus import (
    BANDS, MAX_TIFF, OPTICAL, PROTO, SIZE, exclusion_sources, fetch, label_mask, reproject,
    safe_window, source_context,
)
from src.gee_setup import initialize


def read_plan(root, dest):
    raw = (dest / "plan.json").read_bytes()
    plan = json.loads(raw)
    original = (root / "split.json").read_bytes()
    verify_split(original, original)
    if (plan["split_sha_before"] != digest(original) or plan["split_sha_after"] != digest(original)
            or plan["protocol_sha256"] != digest(PROTO.read_bytes()) or plan["test_sealed"] is not True):
        raise ValueError("Plan and frozen inputs disagree")
    roster = json.loads(original)["groups"]
    patches = plan["patches"]
    ids = [p["patch_id"] for p in patches]
    if (not patches or len(patches) > 45 or len(ids) != len(set(ids))
            or len(patches)*MAX_TIFF != plan["max_download_bytes"]
            or plan["max_download_bytes"] > 500_000_000):
        raise ValueError("Invalid or over-budget export plan")
    group_counts = Counter()
    for patch in patches:
        group = roster[patch["group_id"]]
        if (patch["split"] not in {"train", "validation"} or patch["split"] != group["split"]
                or not set(patch["label_source_fids"]) <= set(group["ids"])):
            raise ValueError("Plan contains TEST or out-of-group labels")
        if patch["state"] not in group["states"]:
            raise ValueError("Patch state and frozen group disagree")
        positive = bool(patch["label_source_fids"])
        if (positive != (patch["weak_label_type"] == "WEAK_UNVERIFIED_POSITIVE")
                or positive == bool(patch["negative_stratum"])):
            raise ValueError("Weak label type and source geometry disagree")
        group_counts[(patch["group_id"], positive)] += 1
        if group_counts[(patch["group_id"], positive)] > (1 if positive else 2):
            raise ValueError("Plan exceeds frozen per-group caps")
    return plan, digest(raw)


def check_plan_geometry(plan, split, geometries, states, project):
    roles = {fid: g["split"] for g in split["groups"].values() for fid in g["ids"]}
    opposing = {role: STRtree([g for fid, g in geometries.items() if roles[fid] != role])
                for role in ("train", "validation")}
    exclusions = STRtree(list(geometries.values()) + project)
    occupied = []
    for row in plan["patches"]:
        window = box(*row["bounds"])
        a = Affine(*row["affine"])
        if ((a.a, a.b, a.d, a.e) != (10, 0, 0, -10) or a.c % 10 or a.f % 10
                or (a.c, a.f-1280, a.c+1280, a.f) != window.bounds
                or not shape(row["geometry"]).equals_exact(reproject(window, row["crs"], 4326), 1e-9)):
            raise ValueError("Patch grid or footprint mismatch")
        footprint = reproject(window, row["crs"], 7755)
        if not safe_window(footprint, states[row["state"]], opposing[row["split"]],
                           exclusions, occupied, not row["label_source_fids"]):
            raise ValueError("Patch violates frozen footprint, exclusion or buffer")
        occupied.append(footprint)


def check_images(image, mask, row):
    with rasterio.open(image) as ds, rasterio.open(mask) as label:
        if (ds.shape != (SIZE, SIZE) or label.shape != ds.shape or label.transform != ds.transform
                or label.crs != ds.crs or ds.crs.to_epsg() != row["crs"]
                or ds.transform != Affine(*row["affine"]) or ds.descriptions != BANDS
                or ds.dtypes != ("float32",)*len(BANDS) or ds.nodata != NODATA
                or label.nodata != 255 or label.dtypes != ("uint8",)):
            raise ValueError("Model image/weak-mask alignment or schema mismatch")
        arrays = dict(zip(BANDS, ds.read(), strict=True))
        y = label.read(1)
    valid = sensor_support(arrays, OPTICAL, "optical_count")
    if not np.isin(y, [0, 1, 255]).all() or (y[~valid] != 255).any():
        raise ValueError("Invalid weak label values or support")
    return np.stack([arrays[b] for b in OPTICAL]), valid, y



def download(image, bands, row, path):
    """Use the preregistered 128-cell grid in both the request and validation."""
    if image.bandNames().getInfo() != list(bands):
        raise ValueError("Incorrect export graph band order")
    crs = f"EPSG:{row['crs']}"
    affine = Affine(*row["affine"])
    url = image.toFloat().unmask(NODATA, False).getDownloadURL(
        dict(crs=crs, crs_transform=row["affine"], dimensions=[SIZE, SIZE], format="GEO_TIFF"))
    raw = fetch(url, MAX_TIFF)
    with MemoryFile(raw) as memory, memory.open() as ds:
        if (ds.shape != (SIZE, SIZE) or ds.count != len(bands)
                or ds.crs is None or ds.crs.to_epsg() != row["crs"]
                or ds.transform != affine or ds.dtypes != ("float32",)*len(bands)
                or (any(ds.descriptions) and ds.descriptions != bands)):
            raise ValueError("Earth Engine returned a noncanonical 128-cell optical grid")
        data, profile = ds.read(), ds.profile
    profile.update(nodata=NODATA, compress="deflate")
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data)
        ds.descriptions = bands
    return dict(zip(bands, data, strict=True)), dict(bytes=len(raw), raw_sha256=digest(raw),
                                                     tiff_sha256=digest(path.read_bytes()))


def build(row, maus, directory, plan_sha):
    patch = row["patch_id"]
    receipt_path = directory / f"{patch}.json"
    image, mask = (directory / f"{patch}_{kind}.tif" for kind in ("image", "weak_mask"))
    if receipt_path.exists():
        old = json.loads(receipt_path.read_bytes())
        provenance = old.pop("provenance_hash")
        if digest(json.dumps(old, sort_keys=True).encode()) != provenance:
            raise ValueError("Cached receipt hash mismatch")
        old["provenance_hash"] = provenance
        if old["plan_sha256"] != plan_sha or old["patch_id"] != patch:
            raise ValueError("Cached receipt is for a different freeze")
        if old.get("image_sha256"):
            if digest(image.read_bytes()) != old["image_sha256"] or digest(mask.read_bytes()) != old["mask_sha256"]:
                raise ValueError("Cached model input or mask hash mismatch")
            check_images(image, mask, row)
        return old
    receipt = row | dict(plan_sha256=plan_sha, human_review="PENDING",
                         source_ids=[], positive_fraction=None, bytes=0)
    target_geometries = [reproject(maus[fid], 4326, row["crs"]) for fid in row["label_source_fids"]]
    crs = f"EPSG:{row['crs']}"
    try:
        region = ee.Geometry.Rectangle(row["bounds"], crs, False)
        optical, count, sources = optical_graph(region, Phase2Config(analysis_crs=crs))
        receipt["source_ids"], receipt["source_dates_ms"] = sources["ids"], sources["dates_ms"]
        if len(sources["ids"]) < 2 or len(sources["ids"]) != len(sources["dates_ms"]):
            raise ValueError("Insufficient eligible optical source records")
        arrays, raw_receipt = download(optical.addBands(count), BANDS, row, image)
        receipt.update(raw_receipt)
        valid = sensor_support(arrays, OPTICAL, "optical_count")
        y = label_mask(target_geometries, row["affine"], valid, bool(row["negative_stratum"]))
        with rasterio.open(mask, "w", driver="GTiff", height=SIZE, width=SIZE, count=1,
                           crs=crs, transform=Affine(*row["affine"]), dtype="uint8",
                           nodata=255, compress="deflate") as ds:
            ds.write(y, 1)
        _, read_valid, read_mask = check_images(image, mask, row)
        if not np.array_equal(valid, read_valid) or not np.array_equal(y, read_mask):
            raise ValueError("Written weak-mask values changed")
        with rasterio.open(image) as ds:
            observation_count = ds.read(4)
        positive, negative = int((y == 1).sum()), int((y == 0).sum())
        receipt.update(image_sha256=digest(image.read_bytes()), mask_sha256=digest(mask.read_bytes()),
                       valid_pixels=int(valid.sum()), valid_fraction=float(valid.mean()),
                       positive_pixels=positive, background_pixels=negative,
                       positive_fraction=positive/int(valid.sum()) if valid.any() else None,
                       observation_count_range=[int(observation_count.min()), int(observation_count.max())])
        if valid.mean() < .70:
            raise ValueError("Optical valid-cell coverage below 70 percent")
        if (negative if row["negative_stratum"] else positive) < 32:
            raise ValueError("Insufficient eligible weak target cells")
        receipt["state_of_patch"] = "QA_ACCEPTED_WEAK"
    except ValueError as exc:
        receipt.update(state_of_patch="REJECTED", reason=str(exc))
    receipt["provenance_hash"] = digest(json.dumps(receipt, sort_keys=True).encode())
    write_json(receipt_path, receipt)
    return receipt


def preview(directory, row):
    key = row["patch_id"]
    x, valid, y = check_images(directory / f"{key}_image.tif", directory / f"{key}_weak_mask.tif", row)
    base = (np.clip(x[[1, 2, 0]].transpose(1, 2, 0)/.3, 0, 1)*255).astype("uint8")
    base[~valid] = (44, 44, 44)
    overlay = base.copy()
    for target, color in ((1, (255, 172, 0)), (0, (46, 165, 210))):
        mask = y == target
        overlay[mask] = ((overlay[mask].astype(float)+color)/2).astype("uint8")
    canvas = Image.new("RGB", (256, 155), (20, 20, 20))
    canvas.paste(Image.fromarray(base), (0, 0))
    canvas.paste(Image.fromarray(overlay), (128, 0))
    ImageDraw.Draw(canvas).text((4, 133), "WEAK MASK | HUMAN REVIEW PENDING", fill="white")
    return canvas


def export_all(root, dest):
    plan, plan_sha = read_plan(root, dest)
    original, split, _, maus, geometries, states = source_context(root)
    project, source_hashes = exclusion_sources()
    if source_hashes != plan["project_exclusions"]:
        raise ValueError("Frozen candidate exclusions changed")
    check_plan_geometry(plan, split, geometries, states, project)
    initialize()
    directory = dest / "patches"
    directory.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda row: build(row, maus, directory, plan_sha), plan["patches"]))
    verify_split(original, (root / "split.json").read_bytes())

    accepted = [row for row in rows if row["state_of_patch"] == "QA_ACCEPTED_WEAK"]
    by_role, summary = {}, {}
    overlays = dest / "overlays"
    overlays.mkdir(exist_ok=True)
    train_cells = []
    for split, cap in (("train", 20), ("validation", 10)):
        samples = [row for row in accepted if row["split"] == split]
        by_role[split] = samples
        for i, row in enumerate(sorted(samples, key=lambda r: stable(r["patch_id"]))):
            patch = row["patch_id"]
            if i < cap:
                preview(directory, row).save(overlays / f"{split}_{patch}.png")
            if split == "train":
                x, valid, _ = check_images(directory / f"{patch}_image.tif",
                                           directory / f"{patch}_weak_mask.tif", row)
                train_cells.append((split, x, valid))
        summary[split] = dict(patches=len(samples),
            positive_patches=sum(r["positive_pixels"] > 0 for r in samples),
            background_patches=sum(r["background_pixels"] > 0 for r in samples),
            positive_groups=len({r["group_id"] for r in samples if r["positive_pixels"]}),
            states=len({r["state"] for r in samples}), valid_pixels=sum(r["valid_pixels"] for r in samples),
            positive_pixels=sum(r["positive_pixels"] for r in samples),
            background_pixels=sum(r["background_pixels"] for r in samples))
    normalization = None
    if train_cells:
        mean, sd = train_normalization(train_cells)
        normalization = dict(bands=OPTICAL, mean=mean.tolist(), sd=sd.tolist(),
                             train_valid_cells=sum(int(v.sum()) for _, _, v in train_cells))
        repeat = train_normalization(train_cells)
        if not (np.array_equal(mean, repeat[0]) and np.array_equal(sd, repeat[1])):
            raise ValueError("Nonreproducible TRAIN-only normalization")
    go = normalization is not None and all(s["positive_groups"] >= 2 and s["background_patches"] > 0
                                           for s in summary.values())
    for split, samples in by_role.items():
        write_json(dest / f"{split}_manifest.json", dict(plan_sha256=plan_sha, patches=samples))
    write_json(dest / "summary.json", dict(dataset_go=go, plan_sha256=plan_sha,
        test_sealed=True, summary=summary, normalization=normalization,
        total_tiff_bytes=sum(r["bytes"] for r in rows),
        label_status="WEAK_UNVERIFIED", verified_independent_labels=0,
        split_sha_before=digest(original), split_sha_after=digest((root/"split.json").read_bytes()),
        rejected=[dict(patch_id=r["patch_id"], split=r["split"], reason=r["reason"])
                  for r in rows if r["state_of_patch"] == "REJECTED"]))
    print("Dataset QA", go, summary, "bytes", sum(r["bytes"] for r in rows), flush=True)


def debug(root, dest):
    import torch
    from torch import nn
    from torch.nn import functional as F

    from src.phase3.model import conv, masked_loss

    _, plan_sha = read_plan(root, dest)
    result = json.loads((dest / "summary.json").read_bytes())
    manifest = json.loads((dest / "train_manifest.json").read_bytes())
    if (result["dataset_go"] is not True or result["test_sealed"] is not True
            or result["plan_sha256"] != plan_sha or manifest["plan_sha256"] != plan_sha):
        raise ValueError("Dataset GO and a verified frozen TRAIN manifest are required")
    rows = sorted(manifest["patches"], key=lambda r: stable(r["patch_id"]))
    if any(r["split"] != "train" or r["state_of_patch"] != "QA_ACCEPTED_WEAK" for r in rows):
        raise ValueError("Diagnostic manifest contains a non-TRAIN or rejected patch")
    chosen = [r for r in rows if r["positive_pixels"]][:4] + [r for r in rows if r["background_pixels"]][:4]
    if len(chosen) != 8:
        raise ValueError("Diagnostic requires four TRAIN patches of each weak type")

    class StaticUNet(nn.Module):
        """Single-date skips with the existing project's U-Net blocks."""
        def __init__(self):
            super().__init__()
            self.e1, self.e2, self.e3 = conv(3, 16), conv(16, 32), conv(32, 64)
            self.d2, self.d1, self.head = conv(96, 32), conv(48, 16), nn.Conv2d(16, 1, 1)

        def forward(self, x):
            a = self.e1(x)
            b = self.e2(F.max_pool2d(a, 2))
            c = self.e3(F.max_pool2d(b, 2))
            d = self.d2(torch.cat([F.interpolate(c, size=b.shape[-2:], mode="bilinear",
                                                align_corners=False), b], 1))
            return self.head(self.d1(torch.cat([F.interpolate(d, size=a.shape[-2:], mode="bilinear",
                                                               align_corners=False), a], 1)))

    torch.manual_seed(42)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    model = StaticUNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    norm = result["normalization"]
    mean, sd = (np.asarray(norm[k])[:, None, None] for k in ("mean", "sd"))
    samples = []
    for row in chosen:
        patch = row["patch_id"]
        directory = dest / "patches"
        image, label = (directory/f"{patch}_{kind}.tif" for kind in ("image", "weak_mask"))
        if digest(image.read_bytes()) != row["image_sha256"] or digest(label.read_bytes()) != row["mask_sha256"]:
            raise ValueError("Diagnostic input hash mismatch")
        x, valid, y = check_images(image, label, row)
        x = np.where(valid, (x-mean)/sd, 0).astype("float32")
        samples.append((torch.from_numpy(x[None]), torch.from_numpy((y == 1)[None, None]).float(),
                        torch.from_numpy((y != 255)[None, None])))

    def measure(step):
        losses, tp, denom = [], 0, 0
        with torch.no_grad():
            for x, target, mask in samples:
                logits = model(x)
                losses.append(float(masked_loss(logits, target, mask)))
                selected, actual = logits[mask] >= 0, target[mask].bool()
                tp += int((selected & actual).sum())
                denom += int((selected | actual).sum())
        return dict(step=step, mean_masked_bce=float(np.mean(losses)), weak_iou=tp/denom if denom else None)

    start = perf_counter()
    track = [measure(0)]
    for step in range(1, 201):
        x, y, mask = samples[(step-1) % len(samples)]
        optimizer.zero_grad(set_to_none=True)
        loss = masked_loss(model(x), y, mask)
        loss.backward()
        if any(p.grad is None or not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise ValueError("Nonfinite diagnostic gradient")
        optimizer.step()
        if step % 25 == 0:
            track.append(measure(step))
    receipt = dict(plan_sha256=plan_sha, seed=42, optimizer="Adam",
        lr=.001, cpu_threads=2, patches=[r["patch_id"] for r in chosen],
        trajectory=track, seconds=perf_counter()-start,
        passed=track[-1]["mean_masked_bce"] < track[0]["mean_masked_bce"],
        verified_accuracy=False, test_sealed=True)
    write_json(dest / "debug.json", receipt)
    print(receipt, flush=True)
