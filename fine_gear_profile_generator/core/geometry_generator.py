"""Generate tooth geometry for spur gears."""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

import numpy as np

from . import gear_math, transformations
from . import shaper_fillet as shaper_fillet_generator
from .models import Arc, GearPairParameters, ShaperCutterParameters, Spline, StructuredToothProfile


def involute_curve(
    module: float,
    teeth: int,
    segment_count: int,
    theta_start: float,
    theta_end: float,
    base_angle: float,
    start_angle: float,
) -> List[Tuple[float, float]]:
    """Generate the involute flank curve."""
    theta_values = np.linspace(theta_start, theta_end, segment_count)
    x_coords, y_coords = gear_math.get_involute_coords(theta_values, module, teeth, base_angle, start_angle)
    return list(zip(x_coords, y_coords))


def rack_trochoid_root_curve(
    module: float,
    teeth: int,
    profile_shift: float,
    dedendum_factor: float,
    hob_edge_radius: float,
    theta_end: float,
    alpha_transition: float,
    segment_count: int,
) -> List[Tuple[float, float]]:
    """Generate the trochoidal root fillet curve based on a rack cutter."""
    theta_values = np.linspace(0, theta_end, segment_count)
    x_coords, y_coords = gear_math.get_trochoid_coords(
        theta_values, module, teeth, profile_shift, dedendum_factor, hob_edge_radius, alpha_transition
    )
    return list(zip(x_coords, y_coords))


def outer_arc(
    module: float, teeth: int, profile_shift: float, addendum_factor: float, edge_angle: float, mid_angle: float
) -> Arc:
    """Generate the outer arc at the tooth tip (addendum circle)."""
    radius = module * (teeth / 2 + addendum_factor + profile_shift)
    return Arc(center=(0, 0), radius=radius, start_angle=edge_angle, end_angle=mid_angle)


def root_arc(
    module: float, teeth: int, profile_shift: float, dedendum_factor: float, transition_angle: float
) -> Arc:
    """Generate the root arc at the bottom of the tooth space (dedendum circle)."""
    radius = module * (teeth / 2 - dedendum_factor + profile_shift)
    return Arc(center=(0, 0), radius=radius, start_angle=0, end_angle=transition_angle)


