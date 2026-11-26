"""Fail-closed NRSC interpretation readiness; diagnostics never become QA or controls."""
import math


def quality_summary(coverage):
 result={}
 for season,row in coverage.items():
  count=row['valid_signal_cells'];flags=row['descriptive_flags']
  result[season]=dict(valid_signal_percent=row['valid_signal_percent'],native_pixel_centres=row['aoi_native_pixel_centres'],bright_proxy_cells=flags['bright_neutral_proxy'],dark_proxy_cells=flags['dark_surface_proxy'],dark_proxy_percent=100*flags['dark_surface_proxy']/count if count else None,cloud_clear_percent=None,cloud_percent=None,haze_percent=None,shadow_percent=None,provider_quality_verified=False,interpretation='Existing brightness/darkness flags are inspection proxies, not cloud/haze/shadow masks. Zero bright flags does not establish clear ground.')
 return result


def registration_summary(diagnostic,verified_landmarks):
 if verified_landmarks:raise ValueError('Reviewed independent controls require a separate explicit registration procedure; no automatic promotion')
 dx=diagnostic['after_shift_columns'];dy=diagnostic['after_shift_rows']
 return dict(accepted_independent_landmarks=0,relative_offset_estimate_m=None,relative_uncertainty_m=None,absolute_accuracy_m=None,correction_applied=False,diagnostic_only=dict(image_column_row_lag_pixels=[dx,dy],map_east_north_lag_m=[24*dx,-24*dy],lag_magnitude_m=24*math.hypot(dx,dy),best_correlation=diagnostic['best_correlation'],search_boundary=diagnostic['search_boundary'],search_step_m=24),status='UNRESOLVED_NO_QUALIFYING_CONTROLS',limitation='Texture-correlation lags are not stable-landmark estimates, confidence intervals, RMSE or CE90. Do not apply a shift or infer0muncertainty.')


def readiness(quality,registration,permissions):
 owner=permissions['private_research']=='SUPPORTED_CONDITIONALLY_REGISTERED_LAWFUL_USE'
 return dict(private_owner_qualitative_inspection=owner,external_reviewer_release=False,verified_reference_interpretation=False,model_input_eligible=False,label_admission=False,operational_alerts=0,blockers=['No independently verified distributed stable controls or positional uncertainty','No validated cloud/haze/shadow quality mask; clear fraction unknown','Exact-product reviewer sharing/public redistribution not confirmed','Two January dates alone do not establish a seasonal agricultural cycle'],provider_qa_complete=all(r['provider_quality_verified'] for r in quality.values()),control_count=registration['accepted_independent_landmarks'])
