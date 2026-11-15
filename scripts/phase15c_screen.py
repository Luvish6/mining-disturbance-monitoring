"""Offline robust multi-sensor change screening for a prepared Indian tile."""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import rasterio

from src.phase3.alerts import run as alert_run
from src.phase3.data import BANDS, BAND_UNITS, digest
from src.phase3.regional_inference import NODATA, check_grid, read_values, validate_values, write_tile

FLOORS = np.array([.5, .5, .015, .015])
COUNTS = ("sar_before_count", "sar_after_count", "optical_before_count", "optical_after_count")
MIN_Z = 2.5
MAX_Z = 6
MAX_SLOPE = 25
METHOD = "robust_cross_sensor_v1"


def anomaly(values, counts, min_observations):
    common = (np.isfinite(values) & (values != NODATA)).all(axis=0)
    observed = (np.isfinite(counts) & (counts >= min_observations)).all(axis=0)
    eligible = common & observed & (values[13] >= 0) & (values[13] <= MAX_SLOPE)
    if eligible.sum() < 25:
        raise ValueError("At least 25 common low-slope, adequately observed cells required")
    changes = values[8:12, eligible]
    med = np.median(changes, axis=1)
    scale = np.maximum(1.4826*np.median(np.abs(changes-med[:, None]), axis=1), FLOORS)
    deviations = np.abs(changes-med[:, None])/scale[:, None]
    both_sensors = np.minimum(deviations[:2].max(axis=0), deviations[2:].max(axis=0))
    scores = np.full(common.shape, NODATA, dtype="float32")
    scores[eligible] = np.minimum(both_sensors, MAX_Z)/MAX_Z
    statistics = dict(common_cells=int(common.sum()), seasonally_supported_cells=int((common & observed).sum()),
                      eligible_cells=int(eligible.sum()), grid_cells=int(common.size),
                      seasonal_count_ranges={key: [int(v.min()), int(v.max())]
                                             for key,v in zip(COUNTS, counts[:, eligible], strict=True)},
                      center=med.tolist(), scale=scale.tolist())
    return scores, eligible, statistics


def screen(feature, receipt, cached, output):
    report = json.loads(receipt.read_bytes())
    if digest(feature) != report["raster_sha256"] or digest(cached) != report["cache_sha256"]:
        raise ValueError("Input hashes differ from feature preparation receipt")
    with rasterio.open(feature) as src, rasterio.open(cached) as quality:
        check_grid(src, report["crs"])
        if (src.descriptions != BANDS or src.units != BAND_UNITS or src.nodata != NODATA
                or (src.crs, src.transform, src.shape) != (quality.crs, quality.transform, quality.shape)
                or src.tags().get("data_kind") != "real"):
            raise ValueError("Expected real aligned canonical 14-band features and observation counts")
        values = read_values(src)
        validate_values(values)
        if any(quality.descriptions.count(key) != 1 for key in COUNTS):
            raise ValueError("Missing or ambiguous seasonal count bands")
        counts = quality.read([quality.descriptions.index(key)+1 for key in COUNTS], masked=True)
        counts = counts.astype(float).filled(np.nan)
        if np.any(np.isfinite(counts) & ((counts < 0) | (counts != np.floor(counts)))):
            raise ValueError("Observation counts must be nonnegative integers")
        minimum = report["processing"]["min_observations"]
        if type(minimum) is not int or minimum < 2:
            raise ValueError("Invalid seasonal coverage threshold")
        score, eligible, diagnostics = anomaly(values, counts, minimum)
        settings = dict(feature_order=list(BANDS[8:12]), scale_floor=FLOORS.tolist(),
                        min_observations=minimum, max_slope_degrees=MAX_SLOPE, min_robust_z=MIN_Z,
                        clipping_z=MAX_Z, minimum_area_m2=3600, connectivity=4)
        with TemporaryDirectory(dir=output.parent) as stage:
            work = Path(stage)/"screen"
            work.mkdir()
            raster = work/"anomaly.tif"
            write_tile(raster, src.profile, ("anomaly_score", "common_valid"),
                       np.stack([score, eligible]).astype("float32"),
                       dict(data_kind="exploratory", model_sha256=digest(Path(__file__)), score_type=METHOD,
                            feature_sha256=report["raster_sha256"], region_id=report["region_id"],
                            windows=json.dumps(report["windows"])))
            # Alert date fields index composite windows by their last included day.
            dates = [(date.fromisoformat(window[1])-timedelta(days=1)).isoformat()
                     for window in report["windows"]]
            manifest = work/"alerts-input.json"
            manifest.write_text(json.dumps(dict(
                rules=dict(threshold=float(np.float32(MIN_Z/MAX_Z)), min_area_m2=3600),
                observations=[dict(raster=raster.name, region_id=report["region_id"],
                                   before_date=dates[0], after_date=dates[1], model_validation="NOT_VALIDATED",
                                   features=os.path.relpath(feature.resolve(), output.resolve()))]), indent=2),
                encoding="utf-8")
            # Run from final path so relative feature provenance remains reproducible.
            work.rename(output)
    alerts = alert_run(output/"alerts-input.json", output/"candidates")
    candidates = alerts["data"]["features"]
    if any(f["properties"]["status"] != "REVIEW_REQUIRED" for f in candidates):
        raise ValueError("Exploratory output escaped review-only gate")
    summary = dict(region_id=report["region_id"], windows=report["windows"],
                   date_basis="Composite window end minus one day; consult preparation receipt for source acquisition dates",
                   status="EXPLORATORY", feature_receipt_sha256=digest(receipt),
                   features_sha256=report["raster_sha256"], cache_sha256=report["cache_sha256"],
                   anomaly_sha256=digest(output/"anomaly.tif"), method=METHOD, settings=settings,
                   coverage=diagnostics, candidate_count=len(candidates),
                   reference="Phase 11C location documents and Phase 15B review context; no independent paired label",
                   uncertainty="Tile-relative absolute deviations; slope screen does not remove radar layover or seasonal effects")
    (output/"receipt.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("feature", "receipt", "cached", "output"):
        parser.add_argument(name, type=Path)
    args = vars(parser.parse_args())
    if args["output"].exists():
        parser.error("Choose a new output directory")
    print(screen(**args))


if __name__ == "__main__":
    main()
