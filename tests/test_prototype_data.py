from pyproj import Transformer
from rasterio import Affine
from shapely import transform
from shapely.geometry import box, mapping
import pytest

from scripts.prototype_data import build_site, review_polygons


def test_review_outline_uses_exact_pixel_coordinates_and_review_gate():
    wgs = Transformer.from_crs(32644, 4326, always_xy=True)
    projected = box(663900, 2470740, 663930, 2470770)
    geometry = transform(projected, wgs.transform, interleaved=False)
    lon, lat = wgs.transform(projected.centroid.x, projected.centroid.y)
    feature = dict(id="fixture", geometry=mapping(geometry), properties=dict(
        status="REVIEW_REQUIRED", evidence_status="UNKNOWN", eligible_observation_count=0,
        longitude=lon, latitude=lat, raster_sha256="fixture", area_m2=900, mean_score=.5,
    ))
    grid = Affine(30, 0, 663870, 0, -30, 2470800)
    bounds = (663870, 2470700, 664000, 2470800)
    [row] = review_polygons([feature], bounds, "EPSG:32644", grid, "fixture")
    assert {tuple(round(coord) for coord in vertex) for vertex in row["rings"][0]} == {
        (1, 1), (1, 2), (2, 1), (2, 2)
    }
    feature["properties"]["eligible_observation_count"] = 1
    with pytest.raises(ValueError, match="operational status"):
        review_polygons([feature], bounds, "EPSG:32644", grid, "fixture")


def test_missing_site_has_no_zero_count_placeholder(tmp_path):
    assert build_site(tmp_path, tmp_path, "gevra") is None


def test_portal_removes_previous_snapshot_on_provenance_error(tmp_path, monkeypatch):
    from scripts import prototype_data

    monkeypatch.chdir(tmp_path)
    target = tmp_path / "frontend/public/local/india-sites"
    target.mkdir(parents=True)
    snapshot = target / "gevra.json"
    snapshot.write_text("old")

    def reject(*args):
        raise ValueError("Scene inventory differs")

    monkeypatch.setattr(prototype_data, "build_site", reject)
    with pytest.raises(ValueError, match="Scene inventory"):
        prototype_data.main()
    assert not snapshot.exists()


def test_meghalaya_snapshot_removed_when_source_missing(tmp_path, monkeypatch):
    from scripts import phase8_river_data

    monkeypatch.chdir(tmp_path)
    snapshot = tmp_path / "frontend/public/local/river.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("old")
    with pytest.raises(FileNotFoundError):
        phase8_river_data.main()
    assert not snapshot.exists()
