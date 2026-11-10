// Phase 1 Earth Engine Code Editor exploration.
// GAUL 2015 administrative units may not match current district boundaries.
// If a district is absent, upload a verified boundary rather than guessing.
var names = ['East Jaintia Hills', 'West Jaintia Hills'];
var admin = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM0_NAME', 'India'))
  .filter(ee.Filter.eq('ADM1_NAME', 'Meghalaya'));
print('Available GAUL ADM2 names in Meghalaya:', admin.aggregate_array('ADM2_NAME').distinct().sort());
var area = admin.filter(ee.Filter.inList('ADM2_NAME', names));
print('Matched features (expect 2):', area.size());
print('Study area km2 (inspect only if matched):', area.geometry().area(100).divide(1e6));
Map.centerObject(admin, 8);
Map.addLayer(admin.style({color:'808080', fillColor:'00000000'}), {}, 'Meghalaya GAUL units');
Map.addLayer(area.style({color:'FF9900', fillColor:'FF990022', width:2}), {}, 'Selected districts');
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(area).filterDate('2023-11-01','2024-04-01')
  .filter(ee.Filter.eq('instrumentMode','IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation','VV'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation','VH'));
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(area).filterDate('2023-11-01','2024-04-01');
print('2023-24 raw S1 count:',s1.size());
print('2023-24 raw S2 count:',s2.size());
// Deliberately no large image rendering/export in this setup phase.
