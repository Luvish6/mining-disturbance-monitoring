"""Geometry-only gate for the frozen Phase 22G weak-label scale-up proposal."""

from collections import Counter
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Point, box, mapping
from shapely.strtree import STRtree

from scripts.phase22b_maus import BUFFER, ROOT, digest, stable, write_json
from scripts.phase22e_maus import DIRECTIONS, STRATA, bounds_row, exclusion_sources
from scripts.phase22e_maus import reproject, source_context
from scripts.phase22e_maus_export import check_plan_geometry
from scripts.phase22e_r_maus import DEST as CACHE, PLAN_SHA
from scripts.phase22f_maus import DEST as PHASE22F, cached_inputs

PROPOSAL_SHA = "7aa19308fb2c9e85dd7a5f359ef7972a523eb6e32a87f81e273d0617ae318eda"
DEST = Path("outputs/phase22g_maus")
MAX_TIFF = 150
MAX_METADATA = 450


def blockers(window, state, opposing, exclusions, occupied, background):
    reasons = []
    if not state.covers(window.buffer(BUFFER)):
        reasons.append("ADM1_FULL_FOOTPRINT_BUFFER")
    if len(opposing.query(window, predicate="dwithin", distance=BUFFER)):
        reasons.append("OPPOSING_OR_EXCLUDED_GROUP_BUFFER")
    if any(window.intersects(other) for other in occupied):
        reasons.append("PATCH_OVERLAP")
    if background and len(exclusions.query(window, predicate="intersects")):
        reasons.append("MAUS_OR_PROJECT_MINING_EXCLUSION")
    return reasons


def pair_candidates(candidates):
    """First seed-ordered background candidate retaining a separate hard slot."""
    ordered = sorted(candidates, key=lambda item: stable(item[0]["patch_id"]))
    for row, geom in ordered:
        disjoint = [(other, area) for other, area in ordered if not geom.intersects(area)]
        if disjoint:
            return (row, geom), disjoint
    return None, []


def authenticated(path, expected):
    content = path.read_bytes()
    if digest(content) != expected:
        raise ValueError(f"Frozen {path.name} hash mismatch")
    return json.loads(content)


def preflight():
    _, _, normalization, _ = cached_inputs()
    proposal = authenticated(PHASE22F / "scale-up-proposal.json", PROPOSAL_SHA)
    plan = authenticated(CACHE / "plan.json", PLAN_SHA)
    original, split, _, maus, geometry, states = source_context(ROOT)
    if proposal["split_sha256"] != digest(original):
        raise ValueError("Scale-up proposal and split disagree")
    frozen = split["groups"]
    groups = proposal["group_candidates"]
    counts = Counter(group["split"] for group in groups)
    if counts != {"train":42,"validation":12} or len({g["group_id"] for g in groups}) != 54:
        raise ValueError("Unexpected scale-up group roster")
    cached = {row["group_id"] for row in plan["patches"]}
    if cached != {g["group_id"] for g in groups if g["cached"]}:
        raise ValueError("Cached groups changed")
    project, metadata = exclusion_sources()
    if metadata != plan["project_exclusions"]:
        raise ValueError("Candidate exclusions differ from the frozen acquisition plan")
    check_plan_geometry(plan, split, geometry, states, project)
    exclusions = STRtree(list(geometry.values())+project)
    roles = {fid:row["split"] for row in frozen.values() for fid in row["ids"]}
    opposing = {role:STRtree([g for fid,g in geometry.items() if roles[fid]!=role])
                for role in ("train","validation")}
    occupied = [reproject(box(*row["bounds"]),row["crs"],7755) for row in plan["patches"]]
    decisions = []
    new_indices = Counter()
    for group in groups:
        key, role = group["group_id"], group["split"]
        record = frozen[key]
        if (record["split"] != role or role not in opposing
                or (group["positive_slots"],group["background_slots"]) != (1,2)):
            raise ValueError("Proposal touches a sealed or changed group")
        if group["cached"]:
            continue
        index = new_indices[role]
        new_indices[role] += 1
        if len(record["states"]) != 1:
            raise ValueError("Non-single-state development group")
        state = states[record["states"][0]]
        fid = min(record["ids"], key=lambda k:(-geometry[k].area,stable(k)))
        point = maus[fid].representative_point()
        crs = 32601+int((point.x+180)//6)
        origin = reproject(point,4326,crs)

        def window(point, suffix):
            bounds, affine = bounds_row(point,crs)
            footprint = reproject(box(*bounds),crs,7755)
            return dict(patch_id=f"{key}-{suffix}", affine=affine, bounds=bounds,
                        crs=crs, geometry=mapping(reproject(box(*bounds),crs,4326))), footprint

        pos, footprint = window(point,"pos")
        failed = blockers(footprint,state,opposing[role],exclusions,occupied,False)
        row = dict(group_id=key,split=role,state=group["state"], anchor_fid=fid,
                   positive_geometry=pos,positive_reasons=failed)
        decisions.append(row)
        if failed:
            row["status"] = "BLOCKED_POSITIVE"
            continue
        candidates, rejected = [], []
        for radius in (3000,4500,6000):
            for bearing,angle in enumerate(DIRECTIONS):
                center = Point(origin.x+radius*np.cos(angle),origin.y+radius*np.sin(angle))
                spec, area = window(reproject(center,crs,4326),f"{radius}-{bearing}")
                why = blockers(area,state,opposing[role],exclusions,occupied+[footprint],True)
                if why:
                    rejected.append(dict(geometry=spec,reasons=why))
                else:
                    candidates.append((spec,area))
        random, hard = pair_candidates(candidates)
        row["rejected_background_geometries"] = rejected
        row["eligible_background_geometries"] = [r for r,_ in candidates]
        if random is None:
            row["status"] = "BLOCKED_BACKGROUND"
            continue
        row.update(status="GEOMETRY_CANDIDATES_ONLY",random_geometry=random[0],
                   hard_geometry_candidates=[r for r,_ in hard],hard_stratum=STRATA[index%4])
        occupied.extend((footprint,random[1]))

    blocked = [r for r in decisions if r["status"].startswith("BLOCKED")]
    if digest((ROOT/"split.json").read_bytes()) != digest(original):
        raise ValueError("Original split changed")
    DEST.mkdir(parents=True,exist_ok=True)
    receipt = dict(split_sha256=digest(original),preregistered_proposal_sha256=PROPOSAL_SHA,
        original_plan_sha256=PLAN_SHA,original_normalization_sha256=digest(json.dumps(
            normalization,sort_keys=True).encode()),test_sealed=True,cached_patches=39,
        new_groups=len(decisions),blocked_groups=len(blocked),
        new_tiff_responses=0,earth_engine_metadata_calls=0,
        new_tiff_cap=MAX_TIFF,metadata_cap=MAX_METADATA,
        gate="STOP_GEOMETRY" if blocked else "METADATA_AND_FINAL_GEOMETRY_PENDING",
        decisions=decisions)
    write_json(DEST/"geometry-preflight.json",receipt)
    print(receipt["gate"],Counter((r["split"],r["status"]) for r in decisions),flush=True)
    print("Positive failure reasons",Counter(reason for r in blocked for reason in r["positive_reasons"]),flush=True)


if __name__ == "__main__":
    preflight()
