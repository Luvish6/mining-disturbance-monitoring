"""Phase 24B: config-driven, resumable India screening over configurable AOIs.

Modes (default --plan, which never contacts Earth Engine):
  --plan       list AOIs, cached-tile status and the request/byte estimate for missing tiles
  --summarise  offline change-feature summaries from saved tiles (checkpointed per AOI, resumable)
  --execute    acquire missing tiles with the Phase 11C S1/S2 graph; needs --approve, takes an
               exclusive lock and enforces the run budget from the shared on-disk ledger

Each tile reuses the frozen seasonal S1/S2 preprocessing (cloud masking, SAR orbit selection,
speckle filter, seasonal medians) from Phase 11C / 3G. Summaries are descriptive screening
statistics. They are not detections, accuracy or mining attribution (attribution: UNKNOWN).
"""
import argparse
import json
from hashlib import sha256
from pathlib import Path

import numpy as np

CONFIG = Path("config/india_aois.json")
INVENTORY = Path("outputs/phase11c_india_discovery/inventory.json")
TILES = Path("outputs/phase11c_india_discovery")
OUT = Path("outputs/phase24b_india_screening")
REPORT = Path("docs/reports/phase24b-india-screening.json")
SNAPSHOT = Path("frontend/public/local/india-screening.json")
DELTAS = ("dVV", "dVH", "dNDVI", "dNDTI")
COUNTS = ("sar_before_count", "sar_after_count", "optical_before_count", "optical_after_count")
NDVI_LOSS = -0.30  # the 22L NDVI-drop threshold; BSI is not in these tiles, so the full 22L rule is not applied
CLAIMS = dict(status="EXPLORATORY", attribution="UNKNOWN", verified_detections=0, accuracy="NOT_ESTIMATED",
              coverage="Only the listed tiles were screened; no national or state coverage is implied.")


def sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def load_config(path=CONFIG):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    aois, seen = [], set()
    for region in cfg["regions"]:
        for aoi in region["aois"]:
            if aoi["id"] in seen:
                raise ValueError(f"Duplicate AOI id {aoi['id']}")
            if ("anchor" in aoi) == ("anchor_from" in aoi):
                raise ValueError(f"AOI {aoi['id']} needs exactly one of anchor / anchor_from")
            seen.add(aoi["id"])
            aois.append(dict(aoi, region=region["region"], state=region["state"]))
    if cfg["tile_cells"] != 32 or cfg["cell_m"] != 30:
        raise ValueError("Tile grid must match the Phase 11C 32x32, 30 m grid")
    return cfg, aois


def resolve(aoi, inventory):
    """Attach the anchor (lon, lat) and Phase 11C metadata; reject anchors outside India's envelope."""
    item = next((i for i in inventory if i["id"] == aoi["id"]), None)
    if aoi.get("anchor_from") == "phase11c":
        if item is None:
            raise ValueError(f"{aoi['id']} not in Phase 11C inventory")
        anchor = item["anchor"]
    else:
        anchor = aoi["anchor"]
    lon, lat = anchor
    if not (68 <= lon <= 98 and 6 <= lat <= 38):
        raise ValueError(f"{aoi['id']} anchor outside Indian screening envelope")
    meta = {k: item.get(k) for k in ("name", "district", "source", "document")} if item else {}
    return dict(aoi, anchor=list(anchor), **meta)


def tile_path(aoi_id):
    for root in (TILES, OUT / "tiles"):
        p = root / aoi_id / "tile.tif"
        if p.is_file():
            return p
    return None


def plan(cfg, aois):
    b = cfg["budget"]
    rows = [dict(id=a["id"], state=a["state"], region=a["region"], cached=tile_path(a["id"]) is not None) for a in aois]
    missing = [r for r in rows if not r["cached"]]
    req, byt = len(missing) * b["requests_per_aoi_estimate"], len(missing) * b["bytes_per_aoi_estimate"]
    return dict(aois=rows, missing=len(missing), estimated_requests=req, estimated_bytes=byt,
                within_budget=req <= b["max_requests_per_run"] and byt <= b["max_response_bytes_per_run"])


