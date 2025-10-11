# -*- coding: utf-8 -*-

import numpy as np
from .newton import newton_raphson_solver
from .involute import involute_polar_angle


def _rotation(angle):
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    return np.array([[cos_a, -sin_a], [sin_a, cos_a]])


def _normalize(vec):
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def _involute_point_and_tangent(rb, phi):
    """Return the involute point and tangent for a base circle of radius ``rb``."""

    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    point = rb * np.array(
        [cos_phi + phi * sin_phi, sin_phi - phi * cos_phi]
    )

    eps = 1e-8
    cos_phi_eps = np.cos(phi + eps)
    sin_phi_eps = np.sin(phi + eps)
    point_eps = rb * np.array(
        [cos_phi_eps + (phi + eps) * sin_phi_eps, sin_phi_eps - (phi + eps) * cos_phi_eps]
    )
    tangent = point_eps - point
    return point, _normalize(tangent)


def _cross_2d(u, v):
    return u[0] * v[1] - u[1] * v[0]

def _inv(phi):
    return np.tan(phi) - phi


def _compute_circular_tip_root_fillet(
    n,
    n0,
    sn0,
    da0,
    rho0,
    delta0,
    ds,
    phi_t,
    phi_t0,
    rb,
    rb0,
    r0,
    C,
    phi_op,
):
    """Fallback trochoid generator for circular cutter tips with protuberance."""

    r_s0 = da0 / 2 - rho0 + delta0
    alpha_e0 = involute_polar_angle(da0 / 2, rb0)
    theta_s0 = (sn0 / (2 * r0)) + _inv(phi_t0) - alpha_e0

    xs0 = r_s0 * np.cos(theta_s0)
    ys0 = r_s0 * np.sin(theta_s0)

    sample_count = max(25, int(np.ceil(np.pi * max(rho0, ds) / max(ds, 1e-6))))
    u_start = -np.pi / 2 - theta_s0
    u_end = np.pi / 2 - theta_s0
    u_values = np.linspace(u_start, u_end, sample_count)

    xp0 = xs0 + rho0 * np.cos(u_values)
    yp0 = ys0 + rho0 * np.sin(u_values)

    rp0 = np.sqrt(xp0**2 + yp0**2)
    thetap0 = np.arctan2(yp0, xp0)

    with np.errstate(divide='ignore', invalid='ignore'):
        xi0_term2_val = (rb0 / rp0) ** 2 - (C * np.cos(phi_op) / rp0 * np.sin(thetap0)) ** 2
        xi0_term2_val = np.where(xi0_term2_val < 0, 0, xi0_term2_val)
        xi0_term2 = np.sqrt(xi0_term2_val)

    xi0 = (C * np.cos(phi_op) - rb0) / rp0 * np.cos(thetap0) - xi0_term2

    valid_indices = ~np.isnan(xi0)
    xi0, xp0, yp0 = xi0[valid_indices], xp0[valid_indices], yp0[valid_indices]

    xi = -(n0 / n) * xi0

    xw = C + xp0 * np.cos(xi0) - yp0 * np.sin(xi0)
    yw = xp0 * np.sin(xi0) + yp0 * np.cos(xi0)

    x_fillet = xw * np.cos(xi) + yw * np.sin(xi)
    y_fillet = -xw * np.sin(xi) + yw * np.cos(xi)

    return np.vstack((x_fillet, y_fillet)).T

