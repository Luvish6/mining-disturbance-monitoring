"""One offline Indian Sentinel masked-sensor pilot with frozen spatial separation."""
import argparse
from itertools import combinations
from pathlib import Path
from time import monotonic

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from shapely.geometry import box
from scipy.ndimage import label
from scipy.stats import spearmanr
import torch
from torch import nn

from config.settings import BEFORE, AFTER
from scripts.phase6b_multitile import DIAGNOSTICS
from scripts.phase15c_screen import FLOORS, MAX_SLOPE, MAX_Z, MIN_Z, anomaly
from src.phase3.data import BANDS, BAND_UNITS, digest, save_json
from src.phase3.regional_inference import NODATA, check_grid, read_values, write_tile
from src.phase3.spatial import block_for, partition

BASE = np.float32(MIN_Z/MAX_Z)
SENSORS = ("s1","s2","s2_cloud")
SEED = 42
EPOCHS = 5


def load(path):
    import json
    return json.loads(path.read_bytes())


def read_tile(folder, legacy=False):
    receipt = load(folder/("quality.json" if legacy else "receipt.json"))
    for name, expected in receipt["hashes"].items():
        if digest(folder/name)!=expected:
            raise ValueError(f"Raster product hash mismatch: {folder.name}/{name}")
    source = load(folder/"sources.json") if legacy else receipt
    cfg = source["config" if legacy else "settings"]
    grid = source["output_transform" if legacy else "transform"]
    with rasterio.open(folder/"features.tif") as src, rasterio.open(folder/"diagnostics.tif") as diag:
        check_grid(src,cfg["analysis_crs"])
        if (src.descriptions!=BANDS or (not legacy and src.units!=BAND_UNITS) or src.nodata!=NODATA
                or list(src.transform)[:6]!=grid or diag.descriptions!=DIAGNOSTICS
                or (src.crs,src.transform,src.shape)!=(diag.crs,diag.transform,diag.shape)):
            raise ValueError("Cache grid, bands or units mismatch")
        values, diagnostics = read_values(src), diag.read()
        profile, bounds = src.profile, list(src.bounds)
    common = diagnostics[-1]==1
    if (not np.array_equal(common,(values!=NODATA).all(0)) or
            int(common.sum())!=receipt["valid_cells"]["common_valid"]):
        raise ValueError("Unexpected common footprint")
    if source["seasons"] != [vars(BEFORE),vars(AFTER)]:
        raise ValueError("Unexpected season definition")
    return dict(values=values,counts=diagnostics[:4],common=common,profile=profile,bounds=bounds,
                cfg=cfg,scenes=source["scenes"],hashes=receipt["hashes"])


def verify(outputs):
    cache = outputs/"indian_ssl_observation_cache"
    retry = outputs/"indian_ssl_bhubaneswari_retry"
    verified = load(cache/"verified_cache.json")
    roster = load(cache/"roster.json")
    retry_roster = load(retry/"roster.json")
    if (digest(cache/"roster.json")!=verified["roster_sha256"] or
            digest(retry/"roster.json")!=verified["retry_roster_sha256"] or
            retry_roster["original_sha256"]!=verified["roster_sha256"]):
        raise ValueError("Frozen roster hash mismatch")
    legacy = outputs/"phase6b_multitile"
    original = load(legacy/"roster.json")
    if digest(legacy/"roster.json")!=roster["source_roster_sha256"] or roster["existing"]!=original["selected"]:
        raise ValueError("Original block roster changed")
    if [roster[k] for k in ("block_m","buffer_m","seed")] != [5000,120,42]:
        raise ValueError("Frozen spatial settings changed")
    splits = {"train":{},"validation":{}}
    reserved = set()
    footprints = {}
    for old, rows in ((True,roster["existing"]),(False,roster["additional"])):
        for record in rows:
            block = block_for(record["bounds"])
            split = record["split"]
            if block!=record["block"] or block in reserved or partition(block)!=split:
                raise ValueError("Buffered spatial split mismatch")
            reserved.add(block)
            footprints[record["id"]] = box(*transform_bounds("EPSG:32646","EPSG:4326",*record["bounds"]))
            if split=="test":
                continue
            folder = (legacy if old else cache)/record["id"]
            tile = read_tile(folder,old)
            if tile["bounds"]!=record["bounds"]:
                raise ValueError("Tile lies outside frozen window")
            splits[split][record["id"]] = tile
    if list(map(len,splits.values())) != [4,4] or len(reserved)!=10:
        raise ValueError("Unexpected independent block count")
    held = {}
    inventories = [{sensor:set() for sensor in SENSORS} for _ in (0,1)]
    for site, parent, expected in (("gevra",cache,roster["comparison"]["gevra"]),
                                  ("bhubaneswari",retry,retry_roster["comparison"])):
        entry = verified["accepted_comparison"][site]
        mask_path = parent/f"{site}-intersection.tif"
        if entry["cache"]!=parent.name or digest(mask_path)!=entry["intersection_sha256"]:
            raise ValueError("Accepted replica mask hash mismatch")
        pair = [read_tile(parent/f"{site}-r{i}") for i in (1,2)]
        for index,tile in enumerate(pair):
            if tile["scenes"]!=expected["replicas"][index] or tile["bounds"]!=expected["bounds"] or tile["cfg"]!=expected["settings"]:
                raise ValueError("Accepted replica source, bounds, or orbit mismatch")
            for sensor in SENSORS:
                inventories[index][sensor].update(sid for season in tile["scenes"] for sid,_ in season[sensor])
        common = pair[0]["common"] & pair[1]["common"]
        with rasterio.open(mask_path) as src:
            if (not np.array_equal(src.read(1),common) or int(common.sum())!=entry["intersection"]
                    or src.transform!=pair[0]["profile"]["transform"] or src.crs!=pair[0]["profile"]["crs"]):
                raise ValueError("Replica intersection mask changed")
        if ((pair[0]["profile"]["crs"], pair[0]["profile"]["transform"]) !=
                (pair[1]["profile"]["crs"], pair[1]["profile"]["transform"])):
            raise ValueError("Replica grids differ")
        footprints[site] = box(*transform_bounds(pair[0]["profile"]["crs"],"EPSG:4326",*pair[0]["bounds"]))
        held[site] = pair
    if any(a.intersects(b) for a,b in combinations(footprints.values(),2)):
        raise ValueError("Development, calibration or held-out windows overlap")
    if any(inventories[0][key]&inventories[1][key] for key in SENSORS):
        raise ValueError("Source scene occurred in both replica groups")
    return splits, held, digest(cache/"verified_cache.json")


