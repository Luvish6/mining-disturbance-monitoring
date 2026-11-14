"""Serve the existing portal and verified Planet diagnostics on numeric loopback."""

import argparse
import io
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio import Affine
from rasterio.warp import transform
from rasterio.windows import Window

from scripts.phase7_planet_reference import BANDS, clear_pixels, normalized
from src.phase3.data import digest

PREFIX = "/__planet_review__/"
SCENES = (
    ("Before_20240308", "20240308_034150_36_24bf"),
    ("After_20250325", "20250325_045348_68_24cb"),
)


def png(values, support):
    rgba = np.dstack((values, support * 255)).astype(np.uint8)
    stream = io.BytesIO()
    Image.fromarray(rgba).save(stream, format="PNG")
    return "image/png", stream.getvalue()


def index_color(index, limit, low, mid, high):
    fraction = np.clip(np.nan_to_num(index) / limit, -1, 1)[..., None]
    return np.array(mid) + np.abs(fraction) * (np.where(fraction < 0, low, high) - mid)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def review_files(root):
    inspection = root / "outputs/phase7_planet_third_before"
    findings = root / "outputs/phase7_korpet_detailed_review"
    receipt_path = inspection / "inspection.json"
    receipt = json.loads(receipt_path.read_text())
    stats = json.loads((findings / "stats.json").read_text())
    require(digest(receipt_path) == stats["phase7_receipt_sha256"], "Inspection receipt mismatch")
    grid = Affine(*stats["transform"])
    require(stats["crs"] == "EPSG:32646" and (grid.a, grid.b, grid.d, grid.e) == (3, 0, 0, -3),
            "Unexpected review grid")
    left, right, bottom, top = stats["extent"]
    width, height = int((right-left)/3), int((top-bottom)/3)
    require(grid.c == left and grid.f == top and (width, height) == (216, 216), "Unexpected review extent")
    east, north = transform("EPSG:4326", stats["crs"], [receipt["point"][0]], [receipt["point"][1]])
    mx, my = (~grid) * (east[0], north[0])
    rows, cols = np.indices((height, width))
    roi = ((cols+.5-mx)**2 + (rows+.5-my)**2)*9 <= receipt["radius_m"]**2
    files, coverages, indices, scenes = {}, [], [], []
    for i, ((folder, identity), scene, meta) in enumerate(zip(SCENES, receipt["scenes"], stats["metadata"], strict=True)):
        directory = inspection / folder
        archive = root.parent / f"KORPET_{folder}_psscene_analytic_8b_sr_udm2.zip"
        require(scene["id"] == identity and meta["acquired"].startswith(scene["acquired"][:19]), "Scene identity mismatch")
        require(digest(archive) == scene["zip_sha256"], "Archive receipt mismatch")
        for filename, sha in scene["files"].items():
            require(Path(filename).name == filename and digest(directory / filename) == sha, "Extracted asset receipt mismatch")
        with rasterio.open(directory / f"{identity}_3B_AnalyticMS_SR_8b_clip.tif") as sr, rasterio.open(
                directory / f"{identity}_3B_udm2_clip.tif") as udm:
            require(sr.crs.to_string() == stats["crs"] and (sr.crs, sr.transform, sr.shape) ==
                    (udm.crs, udm.transform, udm.shape), "SR and UDM2 grids disagree")
            require(tuple(map(normalized, sr.descriptions)) == BANDS and sr.nodata == 0
                    and sr.scales == (1.,)*8 and sr.offsets == (0.,)*8, "Unexpected SR schema")
            col, row = (~sr.transform) * (left, top)
            window = Window(round(col), round(row), width, height)
            require(sr.window_transform(window) == grid, "Native review windows do not align")
            values = sr.read(window=window, masked=True).filled(0)
            flags = udm.read(window=window)
        clear, _ = clear_pixels(values, flags)
        require(int((roi & clear).sum()) == scene["clear"] and int((roi & (values > 0).all(0)).sum()) ==
                scene["valid"] and int(roi.sum()) == scene["roi_cells"], "Coverage receipt mismatch")
        measured_flags = dict(zip(("snow", "shadow", "haze", "heavy_haze", "cloud", "unusable"),
                                  (int((flags[j, roi] > 0).sum()) for j in (1, 2, 3, 4, 5, 7))))
        require(measured_flags == scene["flags"], "UDM2 flags disagree with receipt")
        files[f"rgb-{i}.png"] = png(np.clip(values[[5, 3, 1]].transpose(1, 2, 0)/3500, 0, 1)*255, clear)
        nir, red = values[[7, 5]].astype(float)
        index = np.divide(nir-red, nir+red, out=np.full_like(nir, np.nan), where=nir+red > 0)
        coverages.append(clear)
        indices.append(index)
        scenes.append({**meta, **{key: scene[key] for key in ("id", "roi_cells", "valid", "clear", "flags", "zip_sha256")}})
    common = roi & coverages[0] & coverages[1]
    require(int(common.sum()) == stats["common_clear"] == receipt["common_grid_valid_clear"][-1], "Common support mismatch")
    medians = []
    for i, index in enumerate((*indices, indices[1]-indices[0])):
        record = (*stats["ndvi"], stats["difference"])[i]
        median = record["quantiles"]["median"]
        require(record["n"] == int(common.sum()) and np.isclose(np.median(index[common]), median, rtol=0, atol=1e-12),
                "NDVI receipt mismatch")
        medians.append(median)
        palette = ([36,72,163], [237,237,230], [175,43,35]) if i == 2 else (
            [125,66,32], [235,233,213], [0,98,79])
        key = "difference.png" if i == 2 else f"ndvi-{i}.png"
        files[key] = png(index_color(index, .25 if i == 2 else 1, *palette), common)
    payload = dict(scenes=scenes, medians=medians, common=int(common.sum()), crs=stats["crs"],
                   extent=stats["extent"], marker=[mx/width, my/height], coordinates=receipt["point"],
                   radius=receipt["radius_m"], size=[width, height], receipt=stats["phase7_receipt_sha256"],
                   statistics=digest(findings / "stats.json"), matches=stats["relative_diagnostics"])
    files["receipt.json"] = "application/json", json.dumps(payload, allow_nan=False).encode()
    return files


def handler(dist, files, authority):
    class Portal(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Host") != authority:
                self.send_error(403)
                return
            path = self.path.split("?", 1)[0]
            private = path.startswith(PREFIX)
            if private:
                if (self.headers.get("Sec-Fetch-Site") != "same-origin"
                        or self.headers.get("Origin") not in (None, "http://" + authority)):
                    self.send_error(403)
                    return
                result = files.get(path.removeprefix(PREFIX))
            else:
                path = dist / (path.lstrip("/") or "index.html")
                path = path.resolve()
                result = ((mimetypes.guess_type(path.name)[0] or "application/octet-stream"), path.read_bytes()
                          ) if path.is_relative_to(dist) and path.is_file() else None
            if result is None:
                self.send_error(404)
                return
            kind, content = result
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
    return Portal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5188)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Specify a TCP port between 1 and 65535")
    root = Path(__file__).resolve().parents[1]
    dist = (root / "frontend/dist").resolve()
    if not (dist / "index.html").is_file():
        parser.error("Build the existing frontend first")
    try:
        files = review_files(root)
    except (OSError, ValueError, KeyError, TypeError, rasterio.errors.RasterioError) as exc:
        print(f"Private review unavailable: {exc}", flush=True)
        files = {}
    authority = f"127.0.0.1:{args.port}"
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler(dist, files, authority)) as server:
        print(f"Private portal: http://{authority}/#review", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
