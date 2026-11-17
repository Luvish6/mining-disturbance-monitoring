"""Geometry-only recovery of the four frozen Phase 22G positive windows."""

from collections import Counter
import json
from pathlib import Path

from affine import Affine
import numpy as np
from pyproj import Transformer
from rasterio.features import rasterize
from shapely import contains_xy, distance, points
from shapely.geometry import Point, box, mapping
from shapely.strtree import STRtree

from scripts.phase22b_maus import BUFFER, ROOT, digest, stable, write_json
from scripts.phase22e_maus import DIRECTIONS, exclusion_sources, reproject, source_context
from scripts.phase22e_maus_export import check_plan_geometry
from scripts.phase22e_r_maus import DEST as CACHE, PLAN_SHA
from scripts.phase22f_maus import cached_inputs
from scripts.phase22g_maus_preflight import DEST as ORIGINAL, authenticated, blockers, pair_candidates

DEST = Path("outputs/phase22g_r_maus")
ORIGINAL_SHA = "025118c6fc3263f67d72ecbeb063e3311284ee62360d492642fb6013cc3a9b51"
SHIFT = 640
GRID = 10
WIDTH = 128
TARGET = {"train": 126, "validation": 36}


def grid_spec(x, y, crs, key):
    x, y = round(x / GRID) * GRID, round(y / GRID) * GRID
    bounds = [x-SHIFT, y-SHIFT, x+SHIFT, y+SHIFT]
    return dict(patch_id=key, crs=crs, bounds=bounds,
                affine=[GRID, 0, bounds[0], 0, -GRID, bounds[3]],
                geometry=mapping(reproject(box(*bounds), crs, 4326)))


def metric(spec):
    return reproject(box(*spec["bounds"]), spec["crs"], 7755)


