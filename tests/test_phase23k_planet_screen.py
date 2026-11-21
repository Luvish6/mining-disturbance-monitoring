import numpy as np

from scripts.phase23k_planet_screen import clear_mask, interior, ndi, screen, width_estimate_m


def _udm(shape, **flags):
    u = np.zeros((8, *shape), np.uint8)
    u[0] = 1
    for i, name in enumerate(("clear", "snow", "shadow", "haze_light", "haze_heavy", "cloud")):
        if name in flags:
            u[i][flags[name]] = 1 if name != "clear" else 0
    return u


def test_clear_mask_excludes_haze_shadow_cloud():
    m = np.zeros((3, 3), bool); m[0, 0] = True
    assert clear_mask(_udm((3, 3)))[0, 0]
    for f in ("shadow", "haze_light", "haze_heavy", "cloud", "snow"):
        assert not clear_mask(_udm((3, 3), **{f: m}))[0, 0]


def test_interior_and_width():
    w = np.zeros((20, 20), bool); w[5:15, :] = True  # 10-pixel (30 m) wide band
    assert interior(w, 2)[5:7].sum() == 0 and interior(w, 2)[7:13, 2:-2].all()
    width, comp = width_estimate_m(w)
    assert 27 <= width <= 33 and comp == 200
    assert width_estimate_m(np.zeros((4, 4), bool)) == (0.0, 0)


def test_screen_gate_and_ndti_only_when_supported():
    h = w = 30
    sr = np.full((8, h, w), 1000, np.uint16)
    sr[3], sr[5], sr[7] = 800, 400, 2000          # land: NDWI < 0
    sr[3, 5:25, 5:25], sr[5, 5:25, 5:25], sr[7, 5:25, 5:25] = 600, 300, 100  # water block: NDWI > 0
    args = dict(sr=sr, udm=_udm((h, w)), valid=np.ones((h, w), bool), jrc3=np.full((h, w), 90), corridor=np.ones((h, w), bool))
    out = screen(**args)
    assert out["gate"] and out["interior_px"] == 16 * 16
    assert abs(out["ndti_median"] - (0.03 - 0.06) / 0.09) < 1e-3
    args["jrc3"] = np.zeros((h, w))
    out = screen(**args)
    assert not out["gate"] and "ndti_median" not in out
    assert np.isnan(ndi(np.zeros(1), np.zeros(1))[0])
