import json
from unittest.mock import Mock, patch
import pytest
from config.settings import DISTRICTS
from config.phase2_settings import Phase2Config
from src.coverage_diagnostics import COVERAGE_BANDS, summarize_districts
from src.evaluation_support import validate_evaluation_audit
from phase2 import processing_region
import phase2


def coverage_raw():
    return {'areas': {'features': [{'properties': {
        'GAUL2_NAME': name, 'total_area_m2': 100,
        **{band: 95 for band in COVERAGE_BANDS}}} for name in DISTRICTS]}}


def test_full_region_skips_centroid_and_containment():
    boundary = Mock()
    assert processing_region(boundary, True, None, Phase2Config()) is boundary
    boundary.centroid.assert_not_called()
    boundary.contains.assert_not_called()


def test_small_region_rejects_outside_centroid():
    boundary = Mock()
    boundary.contains.return_value.getInfo.return_value = False
    with pytest.raises(ValueError, match='outside'):
        processing_region(boundary, False, None, Phase2Config())


def test_small_region_keeps_bounded_buffer():
    boundary = Mock()
    boundary.contains.return_value.getInfo.return_value = True
    processing_region(boundary, False, None, Phase2Config())
    boundary.centroid.return_value.buffer.assert_called_once_with(500)


def test_full_region_records_and_blocks_failed_coverage(tmp_path):
    boundary, stack = Mock(), Mock()
    stack.bandNames.return_value.getInfo.return_value = ['dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope']
    with (patch.object(phase2, 'initialize'), patch.object(phase2.ee.data, 'setDeadline'),
          patch.object(phase2, 'get_study_area'),
          patch.object(phase2, 'verify_boundary', return_value=boundary),
          patch.object(phase2, 'build', return_value=(stack, Mock(), {'selected_relative_orbit': 77})),
          patch.object(phase2, 'district_diagnostics', return_value={
              'coverage_gate_passed': False, 'sar_adequate': False, 'common_adequate': False})):
        with pytest.raises(ValueError, match='coverage gate failed'):
            phase2.main(['--full-region', '--output-dir', str(tmp_path)])
    report = json.loads((tmp_path / 'phase2_report.json').read_text())
    assert report['status'] == 'failed'
    assert report['district_coverage_checked']
    assert not report['district_coverage']['sar_adequate']
    boundary.centroid.assert_not_called()
    boundary.contains.assert_not_called()


@pytest.mark.parametrize('district', [0, 1])
@pytest.mark.parametrize('season', ['sar_before_valid', 'sar_after_valid'])
def test_each_district_and_sar_season_must_pass(district, season):
    raw = coverage_raw()
    assert summarize_districts(raw, Phase2Config())['coverage_gate_passed']
    raw['areas']['features'][district]['properties'][season] = 89
    result = summarize_districts(raw, Phase2Config())
    assert not result['sar_adequate']
    assert not result['coverage_gate_passed']


def test_common_gate_is_independent_of_sar_gate():
    raw = coverage_raw()
    raw['areas']['features'][0]['properties']['common_valid'] = 69
    result = summarize_districts(raw, Phase2Config())
    assert result['sar_adequate'] and not result['common_adequate']


@pytest.mark.parametrize('value', [None, float('nan'), -1, 101])
def test_bad_coverage_values_fail(value):
    raw = coverage_raw()
    raw['areas']['features'][0]['properties']['sar_before_valid'] = value
    with pytest.raises(ValueError):
        summarize_districts(raw, Phase2Config())


def test_missing_district_or_denominator_fails():
    raw = coverage_raw()
    with pytest.raises(ValueError):
        summarize_districts({'areas': {'features': raw['areas']['features'][:1]}}, Phase2Config())
    raw['areas']['features'][0]['properties']['total_area_m2'] = 0
    with pytest.raises(ValueError):
        summarize_districts(raw, Phase2Config())


@pytest.mark.parametrize('kwargs', [{'coverage_scale_m': 249}, {'coverage_scale_m': 2001},
    {'min_sar_coverage': 0}, {'min_sar_coverage': 1.01}, {'min_common_coverage': float('nan')}])
def test_diagnostic_configuration_validation(kwargs):
    with pytest.raises(ValueError):
        Phase2Config(**kwargs)


def audit():
    return dict(input_count=10, complete_input_count=10, unique_input_ids=10,
                geometry_types={'Point': 10}, sampled_count=10, unique_sampled_ids=10)


@pytest.mark.parametrize('field,value', [
    ('input_count', 0), ('complete_input_count', 9), ('unique_input_ids', 9),
    ('geometry_types', {'Polygon': 10}), ('sampled_count', 0), ('unique_sampled_ids', 9)])
def test_evaluation_rejects_invalid_or_empty_input(field, value):
    data = audit()
    data[field] = value
    with pytest.raises(ValueError):
        validate_evaluation_audit(data)


def test_evaluation_drops_require_explicit_opt_in():
    data = audit()
    assert validate_evaluation_audit(data)['retained_count'] == 10
    data.update(sampled_count=8, unique_sampled_ids=8)
    with pytest.raises(ValueError, match='lack six-band'):
        validate_evaluation_audit(data)
    assert validate_evaluation_audit(data, allow_dropped=True)['excluded_count'] == 2
