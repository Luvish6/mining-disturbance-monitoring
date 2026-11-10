"""Offline graph verification only, not live satellite-data validation."""
from ee.apitestcase import ApiTestCase
import ee
from config.phase2_settings import Phase2Config
from src.phase3.ee_inputs import paired_graph, export_task
from src.coverage_diagnostics import district_diagnostics_graph, COUNT_BANDS


class Phase3Graphs(ApiTestCase):
    def test_coverage_materializes_bounded_property_rows(self):
        stack = ee.Image.constant([1]*6).rename(['dVV','dVH','dNDVI','dNDTI','elevation','slope'])
        counts = ee.Image.constant([3]*4).rename(list(COUNT_BANDS))
        districts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([92,25]).buffer(500),{'GAUL2_NAME':'test'})])
        graph = district_diagnostics_graph(stack,counts,districts,Phase2Config()).serialize()
        assert 'Collection.toList' in graph and 'features' in graph

    def test_paired_channels_and_no_implicit_exports(self):
        region = ee.Geometry.Point([92.35,25.35]).buffer(500)
        graph = paired_graph(region,Phase2Config(relative_orbit=77)).serialize()
        for band in ('before_VV','after_VV','before_NDVI','after_NDTI','elevation'):
            assert band in graph
        with self.assertRaises(ValueError):
            paired_graph(region,Phase2Config())
        with self.assertRaises(ValueError):
            export_task(region,Phase2Config(relative_orbit=77),{},'test')
