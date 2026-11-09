"""Generate tooth geometry for spur gears."""

from __future__ import annotations

from typing import List, Tuple, Union

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


def edge_round_curve(
    module: float,
    tooth_edge_radius: float,
    flank_vertices: List[Tuple[float, float]],
    edge_x: float,
    edge_y: float,
    edge_center_x: float,
    edge_center_y: float,
    segment_count: int,
) -> List[Tuple[float, float]]:
    """Generate the rounded edge curve at the tooth tip."""
    last_flank_vertex = flank_vertices[-1]
    theta_min = np.arctan2(last_flank_vertex[1] - edge_center_y, last_flank_vertex[0] - edge_center_x)
    theta_max = np.arctan2(edge_y - edge_center_y, edge_x - edge_center_x)
    theta_values = np.linspace(theta_min, theta_max, segment_count)
    x_coords = module * tooth_edge_radius * np.cos(theta_values) + edge_center_x
    y_coords = module * tooth_edge_radius * np.sin(theta_values) + edge_center_y
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

    (
        base_angle, mid_angle, involute_start_angle, involute_theta_start, involute_theta_end,
        edge_angle, tooth_edge_calc, pitch_angle, alignment_angle,
    ) = gear_math.calculate_gear_parameters(
        params.module, teeth_calc, params.pressure_angle_deg, shift_calc, backlash_calc,
        addendum_calc, dedendum_calc, hob_edge_calc, tooth_edge_calc,
    )

    root_radius = params.module * (teeth_calc / 2 - dedendum_calc + shift_calc)

    if params.root_fillet_method == 'shaper_trochoid':
        if gear_spec.teeth < 0:
            raise ValueError(
                "The 'shaper_trochoid' fillet method currently supports external gears only."
            )
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
    if params.root_fillet_method == 'shaper_trochoid':
        # Make the junction exact (the fillet end lies on the involute to ~1e-12).
        flank1_vertices[0] = root1_vertices[-1]

    edge_x = params.module * ((teeth_calc / 2) + shift_calc + addendum_calc) * np.cos(edge_angle)
    edge_y = params.module * ((teeth_calc / 2) + shift_calc + addendum_calc) * np.sin(edge_angle)
    edge_center_x = params.module * (teeth_calc / 2 + shift_calc + addendum_calc - tooth_edge_calc) * np.cos(edge_angle)
    edge_center_y = params.module * (teeth_calc / 2 + shift_calc + addendum_calc - tooth_edge_calc) * np.sin(edge_angle)

    edge1_vertices = edge_round_curve(
        params.module, tooth_edge_calc, flank1_vertices,
        edge_x, edge_y, edge_center_x, edge_center_y, params.segmentation.edge,
    )
    edge2_vertices = transformations.reflect_y_vertices(edge1_vertices)

    outer1_arc = outer_arc(
        params.module, teeth_calc, shift_calc, addendum_calc, edge_angle, mid_angle
    )
    outer2_arc = transformations.reflect_y_arc(outer1_arc)

    root1_arc = root_arc(params.module, teeth_calc, shift_calc, dedendum_calc, root_end_angle)
    root2_arc = transformations.reflect_y_arc(root1_arc)

    if undercut_status == "OK":
        profile1_vertices = root1_vertices + flank1_vertices[1:]
        profile2_vertices = transformations.reflect_y_vertices(profile1_vertices)
        elements = [
            outer2_arc, Spline(vertices=edge2_vertices), Spline(vertices=list(reversed(profile2_vertices))),
            root2_arc, root1_arc, Spline(vertices=profile1_vertices), Spline(vertices=edge1_vertices), outer1_arc,
        ]
    else:
        flank2_vertices = transformations.reflect_y_vertices(flank1_vertices)
        root2_vertices = transformations.reflect_y_vertices(root1_vertices)
        elements = [
            outer2_arc, Spline(vertices=edge2_vertices), Spline(vertices=flank2_vertices),
            Spline(vertices=root2_vertices), root2_arc, root1_arc, Spline(vertices=root1_vertices),
            Spline(vertices=flank1_vertices), Spline(vertices=edge1_vertices), outer1_arc,
        ]

    structured_profile = StructuredToothProfile(elements=elements)

    return structured_profile, float(teeth_calc), float(pitch_angle), float(alignment_angle), undercut_status