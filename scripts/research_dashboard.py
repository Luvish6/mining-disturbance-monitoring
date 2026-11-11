"""Local Streamlit dashboard for existing Phase 3G and Phase 4 evidence."""
import csv
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import re

from PIL import Image
import streamlit as st

PRODUCTS = {
    "satellite": ("phase3g_visualization", "phase3g_visualization.py"),
    "river": ("phase4a_river_feasibility", "phase4a_river.py"),
    "leshka": ("phase4b_leshka_spectral_pilot", "phase4b_leshka.py"),
}
PAGES = ("Satellite change", "River observations", "Leshka feasibility", "Provenance & limits")
STATUS = (
    "No admitted real mining positive or negative labels.",
    "No real trained mining classifier or held-out accuracy.",
    "No validated river degradation or mining-to-river causal attribution.",
)
STATION_NAMES = {
    "Lukha-Khaddum-4315": "Lukha · Khaddum",
    "Lukha-Sunapur-3376": "Lukha · Sunapur",
    "Myntdu-Mihmyntdu-4316": "Myntdu · Mihmyntdu",
    "Myntdu-Leshka-3379": "Myntdu · Leshka",
}


def object_file(path):
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError("Expected an object")
    return result


def table_file(path, fields):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not set(fields).issubset(reader.fieldnames or []):
            raise ValueError("Missing table columns")
        return list(reader)


def viewer_layers(path):
    """Reuse only the Phase 3G manifest, leaving the original viewer script inert."""
    match = re.search(r"const layers = (\[.*?\]);", path.read_text(encoding="utf-8"), re.S)
    if not match:
        raise ValueError("Missing Phase 3G layer manifest")
    layers = json.loads(match.group(1))
    if not layers or any(
        not re.fullmatch(r"[a-zA-Z0-9_]+", layer["key"])
        or not isinstance(layer["colors"], list)
        or any(not re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in layer["colors"])
        or not all(isinstance(layer[k], str) for k in ("title", "period", "legend"))
        for layer in layers
    ):
        raise ValueError("Invalid Phase 3G layer manifest")
    return layers


def unavailable(product, filename):
    folder, script = PRODUCTS[product]
    st.warning(f"Local evidence unavailable or unreadable ({folder}/{filename}).")
    st.caption("Restore the existing output or regenerate it separately with Earth Engine. Use a new destination if the original folder already exists.")
    st.code(f"python -B scripts/{script} --output outputs/{folder}", language="powershell")
    if product == "leshka":
        st.caption("Phase 4B requires the Phase 4A receipt. The daily ledger can be rebuilt with the saved local verifier.")


def read_product(root, product, filename, loader, *args):
    path = root / PRODUCTS[product][0] / filename
    try:
        return loader(path, *args)
    except (OSError, ValueError, TypeError, KeyError):
        unavailable(product, filename)
        return None


def present_image(root, product, filename, caption, width):
    path = root / PRODUCTS[product][0] / filename
    try:
        with Image.open(path) as image:
            if product == "satellite":
                target = max(width, image.width)
                image = image.resize((target, target), Image.Resampling.NEAREST)
            buffer = BytesIO()
            image.save(buffer, format="PNG")
    except (OSError, ValueError):
        unavailable(product, filename)
        return
    st.image(buffer.getvalue(), caption=caption, width=width)


def satellite(root):
    st.header("Satellite change")
    st.caption("REAL OBSERVATIONS · Phase 3G bounded Sentinel tile")
    receipt = read_product(root, "satellite", "receipt.json", object_file)
    layers = read_product(root, "satellite", "index.html", viewer_layers)
    if layers:
        choices = {layer["key"]: layer for layer in layers}
        selected = st.selectbox("Satellite layer", choices,
                                format_func=lambda key: choices[key]["title"], key="satellite_layer")
        zoom = st.select_slider("Display magnification", (320, 480, 640),
                                value=480, format_func=lambda size: f"{size // 32}× 30 m display grid")
        layer = choices[selected]
        st.caption(layer["period"])
        present_image(root, "satellite", selected + ".png", layer["title"], zoom)
        if layer["colors"]:
            gradient = ",".join(layer["colors"])
            st.markdown(
                f'<div aria-hidden="true" style="height:10px;max-width:{zoom}px;'
                f'background:linear-gradient(90deg,{gradient});border-radius:4px"></div>',
                unsafe_allow_html=True)
        st.caption(layer["legend"])
    if receipt:
        st.subheader("Preprocessing support")
        st.caption("Pixel counts describe preprocessing support for the demonstration tile.")
        st.dataframe([{"Layer": key, "Valid pixels": value}
                      for key, value in receipt.get("valid_pixels", {}).items()], hide_index=True)
        st.dataframe([{"Layer": key, "Minimum": value[0], "Maximum": value[1]}
                      for key, value in receipt.get("count_ranges", {}).items()], hide_index=True)
    st.info("Change layers are exploratory. Atmosphere, shadows, terrain, moisture and seasonal vegetation can affect the signal.")


