"""Local disturbance screening records from bounded, aligned Phase 3 raster products."""
import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from pyproj import CRS, Transformer
import rasterio
from rasterio.features import shapes
from scipy.ndimage import find_objects, label
from shapely import transform
from shapely.geometry import mapping, shape
from tempfile import TemporaryDirectory

from .data import BANDS, digest

INDICATORS = ("dVV", "dVH", "dNDVI", "dNDTI")
MAX_PIXELS = 4_000_000


@dataclass(frozen=True)
class Rules:
    threshold: float = .5
    min_area_m2: float = 2700
    min_coverage: float = .8
    high_score: float = .85
    repeat_dates: int = 2
    overlap_iou: float = .5

    def __post_init__(self):
        if not (0 < self.threshold <= self.high_score <= 1 and 0 < self.min_coverage <= 1
                and 0 < self.overlap_iou <= 1 and np.isfinite(self.min_area_m2)
                and self.min_area_m2 > 0 and type(self.repeat_dates) is int and self.repeat_dates >= 2):
            raise ValueError("Invalid alert rules")


def validation(entry, base, tags, source_hash):
    """Check a local, trusted Phase 3 RF evaluation and model-run receipt."""
    if tags.get("data_kind") != "real" or entry.get("model_validation") != "VALIDATED":
        return False, {}
    if not entry.get("evaluation") or not entry.get("run_receipt"):
        return False, {}
    try:
        evaluation = (base / entry["evaluation"]).read_bytes()
        run = (base / entry["run_receipt"]).read_bytes()
        ev, model = json.loads(evaluation), json.loads(run)
        selected = model["selected_experiment"]
        validated = (
            model["data_kind"] == ev["data_kind"] == "real"
            and ev["partition"] == "test"
            and model["selection_partition"] == ev["selection_partition"] == "validation"
            and model["test_used_for_selection"] is False
            and ev["selected_experiment"] == tags["experiment"] == selected
            and model["manifest_sha256"] == ev["manifest_sha256"]
            and model["experiments"][selected]["sha256"] == tags["model_sha256"]
            and tags["model_sha256"] == entry["model_sha256"]
            and len(ev["test_class_counts"]) == 2 and min(ev["test_class_counts"]) > 0
            and ev["independent_test_blocks"] >= 2
            and entry["validated_region_id"] == entry["region_id"]
            and entry["raster_sha256"] == source_hash
            and entry["evaluation_sha256"] == sha256(evaluation).hexdigest()
            and entry["run_sha256"] == sha256(run).hexdigest()
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False, {}
    return bool(validated), dict(evaluation_sha256=sha256(evaluation).hexdigest(),
                                 run_sha256=sha256(run).hexdigest())


def observations(entries, base, rules):
    candidates, runs = [], []
    region_crs = {}
    for entry in sorted(entries, key=lambda e: (e["region_id"], e["after_date"], e["before_date"], e["raster"])):
        region = entry["region_id"]
        before, after = (date.fromisoformat(entry[key]) for key in ("before_date", "after_date"))
        if not region or before >= after:
            raise ValueError("Region and chronological observation dates required")
        path = base / entry["raster"]
        source_hash = digest(path)
        with rasterio.open(path) as src:
            grid = src.transform
            crs = CRS.from_user_input(src.crs)
            if (not crs.is_projected or any(axis.unit_conversion_factor != 1 for axis in crs.axis_info)
                    or not all(np.isfinite(tuple(grid))) or grid.a <= 0 or grid.e >= 0
                    or grid.b or grid.d or src.width*src.height > MAX_PIXELS):
                raise ValueError("Expected bounded north-up metre grid")
            if region_crs.setdefault(region, crs) != crs:
                raise ValueError("All observations in a region must share a CRS")
            if not {"disturbance_probability", "common_valid"} <= set(src.descriptions):
                raise ValueError("Missing probability or valid-data band")
            p, mask = src.read([src.descriptions.index(band)+1 for band in
                                ("disturbance_probability", "common_valid")], masked=True)
            mask_values = mask.compressed()
            if not np.isin(mask_values, [0, 1]).all():
                raise ValueError("Invalid binary mask")
            claimed = mask.filled(0) == 1
            scores = p.astype(float).filled(np.nan)
            valid = claimed & np.isfinite(scores) & (scores >= 0) & (scores <= 1)
            coverage = float(valid.mean())
            tags = src.tags()
            validated, receipts = validation(entry, base, tags, source_hash)
            evidence, feature_hash = {}, None
            if entry.get("features"):
                feature_path = base / entry["features"]
                feature_hash = digest(feature_path)
                with rasterio.open(feature_path) as features:
                    if (features.crs, features.transform, features.shape, features.descriptions) != (
                            src.crs, grid, src.shape, BANDS):
                        raise ValueError("Feature raster does not match inference grid or schema")
                    for band in INDICATORS:
                        evidence[band] = features.read(BANDS.index(band)+1, masked=True).astype(float).filled(np.nan)
            evidence_bound = feature_hash is not None and feature_hash == entry.get("features_sha256")
            status = ("NOT_VALIDATED" if not validated else "REVIEW_REQUIRED"
                      if coverage < rules.min_coverage or np.any(claimed & ~valid) or not evidence_bound
                      else "ALERT_ELIGIBLE")
            run = dict(region_id=region, before_date=before.isoformat(), after_date=after.isoformat(),
                       raster_sha256=source_hash, features_sha256=feature_hash, model_sha256=tags.get("model_sha256"),
                       data_kind=tags.get("data_kind", "unknown"), crs=crs.to_string(), transform=list(grid)[:6],
                       grid_cells=int(valid.size), valid_cells=int(valid.sum()), coverage=coverage,
                       invalid_claimed_cells=int((claimed & ~valid).sum()), status=status, **receipts)
            runs.append(run)
            groups, count = label(valid & (scores >= rules.threshold))
            if not count:
                continue
            cell_area = abs(grid.a*grid.e)
            sizes = np.bincount(groups.ravel())
            keep = sizes*cell_area >= rules.min_area_m2
            keep[0] = False
            selected = keep[groups]
            windows = find_objects(groups)
            for geometry, component in shapes(groups.astype("int32"), mask=selected, transform=grid):
                geom = shape(geometry)
                window = windows[int(component)-1]
                inside = groups[window] == int(component)
                values = scores[window][inside]
                support = {}
                for band, layer in evidence.items():
                    samples = layer[window][inside]
                    finite = samples[np.isfinite(samples)]
                    support[band] = dict(valid_cells=len(finite), median=float(np.median(finite)) if len(finite) else None)
                candidate_status = status
                if status == "ALERT_ELIGIBLE" and any(
                    item["valid_cells"]/len(values) < rules.min_coverage for item in support.values()
                ):
                    candidate_status = "REVIEW_REQUIRED"
                candidates.append((geom, dict(run, status=candidate_status, cells=len(values),
                    area_m2=geom.area, mean_score=float(values.mean()), max_score=float(values.max()),
                    indicators=support)))
    return candidates, runs, region_crs


def consolidate(candidates, region_crs, rules):
    tracks = []
    for geom, record in candidates:
        eligible = []
        for track in tracks:
            previous, old = track[-1]
            if (record["region_id"], record["model_sha256"], record["data_kind"]) != (
                    old["region_id"], old["model_sha256"], old["data_kind"]):
                continue
            iou = geom.intersection(previous).area / geom.union(previous).area
            if iou >= rules.overlap_iou:
                eligible.append((iou, track))
        if eligible:
            max(eligible, key=lambda item: item[0])[1].append((geom, record))
        else:
            tracks.append([(geom, record)])
    features = []
    for track in tracks:
        geom, recent = max(track, key=lambda item: (item[1]["after_date"], -severity(item[1]["status"]),
                                                     item[1]["mean_score"], item[1]["raster_sha256"]))
        by_date = {}
        for _, item in track:
            by_date.setdefault(item["after_date"], []).append(item)
        repeat_count = len(by_date)
        eligible_dates = sum(all(item["status"] == "ALERT_ELIGIBLE" for item in items)
                             for items in by_date.values())
        priority = ("HIGH" if recent["mean_score"] >= rules.high_score and repeat_count >= rules.repeat_dates
                    else "ELEVATED" if recent["mean_score"] >= rules.high_score else "STANDARD")
        properties = dict(recent, screening_priority=priority, observation_count=repeat_count,
                          first_observed=min(by_date), last_observed=max(by_date),
                          observation_dates=sorted(by_date), supporting_rasters=sorted({item["raster_sha256"] for _, item in track}),
                          eligible_observation_count=eligible_dates)
        # Conflicting same-date duplicates fail closed and never increase the repeat count.
        properties["status"] = max((item["status"] for item in by_date[recent["after_date"]]), key=severity)
        projection = Transformer.from_crs(region_crs[recent["region_id"]], 4326, always_xy=True)
        wgs = transform(geom, projection.transform, interleaved=False)
        lon, lat = projection.transform(geom.centroid.x, geom.centroid.y)
        properties.update(longitude=lon, latitude=lat)
        first = track[0][1]
        key = json.dumps([first[k] for k in ("region_id", "after_date", "raster_sha256")]).encode() + track[0][0].wkb
        features.append(dict(type="Feature", id=sha256(key).hexdigest(), geometry=mapping(wgs), properties=properties))
    return features


def severity(status):
    return {"ALERT_ELIGIBLE": 0, "REVIEW_REQUIRED": 1, "NOT_VALIDATED": 2}[status]


def run(manifest, output):
    if output.exists():
        raise ValueError("Choose a new alert output directory")
    spec = json.loads(manifest.read_bytes())
    rules = Rules(**spec.get("rules", {}))
    candidates, receipts, region_crs = observations(spec["observations"], manifest.parent, rules)
    features = consolidate(candidates, region_crs, rules)
    collection = dict(type="FeatureCollection", features=features)
    report = dict(data=collection, sha256=digest(manifest), rules=asdict(rules), observations=receipts,
                  interpretation="Screening priority and uncalibrated model scores. Human evidence status unconfirmed.")
    with TemporaryDirectory(dir=output.parent) as stage:
        directory = Path(stage) / "alerts"
        directory.mkdir()
        (directory/"alerts.geojson").write_text(json.dumps(collection, allow_nan=False), encoding="utf-8")
        (directory/"alerts.json").write_text(json.dumps(report, allow_nan=False), encoding="utf-8")
        with (directory/"alerts.csv").open("w", newline="", encoding="utf-8") as stream:
            rows = [dict(id=f["id"], **f["properties"]) for f in features]
            fields = list(dict.fromkeys(["id", "status", "region_id", "longitude", "latitude",
                                         "after_date", *(key for row in rows for key in row)]))
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows({key: json.dumps(val, sort_keys=True) if isinstance(val, (dict, list)) else val
                              for key, val in row.items()} for row in rows)
        directory.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.manifest, args.output)


if __name__ == "__main__":
    main()