class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(6,16),nn.Tanh(),nn.Linear(16,8))
        self.head = nn.Linear(8,4)

    def view(self,x,sensor):
        masked = x.clone()
        masked[:,sensor*2:sensor*2+2] = 0
        flag = x.new_zeros((len(x),2))
        flag[:,sensor] = 1
        return self.encoder(torch.cat((masked,flag),dim=1))

    def embed(self,x):
        return (self.view(x,0)+self.view(x,1))/2


def development_rows(tile):
    a = tile["values"]
    # Selection cannot depend on after observations or the paired common mask.
    before = a[:4]
    valid = (before!=NODATA).all(0) & (tile["counts"][[0,2]]>=2).all(0)
    return before[:,valid].T


def fit(tiles):
    torch.manual_seed(SEED)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    rng = np.random.default_rng(SEED)
    batches = [development_rows(tile) for tile in tiles.values()]
    x = np.concatenate(batches)
    if min(map(len,batches))<25:
        raise ValueError("Insufficient before-only development support")
    center = np.median(x,axis=0)
    spread = np.maximum(1.4826*np.median(np.abs(x-center),axis=0),FLOORS)
    x = torch.tensor((x-center)/spread,dtype=torch.float32)
    model = Encoder()
    opt = torch.optim.Adam(model.parameters(),lr=.001)
    loss_fn = nn.HuberLoss()
    history = []
    start = monotonic()
    for _ in range(EPOCHS):
        losses = []
        indices = torch.from_numpy(rng.permutation(len(x)))
        for index in indices.split(512):
            if monotonic()-start>600:
                raise TimeoutError("SSL fit reached its CPU wall-time cap")
            batch = x[index]
            losses_by_sensor = []
            for sensor in (0,1):
                channels = slice(sensor*2,sensor*2+2)
                prediction = model.head(model.view(batch,sensor))
                losses_by_sensor.append(loss_fn(prediction[:,channels],batch[:,channels]))
            loss = torch.stack(losses_by_sensor).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(float(loss.detach()))
        history.append(float(np.mean(losses)))
    model.eval().requires_grad_(False)
    return model,center,spread,history,dict(zip(tiles,map(len,batches),strict=True))


def eligible(tile):
    v = tile["values"]
    return tile["common"] & (tile["counts"]>=2).all(0) & (v[13]>=0) & (v[13]<=MAX_SLOPE)


def scores(a,b,static,mask,model,center,spread):
    data = np.concatenate((a,b,np.where(mask[None],b-a,NODATA),static))
    counts = np.broadcast_to(2*mask,(4,*mask.shape))
    baseline, actual,_ = anomaly(data,counts,2)
    if not np.array_equal(actual,mask):
        raise ValueError("Methods do not share the exact eligibility footprint")
    with torch.inference_mode():
        views = [model.embed(torch.tensor((item[:,mask].T-center)/spread,dtype=torch.float32)) for item in (a,b)]
        latent = torch.linalg.vector_norm(views[1]-views[0],dim=1).numpy()
    return baseline[mask],latent


def components(vector, mask, threshold):
    screen = mask.copy()
    screen[mask] = vector>=threshold
    labels,n = label(screen)
    counts = np.bincount(labels.ravel(),minlength=n+1)
    keep = counts>=4
    keep[0] = False
    return keep[labels], int(keep.sum())


