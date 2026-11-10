import math
import pytest
from config.phase2_settings import Phase2Config, STACK_BANDS, ABLATIONS
from src.sar_preprocessing import choose_orbit


@pytest.mark.parametrize('kwargs', [
    {'orbit_pass': 'BOTH'}, {'relative_orbit': 0}, {'relative_orbit': 176},
    {'cloud_probability': -1}, {'scene_cloud_percent': 101},
    {'speckle_radius_m': -1}, {'speckle_radius_m': math.nan},
    {'min_observations': 0}, {'smoke_radius_m': 1001}, {'analysis_scale_m': 10},
])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        Phase2Config(**kwargs)


def test_orbit_selection_balances_seasons_and_breaks_ties():
    assert choose_orbit({'77.0': 8}, {'77': 9}) == 77
    assert choose_orbit({'1': 20, '2': 8, '3': 8}, {'1': 1, '2': 9, '3': 9}) == 2
    assert choose_orbit({'1': 20, '2': 8}, {'1': 1, '2': 9}, 1) == 1


def test_orbit_selection_fails_closed():
    with pytest.raises(ValueError):
        choose_orbit({'1': 2}, {'2': 3})
    with pytest.raises(ValueError):
        choose_orbit({'1': 2}, {'1': 3}, 2)


def test_ablation_contract():
    assert STACK_BANDS == ('dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope')
    assert ABLATIONS['fused'] == ABLATIONS['sar'] + ABLATIONS['optical']
