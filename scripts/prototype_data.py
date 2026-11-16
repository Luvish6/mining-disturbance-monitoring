"""Build local Explorer assets from verified Phase 15B/15C products."""
from datetime import datetime, timezone
import json
from pathlib import Path

import matplotlib
import matplotlib.image
import numpy as np
import rasterio
from pyproj import Transformer
from shapely import transform
from shapely.geometry import box, mapping, shape

from scripts.satellite_previews import SITES, verify as verify_previews
from src.phase3.data import digest


def read(path):
    return json.loads(path.read_bytes())


def review_polygons(features, bounds, crs, affine, raster_hash):
    project = Transformer.from_crs(4326, crs, always_xy=True).transform
    result = []
    for feature in features:
        p = feature["properties"]
        if (p["status"], p["evidence_status"], p["eligible_observation_count"], p["raster_sha256"]) != (
                "REVIEW_REQUIRED", "UNKNOWN", 0, raster_hash):
            raise ValueError("Unexpected evidence or operational status")
        geom = shape(feature["geometry"])
        metric = transform(geom, project, interleaved=False)
        if (not geom.is_valid or geom.geom_type != "Polygon"
                or not box(*bounds).buffer(.01).covers(metric)
                or abs(metric.area-p["area_m2"]) > .1
                or geom.centroid.distance(shape({"type": "Point", "coordinates": [p["longitude"], p["latitude"]]})) > 1e-7):
            raise ValueError("Invalid review geometry or centroid")
        pixels = [[list((~affine) @ (x, y)) for x, y in ring] for ring in mapping(metric)["coordinates"]]
        result.append(dict(id=feature["id"], rings=pixels, longitude=p["longitude"], latitude=p["latitude"],
                           area=p["area_m2"], score=p["mean_score"], status=p["status"], evidence=p["evidence_status"]))
    return result


def build_site(outputs, local, site):
    screen = outputs/f"phase15c_{site}"
    base = outputs/"phase11c_india_discovery"/site
    context = outputs/"phase15b_annotation"/site/"coordinator"/"provenance.json"
    feature_receipt = outputs/f"phase16a_{site}"/"receipt.json"
    inventory = base.parent/"inventory.json"
    preview_folder = outputs/"phase18b_previews"/site
    required = (screen/"receipt.json", screen/"anomaly.tif", screen/"candidates/alerts.geojson",
                base/"tile.tif", context, feature_receipt, inventory, preview_folder/"manifest.json")
    if not all(path.is_file() for path in required):
        return None
    report, provenance = read(required[0]), read(context)
    features_receipt = read(feature_receipt)
    inventory_hash = digest(inventory)
    if (digest(feature_receipt) != report["feature_receipt_sha256"]
            or features_receipt["raster_sha256"] != report["features_sha256"]
            or features_receipt["cache_sha256"] != report["cache_sha256"]
            or features_receipt["source_receipt_sha256"] != inventory_hash
            or provenance["inventory_sha256"] != inventory_hash
            or features_receipt["windows"] != report["windows"]
            or features_receipt["region_id"] != site
            or features_receipt["processing"] != provenance["processing"]):
        raise ValueError("Feature and scene provenance disagree")
    scores_hash = digest(required[1])
    if (scores_hash != report["anomaly_sha256"]
            or provenance["tile_sha256"] != report["cache_sha256"] or digest(base/"tile.tif") != report["cache_sha256"]
            or provenance["windows"] != report["windows"] or report["region_id"] != site):
        raise ValueError("Site input hashes or observation windows disagree")
    for season, (start, end), original in zip(
            ("before", "after"), report["windows"], features_receipt["scene_sources"], strict=True):
        for sensor in ("s1", "s2"):
            scenes = provenance["scenes"][season][sensor]
            expected = [dict(id=key, acquired_utc=datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat())
                        for key, ms in zip(original[f"{sensor}_ids"], original[f"{sensor}_time_start_ms"], strict=True)]
            if not scenes or scenes != expected:
                raise ValueError("Scene inventory differs from feature provenance")
            for scene in scenes:
                instant = datetime.fromisoformat(scene["acquired_utc"])
                if instant.tzinfo is None or not start <= instant.astimezone(timezone.utc).date().isoformat() < end:
                    raise ValueError("Scene acquisition falls outside its composite window")
    preview_hash, previews = verify_previews(outputs, preview_folder, site)
    features = read(required[2])["features"]
    if len(features) != report["candidate_count"] or any(f["properties"]["region_id"] != site for f in features):
        raise ValueError("Candidate inventory disagrees")
    with rasterio.open(required[1]) as grid, rasterio.open(base/"tile.tif") as cache:
        if (str(grid.crs) != provenance["crs"] or tuple(grid.bounds) != tuple(provenance["bounds"])
                or grid.descriptions != ("anomaly_score", "common_valid")
                or (grid.crs, grid.transform, grid.shape) != (cache.crs, cache.transform, cache.shape)):
            raise ValueError("Saved model-input and score grids disagree")
        score, mask = grid.read()
        valid = mask == 1
        if (not np.isin(mask, [0, 1]).all() or int(valid.sum()) != report["coverage"]["eligible_cells"]
                or not np.array_equal(score != grid.nodata, valid)
                or not ((score[valid] >= 0) & (score[valid] <= 1)).all()):
            raise ValueError("Saved anomaly mask or values disagree")
        candidates = review_polygons(features, grid.bounds, grid.crs, grid.transform, scores_hash)
        assets = local/site
        assets.mkdir(parents=True, exist_ok=True)
        for filename, content in previews.items():
            (assets/filename).write_bytes(content)
        rgba = matplotlib.colormaps["magma"](np.clip(score, 0, 1))
        rgba[..., 3] = valid
        matplotlib.image.imsave(assets/"anomaly.png", rgba)
        return dict(crs=str(grid.crs), bounds=list(grid.bounds), shape=list(grid.shape),
                    windows=report["windows"], scenes=provenance["scenes"], observation_counts=report["coverage"],
                    settings=report["settings"], uncertainty=report["uncertainty"], processing=provenance["processing"],
                    candidates=candidates, anomaly_sha256=scores_hash, source_sha256=report["cache_sha256"],
                    preview_manifest_sha256=preview_hash, alert_geojson_sha256=digest(required[2]), status="EXPLORATORY", operational_alerts=0)


def main():
    target = Path("frontend/public/local/india-sites")
    target.mkdir(parents=True, exist_ok=True)
    for site in SITES:
        (target/f"{site}.json").unlink(missing_ok=True)
    for site in SITES:
        path = target/f"{site}.json"
        result = build_site(Path("outputs"), target, site)
        if result is None:
            print(f"{site}: saved site products unavailable")
        else:
            path.write_text(json.dumps(dict(data=result, sha256=result["anomaly_sha256"]), allow_nan=False),
                            encoding="utf-8")
            print(site, len(result["candidates"]), result["crs"])


if __name__ == "__main__":
    main()