def jaccard(a,b):
    den = int((a|b).sum())
    return int((a&b).sum())/den if den else None


def compare(a,b,mask,threshold):
    n = len(a)
    k = int(np.ceil(.05*n))
    top = [np.isin(np.arange(n),np.argsort(-p,kind="stable")[:k]) for p in (a,b)]
    candidates = [components(p,mask,threshold) for p in (a,b)]
    rank = float(spearmanr(a,b).statistic) if len(np.unique(a))>1 and len(np.unique(b))>1 else None
    return dict(spearman=rank,top5_jaccard=jaccard(*top),candidate_jaccard=jaccard(*(p for p,_ in candidates)),
                polygons=[n for _,n in candidates],candidate_area_m2=[int(p.sum())*900 for p,_ in candidates])


def run(outputs,out):
    splits,held,manifest_hash = verify(outputs)
    out.mkdir()
    model,center,spread,history,development = fit(splits["train"])
    checkpoint = out/"encoder.pt"
    torch.save(dict(state=model.state_dict(),center=center.tolist(),spread=spread.tolist(),seed=SEED),checkpoint)
    baseline_cal,ssl_cal = [],[]
    for tile in splits["validation"].values():
        v = tile["values"]
        baseline, latent = scores(v[:4],v[4:8],v[12:],eligible(tile),model,center,spread)
        baseline_cal.append(baseline)
        ssl_cal.append(latent)
    pooled = np.concatenate(ssl_cal)
    quota = int(sum((a>=BASE).sum() for a in baseline_cal))
    threshold = float(np.sort(pooled)[-quota]) if quota else float(np.nextafter(float(pooled.max()),np.inf))
    thresholds = (float(BASE),threshold)
    report = {}
    for site, replicas in held.items():
        values = [tile["values"] for tile in replicas]
        mask = eligible(replicas[0]) & eligible(replicas[1])
        if mask.sum()<25:
            report[site] = dict(status="INSUFFICIENT_DATA",eligible_cells=int(mask.sum()),metrics=None)
            continue
        change = [scores(v[:4],v[4:8],v[12:],mask,model,center,spread) for v in values]
        repeat = [scores(values[0][4*i:4*i+4],values[1][4*i:4*i+4],values[0][12:],mask,model,center,spread)
                  for i in (0,1)]
        methods = {}
        for i,name in enumerate(("phase15c","ssl")):
            point = thresholds[i]
            methods[name] = compare(change[0][i],change[1][i],mask,point)
            methods[name]["same_season_exceedance"] = [float((pair[i]>=point).mean()) for pair in repeat]
            for index, pair in enumerate(change,1):
                score = np.full(mask.shape,NODATA,dtype="float32")
                score[mask] = pair[i]
                candidate,_ = components(pair[i],mask,point)
                write_tile(out/f"{site}-{name}-r{index}.tif",replicas[0]["profile"],
                           ("anomaly_score","common_valid","candidate_mask"),
                           np.stack((score,mask,candidate)).astype("float32"),
                           dict(data_kind="exploratory",status="REVIEW_REQUIRED",evidence_status="UNKNOWN",
                                operational_alerts="0",model_sha256=digest(checkpoint) if i else "phase15c"))
        report[site] = dict(eligible_cells=int(mask.sum()),methods=methods)
    promotion = True
    for site in report.values():
        if "methods" not in site:
            promotion = False
            continue
        baseline,ssl = (site["methods"][k] for k in ("phase15c","ssl"))
        promotion &= (all(ssl[k] is not None and baseline[k] is not None and ssl[k]>baseline[k]
                          for k in ("spearman","top5_jaccard"))
                      and all(a<=b for a,b in zip(ssl["same_season_exceedance"],baseline["same_season_exceedance"],strict=True)))
    save_json(out/"metrics.json",dict(sites=report,calibration=dict(cells=len(pooled),baseline_selected_cells=quota,
              ssl_selected_cells=int((pooled>=threshold).sum()),thresholds=dict(phase15c=thresholds[0],ssl=threshold)),
              train_history=history,development_before_pixels=development,
              decision="GO" if promotion else "NO-GO",status="EXPLORATORY",evidence_status="UNKNOWN",operational_alerts=0))
    save_json(out/"manifest.json",dict(cache_manifest_sha256=manifest_hash,encoder_sha256=digest(checkpoint),
              seed=SEED,epochs=EPOCHS,threads=2,source_hashes={group:{key:tile["hashes"] for key,tile in tiles.items()}
                  for group,tiles in splits.items()},heldout_hashes={key:[t["hashes"] for t in tiles] for key,tiles in held.items()},
              outputs={p.name:digest(p) for p in out.glob("*.tif")}))
    print(dict(sites=report,promotion=bool(promotion),history=history),flush=True)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs",type=Path,default=Path("outputs"))
    parser.add_argument("--out",type=Path,required=True)
    run(**vars(parser.parse_args()))
