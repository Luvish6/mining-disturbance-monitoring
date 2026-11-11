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
PAGES = ("Overview", "Satellite Change Explorer", "River Monitoring",
         "Leshka Feasibility", "Data Quality & Methodology")
SEASONS = ("Nov 2023 – Mar 2024", "Nov 2024 – Mar 2025")
THEME = """
<style>
:root { color-scheme: dark; }
.stApp, [data-testid="stHeader"] { background: #0c1421; color: #e6edf7; }
[data-testid="stSidebar"], [data-testid="stMetric"] { background: #152235; }
.stApp h1, .stApp h2, .stApp h3, [data-testid="stMetricValue"] { color: #f2f7ff; }
.stApp [data-testid="stCaptionContainer"] p { color: #aebed2; }
[data-testid="stSidebar"] label, [data-testid="stWidgetLabel"] label,
[data-testid="stMetricLabel"], [data-testid="stExpander"] summary { color: #dce8f6; }
[data-testid="stMetric"] { padding: 1rem; border: 1px solid #30455d; border-radius: .65rem; }
.stApp a { color: #7cdacf; }
.stApp [data-testid="stMainBlockContainer"] { max-width: 84rem; padding-top: 3.5rem; }
[data-testid="stExpander"] details { border-color: #30455d; }
</style>
"""
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


@st.cache_data(show_spinner=False)
def cached_product(loader_name, path, signature, args, _loader):
    return _loader(path, *args)


def read_product(root, product, filename, loader, *args):
    path = root / PRODUCTS[product][0] / filename
    try:
        stat = path.stat()
        return cached_product(loader.__name__, path, (stat.st_mtime_ns, stat.st_size), args, loader)
    except (OSError, ValueError, TypeError, KeyError):
        unavailable(product, filename)
        return None


@st.cache_data(show_spinner=False)
def image_bytes(path, signature, zoom):
    with Image.open(path) as image:
        if zoom:
            target = max(zoom, image.width)
            image = image.resize((target, target), Image.Resampling.NEAREST)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
    return buffer.getvalue()


def present_image(root, product, filename, caption, width):
    path = root / PRODUCTS[product][0] / filename
    try:
        stat = path.stat()
        content = image_bytes(path, (stat.st_mtime_ns, stat.st_size),
                              width if product == "satellite" else None)
    except (OSError, ValueError):
        unavailable(product, filename)
        return
    with st.container(width=width):
        st.image(content, caption=caption, width="stretch")


def overview(root):
    st.header("Study overview")
    st.write("Explore real satellite observations over the Jaintia Hills and the feasibility of river spectral monitoring.")
    layers = read_product(root, "satellite", "index.html", viewer_layers)
    receipt = read_product(root, "river", "receipt.json", object_file)
    for col, label, value in zip(st.columns(3), ("Study districts", "Satellite layers", "River stations"),
                                 (2, len(layers) if layers else "Unavailable",
                                  len(receipt["stations"]) if receipt and "stations" in receipt else "Unavailable")):
        col.metric(label, value)
    st.caption("East and West Jaintia Hills · Meghalaya")
    st.subheader("Observation windows")
    st.write(f"Before · {SEASONS[0]}  |  After · {SEASONS[1]}")
    st.subheader("Explore the evidence")
    for page, description in zip(PAGES[1:], (
        "Sentinel-2 optical composites and vegetation indices alongside Sentinel-1 radar backscatter.",
        "Dated Sentinel-2 coverage and screened water support across the Lukha and Myntdu stations.",
        "Fixed-footprint support, exclusions and coarse station-cell rainfall.",
        "Collections, acquisition dates, preprocessing rules and local receipts.",
    )):
        with st.container(border=True):
            st.markdown(f"**{page}**")
            st.write(description)
            st.button(f"Open {page}", key=f"open_{page}", on_click=select_page, args=(page,))
    st.caption("Workflow · Local satellite products → quality screening → exploratory visualization → independent reference review pending.")


def select_page(page):
    st.session_state.page = page


