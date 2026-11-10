"""Lightweight collection inventory; no pixel processing or exports."""
import ee
from config.settings import BEFORE, AFTER

COLLECTIONS = {
    'Sentinel-1 GRD': 'COPERNICUS/S1_GRD',
    'Sentinel-2 SR Harmonized': 'COPERNICUS/S2_SR_HARMONIZED',
    'Sentinel-2 cloud probability': 'COPERNICUS/S2_CLOUD_PROBABILITY',
}

def inventory(geometry):
    results = {}
    for season in (BEFORE, AFTER):
        results[season.name] = {}
        for name, asset in COLLECTIONS.items():
            col = ee.ImageCollection(asset).filterBounds(geometry).filterDate(season.start, season.end)
            if name == 'Sentinel-1 GRD':
                col = (col.filter(ee.Filter.eq('instrumentMode', 'IW'))
                         .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                         .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')))
            results[season.name][name] = col.size().getInfo()
    return results
