from streamlit.testing.v1 import AppTest


def test_saved_overlap_view(tmp_path, monkeypatch):
    from scripts.research_dashboard import spatial_results

    folder = tmp_path / "phase7_day2_spatial_patterns"
    folder.mkdir()
    header = "tile,district,split,level,comparison,valid_cells,joint,radar_only,optical_only,neither,jaccard\n"
    (folder / "overlap.csv").write_text(header + "east-94-559,East,train,low,directional_unions,4,1,1,1,1,0.333\n"
                                       + "west-82-563,West,train,low,directional_unions,4,1,1,1,1,0.333\n")
    monkeypatch.setenv("DAY4_FIXTURE", str(tmp_path))
    app = AppTest.from_string(
        "import os\nfrom pathlib import Path\n"
        "from scripts.research_dashboard import spatial_results\n"
        "spatial_results(Path(os.environ['DAY4_FIXTURE']))"
    ).run()
    assert not app.exception
    app.selectbox(key="phase7_district").select("West").run()
    assert not app.exception
    assert app.selectbox(key="phase7_tile").value == "west-82-563"
    assert any("Mining activity is unverified" in item.value for item in app.info)