def stats(values):
    q = np.quantile(values, [0.1, 0.5, 0.9])
    return dict(p10=round(float(q[0]), 4), median=round(float(q[1]), 4), p90=round(float(q[2]), 4))


def summarise_tile(path):
    import rasterio
    with rasterio.open(path) as src:
        names = src.descriptions
        need = DELTAS + COUNTS + ("common_valid",)
        if any(names.count(n) != 1 for n in need):
            raise ValueError(f"{path} lacks the canonical Phase 11C bands")
        band = {n: src.read(names.index(n) + 1).astype("float64") for n in need}
        nodata, shape, crs = src.nodata, src.shape, str(src.crs)
    common = band["common_valid"] == 1
    for n in DELTAS:
        common &= np.isfinite(band[n]) & (band[n] != nodata)
    if common.sum() < 25:
        raise ValueError(f"{path}: fewer than 25 common-valid cells")
    out = dict(grid_cells=int(common.size), common_cells=int(common.sum()), crs=crs, shape=list(shape),
               screened_km2=round(float(common.sum()) * 0.0009, 3),
               changes={n: stats(band[n][common]) for n in DELTAS},
               seasonal_count_ranges={n: [int(band[n][common].min()), int(band[n][common].max())] for n in COUNTS},
               ndvi_loss_fraction=round(float((band["dNDVI"][common] <= NDVI_LOSS).mean()), 4),
               ndvi_loss_and_vh_drop_fraction=round(float(((band["dNDVI"][common] <= NDVI_LOSS)
                                                           & (band["dVH"][common] < 0)).mean()), 4))
    return out


def terrain(aoi_id, tile_sha):
    p = Path(f"outputs/phase16a_{aoi_id}")
    if not (p / "features.tif").is_file():
        return None
    import rasterio
    receipt = json.loads((p / "receipt.json").read_text(encoding="utf-8"))
    if receipt["cache_sha256"] != tile_sha:
        raise ValueError(f"Phase 16A {aoi_id} was prepared from a different tile")
    with rasterio.open(p / "features.tif") as src:
        d = src.descriptions
        elev, slope = src.read(d.index("elevation") + 1), src.read(d.index("slope") + 1)
        ok = (elev != src.nodata) & (slope != src.nodata)
    return dict(source="Phase 16A SRTM elevation/slope on the same grid", features_sha256=sha(p / "features.tif"),
                elevation_m=stats(elev[ok]), slope_deg=stats(slope[ok]),
                slope_over_25_fraction=round(float((slope[ok] > 25).mean()), 4))


def screening(aoi_id):
    p = Path(f"outputs/phase15c_{aoi_id}/receipt.json")
    if not p.is_file():
        return None
    r = json.loads(p.read_text(encoding="utf-8"))
    return dict(method=r["method"], status=r["status"], candidate_polygons=r["candidate_count"],
                eligible_cells=r["coverage"]["eligible_cells"], receipt_sha256=sha(p),
                note="Tile-relative robust cross-sensor anomaly polygons, REVIEW_REQUIRED; not detections")


