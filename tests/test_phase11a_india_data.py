import pytest

from src.phase3 import india_data


def test_unready_review_stops_before_raster_access(monkeypatch, tmp_path):
    monkeypatch.setattr(india_data, "export", lambda *args: dict(
        real_dataset_ready=False, accepted_by_class_partition={"train": [0, 0]}, issues=[]))
    with pytest.raises(ValueError, match="Reviewed reference export is not ready"):
        india_data.prepare_reviewed("workspace", ["missing.tif"], tmp_path / "dataset",
                                    boundary="districts", coverage="coverage")


def test_review_export_is_the_input_to_existing_multitile_loader(monkeypatch, tmp_path):
    def export(workspace, release):
        assert workspace == "workspace"
        release.mkdir()
        (release / "accepted.geojson").write_text("reviewed")
        return {"real_dataset_ready": True}

    def prepare(rasters, labels, output, **settings):
        assert rasters == ["registered.tif"]
        assert labels.read_text() == "reviewed"
        assert settings == {"boundary": "districts", "coverage": "coverage"}
        return output

    monkeypatch.setattr(india_data, "export", export)
    monkeypatch.setattr(india_data, "prepare_tiles", prepare)
    result = tmp_path / "dataset"
    assert india_data.prepare_reviewed("workspace", ["registered.tif"], result,
                                       boundary="districts", coverage="coverage") == result
