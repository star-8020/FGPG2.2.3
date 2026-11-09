"""End-to-end tests: models, configuration, gear_core and the headless entry point."""

import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest import mock

import ezdxf

from fine_gear_profile_generator import main as fgpg_main
from fine_gear_profile_generator.core import gear_core
from fine_gear_profile_generator.core.models import GearPairParameters
from fine_gear_profile_generator.utils import config_manager, output_naming


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
            dxf = [f for f in files if f.endswith('.dxf')]
            doc = ezdxf.readfile(os.path.join(tmp, dxf[0])) if dxf else None
            return code, files, doc

    def test_headless_rack(self):
        code, files, doc = self._run('rack_trochoid')
        self.assertEqual(code, 0)
        self.assertEqual(len(files), 3)
        self.assertEqual({os.path.splitext(f)[1] for f in files}, {'.png', '.dxf', '.json'})
        self.assertTrue(all(f.startswith('FGPG_m1_z18x0.2_z36x0_rack_') for f in files), files)
        self.assertEqual(doc.units, ezdxf.units.MM)
        msp = doc.modelspace()
        self.assertGreater(len(msp.query('SPLINE')), 0)
        self.assertGreater(len(msp.query('ARC')), 0)

    def test_headless_shaper(self):
        code, files, _ = self._run('shaper_trochoid', 30)
        self.assertEqual(code, 0)
        self.assertEqual(len(files), 3)
        self.assertTrue(all('_shaper-n30_' in f for f in files), files)

    def test_repeated_runs_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch('sys.stdout'):
            for _ in range(3):
                self.assertEqual(fgpg_main.run_headless_mode(tmp, name=None), 0)
            self.assertEqual(len(os.listdir(tmp)), 9)

    def test_explicit_name(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch('sys.stdout'):
            fgpg_main.run_headless_mode(tmp, name='pump_gear')
            self.assertEqual(sorted(os.listdir(tmp)),
                             ['pump_gear.dxf', 'pump_gear.json', 'pump_gear.png'])

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

    def test_save_and_load_parameter_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'sub', 'my_gear.json')
            ok, _ = config_manager.save_params(path, {'module_m': '2.0'})
            self.assertTrue(ok)
            ok, data = config_manager.load_params(path)
            self.assertTrue(ok)
            self.assertEqual(data, {'module_m': '2.0'})

    def test_load_reports_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'Inputs.dat')
            with open(path, 'w', encoding='utf-8') as f:
                f.write('{broken')
            ok, message = config_manager.load_params(path)
            self.assertFalse(ok)
            self.assertIn('not a valid JSON', message)

    def test_load_old_inputs_dat_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'Inputs.dat')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'shaper_teeth_n0': '120'}, f)
            ok, data = config_manager.load_params(path)
            self.assertTrue(ok)
            self.assertEqual(data, {'shaper_n0': '120'})

    def test_load_result_record(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch('sys.stdout'):
            fgpg_main.run_headless_mode(tmp, 'shaper_trochoid', 30, name='run1')
            ok, data = config_manager.load_params(os.path.join(tmp, 'run1.json'))
            self.assertTrue(ok)
            self.assertEqual(data['root_fillet_method'], 'shaper_trochoid')
            self.assertEqual(data['shaper_n0'], 30)
            with open(os.path.join(tmp, 'run1.json'), encoding='utf-8') as f:
                record = json.load(f)
            self.assertEqual(record['files'], {'png': 'run1.png', 'dxf': 'run1.dxf'})
            self.assertAlmostEqual(record['results']['contact_ratio'], 1.5471, places=4)


class TestOutputNaming(unittest.TestCase):

    def test_description(self):
        params = config_manager.get_default_gear_pair_parameters({
            'defaults': {'module_m': 2.0, 'teeth_number_z': 21, 'offset_factor_x': 0.25,
                         'teeth_number_z2': -60, 'offset_factor_x2': -0.1},
        })
        self.assertEqual(output_naming.describe_parameters(params), 'm2_z21x0.25_z-60x-0.1_rack')

    def test_same_second_gets_suffix(self):
        params = config_manager.get_default_gear_pair_parameters({})
        now = datetime(2026, 11, 9, 15, 30, 12)
        with tempfile.TemporaryDirectory() as tmp:
            first = output_naming.unique_basename(tmp, params, now)
            self.assertEqual(first, 'FGPG_m1_z18x0.2_z36x0_rack_20261109-153012')
            open(os.path.join(tmp, first + '.dxf'), 'w').close()
            self.assertEqual(output_naming.unique_basename(tmp, params, now), first + '_2')


if __name__ == '__main__':
    unittest.main()
