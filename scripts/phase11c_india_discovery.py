"""Bounded Indian opencast discovery using the existing Phase 3G diagnostics."""
import argparse
import csv
from dataclasses import asdict, replace
import json
from pathlib import Path

import ee
import numpy as np
from pyproj import Transformer
from rasterio import Affine

from config.phase2_settings import Phase2Config
from config.settings import BEFORE, AFTER
from scripts.phase3g_visualization import SIZE, NODATA, graph, download, validate, save_layers
from src.gee_setup import initialize
from src.sar_preprocessing import collection, choose_orbit

BASE = "https://environmentclearance.nic.in/"
# Published project bounds in degrees/minutes/seconds, longitude then latitude.
SOURCES = (
    ("gevra", "Gevra OCP", "Chhattisgarh", "Korba", "Korba coalfield",
     ((82,32,0),(82,39,30),(22,18,0),(22,21,42)),
     "IA/CG/CMIN/19281/2013", "auth/FORM_A_PDF.aspx?cat_id=IA%2FCG%2FCMIN%2F60655%2F2016&pid=found"),
    ("kusmunda", "Kusmunda OCP", "Chhattisgarh", "Korba", "Korba coalfield",
     ((82,38,39),(82,42,8),(22,15,18),(22,21,30)),
     "37th EAC item 37.1, 2015-06-11/12", "writereaddata/modification/Amendment/Attach_file/11072018TPA969WLAnnexure-RevisedForm1andotherdocuments.pdf"),
    ("bhubaneswari", "Bhubaneswari OCP, Talcher", "Odisha", "Angul", "Talcher coalfield",
     ((85,9,10),(85,11,37),(20,57,59),(20,58,43)),
     "J-11015/280/2013-IA.II(M)", "writereaddata/Form-1A/EC/022120141Bhubaneshwari_EC_Expansion.pdf"),
    ("kusunda-cluster-vii", "Kusunda Cluster VII, Jharia", "Jharkhand", "Dhanbad", "Jharia coalfield",
     ((86,23,27.23),(86,25,40.67),(23,43,7.16),(23,44,42)),
     "J-11015/238/2010-IA.II(M) Pt", "writereaddata/Form-1A/EC/102420181ECCluster-VII.PDF"),
    ("nigahi", "Nigahi OCP", "Madhya Pradesh", "Singrauli", "Singrauli coalfield (MP/UP)",
     ((82,35,32.33),(82,39,51.47),(24,5,58.62),(24,11,20.38)),
     "CMPDI job 212206102, 2021 PFR", "writereaddata/Online/TOR/05_Jun_2021_20003824384022258Annexure-Pre-feasibilityReport%28PFR%29File.pdf"),
)


def candidates(outputs):
    for key, name, state, district, group, dms, document, url in SOURCES:
        west, east, south, north = [d + m / 60 + s / 3600 for d, m, s in dms]
        yield dict(id=key, name=name, state=state, district=district, group=group,
                   anchor=[(west+east)/2, (south+north)/2], published_bounds=[west,south,east,north],
                   source=BASE+url, document=document, category="opencast coal project",
                   position="Project-envelope midpoint used as a search anchor; source datum and local error unverified.",
                   polygon=None, status="UNKNOWN", split=None)
    path = outputs / "phase11b_reference_packages/R008.json"
    if path.is_file():
        control = json.loads(path.read_text(encoding="utf-8"))
        yield dict(id="R008", name="Potential stable-background control", state="Meghalaya",
                   district=None, group="Meghalaya initial study area", anchor=control["anchor"],
                   source=path.as_posix(), document="Phase 11B R008", category="potential unchanged",
                   position="Saved search anchor; reference positional error unverified.",
                   polygon=control["geometry"], geometry_kind=control["geometry_kind"],
                   status="UNKNOWN", split=control["split"], block=control["block"])


