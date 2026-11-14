"""Export only aggregate, verified Overview fields from local receipts."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    outputs = ROOT / "outputs"
    inventory = json.loads((outputs / "phase1_inventory.json").read_text(encoding="utf-8"))
    with (outputs / "phase7_real_change_analysis/support.csv").open(newline="", encoding="utf-8") as stream:
        tiles = [row for row in csv.DictReader(stream)
                 if row["scope"] == "tile" and row["field"] == "common_valid"]
    stations = json.loads((outputs / "phase4a_river_feasibility/receipt.json").read_text(encoding="utf-8"))
    payload = {
        "area": inventory["boundary"]["area_km2"],
        "seasons": inventory["collection_counts"],
        "tiles": [{"id": row["group"], "valid": int(row["supported_n"]),
                   "total": int(row["footprint_n"])} for row in tiles],
        "stations": len(stations["stations"]),
    }
    target = ROOT / "frontend/public/local/overview.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