def river(root):
    st.header("River observations")
    st.caption("HEURISTIC SCREENING · Phase 4A water-pixel support on real Sentinel-2 granules")
    receipt = read_product(root, "river", "receipt.json", object_file)
    if not receipt or not receipt.get("stations"):
        return
    stations = receipt["stations"]
    fields = {"unique_joined_dates": "Joined dates", "valid_dates": "Valid dates",
              "water_dates": "Water dates", "core_dates": "Interior dates",
              "wider_core_dates": "Wider-clearance dates"}
    summary = [
        {"Station": STATION_NAMES.get(key, key), "Window": season.title(),
         **{heading: values.get(field) for field, heading in fields.items()}}
        for key, station in stations.items() for season, values in station.get("seasons", {}).items()
    ]
    st.dataframe(summary, hide_index=True)
    key = st.selectbox("Monitoring station", list(stations),
                       format_func=lambda k: STATION_NAMES.get(k, k), key="station")
    st.caption("Counts above use distinct UTC dates. The dated inspection below lists individual granules, including repeat dates.")
    seasons = stations[key].get("seasons", {})
    if not seasons:
        st.warning("No seasonal diagnostics in this station receipt.")
        return
    season = st.radio("Season", list(seasons), horizontal=True, key="river_season")
    diagnostic = st.selectbox("Date support", ("All joined granules", "Valid corridor", "Screened water", "Screened interior"),
                              key="water_support")
    field = {"All joined granules": "available", "Valid corridor": "existing_valid",
             "Screened water": "water", "Screened interior": "core_10m"}[diagnostic]
    records = [r for r in seasons[season].get("scenes", [])
               if diagnostic == "All joined granules" or r.get(field, 0) > 0]
    if records:
        st.dataframe([{k: r.get(k) for k in ("acquired_utc", "id", "existing_valid",
                       "water", "core_10m", "cloud", "shadow")} for r in records], hide_index=True)
    else:
        st.info("No granules meet the selected screen in this window.")
    if seasons[season].get("water_dates", 0):
        present_image(root, "river", f"{key}/{season}_example.png",
                      "Selected dated example · blue screened water · gold heuristic interior", 750)
    st.caption("River lines guide corridor selection. Screened pixels may contain mixed banks, shallow water or residual shadow.")


