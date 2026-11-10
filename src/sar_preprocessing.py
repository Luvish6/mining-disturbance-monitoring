"""Single-pass, single-relative-orbit SAR; linear-power spatial smoothing."""
import ee


def collection(region, season, cfg):
    return (ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(region)
            .filterDate(season.start, season.end)
            .filter(ee.Filter.eq('instrumentMode', 'IW'))
            .filter(ee.Filter.eq('resolution_meters', 10))
            .filter(ee.Filter.eq('orbitProperties_pass', cfg.orbit_pass))
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')))


def choose_orbit(before_hist, after_hist, requested=None):
    """Maximise the smaller seasonal scene count; coverage still needs inspection."""
    before_hist = {int(float(k)): n for k, n in before_hist.items()}
    after_hist = {int(float(k)): n for k, n in after_hist.items()}
    common = {k for k, n in before_hist.items() if n > 0} & {
        k for k, n in after_hist.items() if n > 0}
    if requested is not None:
        if requested not in common:
            raise ValueError(f'Relative orbit {requested} is unavailable in both seasons')
        return requested
    if not common:
        raise ValueError('No common relative orbit; inspect another pass or region')
    return min(common, key=lambda k: (
        -min(before_hist[k], after_hist[k]), k))


def seasonal(col, orbit, region, cfg):
    col = col.filter(ee.Filter.eq('relativeOrbitNumber_start', orbit))

    def prepare(img):
        db = img.select(['VV', 'VH'])
        native_mask = db.mask().reduce(ee.Reducer.min())
        # Keep the source projection (a constant image as first operand loses it).
        power = db.multiply(0.23025850929940458).exp().rename(['VV', 'VH'])
        if cfg.speckle_radius_m:
            power = power.focal_mean(radius=cfg.speckle_radius_m,
                                     kernelType='circle', units='meters')
        return power.updateMask(native_mask).copyProperties(img, ['system:time_start'])

    power = col.map(prepare)
    count = power.select('VV').count().unmask(0).rename('sar_count').clip(region)
    db = power.median().log10().multiply(10).rename(['VV', 'VH'])
    return db.updateMask(count.gte(cfg.min_observations)).clip(region), count
