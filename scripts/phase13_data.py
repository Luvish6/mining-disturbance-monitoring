"""Prepare ignored, read-only Phase 13 snapshots from saved research outputs."""
import ast
import csv
from hashlib import sha256
import json
from pathlib import Path
import shutil


def records(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def candidates(path):
    result = []
    for row in records(path):
        if row["status"] != "UNKNOWN":
            raise ValueError("Phase 11C candidate evidence status must be UNKNOWN")
        lon, lat = float(row["longitude"]), float(row["latitude"])
        if not (68 <= lon <= 98 and 6 <= lat <= 38):
            raise ValueError("Candidate coordinates outside the India screening domain")
        changes = ast.literal_eval(row["median_delta"]) if row["median_delta"] else {}
        result.append(dict(id=row["id"], state=row["state"], district=row["district"],
                           longitude=lon, latitude=lat, status=row["status"], common=int(row["common"]),
                           changes=changes, source=row["source"]))
    return result


def comparison(path):
    summary, *dates = records(path)
    if summary["row_type"] != "summary" or summary["status"] not in {"DESCRIPTIVE ONLY", "INSUFFICIENT DATA"}:
        raise ValueError("Unexpected Phase 12D comparison status")
    if summary["status"] == "DESCRIPTIVE ONLY":
        if (min(int(summary[k]) for k in ("upstream_cells", "downstream_cells")) < 25
                or int(summary["matched_months"]) < 2
                or len(dates) != 2 * int(summary["matched_pairs"])):
            raise ValueError("Phase 12D coverage gate mismatch")
    elif dates:
        raise ValueError("Unsupported comparison contains spectral rows")
    return dict(summary=summary, dates=dates)


def main():
    target = Path("frontend/public/local")
    target.mkdir(parents=True, exist_ok=True)
    inputs = (
        ("india-candidates", Path("outputs/phase11c_india_discovery/candidates.csv"), candidates),
        ("brahmani", Path("outputs/phase12d_brahmani/comparison.csv"), comparison),
    )
    for key, source, load in inputs:
        snapshot, download = (target / f"{key}.{suffix}" for suffix in ("json", "csv"))
        if not source.is_file():
            snapshot.unlink(missing_ok=True)
            download.unlink(missing_ok=True)
            print(f"{key}: saved output unavailable")
            continue
        payload = dict(data=load(source), sha256=sha256(source.read_bytes()).hexdigest())
        snapshot.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
        shutil.copyfile(source, download)


if __name__ == "__main__":
    main()
