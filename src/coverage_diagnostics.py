"""Coarse district diagnostics; never interpret scene counts as spatial coverage."""
import math
import ee
from config.settings import DISTRICTS
from config.phase2_settings import STACK_BANDS

COUNT_BANDS = ('sar_before_count', 'sar_after_count',
               'optical_before_count', 'optical_after_count')
COVERAGE_BANDS = tuple(b.replace('_count', '_valid') for b in COUNT_BANDS) + ('common_valid',)
CHANGE_BANDS = STACK_BANDS[:4]


def common_valid_mask(stack):
    # Explicitly extend zero values outside every scene footprint. Otherwise a
    # reduction can accidentally exclude missing coverage from its denominator.
    return (stack.select(list(STACK_BANDS)).mask().reduce(ee.Reducer.min())
            .gt(0).unmask(0, sameFootprint=False).rename('common_valid'))


def validity_image(stack, counts, cfg):
    seasons = (counts.select(list(COUNT_BANDS)).gte(cfg.min_observations)
               .unmask(0, sameFootprint=False).rename(list(COVERAGE_BANDS[:4])))
    return seasons.addBands(common_valid_mask(stack))


def district_diagnostics_graph(stack, counts, districts, cfg):
    """Two coarse reductions; only two geometry-free property rows returned each."""
    validity = validity_image(stack, counts, cfg)
    area = ee.Image.pixelArea()
    covered_area = validity.multiply(area).addBands(area.rename('total_area_m2'))
    kwargs = dict(collection=districts.select(['GAUL2_NAME']),
                  scale=cfg.coverage_scale_m, crs=cfg.analysis_crs,
                  tileScale=2, maxPixelsPerRegion=100000)
    areas = covered_area.reduceRegions(reducer=ee.Reducer.sum(), **kwargs)
    # A representative coarse-grid distribution, not a native-resolution histogram.
    distribution_reducer = (ee.Reducer.percentile([5, 50, 95], maxBuckets=128, maxRaw=1000)
                            .combine(ee.Reducer.count(), sharedInputs=True))
    values = stack.select(list(CHANGE_BANDS)).addBands(
        counts.select(list(COUNT_BANDS)).unmask(0, sameFootprint=False))
    distributions = values.reduceRegions(reducer=distribution_reducer, **kwargs)

    def properties_only(collection):
        # Nested FeatureCollections in Dictionary.getInfo() can return only
        # collection metadata. Materialize three bounded property rows so two
        # expected districts are retrieved and an unexpected extra is detected.
        rows = collection.toList(3).map(
            lambda f: ee.Dictionary({'properties': ee.Feature(f).toDictionary()}))
        return ee.Dictionary({'features': rows})

    return ee.Dictionary({'areas': properties_only(areas),
                          'distributions': properties_only(distributions)})


def summarize_districts(raw, cfg):
    """Fail closed on missing districts/data and assess every SAR season/district."""
    rows = raw.get('areas', {}).get('features', [])
    names = [f.get('properties', {}).get('GAUL2_NAME') for f in rows]
    if len(names) != 2 or set(names) != set(DISTRICTS):
        raise ValueError('Coverage diagnostic must contain each verified district exactly once')
    result = {'scale_m': cfg.coverage_scale_m, 'crs': cfg.analysis_crs,
              'min_observations': cfg.min_observations,
              'thresholds': {'sar': cfg.min_sar_coverage, 'common': cfg.min_common_coverage},
              'districts': {}, 'sar_adequate': True, 'common_adequate': True}
    distribution_rows = raw.get('distributions', {}).get('features', [])
    distribution_by_name = {f['properties']['GAUL2_NAME']: f['properties'] for f in distribution_rows}
    for f in rows:
        props = f['properties']
        name = props['GAUL2_NAME']
        total = props.get('total_area_m2')
        if total is None or not math.isfinite(total) or total <= 0:
            raise ValueError(f'No coverage denominator for {name}')
        fractions = {}
        for band in COVERAGE_BANDS:
            value = props.get(band)
            if value is None or not math.isfinite(value) or not 0 <= value <= total * (1 + 1e-6):
                raise ValueError(f'Invalid coverage numerator for {name}: {band}')
            fractions[band] = min(1.0, value / total)
        sar_ok = all(fractions[b] >= cfg.min_sar_coverage for b in COVERAGE_BANDS[:2])
        common_ok = fractions['common_valid'] >= cfg.min_common_coverage
        result['sar_adequate'] &= sar_ok
        result['common_adequate'] &= common_ok
        result['districts'][name] = {
            'fractions': fractions, 'sar_adequate': sar_ok, 'common_adequate': common_ok,
            'coarse_area_m2': total,
            'coarse_distributions': {k: v for k, v in distribution_by_name.get(name, {}).items()
                                     if k not in ('GAUL2_NAME', 'system:index')}}
    result['coverage_gate_passed'] = result['sar_adequate'] and result['common_adequate']
    return result


def district_diagnostics(stack, counts, districts, cfg):
    return summarize_districts(district_diagnostics_graph(stack, counts, districts, cfg).getInfo(), cfg)
