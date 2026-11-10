"""Optional interactive layers, initially hidden to avoid unsolicited tile work."""
from src.coverage_diagnostics import COUNT_BANDS, COVERAGE_BANDS, validity_image


def add_diagnostic_layers(m, stack, counts, cfg, districts=None):
    for band in ('dVV', 'dVH', 'dNDVI', 'dNDTI'):
        limit = 5 if band in ('dVV', 'dVH') else 0.4
        m.addLayer(stack.select(band), {'min': -limit, 'max': limit,
                   'palette': ['blue', 'white', 'red']}, band, False)
    for band in COUNT_BANDS:
        m.addLayer(counts.select(band), {'min': 0, 'max': 20 if band.startswith('sar') else 60,
                   'palette': ['black', 'orange', 'green']}, band, False)
    valid = validity_image(stack, counts, cfg)
    for band in COVERAGE_BANDS:
        m.addLayer(valid.select(band), {'min': 0, 'max': 1,
                   'palette': ['red', 'green']}, band, False)
    if districts is not None:
        m.addLayer(districts.style(color='FFFF00', fillColor='00000000', width=2),
                   {}, 'District boundaries', False)
