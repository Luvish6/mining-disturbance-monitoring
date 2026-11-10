"""Phase 2: small AOI by default; full-region runs require coarse coverage checks."""
import argparse
from dataclasses import asdict, replace
import json
import logging
from pathlib import Path
import ee
from config.settings import BEFORE, AFTER
from config.phase2_settings import Phase2Config, STACK_BANDS
from src.gee_setup import initialize
from src.study_area import get_study_area, verify_boundary
from src import sar_preprocessing as sar, optical_preprocessing as optical
from src.change_features import build_stack
from src.coverage_diagnostics import district_diagnostics, validity_image
from src.diagnostic_maps import add_diagnostic_layers

LOG = logging.getLogger(__name__)


def processing_region(boundary, full_region, point, cfg):
    """Full-region runs do not create or validate a centroid."""
    if full_region:
        return boundary
    centre = ee.Geometry.Point(point) if point else boundary.centroid(100)
    if not boundary.contains(centre, 100).getInfo():
        raise ValueError('Smoke centre is outside the study area; supply --point LON LAT')
    return centre.buffer(cfg.smoke_radius_m).intersection(boundary, 10)


def build(region, cfg):
    """Return lazy images and bounded scene metadata; no pixel evaluation."""
    s1 = [sar.collection(region, season, cfg) for season in (BEFORE, AFTER)]
    s2 = [optical.collections(region, season, cfg) for season in (BEFORE, AFTER)]
    metadata = ee.Dictionary({
        's1_orbits': ee.List([c.aggregate_histogram('relativeOrbitNumber_start') for c in s1]),
        's2_raw': ee.List([raw.size() for raw, joined in s2]),
        's2_joined': ee.List([joined.size() for raw, joined in s2]),
    }).getInfo()
    orbit = sar.choose_orbit(*metadata['s1_orbits'], cfg.relative_orbit)
    if any(n == 0 for n in metadata['s2_joined']):
        raise ValueError('No joined optical scenes in at least one season')
    metadata['selected_relative_orbit'] = orbit
    metadata['s2_unmatched'] = [a - b for a, b in zip(metadata['s2_raw'], metadata['s2_joined'])]
    sar_values = [sar.seasonal(c, orbit, region, cfg) for c in s1]
    opt_values = [optical.seasonal(joined, region, cfg) for raw, joined in s2]
    stack = build_stack(sar_values[0][0], sar_values[1][0],
                        opt_values[0][0], opt_values[1][0], region)
    diagnostics = ee.Image.cat([
        pair[1].rename(name) for pair, name in zip(
            sar_values + opt_values,
            ['sar_before_count', 'sar_after_count', 'optical_before_count', 'optical_after_count'])])
    return stack, diagnostics, metadata


