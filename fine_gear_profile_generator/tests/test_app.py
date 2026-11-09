"""End-to-end tests: models, configuration, gear_core and the headless entry point."""

import json
import os
import tempfile
import unittest
from unittest import mock

import ezdxf

from fine_gear_profile_generator import main as fgpg_main
from fine_gear_profile_generator.core import gear_core
from fine_gear_profile_generator.core.models import GearPairParameters
from fine_gear_profile_generator.utils import config_manager


class TestModelsAndConfig(unittest.TestCase):

    def test_from_dict_without_fillet_method(self):
        legacy = config_manager.get_default_calculation_params({})
        legacy.pop('FILLET_METHOD')
        params = GearPairParameters.from_dict(legacy)
        self.assertEqual(params.root_fillet_method, 'rack_trochoid')
        result = gear_core.generate_gear_pair(legacy)
        self.assertGreater(result.analysis.contact_ratio, 1.0)

    def test_dict_round_trip_keeps_fillet_method(self):
        params = config_manager.get_default_gear_pair_parameters({})
        data = params.to_calculation_dict()
        data['FILLET_METHOD'] = 'shaper_trochoid'
        self.assertEqual(GearPairParameters.from_dict(data).root_fillet_method, 'shaper_trochoid')

    def test_unknown_fillet_method_rejected(self):
        params = config_manager.get_default_gear_pair_parameters({})
        data = params.to_calculation_dict()
        data['FILLET_METHOD'] = 'magic'
        with self.assertRaisesRegex(ValueError, "Unknown root fillet method"):
            GearPairParameters.from_dict(data)

    def test_shaper_defaults_from_config(self):
        config = {
            'defaults': {'root_fillet_method': 'shaper_trochoid'},
            'shaper_cutter_defaults': {'n0': 33, 'tip_radius_factor': 0.25},
        }
        params = config_manager.get_default_gear_pair_parameters(config)
        self.assertEqual(params.shaper_cutter.teeth, 33)
        self.assertEqual(params.shaper_cutter.tip_radius_factor, 0.25)
        self.assertEqual(params.shaper_cutter.protuberance_factor, 0.0)

    def test_blank_tip_radius_means_hob_edge_radius(self):
        cutter = config_manager.build_shaper_cutter_parameters({'n0': '40', 'tip_radius_factor': ''})
        self.assertIsNone(cutter.tip_radius_factor)

    def test_repository_config_is_valid(self):
        config = config_manager.load_app_config()
        self.assertTrue(config, "config.json could not be loaded")
        params = config_manager.get_default_gear_pair_parameters(config)
        gear_core.generate_gear_pair(params)

    def test_relative_working_directory_resolves_to_project_root(self):
        resolved = config_manager.resolve_working_directory('./result/')
        self.assertEqual(os.path.dirname(resolved), os.path.dirname(config_manager.get_config_path()))


class TestGearCore(unittest.TestCase):

    def test_undercut_status_comes_from_geometry(self):
        params = config_manager.get_default_gear_pair_parameters({
            'defaults': {'teeth_number_z': 10, 'offset_factor_x': 0.0},
        })
        result = gear_core.generate_gear_pair(params)
        self.assertEqual(result.gear1.undercut_status, "Undercut (profile corrected)")
        self.assertEqual(result.gear2.undercut_status, "OK")


class TestHeadless(unittest.TestCase):

    def _run(self, *args):
        with tempfile.TemporaryDirectory() as tmp, mock.patch('sys.stdout'):
            code = fgpg_main.run_headless_mode(tmp, *args)
            files = sorted(os.listdir(tmp))
            dxf_path = os.path.join(tmp, 'Result_Gear_Pair.dxf')
            doc = ezdxf.readfile(dxf_path) if os.path.exists(dxf_path) else None
            return code, files, doc

    def test_headless_rack(self):
        code, files, doc = self._run('rack_trochoid')
        self.assertEqual(code, 0)
        self.assertEqual(files, ['Result1.png', 'Result_Gear_Pair.dxf'])
        self.assertEqual(doc.units, ezdxf.units.MM)
        msp = doc.modelspace()
        self.assertGreater(len(msp.query('SPLINE')), 0)
        self.assertGreater(len(msp.query('ARC')), 0)

    def test_headless_shaper(self):
        code, files, _ = self._run('shaper_trochoid', 30)
        self.assertEqual(code, 0)
        self.assertEqual(files, ['Result1.png', 'Result_Gear_Pair.dxf'])

    def test_headless_reports_errors_with_exit_code(self):
        code, _, _ = self._run('shaper_trochoid', 2)  # invalid cutter
        self.assertEqual(code, 1)

    def test_main_does_not_need_tkinter_for_headless(self):
        with mock.patch.dict('sys.modules', {'tkinter': None}):
            with self.assertRaises(SystemExit) as ctx, tempfile.TemporaryDirectory() as tmp, \
                    mock.patch('sys.stdout'):
                fgpg_main.main(['--headless', '--output-dir', tmp])
        self.assertEqual(ctx.exception.code, 0)


class TestParamPersistence(unittest.TestCase):

    def test_save_and_load_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok, _ = config_manager.save_params(tmp, {'module_m': '2.0'})
            self.assertTrue(ok)
            ok, data = config_manager.load_params(tmp)
            self.assertTrue(ok)
            self.assertEqual(data, {'module_m': '2.0'})
            with open(os.path.join(tmp, 'Inputs.dat'), 'w', encoding='utf-8') as f:
                f.write('{broken')
            ok, message = config_manager.load_params(tmp)
            self.assertFalse(ok)
            self.assertIn('not a valid JSON', message)

    def test_written_inputs_are_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_manager.save_params(tmp, {'a': 1})
            with open(os.path.join(tmp, 'Inputs.dat'), encoding='utf-8') as f:
                self.assertEqual(json.load(f), {'a': 1})


if __name__ == '__main__':
    unittest.main()