def grid(anchor):
    lon, lat = anchor
    if not (68 <= lon <= 98 and 6 <= lat <= 38):
        raise ValueError("Anchor outside Indian screening envelope")
    crs = f"EPSG:{32601 + int((lon + 180) // 6)}"
    x, y = Transformer.from_crs(4326, crs, always_xy=True).transform(lon, lat)
    left, top = round(x/30)*30 - SIZE*15, round(y/30)*30 + SIZE*15
    return crs, Affine(30, 0, left, 0, -30, top), (left, top-SIZE*30, left+SIZE*30, top)


def screen(item, out):
    crs, affine, bounds = grid(item["anchor"])
    region = ee.Geometry.Rectangle(list(bounds), crs, False)
    cfg = Phase2Config(analysis_crs=crs)
    hist = ee.List([collection(region, season, cfg).aggregate_histogram("relativeOrbitNumber_start")
                    for season in (BEFORE, AFTER)]).getInfo()
    cfg = replace(cfg, relative_orbit=choose_orbit(*hist, None))
    image, bands, sources = graph(region, cfg)
    folder = out / item["id"]
    folder.mkdir()
    arrays = download(image, bands, cfg, affine, folder / "tile.tif")
    validate(arrays, cfg.min_observations)
    save_layers(arrays, folder)
    support = arrays["common_valid"] == 1
    if not support.any():
        raise ValueError("No common valid pixels")
    return dict(state="screened", grid_crs=crs, bounds=bounds, config=asdict(cfg),
                sources=sources, common=int(support.sum()), denominator=SIZE**2,
                valid_pixels={k:int((a==1).sum()) for k,a in arrays.items() if k.endswith("_valid")},
                median_delta={k:float(np.median(arrays[k][support])) for k in ("dVV","dVH","dNDVI","dNDTI")},
                preview=[f"{item['id']}/optical_{season}.png" for season in ("before","after")])


def priority(item):
    diagnostic = item["screen"]
    return (-diagnostic.get("common", -1), -item.get("review_priority", 0), item["id"])


# Preliminary interpretation of the saved Phase 11C previews. Ordered by
# recognizable surface context and a localized difference worth checking.
VISUAL = {
    "bhubaneswari": (5, "Dark patch changes outline. Check pond extent, shadow and actual-work maps."),
    "gevra": (4, "Bright worked-looking surfaces and linear features differ locally. Check road, dumps and pit plans."),
    "nigahi": (3, "Broad bright footprint remains recognizable. Check subtle edges and use stable interiors as controls if verified."),
    "kusunda-cluster-vii": (2, "Small dark patch appears in the after panel. Check water, shadow and individual mine geometry."),
    "kusmunda": (1, "Broad VH decline with modest optical median change. Verify the midpoint sits over the intended surface."),
    "R008": (0, "Potential stable vegetation control. Both composites show vegetation-like false colour; stability remains unverified."),
}


def run(outputs, destination):
    items = list(candidates(outputs))
    destination.mkdir(parents=True, exist_ok=False)
    initialize()
    ee.data.setDeadline(120000)
    for item in items:
        try:
            item["screen"] = screen(item, destination)
        except (ValueError, RuntimeError, ee.EEException) as exc:
            item["screen"] = dict(state="unverified", reason=str(exc))
        (destination / "inventory.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    write_inventory(items, destination)


def write_inventory(items, destination, reviewed=False):
    for item in items:
        if reviewed and item["screen"]["state"] == "screened":
            item["review_priority"], item["preview_observation"] = VISUAL[item["id"]]
        item["windows"] = [asdict(season) for season in (BEFORE, AFTER)]
    (destination / "inventory.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    fields = ("rank","id","state","district","longitude","latitude","status","source","common","median_delta")
    with (destination / "candidates.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, item in enumerate(sorted(items, key=priority), 1):
            subset = {k:item[k] for k in ("id","state","district","status","source")}
            lon, lat = item["anchor"]
            writer.writerow(dict(**subset, rank=rank, longitude=lon, latitude=lat,
                                 common=item["screen"].get("common"), median_delta=item["screen"].get("median_delta")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/phase11c_india_discovery"))
    args = parser.parse_args()
    run(Path("outputs"), args.output)
