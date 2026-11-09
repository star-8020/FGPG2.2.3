"""Mathematical utilities used by the gear generation engine."""

from __future__ import annotations

from typing import Tuple

import numpy as np
from scipy.optimize import fsolve

FULL_TURN = 2 * np.pi
RIGHT_ANGLE = np.pi / 2


def inv(alpha_rad: float) -> float:
    """Calculate the involute function for the provided angle in radians."""

    return float(np.tan(alpha_rad) - alpha_rad)


def calculate_operating_pressure_angle(
    z1: int,
    z2: int,
    x1: float,
    x2: float,
    alpha_deg: float,
) -> float:
    """Determine the operating pressure angle for a meshing gear pair."""

    alpha_rad = np.deg2rad(alpha_deg)
    inv_alpha_w = inv(alpha_rad) + 2 * (x1 + x2) * np.tan(alpha_rad) / (z1 + z2)
    alpha_w = alpha_rad
    for _ in range(50):
        function_val = inv(alpha_w) - inv_alpha_w
        derivative = np.tan(alpha_w) ** 2
        if abs(derivative) < 1e-12:
            break
        alpha_w = alpha_w - function_val / derivative
        if abs(function_val) < 1e-15:
            break
    if not 0 < alpha_w < np.pi / 2 or abs(inv(alpha_w) - inv_alpha_w) > 1e-10:
        raise ValueError("Operating pressure angle did not converge; check the profile shifts.")
    return float(alpha_w)


def calculate_contact_ratio(
    module: float,
    z1: int,
    z2: int,
    x1: float,
    x2: float,
    alpha_deg: float,
    a1: float = 1.0,
) -> Tuple[float, float]:
    """Calculate the contact ratio and center distance for a gear pair."""

    alpha_rad = np.deg2rad(alpha_deg)
    alpha_w_rad = calculate_operating_pressure_angle(z1, z2, x1, x2, alpha_deg)

    center_distance = module * (z1 + z2) / 2 * (np.cos(alpha_rad) / np.cos(alpha_w_rad))

    base_radius_gear1 = module * z1 * np.cos(alpha_rad) / 2
    base_radius_gear2 = module * z2 * np.cos(alpha_rad) / 2

    addendum_radius_gear1 = module * (z1 / 2 + a1 + x1)
    addendum_radius_gear2 = module * (z2 / 2 + a1 + x2)

    val1 = addendum_radius_gear1**2 - base_radius_gear1**2
    val2 = addendum_radius_gear2**2 - base_radius_gear2**2
    if val1 < 0 or val2 < 0:
        return 0.0, float(center_distance)

    path_of_contact = (np.sqrt(val1) + np.sqrt(val2)) - center_distance * np.sin(alpha_w_rad)
    base_pitch = module * np.pi * np.cos(alpha_rad)
    epsilon_alpha = path_of_contact / base_pitch
    return float(epsilon_alpha), float(center_distance)


def check_undercut(teeth: int, pressure_angle_deg: float, profile_shift: float, addendum: float) -> str:
    """Assess whether a gear is at risk of undercutting."""

    if teeth <= 0:
        return "Not applicable for internal gears in this context"
    alpha_rad = np.deg2rad(pressure_angle_deg)
    x_min = addendum - (teeth / 2.0) * (np.sin(alpha_rad) ** 2)
    if profile_shift < x_min:
        return f"Warning: Risk of undercut (x < {x_min:.3f})"
    return "OK"


def handle_internal_gear_parameters(
    teeth: int,
    profile_shift: float,
    backlash_factor: float,
    addendum_factor: float,
    dedendum_factor: float,
    hob_edge_radius: float,
    tooth_edge_radius: float,
) -> Tuple[int, float, float, float, float, float, float]:
    """Normalize the sign conventions for internal gears."""

    if teeth < 0:
        teeth, profile_shift, backlash_factor = -teeth, -profile_shift, -backlash_factor
        addendum_factor, dedendum_factor = dedendum_factor, addendum_factor
        hob_edge_radius, tooth_edge_radius = tooth_edge_radius, hob_edge_radius
    return (
        int(teeth),
        float(profile_shift),
        float(backlash_factor),
        float(addendum_factor),
        float(dedendum_factor),
        float(hob_edge_radius),
        float(tooth_edge_radius),
    )


