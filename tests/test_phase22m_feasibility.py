import json
from pathlib import Path
from shapely.geometry import box

def test_mandatory_site_rectangles_conflict():
    r=json.loads(Path("docs/reports/phase22m-feasibility.json").read_bytes())
    a,b=r["sites"]
    assert a["split"]==b["split"]=="test"
    assert box(*a["bounds"]).intersection(box(*b["bounds"])).area==r["overlap_m2"]>0
    assert r["earth_engine_requests"]==r["imagery_bytes"]==0

def test_phase22l_grid_does_not_meet_frozen_unet_contract():
    from scripts.phase22l_temporal import SIZE,SCALE,FIELDS
    r=json.loads(Path("docs/reports/phase22j-model-registry.json").read_bytes())
    assert (SIZE,SCALE)==(64,30)
    assert "128x128" in r["contract"]["input"] and "10m" in r["contract"]["input"]
    assert "B8" not in FIELDS
