"""Generate tooth geometry for spur gears."""

from __future__ import annotations

from typing import List, Tuple, Union

import numpy as np

from . import gear_math, transformations
from . import shaper_fillet as shaper_fillet_generator
from .models import Arc, Spline, StructuredToothProfile, GearPairParameters


def involute_curve(
    module: float,
    teeth: int,
    segment_count: int,
    theta_start: float,
    theta_end: float,
    base_angle: float,
    start_angle: float,
) -> List[Tuple[float, float]]:
    """Generate the involute flank curve of a gear tooth.

    This function calculates the coordinates for the involute portion of a gear
    tooth profile, which is the primary load-bearing surface.

    Args:
        module: The module of the gear.
        teeth: The number of teeth.
        segment_count: The number of points to generate for the curve.
        theta_start: The starting angular parameter for the involute generation.
        theta_end: The ending angular parameter for the involute generation.
        base_angle: The base pressure angle in radians.
        start_angle: The overall starting angle for the tooth geometry.

    Returns:
        A list of (x, y) tuples representing the vertices of the involute curve.
    """
    theta_values = np.linspace(theta_start, theta_end, segment_count)
    radius = 0.5 * module * teeth * np.cos(base_angle) * np.sqrt(1 + theta_values**2)
    x_coords = radius * np.cos(start_angle + theta_values - np.arctan(theta_values))
    y_coords = radius * np.sin(start_angle + theta_values - np.arctan(theta_values))
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
    """Generate the rounded edge curve at the tooth tip.

    This function creates a small, rounded corner at the tip of the tooth,
    connecting the involute flank to the outer addendum circle. This can
    help to reduce stress concentrations.

    Args:
        module: The module of the gear.
        tooth_edge_radius: The radius of the rounded edge.
        flank_vertices: The vertices of the involute flank.
        edge_x: The x-coordinate of the outer edge point.
        edge_y: The y-coordinate of the outer edge point.
        edge_center_x: The x-coordinate of the center of the edge radius.
        edge_center_y: The y-coordinate of the center of the edge radius.
        segment_count: The number of points to generate for the curve.

    Returns:
        A list of (x, y) tuples for the rounded edge curve.
    """
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
    """Generate the trochoidal root fillet curve based on a rack cutter.

    This function simulates the path of the corner of a rack-shaped cutting
    tool (a hob) to generate the root fillet of the gear tooth. This is a common
    method for modeling gear tooth roots.

    Args:
        module: The module of the gear.
        teeth: The number of teeth.
        profile_shift: The profile shift coefficient.
        dedendum_factor: The dedendum factor.
        hob_edge_radius: The radius of the hob cutter's edge.
        theta_end: The ending angular parameter for the trochoid generation.
        alpha_transition: The transition angle for the trochoid generation.
        segment_count: The number of points to generate for the curve.

    Returns:
        A list of (x, y) tuples for the trochoidal root curve.
    """
    theta_values = np.linspace(0, theta_end, segment_count)
    denominator = module * (dedendum_factor - profile_shift - hob_edge_radius)
    if hob_edge_radius != 0 and denominator == 0:
        theta_s = (np.pi / 2) * np.ones(len(theta_values))
    elif denominator != 0:
        theta_s = np.arctan((module * teeth * theta_values / 2) / denominator)
    else:
        theta_s = np.zeros(len(theta_values))
    x_coords = module * (
        (teeth / 2 + profile_shift - dedendum_factor + hob_edge_radius) * np.cos(theta_values + alpha_transition)
        + (teeth / 2) * theta_values * np.sin(theta_values + alpha_transition)
        - hob_edge_radius * np.cos(theta_s + theta_values + alpha_transition)
    )
    y_coords = module * (
        (teeth / 2 + profile_shift - dedendum_factor + hob_edge_radius) * np.sin(theta_values + alpha_transition)
        - (teeth / 2) * theta_values * np.cos(theta_values + alpha_transition)
        - hob_edge_radius * np.sin(theta_s + theta_values + alpha_transition)
    )
    return list(zip(x_coords, y_coords))


