import unittest
import numpy as np

from fine_gear_profile_generator.core import geometry_generator
from fine_gear_profile_generator.core import models

class TestGeometryGeneration(unittest.TestCase):
    """Test suite for the core geometry generation logic.

    This class contains tests that validate the output of the tooth profile
    generation functions, including handling of standard cases, undercutting,
    and the structural integrity of the generated geometric data.
    """
    def setUp(self):
        """Set up common parameters and configurations for geometry tests."""
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
        """Test that geometry generation runs without errors.

        This test ensures that the main geometry generation function can be
        called with standard parameters without raising any exceptions and that
        it returns data of the expected types.
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
        """Test that generated coordinates are finite and non-empty.

        This test acts as a sanity check to ensure that the geometry generation
        process produces valid numerical data. It checks that all vertices in
        the generated splines and all parameters of the arcs are finite numbers.
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
        """Test that undercut is correctly identified and handled.

        This test uses a gear configuration that is known to cause undercutting.
        It verifies that the system correctly reports a "Corrected" status and
        that the resulting geometry is structured differently, with separate
        splines for the root and flank, which is the expected behavior for
        corrected undercuts.
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
        """Test that splines are merged when there is no undercut.

        This test uses a standard gear configuration where no undercutting is
        expected. It verifies that the system reports an "OK" status and that
        the root and flank splines are merged into a single continuous profile
        spline, which is the correct behavior for non-undercut gears.
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