
"""Phase 1: Earth Engine connection, study-area and dataset inventory."""

import argparse
import json
from pathlib import Path

from src.gee_setup import initialize
from src.study_area import get_study_area, verify_boundary
from src.data_inventory import inventory


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1 satellite dataset inventory"
    )
    parser.add_argument(
        "--authenticate",
        action="store_true",
        help="Authenticate with Google Earth Engine"
    )
    args = parser.parse_args()

    # 1. Initialize Google Earth Engine
    initialize(authenticate=args.authenticate)
    print("Earth Engine initialized successfully!")

    # 2. Load verified GAUL 2025 district boundaries
    fc = get_study_area()
    boundary = verify_boundary(fc)

    print("Boundary source: FAO/GAUL/2025/level2")

    # 3. Collect boundary metadata
    boundary_info = {
        "source": "FAO/GAUL/2025/level2",
        "districts": [
            "East Jaintia Hills",
            "West Jaintia Hills"
        ],
        "area_km2": round(
            boundary.area(maxError=100).divide(1e6).getInfo(),
            2
        )
    }

    print(
        "Boundary check:",
        json.dumps(boundary_info, indent=2)
    )

    # 4. Check satellite dataset availability
    print("Checking satellite image counts...")

    counts = inventory(boundary)

    print(json.dumps(counts, indent=2))

    # 5. Save report
    report = {
        "boundary": boundary_info,
        "collection_counts": counts,
        "warning": (
            "Scene counts indicate dataset availability only. "
            "They do not guarantee cloud-free coverage."
        )
    }

    output = Path("outputs/phase1_inventory.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print(f"Report saved: {output}")


if __name__ == "__main__":
    main()
