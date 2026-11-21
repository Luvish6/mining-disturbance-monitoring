"""Build frontend/public/local/geo.json (git-ignored) for the dashboard's offline GIS map.

Layers come only from verified local assets:
  districts  GAUL 2025 level-2 polygons (Phase 6B frozen copy, hash-checked against its roster)
  rivers     WWF HydroSHEDS Free-Flowing-Rivers reaches cached in Phase 23A (DEM-derived, modelled)
  chains     NDOID main-stem path between each CPCB station pair (Phase 23A topology, modelled)
  stations   4 CPCB WQMN coordinates (Phase 4A receipt)
  aois       20 Phase 22X block-centred sample rectangles with AOI-level aggregates (no cluster locations)
No candidate/cluster coordinates, TEST blocks, review items or imagery. Zero Earth Engine requests.

  python -B -m scripts.phase23_dashboard_geo
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISTRICTS = ROOT / "outputs/phase6b_multitile/districts.json"
ROSTER = ROOT / "outputs/phase6b_multitile/roster.json"
REACHES = ROOT / "outputs/phase23a_linkage/reaches.json"
STATIONS = ROOT / "outputs/phase4a_river_feasibility/receipt.json"
X_PREREG = ROOT / "docs/reports/phase22x-preregistration.json"
X_SUMMARY = ROOT / "docs/reports/phase22x-summary.json"
TARGET = ROOT / "frontend/public/local/geo.json"
MIN_UPLAND_KM2 = 25          # drawn network: reaches draining >= 25 km2 (display density only)
SIMPLIFY_DEG = dict(districts=0.0012, rivers=0.0008)
PAIRS = (("Lukha-Khaddum-4315", 4103404, "Lukha-Sunapur-3376", 4110349),
         ("Myntdu-Mihmyntdu-4316", 4090610, "Myntdu-Leshka-3379", 4100220))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rounded(coords, nd=5):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], nd), round(coords[1], nd)]
    return [rounded(c, nd) for c in coords]


def chain(start, end, ndoid, max_hops=500):
    """GOIDs from start to end following NDOID (inclusive); [] if end is not reached."""
    path, node = [], start
    for _ in range(max_hops):
        path.append(node)
        if node == end:
            return path
        node = ndoid.get(node, 0)
        if not node:
            return []
    return []


def build():
    from pyproj import Transformer
    from shapely.geometry import box, mapping, shape
    roster = json.loads(ROSTER.read_bytes())
    if sha(DISTRICTS) != roster["geometry_sha256"]:
        raise ValueError("District geometry hash differs from the frozen Phase 6B roster")
    dfeat = json.loads(DISTRICTS.read_bytes())["features"]
    districts, union = [], None
    for f in dfeat:
        g = shape(f["geometry"])
        union = g if union is None else union.union(g)
        districts.append(dict(name=f["properties"]["GAUL2_NAME"],
                              geometry=json.loads(json.dumps(mapping(g.simplify(SIMPLIFY_DEG["districts"], preserve_topology=True)))),
                              area_km2=None))
    for d in districts:
        d["geometry"]["coordinates"] = rounded(d["geometry"]["coordinates"])
    w, s, e, n = union.bounds
    pad = 0.02
    view = box(w - pad, s - pad, e + pad, n + pad)
    feats = json.loads(REACHES.read_bytes())["reaches"]["features"]
    ndoid = {int(f["properties"]["GOID"]): int(f["properties"]["NDOID"]) for f in feats}
    by_goid = {int(f["properties"]["GOID"]): f for f in feats}
    rivers = []
    for f in feats:
        p = f["properties"]
        g = shape(f["geometry"])
        if p.get("UPLAND_SKM", 0) < MIN_UPLAND_KM2 or not g.intersects(view):
            continue
        g = g.intersection(view).simplify(SIMPLIFY_DEG["rivers"])
        if g.is_empty:
            continue
        geo = mapping(g)
        rivers.append(dict(goid=int(p["GOID"]), upland_km2=round(p["UPLAND_SKM"], 1),
                           geometry=dict(type=geo["type"], coordinates=rounded(json.loads(json.dumps(geo["coordinates"]))))))
    chains = []
    for a, ga, b, gb in PAIRS:
        path = chain(ga, gb, ndoid)
        lines = [rounded(json.loads(json.dumps(mapping(shape(by_goid[g]["geometry"]))["coordinates"]))) for g in path if g in by_goid]
        chains.append(dict(upstream=a, downstream=b, reaches=len(path), supported=bool(path), lines=lines))
    st = json.loads(STATIONS.read_bytes())["stations"]
    stations = [dict(id=k, river=k.split("-")[0], name=k.split("-")[1], code=k.split("-")[2], lonlat=v["coordinates"]) for k, v in st.items()]
    x = json.loads(X_PREREG.read_bytes())["aois"]
    xs = json.loads(X_SUMMARY.read_bytes())["aois"]
    to_ll = Transformer.from_crs("EPSG:32646", 4326, always_xy=True).transform
    aois = []
    for k, a in sorted(x.items()):
        if a["split"] == "test":
            raise ValueError("TEST AOI must never be mapped")
        x0, y0, x1, y1 = a["bounds"]
        ring = [list(to_ll(px, py)) for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))]
        v = xs[k]
        aois.append(dict(aoi=k, district=a["district"], split=a["split"], ring=rounded(ring),
                         density=round(v["density_ha_per_100ha"], 3), clusters=v["clusters"], candidate_cells=v["candidate_cells"]))
    return dict(
        schema=1, crs="EPSG:4326 lon/lat", view_bounds=[round(w - pad, 4), round(s - pad, 4), round(e + pad, 4), round(n + pad, 4)],
        districts=districts, rivers=rivers, chains=chains, stations=stations, aois=aois,
        provenance=dict(
            districts=dict(source="FAO GAUL 2025 level 2 (GAUL2_NAME)", file="outputs/phase6b_multitile/districts.json", sha256=sha(DISTRICTS),
                           note=f"simplified {SIMPLIFY_DEG['districts']} deg for display; GAUL terms apply; local only"),
            rivers=dict(source="WWF HydroSHEDS Free-Flowing Rivers (DEM-derived, modelled)", file="outputs/phase23a_linkage/reaches.json",
                        sha256=sha(REACHES), note=f"reaches with upstream area >= {MIN_UPLAND_KM2} km2; not surveyed centrelines; no river names"),
            chains=dict(source="Phase 23A NDOID topology", note="modelled main-stem path between station reaches"),
            stations=dict(source="CPCB WQMN register via Phase 4A receipt", file="outputs/phase4a_river_feasibility/receipt.json", sha256=sha(STATIONS)),
            aois=dict(source="Phase 22X preregistered sample + summary", file="docs/reports/phase22x-summary.json", sha256=sha(X_SUMMARY),
                      note="block-centred 1.92 km sample squares; aggregates only, no candidate locations")),
        unavailable=["exact candidate/cluster locations (kept local by project rule)", "surveyed river centrelines and named river lines",
                     "catchment polygons (HydroBASINS not acquired)", "basemap imagery tiles (offline map, no external tile requests)"])


def main():
    payload = build()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print("wrote", TARGET.relative_to(ROOT), TARGET.stat().st_size, "bytes;", len(payload["rivers"]), "reaches;",
          [(c["upstream"], c["reaches"]) for c in payload["chains"]])


if __name__ == "__main__":
    main()