def centers(members):
    """Enumerate unique snapped centers strictly inside source polygons."""
    result = set()
    for member in members:
        w,_,e,_ = member.bounds
        for zone in range(32601+int((w+180)//6), 32602+int((e+180)//6)):
            g = reproject(member,4326,zone)
            left, bottom, right, top = g.bounds
            xs = np.arange(np.ceil(left/GRID),np.floor(right/GRID)+1,dtype=np.int64)*GRID
            ys = np.arange(np.ceil(bottom/GRID),np.floor(top/GRID)+1,dtype=np.int64)*GRID
            inverse = Transformer.from_crs(zone,4326,always_xy=True)
            for y in ys:
                hits = xs[contains_xy(g,xs,y)]
                lon,_ = inverse.transform(hits,np.full(hits.size,y))
                inside = np.floor((lon+180)/6).astype(int)+32601 == zone
                result.update((zone,int(x),int(y)) for x in hits[inside])
    return sorted(result)


def positive_support(spec, members):
    box_utm = box(*spec["bounds"])
    labels = [g for g in members if box_utm.intersects(g)]
    if not labels:
        return 0
    return int(rasterize([(g,1) for g in labels],out_shape=(WIDTH,WIDTH),
                         transform=Affine(*spec["affine"]),all_touched=False).sum())


def window_center(spec):
    return box(*spec["bounds"]).centroid


def background_pair(pos, key, state, opposing, exclusions, occupied, preferred=None):
    center = window_center(pos)
    options, rejected = [], Counter()
    for radius in (3000,4500,6000):
        for bearing,angle in enumerate(DIRECTIONS):
            row = grid_spec(center.x+radius*np.cos(angle),center.y+radius*np.sin(angle),
                            pos["crs"],f"{key}-{radius}-{bearing}")
            shape = metric(row)
            why = blockers(shape,state,opposing,exclusions,occupied,True)
            rejected.update(why)
            if not why:
                options.append((row,shape))
    if preferred:
        random = preferred,metric(preferred)
        if not blockers(random[1],state,opposing,exclusions,occupied,True):
            hard = [pair for pair in options if not pair[1].intersects(random[1])]
            if hard:
                return (random,min(hard,key=lambda p:stable(p[0]["patch_id"]))), rejected
    random,hard = pair_candidates(options)
    if random is None:
        return None,rejected
    return (random,min(hard,key=lambda p:stable(p[0]["patch_id"]))),rejected


def relocate(old, members, state, opposing, exclusions, occupied):
    zone_pts = centers(members)
    previous = metric(old).centroid
    ranking, reasons = [],Counter()
    for zone in sorted({r[0] for r in zone_pts}):
        coords = [(x,y) for z,x,y in zone_pts if z==zone]
        xx,yy = np.asarray(coords).T
        mx,my = Transformer.from_crs(zone,7755,always_xy=True).transform(xx,yy)
        # The guarded footprint contains a radius-BUFFER disk about its center.
        possible = contains_xy(state,mx,my) & (distance(state.boundary,points(mx,my)) >= BUFFER-.01)
        reasons["ADM1_CENTER_GUARD_NECESSARY"] += int((~possible).sum())
        ranking.extend(((gx-previous.x)**2+(gy-previous.y)**2,stable(f"{zone}:{x}:{y}"),zone,x,y)
                       for (x,y),gx,gy,ok in zip(coords,mx,my,possible,strict=True) if ok)
    tried = 0
    for _,_,zone,x,y in sorted(ranking):
        tried += 1
        candidate = grid_spec(x,y,zone,old["patch_id"])
        polygon = metric(candidate)
        why = blockers(polygon,state,opposing,exclusions,occupied,False)
        if not why:
            support = positive_support(candidate,[reproject(g,4326,zone) for g in members])
            if support < 32:
                why = ["INSUFFICIENT_POSITIVE_GRID_CELLS"]
        if not why:
            bg, _ = background_pair(candidate,old["patch_id"].removesuffix("-pos"),state,
                                    opposing,exclusions,occupied+[polygon])
            if bg is not None:
                return candidate,bg,dict(total_centers=len(zone_pts),checked_windows=tried,
                    rejection_counts=dict(reasons),positive_grid_cells=support,exhausted=False)
            why = ["NO_DISJOINT_BACKGROUND_PAIR"]
        reasons.update(why)
    return None,None,dict(total_centers=len(zone_pts),checked_windows=tried,
                          rejection_counts=dict(reasons),exhausted=True)


def run():
    cached_inputs()
    previous = authenticated(ORIGINAL/"geometry-preflight.json",ORIGINAL_SHA)
    plan = authenticated(CACHE/"plan.json",PLAN_SHA)
    original, split, _, maus, geometry, states = source_context(ROOT)
    if digest(original) != previous["split_sha256"]:
        raise ValueError("Frozen split changed")
    project, hashes = exclusion_sources()
    if hashes != plan["project_exclusions"]:
        raise ValueError("Frozen exclusions changed")
    cached = plan["patches"]
    roster = split["groups"]
    roles = {fid:r["split"] for r in roster.values() for fid in r["ids"]}
    opposing = {role:STRtree([g for fid,g in geometry.items() if roles[fid]!=role])
                for role in TARGET}
    exclusions = STRtree(list(geometry.values())+project)
    decisions = previous["decisions"]
    if Counter((r["split"],r["status"]) for r in decisions if r["status"].startswith("BLOCKED")) != {
            ("train","BLOCKED_POSITIVE"):3,("validation","BLOCKED_POSITIVE"):1}:
        raise ValueError("Unexpected original failure roster")
    occupied = {r["patch_id"]:metric(r) for r in cached}
    for record in decisions:
        group = roster[record["group_id"]]
        if group["split"] != record["split"] or group["split"] not in TARGET or len(group["states"])!=1:
            raise ValueError("Invalid frozen group membership")
        if record["status"]=="GEOMETRY_CANDIDATES_ONLY":
            old=record["positive_geometry"]
            occupied[old["patch_id"]]=metric(old)
    resolved, results = list(cached), []
    ordinals = Counter()
    for record in decisions:
        key,role = record["group_id"],record["split"]
        group=roster[key]
        state_name=group["states"][0]
        state=states[state_name]
        index=ordinals[role]
        ordinals[role]+=1
        old=record["positive_geometry"]
        members=[maus[fid] for fid in group["ids"]]
        opposite=opposing[role]
        other=[g for k,g in occupied.items() if k!=old["patch_id"]]
        result=dict(group_id=key,split=role,state=record["state"],old_geometry=old,
                    old_reasons=record["positive_reasons"])
        results.append(result)
        if record["status"]=="BLOCKED_POSITIVE":
            pos,bg,attempts=relocate(old,members,state,opposite,exclusions,other)
            result["relocation"]=attempts
        else:
            pos=old
            support = positive_support(pos,[reproject(g,4326,pos["crs"]) for g in members])
            reasons = blockers(metric(pos),state,opposite,exclusions,other,False)
            if support < 32:
                reasons.append("INSUFFICIENT_POSITIVE_GRID_CELLS")
            result["positive_recheck_reasons"]=reasons
            result["positive_grid_cells"]=support
            bg=None
            if not reasons:
                bg,rejections=background_pair(pos,key,state,opposite,exclusions,
                                              other+[metric(pos)],record.get("random_geometry"))
                result["background_recheck_counts"]=dict(rejections)
            else:
                pos=None
        if pos is None or bg is None:
            result["status"]="MISSING_POSITIVE" if pos is None else "MISSING_BACKGROUND_PAIR"
            continue
        result["status"]="COMPLETE_GEOMETRY_TRIPLE"
        result["new_geometry"]=pos
        for spec,label in [(pos,None),(bg[0][0],"random"),
                           (bg[1][0],record.get("hard_stratum") or ("bare_soil","sand_riverbed","built_up","exposed_rock")[index%4])]:
            occupied[spec["patch_id"]]=metric(spec)
            resolved.append(spec | dict(group_id=key,split=role,state=state_name,
                negative_stratum=label, label_source_fids=[] if label else
                [fid for fid in group["ids"] if occupied[spec["patch_id"]].intersects(geometry[fid])],
                geometry_status="PROPOSED_NO_IMAGERY"))
    check_plan_geometry(dict(patches=resolved),split,geometry,states,project)
    counts = dict(Counter(r["split"] for r in resolved))
    if resolved[:39]!=cached or len({r["patch_id"] for r in resolved})!=len(resolved):
        raise ValueError("Cached slots changed or duplicate patch ID")
    if (ROOT/"split.json").read_bytes()!=original:
        raise ValueError("Original split changed during recovery")
    go = counts == TARGET
    DEST.mkdir(parents=True,exist_ok=True)
    manifest = dict(status="GEOMETRY_GO" if go else "REDUCED_PROPOSAL_ONLY",
        split_sha256=digest(original),test_sealed=True,patches=resolved,counts=counts,
        missing_groups=[r["group_id"] for r in results if r["status"]!="COMPLETE_GEOMETRY_TRIPLE"])
    sha=write_json(DEST/"proposed-geometry.json",manifest)
    write_json(DEST/"recovery.json",dict(original_receipt_sha256=ORIGINAL_SHA,
        geometry_go=go,manifest_sha256=sha,counts=counts,split_sha256=digest(original),
        test_sealed=True,decisions=results))
    print(manifest["status"],counts,sha,flush=True)
    print(Counter((r["split"],r["status"]) for r in results),flush=True)


if __name__ == "__main__":
    run()
