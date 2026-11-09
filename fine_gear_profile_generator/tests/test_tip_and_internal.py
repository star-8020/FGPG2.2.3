"""Tests for narrow/pointed tooth tips, tip-round arcs and internal gear pairs."""

import unittest

import numpy as np

from fine_gear_profile_generator.core import gear_core, gear_math, geometry_generator
from fine_gear_profile_generator.core.models import (
    Arc,
    GearPairParameters,
    GearSpec,
    SegmentationSettings,
    Spline,
)


def _params(z1=18, x1=0.2, z2=36, x2=0.0, e=0.1, method='rack_trochoid', seg=15):
    return GearPairParameters(
        module=1.0, pressure_angle_deg=20.0, backlash_factor=0.05, addendum_factor=1.0,
        dedendum_factor=1.25, hob_edge_radius=0.2, tooth_edge_radius=e,
        driver=GearSpec(z1, x1), driven=GearSpec(z2, x2),
        segmentation=SegmentationSettings(seg, 15, 15), root_fillet_method=method,
    )


def _ends(el):
    if isinstance(el, Spline):
        return [np.array(el.vertices[0]), np.array(el.vertices[-1])]
    return [np.array(el.center) + el.radius * np.array([np.cos(a), np.sin(a)])
            for a in (el.start_angle, el.end_angle)]


class TestTipRound(unittest.TestCase):

    def assert_valid_outline(self, profile):
        for el in profile.elements:
            if isinstance(el, Arc):
                self.assertGreaterEqual(el.end_angle - el.start_angle, 0.0)  # never folded
        for first, second in zip(profile.elements, profile.elements[1:]):
            gap = min(np.hypot(*(p - q)) for p in _ends(first) for q in _ends(second))
            self.assertLess(gap, 1e-9)

    def test_tip_round_is_an_arc_tangent_to_flank_and_tip_circle(self):
        # Dense flank so that its last chord approximates the true tangent.
        profile, *_ = geometry_generator.generate_tooth_profile(_params(seg=5000), 'driver')
        edge = profile.elements[6]
        self.assertIsInstance(edge, Arc)
        self.assertAlmostEqual(edge.radius, 0.1)
        tip_r = 18 / 2 + 0.2 + 1.0
        centre_r = np.hypot(*edge.center)
        self.assertAlmostEqual(centre_r + edge.radius, tip_r, places=12)  # touches tip circle
        # Tangent to the flank: the flank direction at its end is perpendicular
        # to the radius of the arc.
        flank = np.array(profile.elements[5].vertices)
        direction = flank[-1] - flank[-2]
        radius_dir = flank[-1] - np.array(edge.center)
        cos = np.dot(direction, radius_dir) / np.linalg.norm(direction) / np.linalg.norm(radius_dir)
        self.assertLess(abs(cos), 1e-3)
        self.assert_valid_outline(profile)

    def test_no_tip_round_when_radius_zero(self):
        profile, *_ = geometry_generator.generate_tooth_profile(_params(e=0.0), 'driver')
        self.assertEqual(sum(isinstance(el, Arc) for el in profile.elements), 4)  # tip + root arcs
        self.assert_valid_outline(profile)

    def test_narrow_tip_shrinks_round_with_note(self):
        profile, *_ = geometry_generator.generate_tooth_profile(_params(z1=10, x1=0.6), 'driver')
        self.assertTrue(any('Tip round too large' in n for n in profile.notes))
        rounds = [el for el in profile.elements if isinstance(el, Arc) and el.center != (0, 0)]
        self.assertTrue(all(el.radius < 0.1 for el in rounds))
        self.assert_valid_outline(profile)

    def test_pointed_tip_is_topped_with_note(self):
        profile, *_ = geometry_generator.generate_tooth_profile(_params(z1=10, x1=0.8), 'driver')
        self.assertTrue(any('pointed' in n for n in profile.notes))
        self.assertLess(profile.tip_radius, 10 / 2 + 0.8 + 1.0)
        self.assert_valid_outline(profile)

    def test_normal_tooth_has_no_notes(self):
        profile, *_ = geometry_generator.generate_tooth_profile(_params(), 'driver')
        self.assertEqual(profile.notes, [])

    def test_notes_reach_the_result(self):
        result = gear_core.generate_gear_pair(_params(z1=10, x1=0.8))
        self.assertTrue(result.gear1.notes)
        self.assertEqual(result.gear2.notes, [])

    def test_impossible_tooth_raises(self):
        with self.assertRaises(ValueError):
            gear_math.fit_tooth_tip(10, 20.0, -5.0, 0.05, 1.0, 0.1)  # no tooth left


class TestInternalPair(unittest.TestCase):

    def test_textbook_internal_pair(self):
        # z1 = 18, z2 = -60, x = 0, m = 1, alpha = 20 deg:
        # a = (60 - 18)/2 = 21, eps = (sqrt(10^2-rb1^2) - sqrt(29^2-rb2^2) + a sin(alpha)) / pb
        a = np.radians(20)
        rb1, rb2 = 9 * np.cos(a), 30 * np.cos(a)
        expected = (np.sqrt(10 ** 2 - rb1 ** 2) - np.sqrt(29 ** 2 - rb2 ** 2) + 21 * np.sin(a)) / (np.pi * np.cos(a))
        eps, centre = gear_math.calculate_contact_ratio(1, 18, -60, 0.0, 0.0, 20.0)
        self.assertAlmostEqual(centre, -21.0)
        self.assertAlmostEqual(eps, expected, places=10)
        self.assertAlmostEqual(eps, 1.9361, places=4)

    def test_order_of_gears_does_not_matter(self):
        self.assertEqual(gear_math.calculate_contact_ratio(1, 18, -60, 0.1, 0.2, 20.0),
                         gear_math.calculate_contact_ratio(1, -60, 18, 0.2, 0.1, 20.0))

    def test_external_pair_unchanged(self):
        eps, centre = gear_math.calculate_contact_ratio(1, 18, 36, 0.2, 0.0, 20.0)
        self.assertAlmostEqual(eps, 1.5471, places=4)
        self.assertAlmostEqual(centre, 27.1948, places=4)

    def test_invalid_internal_pairs(self):
        with self.assertRaises(ValueError):
            gear_math.calculate_contact_ratio(1, -30, -60, 0, 0, 20.0)
        with self.assertRaises(ValueError):
            gear_math.calculate_contact_ratio(1, 40, -30, 0, 0, 20.0)

    def test_impossible_shift_combination_has_clear_message(self):
        with self.assertRaisesRegex(ValueError, "cannot mesh.*ring gear profile shift"):
            gear_math.calculate_contact_ratio(1, 10, -40, 0.8, 0.0, 20.0)

    def test_internal_pair_result(self):
        result = gear_core.generate_gear_pair(_params(z2=-60, x2=0.0, x1=0.0))
        self.assertTrue(result.analysis.is_internal)
        self.assertAlmostEqual(abs(result.analysis.center_distance), 21.0)
        self.assertAlmostEqual(result.analysis.contact_ratio, 1.9361, places=3)


if __name__ == '__main__':
    unittest.main()
