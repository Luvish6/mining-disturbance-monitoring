"""Offline dashboard for saved satellite and river evidence."""
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
    "day1": ("phase7_real_change_analysis", "phase7_real_change.py"),
    "day2": ("phase7_day2_spatial_patterns", "phase7_day2_spatial.py"),
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
.st-key-portal_header { background: #152235; border-top: 3px solid #63c7bb;
    padding: .75rem 1.3rem .9rem; border-radius: .6rem; }
.st-key-portal_header h1 { font-size: clamp(1.7rem, 3vw, 2.55rem); padding: .15rem 0; }
.stApp a { color: #7cdacf; }
.stApp [data-testid="stMainBlockContainer"] { max-width: 84rem; padding-top: 2.6rem; }
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
    if product in ("day1", "day2"):
        st.caption("Restore the saved Phase 7 result or rebuild it offline from Phase 6B.")
        st.code(f"python -B -m scripts.{Path(script).stem} --output outputs/{folder}")
        return
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
    overlap_path = root / PRODUCTS["day2"][0] / "overlap.csv"
    rows = read_product(root, "day2", "overlap.csv", table_file,
                        ("tile", "level", "comparison", "valid_cells")) if overlap_path.is_file() else []
    support = {r["tile"]: int(r["valid_cells"]) for r in rows or []
               if r["level"] == "low" and r["comparison"] == "directional_unions"
               and r["valid_cells"].isdigit()}
    metrics = (("Study districts", 2), ("Phase 7 tiles", len(support) if support else "Unavailable"),
               ("Common-valid cells", f"{sum(support.values()):,}" if support else "Unavailable"),
               ("River stations", len(receipt["stations"]) if receipt and "stations" in receipt else "Unavailable"))
    for col, (label, value) in zip(st.columns(4), metrics):
        col.metric(label, value)
    st.caption(f"East and West Jaintia Hills · {len(layers) if layers else 'Unavailable'} Phase 3G demonstration layers")
    st.info("Common-valid cells meet the saved preprocessing masks within the sampled footprints.")
    st.subheader("Observation windows")
    st.write(f"Before · {SEASONS[0]}  |  After · {SEASONS[1]}")
    st.subheader("Explore the evidence")
    for col, page, description in zip(st.columns(4), PAGES[1:], (
        "Sentinel-2 optical composites and vegetation indices alongside Sentinel-1 radar backscatter.",
        "Dated Sentinel-2 coverage and screened water support across the Lukha and Myntdu stations.",
        "Fixed-footprint support, exclusions and coarse station-cell rainfall.",
        "Collections, acquisition dates, preprocessing rules and local receipts.",
    )):
        with col, st.container(border=True):
            st.markdown(f"**{page}**")
            st.write(description)
            st.button(f"Open {page}", key=f"open_{page}", on_click=select_page, args=(page,))
    st.caption("Workflow · Local satellite products → quality screening → exploratory visualization → independent reference review pending.")


def select_page(page):
    st.session_state.page = page


def satellite(root):
    st.subheader("Phase 3G demonstration tile")
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


@st.cache_data(show_spinner=False)
def focused_map(path, signature, layer, level):
    """Render a saved panel without re-running any satellite or threshold analysis."""
    # Day 2 sheets are 1800 × 1200 with a fixed 2 × 3 annotated layout.
    panels = {"dVV": (0, 0), "dVH": (1, 0), "dNDVI": (2, 0), "dNDTI": (0, 1),
              "Directional overlap low": (1, 1), "Directional overlap high": (2, 1)}
    if layer == "Directional overlap":
        layer = f"{layer} {level}"
    with Image.open(path) as saved:
        if saved.size != (1800, 1200):
            raise ValueError("Unexpected Day 2 panel dimensions")
        col, row = panels[layer]
        panel = saved.crop((600 * col, 96 if row == 0 else 651,
                            600 * (col + 1), 560 if row == 0 else 1090))
        buffer = BytesIO()
        panel.save(buffer, "PNG")
    return buffer.getvalue()


def spatial_results(root):
    st.subheader("Six-tile seasonal change")
    st.info("Exploratory satellite change patterns. Mining activity is unverified.")
    st.caption("Nov 2023–Mar 2024 versus Nov 2024–Mar 2025 · after minus before · 30 m grid")
    fields = ("tile", "district", "split", "level", "comparison", "valid_cells",
              "joint", "radar_only", "optical_only", "neither", "jaccard")
    rows = read_product(root, "day2", "overlap.csv", table_file, fields)
    if not rows:
        return
    district_col, tile_col, layer_col, threshold_col = st.columns(4)
    district = district_col.selectbox("District", sorted({r["district"] for r in rows}), key="phase7_district")
    tiles = sorted({r["tile"] for r in rows if r["district"] == district
                    and re.fullmatch(r"(east|west)-[0-9]+-[0-9]+", r["tile"])})
    if not tiles:
        st.warning("No verified tile IDs in the selected district.")
        return
    tile = tile_col.selectbox("Change tile", tiles, key="phase7_tile")
    layer = layer_col.selectbox("Map layer", ("All layers", "dVV", "dVH", "dNDVI", "dNDTI", "Directional overlap"),
                               key="phase7_layer")
    level = threshold_col.selectbox("Threshold", ("low", "middle", "high"),
                                    format_func=str.title, key="phase7_threshold")
    selected = [r for r in rows if r["tile"] == tile]
    st.caption(f"Frozen partition · {selected[0]['split']}")
    filename = f"{tile}_patterns.png"
    with st.container(border=True):
        if layer == "All layers" or (layer == "Directional overlap" and level == "middle"):
            present_image(root, "day2", filename, "Saved Day 2 map sheet · EPSG:32646 · north up", 1100)
            if layer == "Directional overlap":
                st.caption("The saved map sheet contains low and high overlays. Middle-threshold results are shown below.")
        else:
            path = root / PRODUCTS["day2"][0] / filename
            try:
                stat = path.stat()
                st.image(focused_map(path, (stat.st_mtime_ns, stat.st_size), layer, level),
                         caption=f"{tile} · EPSG:32646 · north up", width=690)
                if layer == "Directional overlap":
                    st.caption("Grey · neither | Blue · radar only | Amber · optical only | Purple · both")
            except (OSError, ValueError):
                unavailable("day2", filename)
    st.caption("Radar decrease in VV or VH. Optical decrease in NDVI or increase in NDTI. "
               "Low, middle and high cutoffs are 1/2/3 dB and 0.03/0.06/0.09 optical units.")
    comparisons = sorted({r["comparison"] for r in selected})
    comparison = st.selectbox("Overlap comparison", comparisons,
                              index=comparisons.index("directional_unions") if "directional_unions" in comparisons else 0)
    order = {"low": 1, "middle": 2, "high": 3}
    data = sorted((r for r in selected if r["comparison"] == comparison),
                  key=lambda row: order.get(row["level"], 4))
    try:
        graph = [{"Threshold": f"{order[r['level']]} · {r['level']}",
                  "Jaccard": float(r["jaccard"]) if r["jaccard"] else None} for r in data]
    except (KeyError, ValueError):
        unavailable("day2", "overlap.csv")
        return
    if any(r["Jaccard"] is not None for r in graph):
        import altair as alt
        chart = alt.Chart(alt.Data(values=graph)).mark_bar(color="#59bdb2").encode(
            x=alt.X("Threshold:N", title="Descriptive cutoff"),
            y=alt.Y("Jaccard:Q", title="Intersection / union", scale=alt.Scale(domain=[0, 1])),
            tooltip=[alt.Tooltip("Threshold:N"), alt.Tooltip("Jaccard:Q", format=".3f")],
        ).properties(height=210)
        st.altair_chart(chart)
    selected_row = next((r for r in data if r["level"] == level), None)
    if selected_row:
        for col, label, key in zip(st.columns(3), ("Joint cells", "Radar only", "Optical only"),
                                   ("joint", "radar_only", "optical_only")):
            col.metric(label, selected_row[key], help=f"{level.title()} cutoff")
    st.caption("Jaccard is intersection divided by union. These descriptive thresholds were used for sensitivity analysis.")
    st.dataframe([{key: row[key] for key in fields[3:] if key not in ("block", "comparison")}
                  for row in data], hide_index=True)
    components = read_product(root, "day2", "pattern_sizes.csv", table_file,
                              ("tile", "level", "pattern", "components", "largest_cells"))
    if components:
        st.dataframe([{k: r[k] for k in ("level", "components", "largest_cells")}
                      for r in components if r["tile"] == tile and r["pattern"] == "joint"], hide_index=True)
    for filename, title, columns in (
        ("distributions.csv", "Signed change statistics",
         ("band", "unit", "n", "median", "p05", "p95")),
        ("support.csv", "Observation quality",
         ("field", "footprint_n", "supported_n", "excluded_n", "count_min", "count_median", "count_max")),
    ):
        st.subheader(title)
        records = read_product(root, "day1", filename, table_file, ("scope", "group", *columns))
        if records:
            st.dataframe([{key: r[key] for key in columns} for r in records
                          if r["scope"] == "tile" and r["group"] == tile], hide_index=True)
    with st.expander("How to read the satellite layers"):
        st.write("Sentinel-1 synthetic aperture radar (SAR) measures microwave backscatter in VV and VH, "
                 "reported in decibels. Sentinel-2 NDVI compares near-infrared and red reflectance. "
                 "NDTI compares red and green reflectance. Both indices are unitless. "
                 "Vegetation, moisture, terrain and atmosphere can influence the observed differences.")
    st.caption("Support counts describe the local preprocessing masks. Land NDTI is a relative red–green index.")


def satellite_explorer(root):
    st.header("Satellite Change Explorer")
    spatial, legacy = st.tabs(["Phase 7 six-tile results", "Phase 3G demonstration tile"])
    with spatial:
        if (root / PRODUCTS["day2"][0]).exists():
            spatial_results(root)
        else:
            st.caption("Phase 7 outputs are unavailable. Restore them or run the offline rebuild.")
            st.code("python -B -m scripts.phase7_day2_spatial --output outputs/phase7_day2_spatial_patterns")
    with legacy:
        satellite(root)


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
    key = st.selectbox("Monitoring station", list(stations),
                       format_func=lambda k: STATION_NAMES.get(k, k), key="station")
    st.caption("The station summaries count distinct UTC dates. The dated inspection below lists individual granules, including repeat dates.")
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
    with st.expander("All station and season summaries"):
        st.dataframe(summary, hide_index=True)
    with st.expander("Dated satellite observations"):
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
        present_image(root, "leshka", "fixed_water_support.png", "Yellow outlines the screened fixed footprint.", 580)
        with st.expander("Footprint sensitivity and matched dates"):
            leshka_support(receipt)
    leshka_observations(root)


def leshka_support(receipt):
    st.dataframe([{"Footprint test": label, "Cells": receipt.get(key)}
                  for key, label in (("strict_pixels", "Stricter NDWI"), ("wider_pixels", "Wider clearance"),
                                     ("historical_pixels", "Historical water occurrence"))], hide_index=True)
    if receipt.get("native_support"):
        st.dataframe([{"Scene": scene, "Whole SCL cells (20 m)": v.get("SCL"),
                       "Whole B11 cells (20 m)": v.get("B11")}
                      for scene, v in receipt["native_support"].items()], hide_index=True)
    if receipt.get("matched_pairs"):
        st.dataframe([{"Before date": a, "After date": b} for a, b in receipt["matched_pairs"]], hide_index=True)


def leshka_observations(root):
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
        with st.expander(title):
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
    with st.container(key="portal_header"):
        st.caption("MEGHALAYA  /  ENVIRONMENTAL MONITORING")
        st.title("Mining & River Intelligence")
        st.caption("Satellite observation portal · B.Tech research prototype")
    with st.sidebar:
        st.subheader("Monitoring portal")
        st.caption("East & West Jaintia Hills")
        page = st.radio("Research pages", PAGES, key="page")
    with st.expander("Research validation status", expanded=page == "Overview"):
        st.warning(" ".join(STATUS))
    dict(zip(PAGES, (overview, satellite_explorer, river, leshka, provenance)))[page](root)


if __name__ == "__main__":
    main()
