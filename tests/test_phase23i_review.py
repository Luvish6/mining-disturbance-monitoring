import csv
import json
from pathlib import Path

import numpy as np

from scripts.phase23i_review import CHIP, SCHEMA, chip_window, neutral_id, pick, to_rgb


def test_pick_is_deterministic_and_enforces_separation():
    c = [dict(key=f"k{i}", aoi="A", x=i * 100.0, y=0.0) for i in range(30)]
    a, ra = pick(c, 5, [])
    b, rb = pick(list(reversed(c)), 5, [])
    assert [x["key"] for x in a] == [x["key"] for x in b] and ra == rb
    assert all(np.hypot(p["x"] - q["x"], p["y"] - q["y"]) >= 640 for p in a for q in a if p is not q)
    other = [dict(key="z", aoi="B", x=0.0, y=0.0)]
    assert pick(other, 1, a)[0]  # separation only within the same AOI


def test_chip_window_stays_inside_and_rgb_never_fills_invalid():
    assert chip_window(0, 0) == (0, 0) and chip_window(63, 63) == (64 - CHIP, 64 - CHIP)
    img = to_rgb([np.array([[np.nan, .3]]), np.array([[.1, .3]]), np.array([[.1, .0]])])
    assert np.allclose(img[0, 0], .5) and np.allclose(img[0, 1], [1, 1, 0])


def test_schema_and_neutral_ids():
    assert SCHEMA["mining_attribution"] == ["UNKNOWN"] and "UNCERTAIN" in SCHEMA["visible_disturbance"]
    assert neutral_id("x") == neutral_id("x") != neutral_id("y") and len(neutral_id("x")) == 9


def test_published_manifest_is_blinded_and_train_val_only():
    rows = list(csv.DictReader(Path("docs/reports/phase23i-sample-manifest.csv").open(encoding="utf-8")))
    assert len(rows) == 30 and {r["split"] for r in rows} <= {"train", "validation"}
    assert not any(k in rows[0] for k in ("x", "y", "row", "col", "key", "lon", "lat"))
    design = json.loads(Path("docs/reports/phase23i-sample-design.json").read_text())
    assert design["strata"]["PURPOSIVE_TIER1"]["sampled"] == 0


def test_10m_chip_bounds_and_count_packing():
    from scripts.phase23i_review import chip10_bounds, pack_counts, unpack_counts
    b = chip10_bounds(441555.0, 2791555.0)
    assert b[2] - b[0] == 640 and b[3] - b[1] == 640 and all(v % 10 == 0 for v in b)
    c = (np.array([0, 5, 40]), np.array([3, 31, 2]), np.array([1, 0, 31]))
    p = pack_counts(*c)
    assert p.max() <= 32767
    u = unpack_counts(p)
    assert list(u[0]) == [0, 5, 31] and list(u[1]) == [3, 31, 2] and list(u[2]) == [1, 0, 31]
    assert [int(x) for x in unpack_counts(np.array([-9999]))[0]] == [0]
