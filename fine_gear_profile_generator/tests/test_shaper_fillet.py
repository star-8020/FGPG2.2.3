# -*- coding: utf-8 -*-
"""Tests for the shaper-cutter root fillet (core/shaper_fillet.py) and its integration."""

import unittest

import numpy as np
from scipy.spatial.distance import cdist

from fine_gear_profile_generator.core import gear_math, geometry_generator
from fine_gear_profile_generator.core.models import (
    Arc,
    GearPairParameters,
    GearSpec,
    SegmentationSettings,
    ShaperCutterParameters,
    Spline,
)
from fine_gear_profile_generator.core.shaper_fillet import generate_shaper_fillet

MODULE = 1.0
ALPHA_DEG = 20.0
BACKLASH = 0.05
ADDENDUM = 1.0
DEDENDUM = 1.25
HOB_EDGE = 0.2
TIP_EDGE = 0.1


def _gear_data(teeth, shift):
    """Return the quantities shared by the rack and shaper methods for one gear."""
    (z, x, b, a, d, c, e) = gear_math.handle_internal_gear_parameters(
        teeth, shift, BACKLASH, ADDENDUM, DEDENDUM, HOB_EDGE, TIP_EDGE
    )
    (base_angle, _, flank_base, theta_is, _, _, _, _, _) = gear_math.calculate_gear_parameters(
        MODULE, z, ALPHA_DEG, x, b, a, d, c, e
    )
    alpha_transition = (
        (2 * (c * (1 - np.sin(base_angle)) - d) * np.sin(base_angle) + b) / (z * np.cos(base_angle))
        - 2 * c * np.cos(base_angle) / z + np.pi / (2 * z)
    )
    theta_end = (
        2 * c * np.cos(base_angle) / z
        - 2 * (d - x - c * (1 - np.sin(base_angle))) * np.cos(base_angle) / (z * np.sin(base_angle))
    )
    return dict(z=z, x=x, d=d, c=c, base_angle=base_angle, flank_base=flank_base,
                theta_is=theta_is, alpha_transition=alpha_transition, theta_end=theta_end,
                root_radius=MODULE * (z / 2 + x - d), rb=0.5 * MODULE * z * np.cos(base_angle))


def _shaper(g, n0, protuberance=0.0, samples=200):
    return generate_shaper_fillet(
        MODULE, g['z'], g['base_angle'], g['flank_base'], g['root_radius'],
        n0, g['c'] * MODULE, protuberance * MODULE, samples=samples,
    )


def _rack_points(g, count=20000):
    return np.array(geometry_generator.rack_trochoid_root_curve(
        MODULE, g['z'], g['x'], g['d'], g['c'], g['theta_end'], g['alpha_transition'], count
    ))


def _gap_to_involute(g, point):
    """Arc-length distance of a point from the flank-1 involute (positive = into the tooth)."""
    r = np.hypot(*point)
    alpha_r = np.arccos(g['rb'] / r)
    return (np.arctan2(point[1], point[0]) - g['flank_base'] - (np.tan(alpha_r) - alpha_r)) * r


class TestShaperFilletGeometry(unittest.TestCase):

    def test_converges_to_rack_fillet(self):
        """With n0 -> infinity the shaper fillet must approach the rack (hob) fillet ~ 1/n0."""
        g = _gear_data(18, 0.2)
        rack = _rack_points(g)
        deviations = {}
        for n0 in (100, 1000, 10000):
            fillet = _shaper(g, n0).points
            deviations[n0] = cdist(fillet, rack).min(axis=1).max()
        self.assertLess(deviations[1000], 5e-3)
        self.assertLess(deviations[10000], 5e-4)
        self.assertGreater(deviations[100] / deviations[1000], 5)
        self.assertGreater(deviations[1000] / deviations[10000], 5)

    def test_fillet_starts_on_root_circle_and_ends_on_involute(self):
        g = _gear_data(18, 0.2)
        result = _shaper(g, 40)
        self.assertTrue(result.tangent_to_involute)
        self.assertAlmostEqual(np.hypot(*result.points[0]), g['root_radius'], places=10)
        self.assertAlmostEqual(_gap_to_involute(g, result.points[-1]), 0.0, places=9)
        # Below the SOI the fillet stays on the space side of the involute (no undercut).
        for p in result.points[:-1]:
            if np.hypot(*p) >= g['rb']:
                self.assertLess(_gap_to_involute(g, p), 1e-9)

    def test_fewer_cutter_teeth_raise_the_start_of_involute(self):
        g = _gear_data(36, 0.0)
        soi = [_shaper(g, n0).soi_radius for n0 in (20, 50, 200, 5000)]
        self.assertTrue(all(a > b for a, b in zip(soi, soi[1:])), soi)

    def test_undercut_matches_rack_intersection(self):
        g = _gear_data(10, 0.0)
        self.assertLess(g['theta_is'], 0)  # rack method predicts undercut
        theta_is, _ = gear_math.solve_undercut_angles(
            MODULE, g['z'], g['base_angle'], g['x'], g['d'], g['c'],
            g['flank_base'], g['alpha_transition'], [0.01, g['theta_end']],
        )
        rack_soi = g['rb'] * np.sqrt(1 + theta_is ** 2)
        result = _shaper(g, 100000)
        self.assertFalse(result.tangent_to_involute)
        self.assertAlmostEqual(result.soi_radius, rack_soi, delta=1e-4)
        self.assertAlmostEqual(_gap_to_involute(g, result.points[-1]), 0.0, places=9)

    def test_protuberance_creates_relief_and_raises_soi(self):
        g = _gear_data(18, 0.2)
        plain = _shaper(g, 50)
        relieved = _shaper(g, 50, protuberance=0.03)
        self.assertTrue(plain.tangent_to_involute)
        self.assertFalse(relieved.tangent_to_involute)
        self.assertGreater(relieved.soi_radius, plain.soi_radius)

    def test_infeasible_cutters_are_rejected(self):
        g = _gear_data(18, 0.2)
        with self.assertRaises(ValueError):
            generate_shaper_fillet(MODULE, g['z'], g['base_angle'], g['flank_base'],
                                   g['root_radius'], 4, 0.2)  # too few teeth
        with self.assertRaises(ValueError):
            generate_shaper_fillet(MODULE, g['z'], g['base_angle'], g['flank_base'],
                                   g['root_radius'], 50, 0.8)  # tip round does not fit
        with self.assertRaises(ValueError):
            generate_shaper_fillet(MODULE, -g['z'], g['base_angle'], g['flank_base'],
                                   g['root_radius'], 50, 0.2)  # internal gear


