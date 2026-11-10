"""Lazy paired seasonal graph. Does not submit exports or relax Phase 2 gates."""
from dataclasses import asdict
import ee
from config.settings import BEFORE, AFTER
from src import sar_preprocessing as sar, optical_preprocessing as optical
from src.change_features import build_stack
from .data import BANDS


def paired_graph(region, cfg):
    if cfg.relative_orbit is None:
        raise ValueError('Pin the orbit verified by district coverage diagnostics first')
    s = [sar.seasonal(sar.collection(region, t, cfg), cfg.relative_orbit, region, cfg)[0] for t in (BEFORE, AFTER)]
    o = [optical.seasonal(optical.collections(region, t, cfg)[1], region, cfg)[0] for t in (BEFORE, AFTER)]
    pair = ee.Image.cat([s[0], o[0], s[1], o[1], build_stack(s[0], s[1], o[0], o[1], region)])
    return pair.rename(list(BANDS)).toFloat()


def export_task(region, cfg, coverage_report, description, folder='mining_phase3',
                transform=(30, 0, 0, 0, -30, 0)):
    """Return UNSUBMITTED small-tile export task. Caller must inspect and start it.

    Regional coverage is a prerequisite, not a substitute for tile mask QA.
    Export nodata is explicit; ingest checks raster band descriptions and grid.
    """
    report_cfg = coverage_report.get('config', {})
    controls = ('orbit_pass', 'cloud_probability', 'scene_cloud_percent',
                'speckle_radius_m', 'min_observations', 'analysis_scale_m', 'analysis_crs')
    if (coverage_report.get('status') != 'district_coverage_passed'
            or not coverage_report.get('district_coverage_checked')
            or not coverage_report.get('district_coverage', {}).get('coverage_gate_passed')
            or coverage_report.get('metadata', {}).get('selected_relative_orbit') != cfg.relative_orbit
            or any(report_cfg.get(k) != asdict(cfg)[k] for k in controls)):
        raise ValueError('Matching successful Phase 2 coverage report required')
    if len(transform) != 6 or transform[0] != 30 or transform[4] != -30 or transform[1] or transform[3]:
        raise ValueError('Use an explicit aligned 30 m north-up grid')
    image = paired_graph(region, cfg).unmask(-9999, sameFootprint=False)
    return ee.batch.Export.image.toDrive(image=image, description=description,
        folder=folder, region=region, crs='EPSG:32646', crsTransform=list(transform),
        maxPixels=4_000_000, fileFormat='GeoTIFF', formatOptions={'noData': -9999})
