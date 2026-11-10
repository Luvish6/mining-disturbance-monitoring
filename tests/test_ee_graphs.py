"""Offline API graph checks, not evidence of server pixel execution."""
import json
from unittest.mock import patch
import ee
from ee.apitestcase import ApiTestCase
from config.settings import BEFORE, AFTER
from config.phase2_settings import Phase2Config
from src import sar_preprocessing as sar, optical_preprocessing as optical
from src.change_features import build_stack, ablation
from phase2 import smoke
from src.coverage_diagnostics import district_diagnostics_graph, COUNT_BANDS
from src.evaluation_support import shared_evaluation_samples
from src.diagnostic_maps import add_diagnostic_layers
from unittest.mock import Mock


class GraphTests(ApiTestCase):
    def test_coarse_coverage_graph_has_bounded_reductions_and_zero_fill(self):
        stack = ee.Image.constant([1] * 6).rename(
            ['dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope'])
        counts = ee.Image.constant([3] * 4).rename(list(COUNT_BANDS))
        districts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([92, 25]).buffer(500),
                                                      {'GAUL2_NAME': 'test'})])
        graph = district_diagnostics_graph(stack, counts, districts, Phase2Config()).serialize()
        assert 'maxPixelsPerRegion' in graph and '100000' in graph
        assert 'sameFootprint' in graph and 'false' in graph
        assert 'Reducer.percentile' in graph

    def test_all_diagnostic_layers_are_present_and_hidden(self):
        stack = ee.Image.constant([1] * 6).rename(
            ['dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope'])
        counts = ee.Image.constant([3] * 4).rename(list(COUNT_BANDS))
        m = Mock()
        add_diagnostic_layers(m, stack, counts, Phase2Config())
        names = [call.args[2] for call in m.addLayer.call_args_list]
        assert set(('dVV', 'dVH', 'dNDVI', 'dNDTI') + COUNT_BANDS).issubset(names)
        assert 'common_valid' in names
        assert all(call.args[3] is False for call in m.addLayer.call_args_list)

    def test_evaluation_tables_share_one_sample_graph(self):
        stack = ee.Image.constant([1] * 6).rename(
            ['dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope'])
        points = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([92, 25]),
                                                   {'sample_id': 'a', 'label': 1})])
        audit = dict(input_count=1, complete_input_count=1, unique_input_ids=1,
                     geometry_types={'Point': 1}, sampled_count=1, unique_sampled_ids=1)
        with patch.object(ee.Dictionary, 'getInfo', return_value=audit):
            result = shared_evaluation_samples(stack, points, Phase2Config())
        assert result['audit']['retained_count'] == 1
        for table in result['experiments'].values():
            graph = table.serialize()
            assert graph.count('Image.sampleRegions') == 1
            assert 'EPSG:32646' in graph
        with self.assertRaises(ValueError):
            shared_evaluation_samples(stack, points, Phase2Config(), id_property='dVV')

    def test_end_to_end_graph_serializes_with_native_sar_projection(self):
        cfg = Phase2Config()
        region = ee.Geometry.Point([92.35, 25.35]).buffer(500)
        s = [sar.seasonal(sar.collection(region, t, cfg), 63, region, cfg)
             for t in (BEFORE, AFTER)]
        o = [optical.seasonal(optical.collections(region, t, cfg)[1], region, cfg)
             for t in (BEFORE, AFTER)]
        stack = build_stack(s[0][0], s[1][0], o[0][0], o[1][0], region)
        graph = json.loads(stack.serialize())
        def function_names(value):
            if isinstance(value, dict):
                if 'functionName' in value:
                    yield value['functionName']
                for child in value.values():
                    yield from function_names(child)
            elif isinstance(value, list):
                for child in value:
                    yield from function_names(child)
        functions = set(function_names(graph))
        assert 'Image.exp' in functions
        assert 'Image.log10' in functions
        assert 'Image.focal_mean' in functions
        assert 'Join.saveFirst' in functions
        assert 'Terrain.slope' in functions
        for name in ('sar', 'optical', 'fused', 'fused_terrain'):
            assert ablation(stack, name).serialize()

    def test_smoke_requires_common_valid_pixels(self):
        region = ee.Geometry.Point([92.35, 25.35]).buffer(500)
        stack = ee.Image.constant([1] * 6).rename(
            ['dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope'])
        values = {b + '_valid_fraction_mean': 1 for b in
                  ['dVV', 'dVH', 'dNDVI', 'dNDTI', 'elevation', 'slope']}
        with patch.object(ee.Dictionary, 'getInfo', return_value=values):
            assert not smoke(stack, ee.Image.constant(1), region, Phase2Config())[1]
            values['common_valid_fraction_mean'] = 1
            assert smoke(stack, ee.Image.constant(1), region, Phase2Config())[1]
