"""Lazy change stack with independent band masks for fair sensor ablations."""
import ee
from config.phase2_settings import ABLATIONS, STACK_BANDS


def build_stack(sar_before, sar_after, optical_before, optical_after, region):
    sar = sar_after.subtract(sar_before).rename(['dVV', 'dVH'])
    optical = optical_after.subtract(optical_before).rename(['dNDVI', 'dNDTI'])
    elevation = ee.Image('USGS/SRTMGL1_003').select('elevation')
    # Derive slope at the DEM's native projection before clipping.
    terrain = elevation.addBands(ee.Terrain.slope(elevation).rename('slope'))
    return sar.addBands(optical).addBands(terrain).select(list(STACK_BANDS)).clip(region)


def ablation(stack, experiment):
    selected = stack.select(list(ABLATIONS[experiment]))
    return selected.updateMask(selected.mask().reduce(ee.Reducer.min()))