def smoke(stack, diagnostics, region, cfg):
    """One bounded pixel reduction; explicit CRS avoids composite WGS84 defaults."""
    valid = stack.mask().unmask(0).rename([b + '_valid_fraction' for b in STACK_BANDS])
    common = stack.mask().reduce(ee.Reducer.min()).unmask(0).rename('common_valid_fraction')
    seasonal_valid = validity_image(stack, diagnostics, cfg).select(
        ['sar_before_valid', 'sar_after_valid', 'optical_before_valid', 'optical_after_valid'])
    reducer = (ee.Reducer.mean().combine(ee.Reducer.minMax(), sharedInputs=True)
               .combine(ee.Reducer.percentile([5, 50, 95], maxBuckets=128, maxRaw=1000), sharedInputs=True))
    result = stack.addBands(diagnostics).addBands(valid).addBands(common).addBands(seasonal_valid).reduceRegion(
        reducer=reducer, geometry=region, scale=cfg.analysis_scale_m,
        crs=cfg.analysis_crs, maxPixels=100000, tileScale=2).getInfo()
    fractions = [result.get(b + '_valid_fraction_mean') or 0 for b in STACK_BANDS]
    return result, all(v > 0 for v in fractions) and (result.get('common_valid_fraction_mean') or 0) > 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authenticate', action='store_true')
    parser.add_argument('--pass', dest='orbit_pass', choices=['ASCENDING', 'DESCENDING'], default='DESCENDING')
    parser.add_argument('--relative-orbit', type=int)
    parser.add_argument('--cloud-probability', type=int, default=40)
    parser.add_argument('--scene-cloud-percent', type=int, default=80)
    parser.add_argument('--speckle-radius-m', type=float, default=20)
    parser.add_argument('--min-observations', type=int, default=2)
    parser.add_argument('--smoke-radius-m', type=float, default=500)
    parser.add_argument('--analysis-scale-m', type=int, default=30)
    parser.add_argument('--coverage-scale-m', type=int, default=500)
    parser.add_argument('--min-sar-coverage', type=float, default=0.90)
    parser.add_argument('--min-common-coverage', type=float, default=0.70)
    parser.add_argument('--district-coverage', action='store_true',
                        help='Evaluate coarse district coverage for the same selected orbit; automatic with --full-region')
    parser.add_argument('--point', type=float, nargs=2, metavar=('LON', 'LAT'),
                        help='Optional smoke centre within verified districts')
    parser.add_argument('--full-region', action='store_true', help='Construct full district graph')
    parser.add_argument('--smoke', action='store_true', help='Evaluate small-area pixels')
    parser.add_argument('--map', action='store_true', help='Save optional geemap HTML; opening renders EE tiles')
    parser.add_argument('--output-dir', type=Path, default=Path('outputs'))
    args = parser.parse_args(argv)
    if args.smoke and args.full_region:
        parser.error('--smoke cannot be combined with --full-region')
    cfg = Phase2Config(**{k: getattr(args, k) for k in (
        'orbit_pass', 'relative_orbit', 'cloud_probability', 'scene_cloud_percent',
        'speckle_radius_m', 'min_observations', 'smoke_radius_m', 'analysis_scale_m',
        'coverage_scale_m', 'min_sar_coverage', 'min_common_coverage')})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(),
        logging.FileHandler(args.output_dir / 'phase2.log', encoding='utf-8')])
    report = {'status': 'started', 'config': asdict(cfg), 'district_coverage_checked': False,
              'seasons': [asdict(BEFORE), asdict(AFTER)], 'full_region': args.full_region}
    try:
        initialize(authenticate=args.authenticate)
        ee.data.setDeadline(60000)
        districts = get_study_area()
        boundary = verify_boundary(districts)
        region = processing_region(boundary, args.full_region, args.point, cfg)
        LOG.info('Building %s graph; no automatic exports', 'full district' if args.full_region else 'small-area')
        stack, diagnostics, metadata = build(region, cfg)
        report.update(metadata=metadata, bands=stack.bandNames().getInfo(), status='graph_built_pixels_not_evaluated')
        if args.smoke:
            result, usable = smoke(stack, diagnostics, region, cfg)
            report.update(pixel_diagnostics=result,
                          status='smoke_passed' if usable else 'smoke_failed_missing_valid_pixels')
            LOG.info('Smoke diagnostics: %s', json.dumps(result))
            if not usable:
                raise ValueError('At least one feature has no valid pixels in smoke region')
        coverage_ok = True
        if args.full_region or args.district_coverage:
            LOG.info('Evaluating bounded district coverage at %s m', cfg.coverage_scale_m)
            if args.full_region:
                district_stack, district_counts = stack, diagnostics
            else:
                orbit_cfg = replace(cfg, relative_orbit=metadata['selected_relative_orbit'])
                district_stack, district_counts, district_metadata = build(boundary, orbit_cfg)
                report['district_metadata'] = district_metadata
            coverage = district_diagnostics(district_stack, district_counts, districts, cfg)
            report['district_coverage'] = coverage
            report['district_coverage_checked'] = True
            coverage_ok = coverage['coverage_gate_passed']
            report['status'] = ('district_coverage_passed' if coverage_ok else 'district_coverage_failed')
            LOG.info('District coverage: %s', json.dumps(coverage))
        if args.map:
            import geemap.foliumap as geemap
            m = geemap.Map()
            m.centerObject(region, 13 if not args.full_region else 9)
            add_diagnostic_layers(m, stack, diagnostics, cfg, districts)
            m.to_html(str(args.output_dir / 'phase2_map.html'))
        if not coverage_ok:
            raise ValueError('District coverage gate failed; inspect per-season SAR and common fractions before Phase 3')
        LOG.info('Phase 2 status: %s', report['status'])
    except Exception as exc:
        report.update(status='failed', error=str(exc))
        LOG.exception('Phase 2 failed')
        raise
    finally:
        (args.output_dir / 'phase2_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