class TestShaperFilletIntegration(unittest.TestCase):

    def _params(self, method, teeth=18, shift=0.2, cutter=None):
        return GearPairParameters(
            module=MODULE, pressure_angle_deg=ALPHA_DEG, backlash_factor=BACKLASH,
            addendum_factor=ADDENDUM, dedendum_factor=DEDENDUM, hob_edge_radius=HOB_EDGE,
            tooth_edge_radius=TIP_EDGE, driver=GearSpec(teeth, shift), driven=GearSpec(36, 0.0),
            segmentation=SegmentationSettings(15, 15, 15), root_fillet_method=method,
            shaper_cutter=cutter,
        )

    def _assert_continuous(self, profile):
        """Consecutive profile elements must share an end point."""

        def ends(el):
            if isinstance(el, Spline):
                return [np.array(el.vertices[0]), np.array(el.vertices[-1])]
            assert isinstance(el, Arc)
            return [np.array(el.center) + el.radius * np.array([np.cos(a), np.sin(a)])
                    for a in (el.start_angle, el.end_angle)]

        for first, second in zip(profile.elements, profile.elements[1:]):
            gap = min(np.hypot(*(p - q)) for p in ends(first) for q in ends(second))
            self.assertLess(gap, 1e-9, f"gap between {type(first).__name__} and {type(second).__name__}")

    def test_profile_is_continuous_for_both_methods(self):
        for method, teeth, shift in [
            ('rack_trochoid', 18, 0.2), ('shaper_trochoid', 18, 0.2),
            ('rack_trochoid', 10, 0.0), ('shaper_trochoid', 10, 0.0),
        ]:
            with self.subTest(method=method, teeth=teeth):
                profile, *_ = geometry_generator.generate_tooth_profile(
                    self._params(method, teeth, shift, ShaperCutterParameters(teeth=40)), 'driver'
                )
                self._assert_continuous(profile)

    def test_shaper_profile_differs_from_rack_for_small_cutter(self):
        rack, *_ = geometry_generator.generate_tooth_profile(self._params('rack_trochoid'), 'driver')
        shaper, *_ = geometry_generator.generate_tooth_profile(
            self._params('shaper_trochoid', cutter=ShaperCutterParameters(teeth=20)), 'driver'
        )
        rack_fillet = np.array(rack.elements[5].vertices[:15])
        shaper_fillet = np.array(shaper.elements[5].vertices[:15])
        self.assertGreater(np.abs(rack_fillet - shaper_fillet).max(), 1e-3)

    def test_default_cutter_used_when_parameters_missing(self):
        profile, *_, status = geometry_generator.generate_tooth_profile(
            self._params('shaper_trochoid', cutter=None), 'driver'
        )
        self.assertEqual(status, "OK")
        self._assert_continuous(profile)

    def test_undercut_status_reported(self):
        *_, status = geometry_generator.generate_tooth_profile(
            self._params('shaper_trochoid', 10, 0.0, ShaperCutterParameters(teeth=40)), 'driver'
        )
        self.assertEqual(status, "Corrected")

    def test_internal_gear_rejected_for_shaper_method(self):
        with self.assertRaisesRegex(ValueError, "external gears only"):
            geometry_generator.generate_tooth_profile(
                self._params('shaper_trochoid', -40, 0.0), 'driver'
            )

    def test_invalid_cutter_parameters(self):
        with self.assertRaises(ValueError):
            ShaperCutterParameters(teeth=3)
        with self.assertRaises(ValueError):
            ShaperCutterParameters(teeth=40, protuberance_factor=-0.1)


if __name__ == '__main__':
    unittest.main()
