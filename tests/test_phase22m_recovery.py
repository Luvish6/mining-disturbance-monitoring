import json
from pathlib import Path

def test_incomplete_context_roster_stops_before_acquisition():
    r=json.loads(Path("docs/reports/phase22m-recovery-selection.json").read_bytes())
    assert r["requirements"]==dict(mining_context=3,forest_context=1,farmland_context=1,river_context=1)
    assert r["documented_mining_context"]==1 and r["mining_context_deficit"]==2
    assert r["forest_context_verified"]==r["farmland_context_verified"]==0
    assert r["frozen_aoi_count"]==r["imagery_requests"]==r["earth_engine_requests"]==0
    assert not r["all_six_buffer_verified"]

def test_only_development_locators_are_listed_without_test_claims():
    r=json.loads(Path("docs/reports/phase22m-recovery-selection.json").read_bytes())
    assert all(d["split"] in ("train","validation") for d in r["development_locators"])
    assert not r["test_access"]
    assert all(s["full_aoi_split_and_buffer_status"]=="UNCHECKED"
               for s in r["river_location_metadata"])
