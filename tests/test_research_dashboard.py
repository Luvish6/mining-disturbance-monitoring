"""Dashboard software fixtures. Measurements here are synthetic test values."""
import json
from pathlib import Path
import runpy

from PIL import Image
import pytest
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

APP = Path(__file__).resolve().parents[1] / "scripts" / "research_dashboard.py"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def products(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_DASHBOARD_OUTPUTS", str(tmp_path))
    satellite = tmp_path / "phase3g_visualization"
    write_json(satellite / "receipt.json", {"valid_pixels": {"common_valid": 1},
        "count_ranges": {"sar_before_count": [2, 2]}, "collections": ["fixture"]})
    layers = [
        {"key": "optical_before", "title": "Fixture before", "period": "fixture dates", "legend": "test RGB", "colors": []},
        {"key": "dVV", "title": "Fixture change", "period": "fixture dates", "legend": "test dB", "colors": ["#123456"]},
    ]
    (satellite / "index.html").write_text(f"const layers = {json.dumps(layers)};", encoding="utf-8")
    for layer in layers:
        Image.new("RGB", (32, 32)).save(satellite / f"{layer['key']}.png")
    station = {"seasons": {"before": {"unique_joined_dates": 1, "valid_dates": 1,
        "water_dates": 0, "core_dates": 0, "scenes": [{"acquired_utc": "fixture UTC",
        "id": "fixture", "existing_valid": 1, "water": 0, "core_10m": 0}]}}}
    write_json(tmp_path / "phase4a_river_feasibility" / "receipt.json",
               {"stations": {"Lukha-Khaddum-4315": station, "Myntdu-Leshka-3379": station}})
    leshka = tmp_path / "phase4b_leshka_spectral_pilot"
    write_json(leshka / "receipt.json", {"reportable": False, "common_pixels": 2,
        "analysis_rules": {"minimum_common_pixels": 25}, "matched_pairs": [["fixture", "fixture"]]})
    Image.new("RGB", (8, 8)).save(leshka / "fixed_water_support.png")
    (leshka / "observations.csv").write_text(
        "acquired_utc,status,core_10m,rain_1d_mm,rain_3d_mm,rain_7d_mm,common_red\n"
        "fixture,insufficient fixed support,2,0,,5,DO_NOT_RENDER\n", encoding="utf-8")
    return tmp_path


def test_loaders_and_manifest_validation(products, tmp_path):
    module = runpy.run_path(str(APP))
    satellite = products / "phase3g_visualization"
    assert module["object_file"](satellite / "receipt.json")["valid_pixels"]["common_valid"] == 1
    assert len(module["viewer_layers"](satellite / "index.html")) == 2
    unsafe = tmp_path / "unsafe.html"
    unsafe.write_text('const layers = [{"key":"../other","colors":[]}];', encoding="utf-8")
    with pytest.raises(ValueError):
        module["viewer_layers"](unsafe)
    with pytest.raises(ValueError):
        module["table_file"](products / "phase4b_leshka_spectral_pilot" / "observations.csv", ["absent"])


def test_navigation_and_scientific_guardrails(products):
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    status = app.warning[0].value
    assert "No admitted real mining positive or negative labels" in status
    assert "No real trained mining classifier or held-out accuracy" in status
    assert "No validated river degradation or mining-to-river causal attribution" in status
    assert app.header[0].value == "Study overview"
    app.button(key="open_Satellite Change Explorer").click().run()
    app.selectbox(key="satellite_layer").select("dVV").run()
    assert not app.exception and any("test dB" in c.value for c in app.caption)
    app.radio(key="page").set_value("River Monitoring").run()
    app.selectbox(key="station").select("Myntdu-Leshka-3379").run()
    app.selectbox(key="water_support").select("Screened interior").run()
    assert not app.exception and any("No granules meet" in i.value for i in app.info)
    app.radio(key="page").set_value("Leshka Feasibility").run()
    assert not app.exception
    assert any("comparison screen did not pass" in w.value for w in app.warning)
    assert all("common_red" not in frame.value.columns for frame in app.dataframe)
    assert not any("DO_NOT_RENDER" in str(frame.value) for frame in app.dataframe)
    app.radio(key="page").set_value("Data Quality & Methodology").run()
    assert not app.exception
    assert any("Synthetic fixtures" in item.value for item in app.markdown)


def test_missing_and_unreadable_outputs(monkeypatch, tmp_path):
    monkeypatch.setenv("RESEARCH_DASHBOARD_OUTPUTS", str(tmp_path))
    app = AppTest.from_file(str(APP)).run()
    for page in ("Satellite Change Explorer", "River Monitoring", "Leshka Feasibility", "Data Quality & Methodology"):
        app.radio(key="page").set_value(page).run()
        assert not app.exception
        assert any("Local evidence unavailable" in w.value for w in app.warning)
        assert any("--output" in block.value for block in app.code)
    corrupt = tmp_path / "phase4a_river_feasibility" / "receipt.json"
    corrupt.parent.mkdir()
    corrupt.write_text("{invalid", encoding="utf-8")
    app.radio(key="page").set_value("River Monitoring").run()
    assert not app.exception
    assert any("unreadable" in w.value for w in app.warning)