def outer_arc(
    module: float, teeth: int, profile_shift: float, addendum_factor: float, edge_angle: float, mid_angle: float
) -> Arc:
    """Generate the outer arc at the tooth tip (addendum circle).

    This function defines the circular arc that forms the top land of the gear
    tooth, which is part of the addendum circle.

    Args:
        module: The module of the gear.
        teeth: The number of teeth.
        profile_shift: The profile shift coefficient.
        addendum_factor: The addendum factor.
        edge_angle: The starting angle of the arc.
        mid_angle: The ending angle of the arc.

    Returns:
        An ``Arc`` object representing the outer arc of the tooth.
    """
    radius = module * (teeth / 2 + addendum_factor + profile_shift)
    return Arc(center=(0, 0), radius=radius, start_angle=edge_angle, end_angle=mid_angle)


def root_arc(
    module: float, teeth: int, profile_shift: float, dedendum_factor: float, transition_angle: float
) -> Arc:
    """Generate the root arc at the bottom of the tooth space (dedendum circle).

    This function defines the circular arc that forms the bottom land of the
    tooth space, which is part of the dedendum circle.

    Args:
        module: The module of the gear.
        teeth: The number of teeth.
        profile_shift: The profile shift coefficient.
        dedendum_factor: The dedendum factor.
        transition_angle: The ending angle of the arc.

    Returns:
        An ``Arc`` object representing the root arc of the tooth space.
    """
    radius = module * (teeth / 2 - dedendum_factor + profile_shift)
    return Arc(center=(0, 0), radius=radius, start_angle=0, end_angle=transition_angle)


def generate_tooth_profile(
    params: GearPairParameters, gear_type: str, use_structured_output: bool = True
) -> Union[
    Tuple[np.ndarray, np.ndarray, float, float, float],
    Tuple[StructuredToothProfile, float, float, float, str],
]:
    """Generate a single gear tooth profile with associated metadata.

    This is the main function for generating the complete profile of a single
    gear tooth. It orchestrates the creation of all the geometric components:
    the involute flanks, the root fillet, the edge rounds, and the top/bottom
    arcs. It also handles different fillet generation methods and corrects for
    undercutting if necessary.

    Args:
        params: A ``GearPairParameters`` object containing all the necessary
            parameters for the gear pair.
        gear_type: A string indicating whether to generate the 'driver' or
            'driven' gear profile.
        use_structured_output: If True, returns a ``StructuredToothProfile``
            object; otherwise, returns raw vertex data (deprecated).

    Returns:
        A tuple containing the generated tooth profile and associated metadata.
        The profile can be either a ``StructuredToothProfile`` or raw vertices,
        depending on the ``use_structured_output`` flag.
    """
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

    flank1_vertices = involute_curve(
        params.module, teeth_calc, params.segmentation.involute,
        involute_theta_start, involute_theta_end, base_angle, involute_start_angle,
    )

    if params.root_fillet_method == 'shaper_trochoid':
        if not params.shaper_cutter:
            raise ValueError("Shaper cutter parameters must be provided for 'shaper_trochoid' method.")

        # Prepare parameters for the shaper fillet algorithm
        # Assuming spur gear (psi = 0)
        phi_t = np.arctan(np.tan(np.radians(params.pressure_angle_deg)) / 1.0)
        s_t = params.module * (np.pi/2 + 2 * shift_calc * np.tan(phi_t))
        s_t -= backlash_calc / 2
        sn_inch = s_t / 25.4
        assert sn_inch < 2, "Expected normal tooth thickness in inches; check unit conversions."

        gear_dict = {
            'Pnd': 25.4 / params.module, # Conversion from module (mm) to Pnd (in^-1)
            'n': teeth_calc,
            'φn': params.pressure_angle_deg,
            'ψ': 0, # Assuming spur gear
            'sn': sn_inch, # Normal thickness for spur gear (inches)
        }
        tool_dict = params.shaper_cutter.__dict__
        opts_dict = {'tol': 1e-10, 'max_iter': 30, 'ds': 0.001}

        # NOTE: The current implementation of compute_shaper_root_fillet is a stub.
        # The returned points will need transformation to be correctly placed.
        # This section serves as an integration hook for the new algorithm.
        fillet_points, _ = shaper_fillet_generator.compute_shaper_root_fillet(gear_dict, tool_dict, opts_dict)
        # Placeholder for transformation and selecting one side of the fillet
        root1_vertices = list(fillet_points[:len(fillet_points)//2])

    else: # 'rack_trochoid'
        root1_vertices = rack_trochoid_root_curve(
            params.module, teeth_calc, shift_calc, dedendum_calc, hob_edge_calc,
            theta_end, alpha_transition, params.segmentation.root_round,
        )

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

    root1_arc = root_arc(params.module, teeth_calc, shift_calc, dedendum_calc, alpha_transition)
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