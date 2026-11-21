"""Phase 23K: screen one PlanetScope SR 8-band + UDM2 scene for interior river water in the preregistered
Phase 4A station windows (720 m) and, only if the gates pass, report descriptive single-date NDTI.

Raw Planet data stays in git-ignored outputs/phase23k_planet/<scene_id>/; only derived statistics are written
to docs/reports/phase23k-<scene_id>-screen.json. Zero Earth Engine requests, no downloads.

  python -B -m scripts.phase23k_planet_screen outputs/phase23k_planet/<scene_id>
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt, label

from scripts.phase22p_sar_corroboration import save, sha

PHASE4A = Path("outputs/phase4a_river_feasibility")
REACHES = Path("outputs/phase22o_river/cache/hydrosheds.json")
SR_SCALE = 1e-4                  # Planet SR GeoTIFF: reflectance x 10,000 (checked against value ranges below)
ERODE_PX, MIN_INTERIOR = 2, 25   # preregistered: 2-pixel (6 m) erosion, >= 25 interior pixels
SENS = dict(ndwi_gt_0_1=dict(ndwi_gt=0.1), erode_1px=dict(erode=1), min_interior_50=dict(min_interior=50))
WINDOWS = {"Lukha-Sunapur-3376": "downstream", "Lukha-Khaddum-4315": "upstream"}


def clear_mask(udm):
    """UDM2 band order: clear, snow, shadow, haze_light, haze_heavy, cloud, confidence, udm1."""
    clear, snow, shadow, hl, hh, cloud = (udm[i] for i in range(6))
    return (clear == 1) & (snow == 0) & (shadow == 0) & (hl == 0) & (hh == 0) & (cloud == 0)


def ndi(a, b):
    a, b = a.astype(float), b.astype(float)
    den = a + b
    return np.divide(a - b, den, out=np.full(a.shape, np.nan), where=den > 0)


def interior(water, erode=ERODE_PX):
    return binary_erosion(water, structure=np.ones((3, 3), bool), iterations=erode, border_value=0) if erode else water


def width_estimate_m(water, px=3.0):
    """Largest connected water component: max inscribed diameter (2 x max distance to non-water) in metres."""
    lab, n = label(water, structure=np.ones((3, 3), int))
    if not n:
        return 0.0, 0
    sizes = np.bincount(lab.ravel())[1:]
    comp = lab == (1 + int(np.argmax(sizes)))
    return float(2 * distance_transform_edt(np.pad(comp, 1))[1:-1, 1:-1].max() * px), int(sizes.max())


def screen(sr, udm, valid, jrc3, corridor, ndwi_gt=0.0, erode=ERODE_PX, min_interior=MIN_INTERIOR):
    green, red, nir = sr[3] * SR_SCALE, sr[5] * SR_SCALE, sr[7] * SR_SCALE
    ok = valid & clear_mask(udm)
    ndwi = ndi(green, nir)
    water = ok & (np.nan_to_num(ndwi, nan=-1) > ndwi_gt) & (jrc3 >= 50) & (jrc3 <= 100)
    core = interior(water, erode) & corridor
    width, comp = width_estimate_m(water & corridor)
    ndti = ndi(red, green)
    vals = ndti[core & np.isfinite(ndti)]
    out = dict(corridor_px=int(corridor.sum()), corridor_valid_px=int((valid & corridor).sum()),
               corridor_clear_px=int((ok & corridor).sum()), water_px_corridor=int((water & corridor).sum()),
               interior_px=int(core.sum()), largest_water_component_px=comp, width_estimate_m=round(width, 1),
               gate=bool(vals.size >= min_interior))
    if out["gate"]:
        out.update(ndti_median=round(float(np.median(vals)), 4), ndti_iqr=[round(float(v), 4) for v in np.percentile(vals, [25, 75])],
                   red_median=round(float(np.median(red[core])), 4), green_median=round(float(np.median(green[core])), 4),
                   nir_median=round(float(np.median(nir[core])), 4))
    return out


def window_arrays(scene_dir, station):
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.windows import from_bounds
    from pyproj import Transformer
    from shapely.geometry import Point, box, mapping, shape
    from shapely import transform as gt
    rec = json.loads((PHASE4A / "receipt.json").read_bytes())["stations"][station]
    x0, y0, x1, y1 = rec["extent"]
    srf = next(Path(scene_dir).glob("*_AnalyticMS_SR_8b_clip.tif"))
    udf = next(Path(scene_dir).glob("*_udm2_clip.tif"))
    with rasterio.open(srf) as s, rasterio.open(udf) as u:
        if s.crs.to_epsg() != 32646 or s.res != (3.0, 3.0) or u.transform != s.transform:
            raise ValueError("Unexpected SR/UDM2 grid")
        sb = s.bounds
        covered = sb.left <= x0 and sb.bottom <= y0 and sb.right >= x1 and sb.top >= y1
        if not covered:
            return None, dict(covered=False)
        win = from_bounds(x0, y0, x1, y1, s.transform).round_offsets().round_lengths()
        sr, udm = s.read(window=win), u.read(window=win)
        tf = s.window_transform(win)
    valid = np.all(sr > 0, axis=0)  # SR nodata = 0 in every band
    with rasterio.open(PHASE4A / station / "historical_water.tif") as j:
        jrc = j.read(1)
        jt = j.transform
    h, w = valid.shape
    xs = tf.c + (np.arange(w) + .5) * tf.a
    ys = tf.f + (np.arange(h) + .5) * tf.e
    ci = np.clip(((xs - jt.c) / jt.a).astype(int), 0, jrc.shape[1] - 1)
    ri = np.clip(((ys - jt.f) / jt.e).astype(int), 0, jrc.shape[0] - 1)
    jrc3 = jrc[np.ix_(ri, ci)]
    to_utm = Transformer.from_crs(4326, "EPSG:32646", always_xy=True).transform
    feats = json.loads(REACHES.read_bytes())["lines"].get(station, {}).get("features", [])
    lon, lat = rec["coordinates"]
    centre = Point(*to_utm(lon, lat))
    lines = [gt(shape(f["geometry"]), to_utm, interleaved=False).intersection(box(x0, y0, x1, y1)) for f in feats]
    lines = [g for g in lines if g.length > 0]
    reach = min(lines, key=lambda g: g.distance(centre))
    corridor = geometry_mask([mapping(reach.buffer(80).intersection(centre.buffer(260)))], out_shape=valid.shape, transform=tf, invert=True)
    return dict(sr=sr, udm=udm, valid=valid, jrc3=jrc3, corridor=corridor), dict(
        covered=True, window_valid_fraction=round(float(valid.mean()), 4), window_clear_fraction=round(float((valid & clear_mask(udm)).mean()), 4),
        window_haze_light_fraction=round(float((valid & (udm[3] == 1)).mean()), 4), window_shadow_fraction=round(float((valid & (udm[2] == 1)).mean()), 4),
        sr_percentiles_green_red_nir=[np.percentile(sr[b][valid], [5, 50, 95]).round(0).tolist() for b in (3, 5, 7)] if valid.any() else None)


def main(scene_dir):
    scene_dir = Path(scene_dir)
    md = json.loads(next(scene_dir.glob("*_metadata.json")).read_bytes())
    props = md.get("properties", md)
    scene = scene_dir.name
    res = dict(phase="23K", scene_id=scene, acquired=props.get("acquired"), instrument=props.get("instrument"),
               view_angle=props.get("view_angle"), sun_elevation=props.get("sun_elevation"), scene_clear_percent=props.get("clear_percent"),
               scene_light_haze_percent=props.get("light_haze_percent"), harmonized_to_sentinel2="not indicated in delivered metadata",
               sr_scale=SR_SCALE, bands="coastal_blue, blue, green_i, green, yellow, red, rededge, nir (green = band 4, red = band 6)",
               preregistration_sha256=sha("docs/reports/phase23k-planet-preregistration.md"), windows={})
    for st, role in WINDOWS.items():
        arr, info = window_arrays(scene_dir, st)
        info["role"] = role
        if arr:
            info["primary"] = screen(**arr)
            info["sensitivity"] = {k: screen(**arr, **kw) for k, kw in SENS.items()}
        res["windows"][st] = info
    both = all(res["windows"][s].get("primary", {}).get("gate") for s in WINDOWS)
    res["paired_ndti_feasible_this_date"] = both
    if both:
        res["sunapur_minus_khaddum_ndti"] = round(res["windows"]["Lukha-Sunapur-3376"]["primary"]["ndti_median"]
                                                  - res["windows"]["Lukha-Khaddum-4315"]["primary"]["ndti_median"], 4)
    res["interpretation"] = "single-date descriptive relative NDTI only; no NTU, degradation or causal claim"
    out = Path("docs/reports") / f"phase23k-{scene}-screen.json"
    save(out, res)
    print(json.dumps(res, indent=1)[:4000])


if __name__ == "__main__":
    main(sys.argv[1])
