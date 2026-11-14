"""Export a private Explorer snapshot from verified local products."""
import csv
from pathlib import Path

import numpy as np

from scripts import phase7_real_change as change
from scripts.phase7_day2_spatial import LEVELS, masks, overlap
from src.phase3.data import digest, save_json


def main():
    root = Path("outputs")
    day2 = root / "phase7_day2_spatial_patterns"
    receipt = change.read(day2 / "provenance.json")
    tiles, roster = change.load_tiles(root / "phase6b_multitile")
    if roster != receipt["roster_sha256"] or digest(day2 / "overlap.csv") != receipt["output_sha256"]["overlap.csv"]:
        raise ValueError("Day 2 evidence hash mismatch")
    if receipt["levels"] != {name: list(cuts) for name, cuts in LEVELS.items()}:
        raise ValueError("Day 2 thresholds differ from the analysis code")
    with (day2 / "overlap.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    records = []
    for tile in tiles:
        arrays, valid = tile["arrays"], tile["common"]
        source = receipt["sources"][tile["id"]]
        if tile["hashes"] != source["hashes"] or tile["quality_sha256"] != source["quality_sha256"]:
            raise ValueError("Saved Day 2 source does not match the verified tile")
        statistics = {}
        overlays = {}
        for level, cuts in LEVELS.items():
            row, = [r for r in rows if r["tile"] == tile["id"] and r["level"] == level
                    and r["comparison"] == "directional_unions"]
            fields = masks(arrays, valid, *cuts)
            computed = overlap(fields["radar"], fields["optical"], valid)
            for key, value in computed.items():
                if (value is None and row[key]) or (value is not None and float(row[key]) != value):
                    raise ValueError("Saved overlap differs from native-grid masks")
            statistics[level] = computed
            if level != "middle":
                category = fields["radar"].astype(int) + 2 * fields["optical"]
                overlays[level] = np.where(valid, category, -1).ravel().tolist()
        records.append(dict(
            id=tile["id"], district=tile["district"], split=tile["split"], bounds=tile["bounds"],
            shape=list(valid.shape), common=int(valid.sum()), overlaps=statistics, overlays=overlays,
            layers={band: [float(v) if ok else None for v, ok in zip(arrays[band].ravel(), valid.ravel())]
                    for band in change.CHANGE},
            counts={key: [int(arrays[key][valid].min()), int(arrays[key][valid].max())] if valid.any() else None
                    for key in change.pilot.COUNT_BANDS},
            sourceHashes=source["hashes"]))
    target = Path("frontend/public/local/explorer.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    save_json(target, dict(crs="EPSG:32646", spacing=30, roster=roster,
                           overlapSha256=digest(day2 / "overlap.csv"),
                           periods=[[s.start, s.end] for s in change.pilot.SEASONS],
                           tiles=records))


if __name__ == "__main__":
    main()