def leshka(root):
    st.header("Leshka feasibility")
    st.caption("HEURISTIC SCREENING · Phase 4B fixed-footprint comparison readiness")
    receipt = read_product(root, "leshka", "receipt.json", object_file)
    if receipt:
        if receipt.get("reportable") is False:
            st.warning("Seasonal spectral contrast unavailable. The Phase 4B comparison screen did not pass.")
        else:
            st.info("This prototype displays feasibility diagnostics only. No seasonal spectral contrast or water-quality trend is shown.")
        cols = st.columns(3)
        for col, label, value in zip(cols, ("Common 10 m cells", "Pilot minimum", "Matched date pairs"),
                (receipt.get("common_pixels"), receipt.get("analysis_rules", {}).get("minimum_common_pixels"),
                 len(receipt["matched_pairs"]) if "matched_pairs" in receipt else None)):
            col.metric(label, "Unavailable" if value is None else value)
        st.dataframe([{"Footprint test": label, "Cells": receipt.get(key)}
                      for key, label in (("strict_pixels", "Stricter NDWI"), ("wider_pixels", "Wider clearance"),
                                         ("historical_pixels", "Historical water occurrence"))], hide_index=True)
        if receipt.get("native_support"):
            st.dataframe([{"Scene": scene, "Whole SCL cells (20 m)": v.get("SCL"),
                           "Whole B11 cells (20 m)": v.get("B11")}
                          for scene, v in receipt["native_support"].items()], hide_index=True)
        if receipt.get("matched_pairs"):
            st.dataframe([{"Before date": a, "After date": b} for a, b in receipt["matched_pairs"]], hide_index=True)
        present_image(root, "leshka", "fixed_water_support.png", "Yellow outlines the screened fixed footprint.", 580)
    rows = read_product(root, "leshka", "observations.csv", table_file,
                        ("acquired_utc", "status", "core_10m", "rain_1d_mm", "rain_3d_mm", "rain_7d_mm"))
    if rows:
        reasons = sorted({r["status"] for r in rows})
        selected = st.selectbox("Observation status", ["All statuses", *reasons], key="leshka_status")
        shown = [r for r in rows if selected == "All statuses" or r["status"] == selected]
        st.subheader("Exclusions and rainfall availability")
        st.caption("CHIRPS estimates refer to the coarse station cell. Blank values indicate missing data.")
        st.dataframe([{"Status": reason, "Granules": sum(r["status"] == reason for r in rows)}
                      for reason in reasons], hide_index=True)
        st.dataframe([{k: r.get(k) or None for k in ("acquired_utc", "status", "core_10m",
                          "rain_1d_mm", "rain_3d_mm", "rain_7d_mm")} for r in shown], hide_index=True)
    with st.expander("Daily coverage and rainfall ledger"):
        ledger_fields = ("date", "season", "joined_granules", "interior_granules",
                         "matched", "status", "rain_1d_mm", "rain_3d_mm", "rain_7d_mm")
        ledger = read_product(root, "leshka", "daily_availability.csv", table_file, ledger_fields)
        if ledger:
            st.dataframe([{key: row[key] or None for key in ledger_fields}
                          for row in ledger], hide_index=True)
    st.info("The sampled waterbody may be regulated. These diagnostics do not establish a water-quality trend.")


def provenance(root):
    st.header("Provenance & limits")
    st.markdown(
        "**Real observations** are locally saved Sentinel measurements and acquisition receipts. "
        "**Heuristic screening** describes mask-based support. "
        "**Synthetic fixtures** are used only in software tests. "
        "**Unavailable results** have no displayed substitute.")
    for product, title in (("satellite", "Phase 3G satellite"), ("river", "Phase 4A river"),
                           ("leshka", "Phase 4B Leshka")):
        with st.expander(title, expanded=product == "satellite"):
            st.code(f"outputs/{PRODUCTS[product][0]}/receipt.json")
            receipt = read_product(root, product, "receipt.json", object_file)
            if not receipt:
                continue
            collections = receipt.get("collections", receipt.get("sources", receipt.get("source_collections", [])))
            if product == "satellite":
                st.write("Source collections", collections)
                st.json({key: receipt.get(key) for key in ("seasons", "config", "source_pixel_spacing_m", "band_definitions")})
                rows = []
                for index, source in enumerate(receipt.get("sources", [])):
                    for sensor in ("s1", "s2"):
                        for scene, time in zip(source.get(f"{sensor}_ids", []), source.get(f"{sensor}_time_start_ms", [])):
                            rows.append({"Season": ("Before", "After")[index], "Sensor": sensor.upper(),
                                         "Scene": scene, "Acquired UTC": datetime.fromtimestamp(time / 1000, timezone.utc).isoformat()})
                if rows:
                    st.dataframe(rows, hide_index=True)
            else:
                st.write("Source collections", collections)
                st.write("Sentinel-2 red and green are native 10 m bands. SCL and B11 are native 20 m bands. Historical JRC water is 30 m.")
                st.write("Existing cloud-probability, SCL and edge masks precede the water and interior screens. See dated records on the river pages.")
                if product == "leshka":
                    st.json(receipt.get("analysis_rules", {}))
                    st.write(receipt.get("rainfall_geometry", "Rainfall geometry unavailable."))
    st.caption("Research protocols: docs/reference/REAL_REFERENCE_PROTOCOL.md and docs/reference/PHASE4_INPUT_CONTRACT.md")


def main():
    st.set_page_config(page_title="Jaintia Hills research dashboard", layout="wide")
    root = Path(os.environ.get("RESEARCH_DASHBOARD_OUTPUTS", Path(__file__).resolve().parents[1] / "outputs"))
    st.title("Jaintia Hills research dashboard")
    st.caption("Phase 5A · Offline research prototype")
    with st.sidebar:
        page = st.radio("Research pages", PAGES, key="page")
    st.warning("**Research validation status**\n\n" + "\n".join(f"- {line}" for line in STATUS))
    dict(zip(PAGES, (satellite, river, leshka, provenance)))[page](root)


if __name__ == "__main__":
    main()