def summarise(cfg, aois, cfg_sha, out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    sites, skipped = [], []
    for a in aois:
        t = tile_path(a["id"])
        if t is None:
            skipped.append(dict(id=a["id"], reason="NO_CACHED_TILE (needs approved --execute)"))
            continue
        tsha = sha(t)
        ck = out / f"{a['id']}.json"
        if ck.is_file():  # resume: reuse only if inputs and config are unchanged
            prev = json.loads(ck.read_text(encoding="utf-8"))
            if prev["provenance"]["tile_sha256"] == tsha and prev["provenance"]["config_sha256"] == cfg_sha:
                sites.append(prev)
                continue
        tier = "MEGHALAYA_LEAD" if a["state"] == "Meghalaya" else "UNVERIFIED_LEAD"
        s15 = screening(a["id"])
        site = dict(id=a["id"], name=a.get("name"), state=a["state"], district=a.get("district"), region=a["region"],
                    tier="SCREENED_SITE" if s15 else tier, status="UNKNOWN", attribution="UNKNOWN",
                    tile=summarise_tile(t), terrain=terrain(a["id"], tsha), screening=s15,
                    provenance=dict(tile_sha256=tsha, config_sha256=cfg_sha, location_source=a.get("source"),
                                    location_document=a.get("document"),
                                    position_note="Anchor from public project documents; datum and local error unverified"),
                    uncertainty="Seasonal medians over one 0.92 km2 tile; tile-relative; SAR layover and phenology not removed")
        ck.write_text(json.dumps(site, indent=2), encoding="utf-8")
        sites.append(site)
    return dict(phase="24B", config_version=cfg["version"], config_sha256=cfg_sha, seasons=cfg["seasons"],
                claims=CLAIMS, method=dict(
                    statistics="p10/median/p90 of after-minus-before seasonal medians over common-valid 30 m cells",
                    ndvi_loss_threshold=NDVI_LOSS, note="BSI is absent from the cached tiles, so the full 22L candidate rule is not applied"),
                coverage=dict(aois_configured=len(aois), aois_screened=len(sites),
                              states=sorted({s["state"] for s in sites}),
                              screened_km2=round(sum(s["tile"]["screened_km2"] for s in sites), 3),
                              national_coverage=False),
                sites=sites, skipped=skipped)


def execute(cfg, aois, max_requests, out=OUT):
    """Acquire missing tiles only. Lock + ledger guard; the budget is read from disk before every AOI."""
    from scripts.phase22w_ablation import acquire_lock, ledger_usage
    missing = [a for a in aois if tile_path(a["id"]) is None]
    if not missing:
        return dict(acquired=[], requests=0, note="All configured AOIs already cached; no Earth Engine requests made")
    out.mkdir(parents=True, exist_ok=True)
    lock, ledger = acquire_lock(out / ".lock"), out / "ledger.jsonl"
    b, done = cfg["budget"], []
    try:
        import ee
        from scripts.phase11c_india_discovery import screen
        from src.gee_setup import initialize
        initialize()
        ee.data.setDeadline(120000)
        (out / "tiles").mkdir(exist_ok=True)
        for a in missing:
            n, size = ledger_usage(ledger)
            if (n + b["requests_per_aoi_estimate"] > min(max_requests, b["max_requests_per_run"])
                    or size + b["bytes_per_aoi_estimate"] > b["max_response_bytes_per_run"]):
                done.append(dict(id=a["id"], state="BLOCKED_BUDGET"))
                break
            try:
                record = screen(dict(id=a["id"], anchor=a["anchor"]), out / "tiles")
                state = "screened"
            except (ValueError, RuntimeError, ee.EEException) as exc:
                record, state = dict(reason=str(exc)), "unverified"
            t = out / "tiles" / a["id"] / "tile.tif"
            with ledger.open("a", encoding="utf-8") as f:
                f.write(json.dumps(dict(id=a["id"], requests=b["requests_per_aoi_estimate"], state=state,
                                        response_bytes=t.stat().st_size if t.is_file() else 0)) + "\n")
            (out / "tiles" / f"{a['id']}.receipt.json").write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
            done.append(dict(id=a["id"], state=state))
    finally:
        lock.unlink(missing_ok=True)
    return dict(acquired=done, ledger=ledger_usage(ledger))


def write(report):
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(dict(data=report, sha256=sha(REPORT))), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", type=Path, default=CONFIG)
    m = p.add_mutually_exclusive_group()
    m.add_argument("--plan", action="store_true")
    m.add_argument("--summarise", action="store_true")
    m.add_argument("--execute", action="store_true")
    p.add_argument("--approve", action="store_true", help="required with --execute")
    p.add_argument("--max-requests", type=int, default=0)
    a = p.parse_args()
    cfg, aois = load_config(a.config)
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8")) if INVENTORY.is_file() else []
    aois = [resolve(x, inventory) for x in aois]
    if a.execute:
        if not a.approve or a.max_requests <= 0:
            p.error("--execute needs --approve and a positive --max-requests")
        print(json.dumps(execute(cfg, aois, a.max_requests), indent=2))
    elif a.summarise:
        report = summarise(cfg, aois, sha(a.config))
        write(report)
        print(json.dumps(report["coverage"], indent=2))
    else:
        print(json.dumps(plan(cfg, aois), indent=2))


if __name__ == "__main__":
    main()
