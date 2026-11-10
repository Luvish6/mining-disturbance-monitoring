"""Explicit, validated Phase 2 controls; Phase 1 settings remain unchanged."""
from dataclasses import dataclass
import math

ABLATIONS = {
    'sar': ('dVV', 'dVH'),
    'optical': ('dNDVI', 'dNDTI'),
    'fused': ('dVV', 'dVH', 'dNDVI', 'dNDTI'),
    'fused_terrain': ('dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope'),
}
STACK_BANDS = ABLATIONS['fused_terrain']


@dataclass(frozen=True)
class Phase2Config:
    orbit_pass: str = 'DESCENDING'
    relative_orbit: int | None = None
    cloud_probability: int = 40
    scene_cloud_percent: int = 80
    speckle_radius_m: float = 20
    min_observations: int = 2
    smoke_radius_m: float = 500
    analysis_scale_m: int = 30
    analysis_crs: str = 'EPSG:32646'
    coverage_scale_m: int = 500
    min_sar_coverage: float = 0.90
    min_common_coverage: float = 0.70

    def __post_init__(self):
        if self.orbit_pass not in ('ASCENDING', 'DESCENDING'):
            raise ValueError('orbit_pass must be ASCENDING or DESCENDING')
        if self.relative_orbit is not None and not 1 <= self.relative_orbit <= 175:
            raise ValueError('relative_orbit must be in [1, 175]')
        for value in (self.cloud_probability, self.scene_cloud_percent):
            if not 0 <= value <= 100:
                raise ValueError('Cloud thresholds must be in [0, 100]')
        if not math.isfinite(self.speckle_radius_m) or not 0 <= self.speckle_radius_m <= 100:
            raise ValueError('Speckle radius must be in [0, 100] metres')
        if self.min_observations < 1:
            raise ValueError('min_observations must be positive')
        if not math.isfinite(self.smoke_radius_m) or not 100 <= self.smoke_radius_m <= 1000:
            raise ValueError('Smoke radius must be in [100, 1000] metres')
        if self.analysis_scale_m < 20:
            raise ValueError('Use a diagnostic/export scale of at least 20 m')
        if not 250 <= self.coverage_scale_m <= 2000:
            raise ValueError('coverage_scale_m must be in [250, 2000]')
        for value in (self.min_sar_coverage, self.min_common_coverage):
            if not math.isfinite(value) or not 0 < value <= 1:
                raise ValueError('Coverage thresholds must be finite and in (0, 1]')
