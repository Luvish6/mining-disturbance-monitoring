"""Small offline layer/grid and retrospective pseudo-state contracts."""
from dataclasses import dataclass
import numpy as np
from affine import Affine
from rasterio.crs import CRS
from rasterio.warp import reproject, Resampling


@dataclass(frozen=True)
class Grid:
    crs: str
    affine: tuple
    shape: tuple

    def __post_init__(self):
        a = Affine(*self.affine)
        if (not CRS.from_user_input(self.crs).is_projected or len(self.shape) != 2
                or any(int(n) != n or not 0 < n <= 2048 for n in self.shape)
                or a.a <= 0 or a.e >= 0 or a.b or a.d or not np.isfinite(self.affine).all()):
            raise ValueError('Invalid bounded north-up metric grid')


def align(values, valid, source, target, kind, *, allow_resampling=False):
    if kind not in ('continuous', 'categorical', 'count', 'mask'):
        raise ValueError('Declare layer semantics')
    values, valid = np.asarray(values, float), np.asarray(valid, bool)
    if values.shape != source.shape or valid.shape != source.shape:
        raise ValueError('Layer/mask grid mismatch')
    valid = valid & np.isfinite(values)
    if kind in ('categorical', 'count', 'mask') and (values[valid] != np.floor(values[valid])).any():
        raise ValueError('Noninteger discrete values')
    if source == target:
        return np.where(valid, values, np.nan), valid
    if not allow_resampling:
        raise ValueError('Grid mismatch; no silent reprojection/resampling')
    out = np.full(target.shape, np.nan, dtype='float64')
    reproject(np.where(valid, values, np.nan), out,
              src_transform=Affine(*source.affine), src_crs=source.crs, src_nodata=np.nan,
              dst_transform=Affine(*target.affine), dst_crs=target.crs, dst_nodata=np.nan,
              resampling=Resampling.bilinear if kind == 'continuous' else Resampling.nearest)
    return out, np.isfinite(out)


def stack_layers(layers, grid, specs):
    if len({s['name'] for s in specs}) != len(specs):
        raise ValueError('Duplicate feature names')
    values, masks, availability = [], [], {}
    for spec in specs:
        name = spec['name']
        if spec['role'] not in ('signal', 'context_only'):
            raise ValueError('Unapproved feature role')
        if name not in layers:
            v, m = np.full(grid.shape, np.nan), np.zeros(grid.shape, bool)
            availability[name] = 'UNAVAILABLE'
        else:
            v, m, source_grid = layers[name]
            v, m = align(v, m, source_grid, grid, spec['kind'])
            availability[name] = 'AVAILABLE' if m.any() else 'NO_VALID_SUPPORT'
        values.append(v); masks.append(m)
    return np.stack(values), np.stack(masks), availability


def require_calibration_partition(split):
    if split != 'train':
        raise ValueError('Calibration may use TRAIN only; VAL is not independent truth')


def pseudo_states(before, after, follow, cb, ca, cf, vv0, vv1, vh0, vh1, sc0, sc1, slope, rules):
    """0 potential stable, 1 potential disturbance, 255 uncertain; never reference labels.

    Follow-up is retrospective annotation evidence, not an earlier model-input feature.
    Optional contextual products never determine these states or mining attribution.
    """
    from scripts.phase22l_temporal import select_candidates
    arrays = [before, after, follow]
    shape = np.asarray(cb).shape
    if any(np.asarray(a).shape != (6, *shape) for a in arrays):
        raise ValueError('Optical schema must be B4/B3/B2/NDVI/BSI/NDWI')
    if any(np.asarray(x).shape != shape for x in (ca, cf, vv0, vv1, vh0, vh1, sc0, sc1, slope)):
        raise ValueError('Paired grid mismatch')
    for count in (cb, ca, cf, sc0, sc1):
        c = np.asarray(count)
        if ((c[np.isfinite(c)] < 0) | (c[np.isfinite(c)] != np.floor(c[np.isfinite(c)]))).any():
            raise ValueError('Invalid observation count')
    # Reuse the frozen land/count screen, while allowing separately versioned exploratory rule values.
    eligible, _, dn, db = select_candidates(before, after, cb, ca, slope)
    eligible &= (cb >= rules['min_observations']) & (ca >= rules['min_observations'])
    optical = eligible & (dn <= rules['ndvi_drop']) & (db > rules['bsi_increase'])
    sar = (np.isfinite(vv0) & np.isfinite(vv1) & np.isfinite(vh0) & np.isfinite(vh1)
           & (sc0 >= rules['min_observations']) & (sc1 >= rules['min_observations']))
    dv, dh = vv1-vv0, vh1-vh0
    corroborated = sar & (dv <= rules['sar_drop_max']) & (dh <= rules['sar_drop_max'])
    fv = np.isfinite(follow).all(0) & (cf >= rules['min_observations']) & (follow[5] < 0)
    persistent = fv & (follow[3]-before[3] <= rules['ndvi_drop']) & (follow[4]-before[4] > rules['bsi_increase'])
    stable = (eligible & sar & (np.abs(dn) <= rules['stable_ndvi_abs'])
              & (np.abs(db) <= rules['stable_bsi_abs']) & (np.abs(dv) <= rules['stable_sar_abs_db'])
              & (np.abs(dh) <= rules['stable_sar_abs_db']))
    if rules['require_persistence']:
        stable &= fv & (np.abs(follow[3]-before[3]) <= rules['stable_ndvi_abs']) & (np.abs(follow[4]-before[4]) <= rules['stable_bsi_abs'])
    candidate = optical & corroborated
    if rules['require_persistence']:
        candidate &= persistent
    state = np.full(shape, 255, dtype='uint8')
    state[stable] = 0
    state[candidate] = 1
    evidence = dict(eligible=eligible, optical_rule=optical, sar_valid=sar,
                    sar_agreement=corroborated, follow_valid=fv, persistent=persistent,
                    steep_context=np.isfinite(slope) & (slope >= rules['steep_context_degrees']))
    return state, evidence
