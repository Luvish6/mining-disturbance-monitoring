"""Prepare the initial Indian study dataset from the reviewed annotation ledger."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from .annotation import export
from .multitile import prepare_tiles


def prepare_reviewed(workspace, rasters, output, *, boundary, coverage):
    """Revalidate the independent review ledger before the registered-raster handoff."""
    with TemporaryDirectory(prefix="india-reference-") as directory:
        release = Path(directory) / "release"
        summary = export(workspace, release)
        if not summary["real_dataset_ready"]:
            raise ValueError(
                "Reviewed reference export is not ready: "
                f"{summary['accepted_by_class_partition']}; "
                f"{len(summary['issues'])} invalid acceptance records"
            )
        return prepare_tiles(rasters, release / "accepted.geojson", output,
                             boundary=boundary, coverage=coverage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("output")
    parser.add_argument("rasters", nargs="+")
    parser.add_argument("--boundary", required=True, help="Original Meghalaya GAUL district snapshot")
    parser.add_argument("--coverage", required=True, help="Matching successful district coverage receipt")
    args = vars(parser.parse_args())
    prepare_reviewed(**args)


if __name__ == "__main__":
    main()