def compute_shaper_root_fillet(gear, tool, opts):
    # 1. Parameter Extraction and Conversion
    Pnd, n, phi_n_deg, psi_deg, sn = gear['Pnd'], gear['n'], gear['φn'], gear['ψ'], gear['sn']
    phi_n = np.radians(phi_n_deg)
    psi = np.radians(psi_deg)

    Pnd0, n0, phi_n0_deg, psi0_deg = tool['Pnd0'], tool['n0'], tool['phi_n0_deg'], tool['psi0_deg']
    sn0, da0, rho0, delta0 = tool['sn0'], tool['da0'], tool['rho0'], tool['delta0']
    ellipse_a = tool.get('ellipse_a', rho0)
    ellipse_b = tool.get('ellipse_b', rho0)
    ellipse_orientation = np.radians(tool.get('ellipse_orientation_deg', 0.0))
    phi_n0 = np.radians(phi_n0_deg)
    psi0 = np.radians(psi0_deg)

    target_rs0 = da0 / 2.0 - rho0 + delta0
    is_circular_tip = np.isclose(ellipse_a, ellipse_b, rtol=1e-6, atol=1e-9)

    tol = opts.get('tol', 1e-10)
    max_iter = opts.get('max_iter', 30)
    ds = opts.get('ds', 0.0005)

    # 2. Base Geometry Calculation
    phi_t = np.arctan(np.tan(phi_n) / np.cos(psi))
    phi_t0 = np.arctan(np.tan(phi_n0) / np.cos(psi0))

    r = (n / Pnd) / 2
    rb = r * np.cos(phi_t)

    r0 = (n0 / Pnd0) / 2
    rb0 = r0 * np.cos(phi_t0)

    C = r + r0

    def f_phi_op(phi_op):
        s_t = sn / np.cos(psi)
        s_t0 = sn0 / np.cos(psi0)
        p_t = np.pi / Pnd
        return _inv(phi_t) + (s_t + s_t0 - p_t) / (2 * C) - _inv(phi_op)

    phi_op = newton_raphson_solver(f_phi_op, phi_t, tol=1e-9, max_iter=20)

    if is_circular_tip:
        fillet_points = _compute_circular_tip_root_fillet(
            n, n0, sn0, da0, rho0, delta0, ds, phi_t, phi_t0, rb, rb0, r0, C, phi_op
        )
    else:
        def residuals(x):
            r_s0, lambda_s0, theta_p, theta_e = x
            S0 = np.array([r_s0 * np.cos(lambda_s0), r_s0 * np.sin(lambda_s0)])
            rot = _rotation(lambda_s0 + ellipse_orientation)

            def ellipse_point(theta):
                local = np.array([ellipse_a * np.cos(theta), ellipse_b * np.sin(theta)])
                return S0 + rot @ local

            def ellipse_tangent(theta):
                local_tangent = np.array([-ellipse_a * np.sin(theta), ellipse_b * np.cos(theta)])
                return _normalize(rot @ local_tangent)

            XP = ellipse_point(theta_p)
            XE = ellipse_point(theta_e)
            TP = ellipse_tangent(theta_p)
            TE = ellipse_tangent(theta_e)

            norm_XE = np.linalg.norm(XE)
            rhatE = XE / norm_XE if norm_XE != 0 else XE

            phi_val = np.sqrt(max((np.linalg.norm(XP) / max(rb0, 1e-12)) ** 2 - 1.0, 0.0))
            involute_point, involute_tangent = _involute_point_and_tangent(rb0, phi_val)
            angle_offset = np.arctan2(XP[1], XP[0]) - np.arctan2(involute_point[1], involute_point[0])
            involute_tangent = _normalize(_rotation(angle_offset) @ involute_tangent)

            F1 = _cross_2d(TP, involute_tangent)
            F2 = norm_XE - da0 / 2.0
            F3 = _cross_2d(TE, rhatE)
            orientation_penalty = 1e-6 * (lambda_s0 - ellipse_orientation)
            F4 = r_s0 - target_rs0 + orientation_penalty
            return np.array([F1, F2, F3, F4])

        initial_guess = np.array([
            target_rs0,
            0.0,
            -np.radians(phi_n0_deg),
            -1.2,
        ])

        solution = newton_raphson_solver(residuals, initial_guess, tol=tol, max_iter=max_iter)
        r_s0, lambda_s0, theta_p, theta_e = solution

        S0 = np.array([r_s0 * np.cos(lambda_s0), r_s0 * np.sin(lambda_s0)])
        rot = _rotation(lambda_s0 + ellipse_orientation)

        theta_span = theta_e - theta_p
        arc_scale = max(ellipse_a, ellipse_b)
        sample_count = max(25, int(np.ceil(max(abs(theta_span), 1e-3) * arc_scale / max(ds, 1e-6))))
        theta_values = np.linspace(theta_p, theta_e, sample_count)

        ellipse_points = rot @ np.vstack(
            (ellipse_a * np.cos(theta_values), ellipse_b * np.sin(theta_values))
        )
        xp0 = S0[0] + ellipse_points[0]
        yp0 = S0[1] + ellipse_points[1]

        rp0 = np.sqrt(xp0**2 + yp0**2)
        thetap0 = np.arctan2(yp0, xp0)

        with np.errstate(divide='ignore', invalid='ignore'):
            xi0_term2_val = (rb0 / rp0) ** 2 - (C * np.cos(phi_op) / rp0 * np.sin(thetap0)) ** 2
            xi0_term2_val = np.where(xi0_term2_val < 0, 0, xi0_term2_val)
            xi0_term2 = np.sqrt(xi0_term2_val)

        xi0 = (C * np.cos(phi_op) - rb0) / rp0 * np.cos(thetap0) - xi0_term2

        valid_indices = ~np.isnan(xi0)
        xi0, xp0, yp0 = xi0[valid_indices], xp0[valid_indices], yp0[valid_indices]

        xi = -(n0 / n) * xi0

        xw = C + xp0 * np.cos(xi0) - yp0 * np.sin(xi0)
        yw = xp0 * np.sin(xi0) + yp0 * np.cos(xi0)

        x_fillet = xw * np.cos(xi) + yw * np.sin(xi)
        y_fillet = -xw * np.sin(xi) + yw * np.cos(xi)

        fillet_points = np.vstack((x_fillet, y_fillet)).T

    # 5. Start of Involute (SOI) Calculation
    s_b = (np.pi/n + 2*_inv(phi_t)) * rb
    epsilon_base_centerline = s_b / (2 * rb)

    soi_radius = 0.0
    soi_point = np.array([0.0, 0.0])

    for point in reversed(fillet_points):
        r_fillet = np.sqrt(point[0]**2 + point[1]**2)
        if r_fillet < rb:
            continue
        epsilon_fillet = np.arctan2(point[1], point[0])
        epsilon_involute = epsilon_base_centerline + involute_polar_angle(r_fillet, rb)
        if epsilon_fillet <= epsilon_involute:
            soi_radius = r_fillet
            soi_point = point
            break

    if soi_radius == 0.0 and len(fillet_points) > 0:
        soi_radius = np.sqrt(fillet_points[-1][0]**2 + fillet_points[-1][1]**2)
        soi_point = fillet_points[-1]

    soi_diameter = 2 * soi_radius
    soi_data = {'diameter': soi_diameter, 'point': soi_point}

    soi_index = -1
    if soi_point is not None and len(fillet_points) > 0:
        distances = np.linalg.norm(fillet_points - soi_point, axis=1)
        if len(distances) > 0:
            soi_index = np.argmin(distances)

    trimmed_fillet_points = fillet_points[:soi_index+1] if soi_index != -1 else fillet_points

    return trimmed_fillet_points, soi_data
