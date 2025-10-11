# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch
import numpy as np

from fine_gear_profile_generator.core.models import GearPairParameters, GearSpec, SegmentationSettings, ShaperCutterParameters
from fine_gear_profile_generator.core import geometry_generator
from fine_gear_profile_generator.core import gear_math
from fine_gear_profile_generator.core.shaper_fillet import compute_shaper_root_fillet
from fine_gear_profile_generator.core.geometry_generator import rack_trochoid_root_curve


class TestShaperFilletIntegration(unittest.TestCase):

    def setUp(self):
        """Set up common parameters for testing."""
        self.segmentation = SegmentationSettings(involute=15, edge=15, root_round=15)
        self.driver = GearSpec(teeth=18, profile_shift=0.2)
        self.driven = GearSpec(teeth=36, profile_shift=0.0)
        self.shaper_cutter_params = ShaperCutterParameters(
            Pnd0=12, n0=1000, phi_n0_deg=20.0, psi0_deg=22.1,
            sn0=0.13, da0=9.23, rho0=0.01, delta0=0.0025
        )
        self.base_params = {
            "module": 1.0,
            "pressure_angle_deg": 20.0,
            "backlash_factor": 0.05,
            "addendum_factor": 1.0,
            "dedendum_factor": 1.25,
            "hob_edge_radius": 0.2,
            "tooth_edge_radius": 0.1,
            "driver": self.driver,
            "driven": self.driven,
            "segmentation": self.segmentation,
        }

    @patch('fine_gear_profile_generator.core.shaper_fillet.compute_shaper_root_fillet')
    def test_shaper_fillet_called_when_method_is_shaper(self, mock_compute_shaper_fillet):
        """
        Verify that compute_shaper_root_fillet is called when the method is 'shaper_trochoid'.
        """
        # Arrange
        # Mock the function to return a dummy fillet and SOI data
        mock_compute_shaper_fillet.return_value = ([[0, 0], [1, 1]], {'diameter': 2.0, 'point': (1,1)})

        params = GearPairParameters(
            **self.base_params,
            root_fillet_method='shaper_trochoid',
            shaper_cutter=self.shaper_cutter_params
        )

        # Act
        geometry_generator.generate_tooth_profile(params=params, gear_type='driver')

        # Assert
        mock_compute_shaper_fillet.assert_called_once()

    @patch('fine_gear_profile_generator.core.shaper_fillet.compute_shaper_root_fillet')
    def test_normal_tooth_thickness_converted_to_inches(self, mock_compute_shaper_root_fillet):
        """Ensure the normal tooth thickness passed to the shaper fillet is in inches."""

        mock_compute_shaper_root_fillet.return_value = ([[0, 0], [1, 1]], {})

        params = GearPairParameters(
            **self.base_params,
            root_fillet_method='shaper_trochoid',
            shaper_cutter=self.shaper_cutter_params
        )

        geometry_generator.generate_tooth_profile(params=params, gear_type='driver')

        self.assertTrue(mock_compute_shaper_root_fillet.called)
        gear_dict = mock_compute_shaper_root_fillet.call_args[0][0]

        (
            _, shift_calc, backlash_calc, _, _, _, _
        ) = gear_math.handle_internal_gear_parameters(
            params.driver.teeth,
            params.driver.profile_shift,
            params.backlash_factor,
            params.addendum_factor,
            params.dedendum_factor,
            params.hob_edge_radius,
            params.tooth_edge_radius,
        )

        phi_t = np.arctan(np.tan(np.radians(params.pressure_angle_deg)))
        expected_sn = (
            params.module * (np.pi / 2 + 2 * shift_calc * np.tan(phi_t))
            - backlash_calc / 2
        ) / 25.4

        self.assertAlmostEqual(gear_dict['sn'], expected_sn)

    @patch('fine_gear_profile_generator.core.geometry_generator.rack_trochoid_root_curve')
    def test_rack_trochoid_called_when_method_is_rack(self, mock_rack_trochoid_root_curve):
        """
        Verify that the classic rack_trochoid_root_curve is called for the 'rack_trochoid' method.
        """
        # Arrange
        mock_rack_trochoid_root_curve.return_value = [[0, 0], [1, 1]]
        params = GearPairParameters(
            **self.base_params,
            root_fillet_method='rack_trochoid',
            shaper_cutter=None # No shaper params needed
        )

        # Act
        geometry_generator.generate_tooth_profile(params=params, gear_type='driver')

        # Assert
        mock_rack_trochoid_root_curve.assert_called_once()

    def test_raises_error_if_shaper_params_missing(self):
        """
        Verify that a ValueError is raised if 'shaper_trochoid' is selected
        but shaper_cutter parameters are not provided.
        """
        # Arrange
        params = GearPairParameters(
            **self.base_params,
            root_fillet_method='shaper_trochoid',
            shaper_cutter=None # Missing parameters
        )

        # Act & Assert
        with self.assertRaisesRegex(ValueError, "Shaper cutter parameters must be provided"):
            geometry_generator.generate_tooth_profile(params=params, gear_type='driver')

    def test_shaper_fillet_converges_to_rack_fillet(self):
        """
        Verify that the shaper fillet converges to the rack trochoid as the
        shaper cutter's number of teeth approaches infinity, as described
        in README.md.
        """
        # 1. Test Parameters (using module system, lengths in mm)
        module = 1.0
        pressure_angle_deg = 20.0
        backlash_factor = 0.05
        addendum_factor = 1.0
        dedendum_factor = 1.25
        hob_edge_radius_factor = 0.2 # As a factor of module

        gear_spec = self.driver # teeth=18, profile_shift=0.2
        segment_count = 100 # Number of points for curve generation

        # 2. Calculate Rack Fillet (Reference Curve in mm)
        (teeth_calc, shift_calc, backlash_calc, _, dedendum_calc,
         hob_edge_calc, tooth_edge_calc) = gear_math.handle_internal_gear_parameters(
            gear_spec.teeth, gear_spec.profile_shift, backlash_factor, addendum_factor,
            dedendum_factor, hob_edge_radius_factor, 0.1
        )

        (base_angle, _, _, _, _, _, _, _, _,) = gear_math.calculate_gear_parameters(
            module, teeth_calc, pressure_angle_deg, shift_calc, backlash_calc,
            addendum_factor, dedendum_calc, hob_edge_calc, tooth_edge_calc,
        )

        alpha_transition = (
            (2 * (hob_edge_calc * (1 - np.sin(base_angle)) - dedendum_calc) * np.sin(base_angle) + backlash_calc)
            / (teeth_calc * np.cos(base_angle))
            - 2 * hob_edge_calc * np.cos(base_angle) / teeth_calc + np.pi / (2 * teeth_calc)
        )
        theta_end = (
            2 * hob_edge_calc * np.cos(base_angle) / teeth_calc
            - 2 * (dedendum_calc - shift_calc - hob_edge_calc * (1 - np.sin(base_angle)))
            * np.cos(base_angle) / (teeth_calc * np.sin(base_angle))
        )

        rack_fillet_mm = rack_trochoid_root_curve(
            module, teeth_calc, shift_calc, dedendum_calc, hob_edge_calc,
            theta_end, alpha_transition, segment_count,
        )
        rack_fillet_in = np.array(rack_fillet_mm) / 25.4

        # 3. Calculate Shaper Fillet (Test Curve in inches)
        shaper_n0 = 10000
        pnd = 25.4 / module
        phi_t = np.arctan(np.tan(np.radians(pressure_angle_deg)))
        # Correctly calculate normal tooth thickness, accounting for backlash
        sn_mm = module * (np.pi / 2 + 2 * shift_calc * np.tan(phi_t)) - backlash_calc / 2

        gear_dict = {
            'Pnd': pnd, 'n': teeth_calc, 'φn': pressure_angle_deg, 'ψ': 0, 'sn': sn_mm / 25.4,
        }
        tool_dict = {
            'Pnd0': pnd, 'n0': shaper_n0, 'phi_n0_deg': pressure_angle_deg, 'psi0_deg': 0,
            'sn0': (np.pi / 2) / pnd,
            'da0': (shaper_n0 + 2 * addendum_factor) / pnd,
            'rho0': hob_edge_radius_factor * module / 25.4,
            'delta0': 0.0,
        }
        opts_dict = {'ds': 0.0001}

        shaper_fillet_in_raw, _ = compute_shaper_root_fillet(gear_dict, tool_dict, opts_dict)

        # 4. Align coordinate systems by rotating the shaper fillet
        # The rack trochoid is generated with a starting angle of alpha_transition.
        # We must rotate the shaper fillet to match this orientation for a valid comparison.
        rot_matrix = np.array([
            [np.cos(alpha_transition), -np.sin(alpha_transition)],
            [np.sin(alpha_transition),  np.cos(alpha_transition)]
        ])
        shaper_fillet_in = np.dot(shaper_fillet_in_raw, rot_matrix.T)

        # 5. Compare Curves using one-sided Hausdorff distance
        try:
            from scipy.spatial.distance import cdist
            # Ensure both arrays are not empty before comparison
            if shaper_fillet_in.size == 0 or rack_fillet_in.size == 0:
                self.fail("Fillet generation resulted in an empty array.")
            distances = cdist(shaper_fillet_in, rack_fillet_in)
            max_deviation = np.max(np.min(distances, axis=1))
        except ImportError:
            max_dev_sq = 0.0
            for p1 in shaper_fillet_in:
                min_dist_sq = min(np.sum((p1 - p2)**2) for p2 in rack_fillet_in)
                if min_dist_sq > max_dev_sq:
                    max_dev_sq = min_dist_sq
            max_deviation = np.sqrt(max_dev_sq)

        # From README, for n0=10000, deviation is ~0.000011 inches.
        # We use a slightly larger tolerance for robustness.
        self.assertLess(max_deviation, 5e-5, "Shaper fillet should converge to rack fillet for large n0")


if __name__ == '__main__':
    unittest.main()