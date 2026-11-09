"""Drive the real Tkinter GUI.

Skipped automatically when Tk or a display is not available.  In CI the
suite runs under ``xvfb-run`` so these tests execute there.
"""

import os
import tempfile
import unittest

try:
    import tkinter as tk
    _root = tk.Tk()
    _root.destroy()
    TK_AVAILABLE = True
except Exception:  # ImportError (no Tk) or TclError (no display)
    TK_AVAILABLE = False


@unittest.skipUnless(TK_AVAILABLE, "Tkinter with a display is required")
class TestGearAppGui(unittest.TestCase):

    def setUp(self):
        from fine_gear_profile_generator.gui import fgpg_gui

        self.fgpg_gui = fgpg_gui
        self.errors = []
        self._orig_showerror = fgpg_gui.messagebox.showerror
        fgpg_gui.messagebox.showerror = lambda title, msg: self.errors.append(msg)
        self._tmp = tempfile.TemporaryDirectory()
        self.app = fgpg_gui.GearApp()
        self.app.withdraw()
        self.app.vars['working_directory'].set(self._tmp.name)

    def tearDown(self):
        self.app.destroy()
        self.fgpg_gui.messagebox.showerror = self._orig_showerror
        self._tmp.cleanup()

    def test_run_rack_and_shaper(self):
        for method in ('rack_trochoid', 'shaper_trochoid'):
            with self.subTest(method=method):
                self.app.vars['root_fillet_method'].set(method)
                self.app._toggle_shaper_widgets()
                self.app.run_calculation()
                self.assertEqual(self.errors, [])
                self.assertTrue(self.app.status_var.get().startswith("Run: OK"))
                self.assertEqual(self.app.vars['contact_ratio'].get(), "1.5471")
                self.assertTrue(os.path.exists(os.path.join(self._tmp.name, 'Result_Gear_Pair.dxf')))

    def test_shaper_frame_visibility_follows_method(self):
        self.app.vars['root_fillet_method'].set('shaper_trochoid')
        self.app._toggle_shaper_widgets()
        self.assertTrue(self.app.shaper_frame.grid_info())
        self.app.vars['root_fillet_method'].set('rack_trochoid')
        self.app._toggle_shaper_widgets()
        self.assertFalse(self.app.shaper_frame.grid_info())

    def test_invalid_input_shows_error(self):
        self.app.vars['root_fillet_method'].set('shaper_trochoid')
        self.app.vars['shaper_n0'].set('3')
        self.app.run_calculation()
        self.assertEqual(len(self.errors), 1)
        self.assertIn('>= 5', self.errors[0])

    def test_save_then_load_restores_values(self):
        self.app.vars['root_fillet_method'].set('shaper_trochoid')
        self.app.vars['shaper_n0'].set('42')
        self.app.save_params_to_file()
        self.app.vars['root_fillet_method'].set('rack_trochoid')
        self.app.vars['shaper_n0'].set('99')
        self.app.load_params_from_file()
        self.assertEqual(self.app.vars['shaper_n0'].get(), '42')
        self.assertTrue(self.app.shaper_frame.grid_info())  # toggled after load


if __name__ == '__main__':
    unittest.main()
