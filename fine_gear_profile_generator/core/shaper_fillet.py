# -*- coding: utf-8 -*-

import numpy as np
from .newton import newton_raphson_solver
from .involute import involute_polar_angle

def _inv(phi):
    return np.tan(phi) - phi

def compute_shaper_root_fillet(gear, tool, opts):
    # 1. Parameter Extraction and Conversion
    Pnd, n, phi_n_deg, psi_deg, sn = gear['Pnd'], gear['n'], gear['φn'], gear['ψ'], gear['sn']
    phi_n = np.radians(phi_n_deg)
    psi = np.radians(psi_deg)

    Pnd0, n0, phi_n0_deg, psi0_deg = tool['Pnd0'], tool['n0'], tool['phi_n0_deg'], tool['psi0_deg']
    sn0, da0, rho0, delta0 = tool['sn0'], tool['da0'], tool['rho0'], tool['delta0']
    phi_n0 = np.radians(phi_n0_deg)
    psi0 = np.radians(psi0_deg)

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

    # 3. Cutter Tip Geometry
    r_s0 = da0 / 2 - rho0
    alpha_e0 = involute_polar_angle(da0 / 2, rb0)
    theta_s0 = (sn0 / (2 * r0)) + _inv(phi_t0) - alpha_e0
    xs0 = r_s0 * np.cos(theta_s0)
    ys0 = r_s0 * np.sin(theta_s0)

    # 4. Trochoid Generation
    u_start = -np.pi/2 - theta_s0
    u_end = np.pi/2 - theta_s0
    u_values = np.linspace(u_start, u_end, int(np.pi*rho0/ds))

    xp0 = xs0 + rho0 * np.cos(u_values)
    yp0 = ys0 + rho0 * np.sin(u_values)

    rp0 = np.sqrt(xp0**2 + yp0**2)
    thetap0 = np.arctan2(yp0, xp0)

    # Kinematic relationship for meshing
    with np.errstate(divide='ignore', invalid='ignore'):
        xi0_term2_val = (rb0/rp0)**2 - (C*np.cos(phi_op)/rp0 * np.sin(thetap0))**2
        xi0_term2_val[xi0_term2_val < 0] = 0
        xi0_term2 = np.sqrt(xi0_term2_val)

    xi0 = (C * np.cos(phi_op) - rb0) / rp0 * np.cos(thetap0) - xi0_term2

    valid_indices = ~np.isnan(xi0)
    xi0, xp0, yp0 = xi0[valid_indices], xp0[valid_indices], yp0[valid_indices]

    xi = -(n0 / n) * xi0

    # Transformation to the gear's coordinate system (O frame) using standard kinematics.
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