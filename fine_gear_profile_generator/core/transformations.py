from __future__ import annotations

from typing import List, Tuple

import numpy as np

from .models import Arc


def reflect_y(XX, YY):
    """Reflects coordinates across the Y-axis."""
    # Reverses the order of points and negates the Y values
    # to create a symmetrical shape across the vertical axis.
    return XX[::-1], -YY[::-1]


def reflect_y_vertices(vertices: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Reflect a list of vertices across the y-axis, reversing order."""
    return [(x, -y) for x, y in reversed(vertices)]


def reflect_y_arc(arc: Arc) -> Arc:
    """Reflect an Arc across the y-axis."""
    reflected_start_angle = -arc.end_angle
    reflected_end_angle = -arc.start_angle
    return Arc(
        center=(arc.center[0], -arc.center[1]),
        radius=arc.radius,
        start_angle=reflected_start_angle,
        end_angle=reflected_end_angle,
    )


def translate(Xtemp, Ytemp, X_0, Y_0):
    """Translates coordinates by a given offset (X_0, Y_0)."""
    return Xtemp + X_0, Ytemp + Y_0


def rotate(Xtemp, Ytemp, ANGLE):
    """Rotates coordinates around the origin by a given ANGLE in radians."""
    XX = np.cos(ANGLE) * Xtemp - np.sin(ANGLE) * Ytemp
    YY = np.sin(ANGLE) * Xtemp + np.cos(ANGLE) * Ytemp
    return XX, YY


def create_circular_pattern(X_tooth, Y_tooth, Z, P_ANGLE, ALIGN_ANGLE):
    """Creates a full gear by rotating a single tooth profile."""
    all_X = []
    all_Y = []

    # Apply initial alignment rotation to the first tooth
    X_rot, Y_rot = rotate(X_tooth, Y_tooth, ALIGN_ANGLE)

    for i in range(int(Z)):
        # Rotate the aligned tooth to its final position
        X_final, Y_final = rotate(X_rot, Y_rot, P_ANGLE * i)
        all_X.append(X_final)
        all_Y.append(Y_final)

    return all_X, all_Y