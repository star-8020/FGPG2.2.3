import unittest
import numpy as np

from fine_gear_profile_generator.core import geometry_generator
from fine_gear_profile_generator.core import models

class TestGeometryGeneration(unittest.TestCase):
    def setUp(self):
        """Set up common parameters for geometry tests."""
        segmentation = models.SegmentationSettings(involute=20, edge=10, root_round=10)
        # A dummy driven gear is needed for the GearPairParameters model
        driven_spec = models.GearSpec(teeth=30, profile_shift=0.0)

        # Parameters for a standard gear (no undercut expected)
        driver_spec_std = models.GearSpec(teeth=20, profile_shift=0.5)
        self.standard_params = models.GearPairParameters(
            module=1.5,
            pressure_angle_deg=20.0,
            backlash_factor=0.1,
            addendum_factor=1.0,
            dedendum_factor=1.25,
            hob_edge_radius=0.2,
            tooth_edge_radius=0.1,
            driver=driver_spec_std,
            driven=driven_spec,
            segmentation=segmentation,
            root_fillet_method='rack_trochoid'
        )

        # Parameters likely to cause an undercut (low tooth count, no shift)
        driver_spec_undercut = models.GearSpec(teeth=10, profile_shift=0.0)
        self.undercut_params = models.GearPairParameters(
            module=1.5,
            pressure_angle_deg=20.0,
            backlash_factor=0.1,
            addendum_factor=1.0,
            dedendum_factor=1.25,
            hob_edge_radius=0.2,
            tooth_edge_radius=0.1,
            driver=driver_spec_undercut,
            driven=driven_spec,
            segmentation=segmentation,
            root_fillet_method='rack_trochoid'
        )

    def test_generate_single_tooth_profile_runs_successfully(self):
        """
        Tests that the main geometry generation function runs without raising exceptions
        and returns valid data structures.
        """
        try:
            profile, Z_calc, P_ANGLE, ALIGN_ANGLE, status = geometry_generator.generate_tooth_profile(
                params=self.standard_params, gear_type='driver'
            )

            # Check if the outputs are of the correct type
            self.assertIsInstance(profile, models.StructuredToothProfile)
            self.assertIsInstance(Z_calc, (int, float))
            self.assertIsInstance(P_ANGLE, float)
            self.assertIsInstance(ALIGN_ANGLE, float)
            self.assertIsInstance(status, str)

        except Exception as e:
            self.fail(f"generate_tooth_profile() raised an exception unexpectedly: {e}")

    def test_generated_coordinates_are_valid(self):
        """
        Tests that the generated coordinates are finite and non-empty, which is a
        proxy for checking spline smoothness and avoiding mathematical errors.
        """
        profile, _, _, _, _ = geometry_generator.generate_tooth_profile(
            params=self.standard_params, gear_type='driver'
        )

        all_vertices = []
        for element in profile.elements:
            if isinstance(element, models.Spline):
                all_vertices.extend(element.vertices)
            elif isinstance(element, models.Arc):
                self.assertTrue(np.all(np.isfinite(element.center)))
                self.assertTrue(np.isfinite(element.radius))
                self.assertTrue(np.isfinite(element.start_angle))
                self.assertTrue(np.isfinite(element.end_angle))

        # Check that we have some vertices from the splines
        self.assertTrue(len(all_vertices) > 0)

        # Check for finite values in spline vertices
        all_vertices_arr = np.array(all_vertices)
        self.assertTrue(np.all(np.isfinite(all_vertices_arr)))

    def test_undercut_is_corrected(self):
        """
        Tests that the system correctly identifies an undercut and that the geometry
        is generated with separate, unmerged splines.
        """
        profile, _, _, _, status = geometry_generator.generate_tooth_profile(
            params=self.undercut_params, gear_type='driver'
        )

        # Check that the undercut was detected and corrected
        self.assertEqual(status, "Corrected")

        # Check that the geometry is still valid
        all_vertices = []
        for element in profile.elements:
            if isinstance(element, models.Spline):
                all_vertices.extend(element.vertices)
        all_vertices_arr = np.array(all_vertices)
        self.assertTrue(np.all(np.isfinite(all_vertices_arr)))

        # In a corrected undercut, flank and root are separate.
        # We expect 6 splines: edge, flank, root (x2 for each side)
        spline_count = sum(1 for el in profile.elements if isinstance(el, models.Spline))
        self.assertEqual(spline_count, 6)

    def test_no_undercut_splines_are_merged(self):
        """
        Tests that the root and flank splines are correctly merged into a single
        profile spline when there is no undercut.
        """
        profile, _, _, _, status = geometry_generator.generate_tooth_profile(
            params=self.standard_params, gear_type='driver'
        )

        # Check that there was no undercut
        self.assertEqual(status, "OK")

        # When merged, root and flank become one.
        # We expect 4 splines: edge, profile (x2 for each side)
        spline_count = sum(1 for el in profile.elements if isinstance(el, models.Spline))
        self.assertEqual(spline_count, 4)

if __name__ == '__main__':
    unittest.main()