def generate_tooth_profile(
    params: GearPairParameters, gear_type: str, use_structured_output: bool = True
) -> Union[
    Tuple[np.ndarray, np.ndarray, float, float, float],
    Tuple[StructuredToothProfile, float, float, float, str],
]:
    """Generate a single gear tooth profile with associated metadata."""

    gear_spec = params.driver if gear_type == 'driver' else params.driven

    (teeth_calc, shift_calc, backlash_calc, addendum_calc, dedendum_calc,
     hob_edge_calc, tooth_edge_calc) = gear_math.handle_internal_gear_parameters(
        gear_spec.teeth, gear_spec.profile_shift, params.backlash_factor, params.addendum_factor,
        params.dedendum_factor, params.hob_edge_radius, params.tooth_edge_radius
    )

    notes: List[str] = []
    method = params.fillet_method_for(gear_type)
    if method == 'shaper_trochoid' and gear_spec.teeth < 0:
        notes.append("Internal gear: the shaper-cutter fillet is not available yet, "
                     "the rack fillet is used.")
        method = 'rack_trochoid'

    # Narrow or pointed tips: shrink the tip round / top the tip instead of
    # producing a folded outline.
    addendum_calc, tooth_edge_calc, tip_notes = gear_math.fit_tooth_tip(
        teeth_calc, params.pressure_angle_deg, shift_calc, backlash_calc,
        addendum_calc, tooth_edge_calc,
    )
    notes.extend(tip_notes)

    (
        base_angle, mid_angle, involute_start_angle, involute_theta_start, involute_theta_end,
        edge_angle, tooth_edge_calc, pitch_angle, alignment_angle,
    ) = gear_math.calculate_gear_parameters(
        params.module, teeth_calc, params.pressure_angle_deg, shift_calc, backlash_calc,
        addendum_calc, dedendum_calc, hob_edge_calc, tooth_edge_calc,
    )

    root_radius = params.module * (teeth_calc / 2 - dedendum_calc + shift_calc)

    if method == 'shaper_trochoid':
        cutter = params.shaper_cutter or ShaperCutterParameters()
        tip_factor = hob_edge_calc if cutter.tip_radius_factor is None else cutter.tip_radius_factor
        fillet = shaper_fillet_generator.generate_shaper_fillet(
            module=params.module,
            teeth=teeth_calc,
            pressure_angle_rad=base_angle,
            flank_base_angle=involute_start_angle,
            root_radius=root_radius,
            cutter_teeth=cutter.teeth,
            tip_radius=tip_factor * params.module,
            protuberance=cutter.protuberance_factor * params.module,
            cutter_profile_shift=cutter.profile_shift,
            samples=params.segmentation.root_round,
        )
        root1_vertices = [(float(x), float(y)) for x, y in fillet.points]
        root_end_angle = fillet.root_angle
        base_radius = 0.5 * params.module * teeth_calc * np.cos(base_angle)
        involute_theta_start = float(np.sqrt(max((fillet.soi_radius / base_radius) ** 2 - 1.0, 0.0)))
        undercut_status = "OK" if fillet.tangent_to_involute else "Corrected"
    else:  # 'rack_trochoid'
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

        undercut_status = "OK"
        if involute_theta_start < 0:
            undercut_status = "Corrected"
            initial_guess = [0.01, theta_end]
            involute_theta_start, theta_end = gear_math.solve_undercut_angles(
                params.module, teeth_calc, base_angle, shift_calc, dedendum_calc, hob_edge_calc,
                involute_start_angle, alpha_transition, initial_guess,
            )

        root1_vertices = rack_trochoid_root_curve(
            params.module, teeth_calc, shift_calc, dedendum_calc, hob_edge_calc,
            theta_end, alpha_transition, params.segmentation.root_round,
        )
        root_end_angle = alpha_transition

    if involute_theta_start >= involute_theta_end:
        raise ValueError(
            "The root fillet reaches the tooth tip: no involute flank is left. "
            "Check the profile shift, dedendum and tip radius values."
        )

    flank1_vertices = involute_curve(
        params.module, teeth_calc, params.segmentation.involute,
        involute_theta_start, involute_theta_end, base_angle, involute_start_angle,
    )
    if method == 'shaper_trochoid':
        # Make the junction exact (the fillet end lies on the involute to ~1e-12).
        flank1_vertices[0] = root1_vertices[-1]

    tip_radius = params.module * (teeth_calc / 2 + shift_calc + addendum_calc)
    edge_radius = params.module * tooth_edge_calc

    # Tip round: a true circular arc tangent to the involute and the tip circle.
    edge1: Optional[Arc] = None
    if edge_radius > 0:
        centre = (tip_radius - edge_radius) * np.array([np.cos(edge_angle), np.sin(edge_angle)])
        tangent_point = np.array(flank1_vertices[-1])
        start = float(np.arctan2(*(tangent_point - centre)[::-1]))
        end = float(edge_angle)
        while end < start:
            end += 2 * np.pi
        edge1 = Arc(center=(float(centre[0]), float(centre[1])), radius=float(edge_radius),
                    start_angle=start, end_angle=end)
        # Snap the flank end onto the arc (it lies on it to rounding error).
        flank1_vertices[-1] = (float(centre[0] + edge_radius * np.cos(start)),
                               float(centre[1] + edge_radius * np.sin(start)))

    outer1 = outer_arc(params.module, teeth_calc, shift_calc, addendum_calc, edge_angle, mid_angle)
    root1_arc = root_arc(params.module, teeth_calc, shift_calc, dedendum_calc, root_end_angle)

    def mirrored(arc: Optional[Arc]) -> Optional[Arc]:
        return transformations.reflect_y_arc(arc) if arc is not None else None

    if outer1.end_angle - outer1.start_angle <= 1e-12:
        outer1 = None  # the two tip rounds (or flanks) meet on the centre line

    if undercut_status == "OK":
        profile1 = Spline(vertices=root1_vertices + flank1_vertices[1:])
        profile2 = Spline(vertices=list(reversed(
            transformations.reflect_y_vertices(profile1.vertices))))
        side1 = [root1_arc, profile1, edge1, outer1]
        side2 = [mirrored(outer1), mirrored(edge1), profile2, mirrored(root1_arc)]
    else:
        root1 = Spline(vertices=root1_vertices)
        flank1 = Spline(vertices=flank1_vertices)
        side1 = [root1_arc, root1, flank1, edge1, outer1]
        side2 = [mirrored(outer1), mirrored(edge1),
                 Spline(vertices=transformations.reflect_y_vertices(flank1_vertices)),
                 Spline(vertices=transformations.reflect_y_vertices(root1_vertices)),
                 mirrored(root1_arc)]
    elements = [el for el in side2 + side1 if el is not None]

    structured_profile = StructuredToothProfile(elements=elements, notes=notes, tip_radius=float(tip_radius))

    return structured_profile, float(teeth_calc), float(pitch_angle), float(alignment_angle), undercut_status
