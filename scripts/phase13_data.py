"""Prepare ignored, read-only Phase 13 snapshots from saved research outputs."""
import ast
import csv
from datetime import date
import re
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
        provenance = ("source_receipt_sha256", "station_table_sha256",
                      "upstream_mask_sha256", "downstream_mask_sha256")
        if (any(not re.fullmatch(r"[0-9a-f]{64}", summary.get(key, "")) for key in provenance)
                or not summary.get("source_collections") or not summary.get("rainfall_geometry")
                or summary.get("mine_connectivity") != "UNKNOWN"):
            raise ValueError("Phase 12D provenance is incomplete")
        seen, pairs = set(), {}
        windows = {"before": ("2023-11-01", "2024-04-01"), "after": ("2024-11-01", "2025-04-01")}
        for row in dates:
            season, stamp = row["season"], row["date"]
            day = date.fromisoformat(stamp)
            start, end = windows[season]
            slot = (int(row["pair"]), season)
            if (row["row_type"] != "date" or row["status"] != "DESCRIPTIVE ONLY"
                    or not start <= stamp < end or (season, day) in seen or slot in pairs):
                raise ValueError("Phase 12D has invalid or duplicate matched dates")
            seen.add((season, day))
            pairs[slot] = day.month
        months = set()
        for number in range(1, int(summary["matched_pairs"]) + 1):
            before, after = (pairs.get((number, season)) for season in windows)
            if before is None or before != after:
                raise ValueError("Phase 12D has incomplete or mismatched date pairs")
            months.add(before)
        if len(months) != int(summary["matched_months"]):
            raise ValueError("Phase 12D matched month count disagrees")
    elif dates:
        raise ValueError("Unsupported comparison contains spectral rows")
    return dict(summary=summary, dates=dates)


def brahmani_snapshot(path):
    data = comparison(path)
    summary = data["summary"]
    if summary["status"] == "DESCRIPTIVE ONLY":
        source = path.parent.parent / "phase12c_brahmani"
        receipt = source / "receipt.json"
        raw = receipt.read_bytes()
        if sha256(raw).hexdigest() != summary["source_receipt_sha256"]:
            raise ValueError("Phase 12C receipt hash differs from Phase 12D")
        metadata = json.loads(raw)
        for role, station in (("upstream", "Talcher upstream SW3"),
                              ("downstream", "Talcher far downstream 2416")):
            mask = source / metadata["observations"][station]["support_raster"]
            if sha256(mask.read_bytes()).hexdigest() != summary[f"{role}_mask_sha256"]:
                raise ValueError("Phase 12C support mask differs from Phase 12D")
        if (sha256((source / "stations.csv").read_bytes()).hexdigest() != summary["station_table_sha256"]
                or not metadata["crs"]
                or "; ".join(metadata["source_collections"]) != summary["source_collections"]):
            raise ValueError("Phase 12C source metadata differs from Phase 12D")
        data["crs"] = metadata["crs"]
    return data


def main():
    target = Path("frontend/public/local")
    target.mkdir(parents=True, exist_ok=True)
    inputs = (
        ("india-candidates", Path("outputs/phase11c_india_discovery/candidates.csv"), candidates),
        ("brahmani", Path("outputs/phase12d_brahmani/comparison.csv"), brahmani_snapshot),
    )
    for key, source, load in inputs:
        snapshot, download = (target / f"{key}.{suffix}" for suffix in ("json", "csv"))
        snapshot.unlink(missing_ok=True)
        download.unlink(missing_ok=True)
        if not source.is_file():
            print(f"{key}: saved output unavailable")
            continue
        payload = dict(data=load(source), sha256=sha256(source.read_bytes()).hexdigest())
        snapshot.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
        shutil.copyfile(source, download)


if __name__ == "__main__":
    main()