def calculate_gear_parameters(
    module: float,
    teeth: int,
    pressure_angle_deg: float,
    profile_shift: float,
    backlash_factor: float,
    addendum_factor: float,
    dedendum_factor: float,
    hob_edge_radius: float,
    tooth_edge_radius: float,
) -> Tuple[float, float, float, float, float, float, float, float, float]:
    """Derive the angular parameters used to build the tooth profile."""

    base_pressure_angle = np.deg2rad(pressure_angle_deg)
    tooth_center_angle = np.pi / teeth
    half_tooth_center_angle = tooth_center_angle / 2
    pitch_angle = FULL_TURN / teeth
    mid_tooth_angle = tooth_center_angle
    involute_start_angle = (
        base_pressure_angle
        + half_tooth_center_angle
        + backlash_factor / (teeth * np.cos(base_pressure_angle))
        - (1 + 2 * profile_shift / teeth) * np.sin(base_pressure_angle) / np.cos(base_pressure_angle)
    )
    involute_theta_start = np.tan(base_pressure_angle) + 2 * (
        hob_edge_radius * (1 - np.sin(base_pressure_angle)) + profile_shift - dedendum_factor
    ) / (teeth * np.cos(base_pressure_angle) * np.sin(base_pressure_angle))

    sqrt_val_ie = ((teeth + 2 * (profile_shift + addendum_factor - tooth_edge_radius)) / (teeth * np.cos(base_pressure_angle)))**2 - 1
    sqrt_val_ie = max(sqrt_val_ie, 0)
    involute_theta_end = 2 * tooth_edge_radius / (teeth * np.cos(base_pressure_angle)) + np.sqrt(sqrt_val_ie)

    sqrt_val_ae = ((teeth + 2 * (profile_shift + addendum_factor - tooth_edge_radius)) / (teeth * np.cos(base_pressure_angle)))**2 - 1
    sqrt_val_ae = max(sqrt_val_ae, 0)
    edge_angle = involute_start_angle + involute_theta_end - np.arctan(np.sqrt(sqrt_val_ae))

    if (edge_angle > mid_tooth_angle) and (mid_tooth_angle > involute_start_angle + involute_theta_end - np.arctan(involute_theta_end)):
        sqrt_val_e = (1 / np.cos(involute_start_angle + involute_theta_end - mid_tooth_angle))**2 - 1
        sqrt_val_e = max(sqrt_val_e, 0)
        tooth_edge_radius = (tooth_edge_radius / 2) * np.cos(base_pressure_angle) * (involute_theta_end - np.sqrt(sqrt_val_e))

    alignment_angle = RIGHT_ANGLE - tooth_center_angle

    return (
        float(base_pressure_angle),
        float(mid_tooth_angle),
        float(involute_start_angle),
        float(involute_theta_start),
        float(involute_theta_end),
        float(edge_angle),
        float(tooth_edge_radius),
        float(pitch_angle),
        float(alignment_angle),
    )



def get_involute_coords(
    theta_values: np.ndarray,
    module: float,
    teeth: int,
    base_angle: float,
    start_angle: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate the coordinates of points on the involute curve."""
    radius = 0.5 * module * teeth * np.cos(base_angle) * np.sqrt(1 + theta_values**2)
    angle = start_angle + theta_values - np.arctan(theta_values)
    x_coords = radius * np.cos(angle)
    y_coords = radius * np.sin(angle)
    return x_coords, y_coords


def get_trochoid_coords(
    theta_values: np.ndarray,
    module: float,
    teeth: int,
    profile_shift: float,
    dedendum_factor: float,
    hob_edge_radius: float,
    alpha_transition: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate the coordinates of points on the trochoid root curve."""
    denominator = module * (dedendum_factor - profile_shift - hob_edge_radius)
    if hob_edge_radius != 0 and denominator == 0:
        theta_s = np.full_like(theta_values, np.pi / 2)
    elif denominator != 0:
        theta_s = np.arctan((module * teeth * theta_values / 2) / denominator)
    else:
        theta_s = np.zeros_like(theta_values)

    common_factor = teeth / 2 + profile_shift - dedendum_factor + hob_edge_radius
    angle = theta_values + alpha_transition

    x_coords = module * (
        common_factor * np.cos(angle)
        + (teeth / 2) * theta_values * np.sin(angle)
        - hob_edge_radius * np.cos(theta_s + angle)
    )
    y_coords = module * (
        common_factor * np.sin(angle)
        - (teeth / 2) * theta_values * np.cos(angle)
        - hob_edge_radius * np.sin(theta_s + angle)
    )
    return x_coords, y_coords


def solve_undercut_angles(
    module: float,
    teeth: int,
    base_angle: float,
    profile_shift: float,
    dedendum_factor: float,
    hob_edge_radius: float,
    involute_start_angle: float,
    alpha_transition: float,
    initial_guess: list[float],
) -> Tuple[float, float]:
    """
    Solve for the intersection point of involute and trochoid curves in case of an undercut.

    Returns the corrected involute start angle (theta_is) and trochoid end angle (theta_te).
    """

    def equations(p):
        theta_i, theta_t = p

        # Involute coordinates for a single point
        x_i, y_i = get_involute_coords(
            np.array([theta_i]), module, teeth, base_angle, involute_start_angle
        )

        # Trochoid coordinates for a single point
        x_t, y_t = get_trochoid_coords(
            np.array([theta_t]), module, teeth, profile_shift, dedendum_factor, hob_edge_radius, alpha_transition
        )

        return (x_i[0] - x_t[0], y_i[0] - y_t[0])

    solution, _info, ier, message = fsolve(equations, initial_guess, full_output=True)
    if ier != 1:
        raise RuntimeError(f"Undercut intersection could not be found: {message}")
    theta_is, theta_te = solution[0], solution[1]

    return float(theta_is), float(theta_te)