def satellite(root):
    st.header("Satellite Change Explorer")
    st.caption("REAL OBSERVATIONS · Phase 3G bounded Sentinel tile")
    st.write(f"Before · {SEASONS[0]}  |  After · {SEASONS[1]}")
    st.caption("The 960 m demonstration tile uses a 30 m display grid. Magnification enlarges the saved pixels.")
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
        stem, _, suffix = selected.rpartition("_")
        before, after = f"{stem}_before", f"{stem}_after"
        if suffix in ("before", "after") and before in choices and after in choices and st.checkbox(
            "Compare before and after", value=True, key="compare_satellite"
        ):
            for col, key in zip(st.columns(2), (before, after)):
                with col:
                    st.caption(choices[key]["period"])
                    present_image(root, "satellite", key + ".png", choices[key]["title"], zoom)
        else:
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
        st.metric("Common valid display pixels", receipt.get("valid_pixels", {}).get("common_valid", "Unavailable"),
                  help="Pixels supported by the saved common-valid mask on the display grid.")
        st.caption("Pixel counts describe preprocessing support for the demonstration tile.")
        st.dataframe([{"Layer": key, "Valid pixels": value}
                      for key, value in receipt.get("valid_pixels", {}).items()], hide_index=True)
        st.dataframe([{"Layer": key, "Minimum": value[0], "Maximum": value[1]}
                      for key, value in receipt.get("count_ranges", {}).items()], hide_index=True)
    st.info("Change layers are exploratory. Atmosphere, shadows, terrain, moisture and seasonal vegetation can affect the signal.")


def river(root):
    st.header("River Monitoring")
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
    selected_season = seasons[season]
    metrics = ("unique_joined_dates", "water_dates", "core_dates")
    for col, field in zip(st.columns(3), metrics):
        col.metric(fields[field], selected_season.get(field, "Unavailable"))
    if all(isinstance(selected_season.get(field), int) for field in fields):
        st.bar_chart([{"Screen": label, "Dates": selected_season[field]} for field, label in fields.items()],
                     x="Screen", y="Dates", horizontal=True, x_label="Distinct UTC dates")
    st.caption("A date without screened water support may reflect masking or limited spatial support. River flow remains unknown.")
    with st.expander("Advanced Satellite Diagnostics", expanded=True):
        river_granules(selected_season)
    if selected_season.get("water_dates", 0):
        present_image(root, "river", f"{key}/{season}_example.png",
                      "Selected dated example · blue screened water · gold heuristic interior", 750)
    st.caption("River lines guide corridor selection. Screened pixels may contain mixed banks, shallow water or residual shadow.")


def river_granules(season):
    diagnostic = st.selectbox("Date support", ("All joined granules", "Valid corridor", "Screened water", "Screened interior"),
                              key="water_support")
    field = {"All joined granules": "available", "Valid corridor": "existing_valid",
             "Screened water": "water", "Screened interior": "core_10m"}[diagnostic]
    records = [r for r in season.get("scenes", [])
               if diagnostic == "All joined granules" or r.get(field, 0) > 0]
    if records:
        fields = {"acquired_utc": "Acquired UTC", "id": "Granule ID",
                  "existing_valid": "Valid corridor pixels", "water": "Screened water pixels",
                  "core_10m": "Interior 10 m pixels", "cloud": "Cloud pixels", "shadow": "Shadow pixels"}
        st.dataframe([{label: r.get(key) for key, label in fields.items()} for r in records], hide_index=True)
    else:
        st.info("No granules meet the selected screen in this window.")


def leshka(root):
    st.header("Leshka Feasibility")
    st.caption("HEURISTIC SCREENING · Phase 4B fixed-footprint comparison readiness")
    receipt = read_product(root, "leshka", "receipt.json", object_file)
    if receipt:
        if receipt.get("reportable") is False:
            st.warning("Seasonal spectral contrast unavailable. The Phase 4B comparison screen did not pass.")
            st.caption("The pilot requires sufficient common interior-water support on the same footprint in both windows.")
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
    st.header("Data Quality & Methodology")
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
    st.set_page_config(page_title="Mining & River Intelligence", layout="wide")
    st.markdown(THEME, unsafe_allow_html=True)
    root = Path(os.environ.get("RESEARCH_DASHBOARD_OUTPUTS", Path(__file__).resolve().parents[1] / "outputs"))
    st.title("Mining & River Intelligence")
    st.caption("Satellite-Based Environmental Monitoring — Meghalaya · Research Prototype")
    with st.sidebar:
        st.subheader("Research Prototype")
        page = st.radio("Research pages", PAGES, key="page")
    st.warning("**Research validation status**\n\n" + "\n".join(f"- {line}" for line in STATUS))
    dict(zip(PAGES, (overview, satellite, river, leshka, provenance)))[page](root)


if __name__ == "__main__":
    main()
