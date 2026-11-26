import json
from pathlib import Path
import pytest
from src.phase25.nrsc_readiness import quality_summary,registration_summary,readiness


def coverage(cells=1600,dark=0):
 return {'before':dict(valid_signal_cells=cells,aoi_native_pixel_centres=cells,valid_signal_percent=100 if cells else 0,descriptive_flags=dict(bright_neutral_proxy=0,dark_surface_proxy=dark))}


def diagnostic():return dict(after_shift_columns=-3,after_shift_rows=3,best_correlation=.64,search_boundary=True)


def test_zero_bright_or_dark_flags_never_prove_clear_ground():
 q=quality_summary(coverage())['before']
 assert q['dark_proxy_percent']==0 and q['cloud_percent'] is None and q['cloud_clear_percent'] is None
 assert q['haze_percent'] is None and q['shadow_percent'] is None and not q['provider_quality_verified']


def test_proxy_percent_is_descriptive_and_no_support_undefined():
 assert quality_summary(coverage(1600,4))['before']['dark_proxy_percent']==.25
 assert quality_summary(coverage(0))['before']['dark_proxy_percent'] is None


def test_no_control_means_unknown_offset_uncertainty_not_zero():
 r=registration_summary(diagnostic(),[])
 assert r['relative_offset_estimate_m'] is None and r['relative_uncertainty_m'] is None and r['absolute_accuracy_m'] is None
 assert r['accepted_independent_landmarks']==0 and not r['correction_applied']
 assert r['diagnostic_only']['map_east_north_lag_m']==[-72,-72]


def test_unreviewed_controls_cannot_trigger_automatic_registration():
 with pytest.raises(ValueError):registration_summary(diagnostic(),[dict(x=1,y=1)])


def test_reviewer_and_model_gates_remain_blocked():
 policy=json.loads(Path('config/phase25_nrsc_permissions_v1.json').read_bytes());r=readiness(quality_summary(coverage()),registration_summary(diagnostic(),[]),policy)
 assert r['private_owner_qualitative_inspection'] and not r['external_reviewer_release'] and not r['label_admission'] and not r['model_input_eligible']
 assert policy['reviewer_sharing'].startswith('BLOCKED') and policy['public_redistribution'].startswith('BLOCKED')
 assert r['operational_alerts']==0
