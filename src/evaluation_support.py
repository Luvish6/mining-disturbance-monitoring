"""One audited held-out table shared by every Phase 3 ablation; no training."""
import ee
from config.phase2_settings import STACK_BANDS, ABLATIONS
from src.coverage_diagnostics import common_valid_mask


def validate_evaluation_audit(audit, allow_dropped=False):
    n = audit['input_count']
    if n <= 0:
        raise ValueError('Held-out locations must not be empty')
    if audit['geometry_types'] != {'Point': n}:
        raise ValueError('Held-out locations must be Point features')
    if audit['complete_input_count'] != n or audit['unique_input_ids'] != n:
        raise ValueError('Held-out locations need non-null labels and unique non-null IDs')
    sampled = audit['sampled_count']
    if sampled <= 0 or audit['unique_sampled_ids'] != sampled or sampled > n:
        raise ValueError('Shared evaluation samples are empty or contain duplicate IDs')
    if sampled != n and not allow_dropped:
        raise ValueError('Some held-out locations lack six-band data; use an explicit common-valid set')
    return {'input_count': n, 'retained_count': sampled, 'excluded_count': n - sampled}


def shared_evaluation_samples(stack, heldout_points, cfg, id_property='sample_id',
                              label_property='label', allow_dropped=False):
    """Sample all six bands once; subset the same rows for all four models.

    Input must be an independently held-out Point collection with stable unique
    IDs and labels. Missing rows fail by default. Explicit allow_dropped=True
    records attrition for a deliberately restricted common-footprint experiment.
    """
    if (not id_property or not label_property or id_property == label_property
            or id_property in STACK_BANDS or label_property in STACK_BANDS):
        raise ValueError('Choose distinct ID/label properties outside the feature band names')
    heldout_points = ee.FeatureCollection(heldout_points)
    properties = [id_property, label_property]
    master = stack.select(list(STACK_BANDS)).updateMask(common_valid_mask(stack)).sampleRegions(
        collection=heldout_points, properties=properties, scale=cfg.analysis_scale_m,
        projection=ee.Projection(cfg.analysis_crs), tileScale=2, geometries=True)
    audit = ee.Dictionary({
        'input_count': heldout_points.size(),
        'complete_input_count': heldout_points.filter(ee.Filter.notNull(properties)).size(),
        'unique_input_ids': heldout_points.aggregate_count_distinct(id_property),
        'geometry_types': heldout_points.map(lambda f: f.set('_eval_geometry_type', f.geometry().type()))
                                        .aggregate_histogram('_eval_geometry_type'),
        'sampled_count': master.size(),
        'unique_sampled_ids': master.aggregate_count_distinct(id_property),
    }).getInfo()
    summary = validate_evaluation_audit(audit, allow_dropped=allow_dropped)
    tables = {name: master.select(properties + list(bands)) for name, bands in ABLATIONS.items()}
    return {'master': master, 'experiments': tables, 'audit': summary,
            'crs': cfg.analysis_crs, 'scale_m': cfg.analysis_scale_m}
