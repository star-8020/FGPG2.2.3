# -*- coding: utf-8 -*-

import numpy as np
from .newton import newton_raphson_solver
from .involute import involute_polar_angle

def _inv(phi):
    return np.tan(phi) - phi

def involute_tangent(rb, phi, eps=1e-6):
    """Computes the tangent to an involute curve at a given roll angle."""
    r0 = rb * np.sqrt(1 + np.tan(phi)**2)
    p0 = np.array([r0 * np.cos(phi), r0 * np.sin(phi)])

    phi_plus_eps = phi + eps
    r1 = rb * np.sqrt(1 + np.tan(phi_plus_eps)**2)
    p1 = np.array([r1 * np.cos(phi_plus_eps), r1 * np.sin(phi_plus_eps)])

    t = p1 - p0
    return t / np.linalg.norm(t)

def residuals(x, tool_params):
    """
    Computes the residuals for the Newton-Raphson solver based on geometric constraints.
    """
    rS0, lamS0, thP, thE = x
    a, b = tool_params['a'], tool_params['b']
    rb0, da0 = tool_params['rb0'], tool_params['da0']

    S0 = np.array([rS0 * np.cos(lamS0), rS0 * np.sin(lamS0)])

    # Elliptical tip geometry
    XP = S0 + np.array([a * np.cos(thP), b * np.sin(thP)])
    XE = S0 + np.array([a * np.cos(thE), b * np.sin(thE)])

    TP = np.array([-a * np.sin(thP), b * np.cos(thP)])
    TE = np.array([-a * np.sin(thE), b * np.cos(thE)])
    TP /= np.linalg.norm(TP)
    TE /= np.linalg.norm(TE)

    # OD contact and tangency
    rE = np.linalg.norm(XE)
    rhatE = XE / rE
    F2 = rE - da0 / 2.0
    F3 = np.dot(TE, rhatE)

    # Involute tangency
    try:
        phi_arg = (np.linalg.norm(XP) / rb0)**2 - 1.0
        if phi_arg < 0:
            phi_arg = 0
        phi = np.sqrt(phi_arg)
        tinv = involute_tangent(rb0, phi)
        F1 = TP[0] * tinv[1] - TP[1] * tinv[0]
    except (ValueError, FloatingPointError):
        F1 = 1e6  # Penalize invalid states

    # Geometric closure
    F4 = np.linalg.norm(XP - S0) - np.linalg.norm([a * np.cos(thP), b * np.sin(thP)])

    return np.array([F1, F2, F3, F4])

def compute_shaper_root_fillet(gear, tool, opts):
    # 1. Parameter Extraction and Conversion
    Pnd, n, phi_n_deg, psi_deg, sn = gear['Pnd'], gear['n'], gear['phi_n'], gear['psi'], gear['sn']
    phi_n = np.radians(phi_n_deg)
    psi = np.radians(psi_deg)

    Pnd0, n0, phi_n0_deg, psi0_deg = tool['Pnd0'], tool['n0'], tool['phi_n0_deg'], tool['psi0_deg']
    sn0, da0, rho0, delta0 = tool['sn0'], tool['da0'], tool['rho0'], tool['delta0']
    a, b = tool['a'], tool['b']
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

    # 3. Newton-Raphson Solver for Elliptical Tip Contact
    tool_params = {'a': a, 'b': b, 'rb0': rb0, 'da0': da0}

    x0 = np.array([r0 - rho0, 0.0, -phi_t0, -1.5])

    x, converged, iters, nrm = newton_raphson_solver(lambda x: residuals(x, tool_params), x0, tol=1e-9)
    if not converged:
        raise RuntimeError(f"Newton solver failed to converge for shaper fillet. Norm: {nrm}")

    rS0, lamS0, thP, thE = x
    S0 = np.array([rS0 * np.cos(lamS0), rS0 * np.sin(lamS0)])

    # 4. Trochoid Generation
    u_values = np.linspace(thP, thE, int(np.pi * (a + b) / 2 / ds))
    xp0 = S0[0] + a * np.cos(u_values)
    yp0 = S0[1] + b * np.sin(u_values)

    rp0 = np.sqrt(xp0**2 + yp0**2)
    thetap0 = np.arctan2(yp0, xp0)

    phi_op, converged, _, _ = newton_raphson_solver(
        lambda pop: _inv(phi_t) + (sn / np.cos(psi) + sn0 / np.cos(psi0) - np.pi / Pnd) / (2 * C) - _inv(pop),
        phi_t, tol=1e-9, max_iter=20
    )
    if not converged:
        raise RuntimeError("Failed to converge for operating pressure angle.")

    with np.errstate(divide='ignore', invalid='ignore'):
        xi0_term2_val = (rb0/rp0)**2 - (C*np.cos(phi_op)/rp0 * np.sin(thetap0))**2
        xi0_term2_val[xi0_term2_val < 0] = 0
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