from __future__ import annotations

from typing import List, Tuple

import numpy as np

from .models import Arc


def reflect_y(XX, YY):
    """Reflects coordinates across the Y-axis.

    This function takes arrays of x and y coordinates, reverses their order,
    and negates the y-values to create a mirror image across the y-axis.
    This is typically used to generate the opposite flank of a symmetric
    gear tooth.

    Args:
        XX: A NumPy array of x-coordinates.
        YY: A NumPy array of y-coordinates.

    Returns:
        A tuple of two NumPy arrays representing the reflected x and y coordinates.
    """
    return XX[::-1], -YY[::-1]


def reflect_y_vertices(vertices: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Reflect a list of vertices across the y-axis, reversing order.

    Similar to ``reflect_y``, but operates on a list of vertex tuples. It
    reverses the list and negates the y-coordinate of each vertex.

    Args:
        vertices: A list of (x, y) tuples.

    Returns:
        A new list of vertices, reflected and reversed.
    """
    return [(x, -y) for x, y in reversed(vertices)]


def reflect_y_arc(arc: Arc) -> Arc:
    """Reflect an Arc across the y-axis.

    This function creates a new ``Arc`` object that is a mirror image of the
    input arc across the y-axis. The center's y-coordinate is negated, and
    the start and end angles are swapped and negated.

    Args:
        arc: The ``Arc`` object to reflect.

    Returns:
        A new, reflected ``Arc`` object.
    """
    reflected_start_angle = -arc.end_angle
    reflected_end_angle = -arc.start_angle
    return Arc(
        center=(arc.center[0], -arc.center[1]),
        radius=arc.radius,
        start_angle=reflected_start_angle,
        end_angle=reflected_end_angle,
    )


def translate(Xtemp, Ytemp, X_0, Y_0):
    """Translates coordinates by a given offset (X_0, Y_0).

    This function shifts a set of coordinates by adding a constant offset
    to each x and y value.

    Args:
        Xtemp: A NumPy array of x-coordinates.
        Ytemp: A NumPy array of y-coordinates.
        X_0: The translation offset in the x-direction.
        Y_0: The translation offset in the y-direction.

    Returns:
        A tuple of two NumPy arrays with the translated coordinates.
    """
    return Xtemp + X_0, Ytemp + Y_0


def rotate(Xtemp, Ytemp, ANGLE):
    """Rotates coordinates around the origin by a given ANGLE in radians.

    This function applies a 2D rotation transformation to a set of coordinates
    around the origin (0, 0).

    Args:
        Xtemp: A NumPy array of x-coordinates.
        Ytemp: A NumPy array of y-coordinates.
        ANGLE: The rotation angle in radians.

    Returns:
        A tuple of two NumPy arrays with the rotated coordinates.
    """
    XX = np.cos(ANGLE) * Xtemp - np.sin(ANGLE) * Ytemp
    YY = np.sin(ANGLE) * Xtemp + np.cos(ANGLE) * Ytemp
    return XX, YY


def create_circular_pattern(X_tooth, Y_tooth, Z, P_ANGLE, ALIGN_ANGLE):
    """Creates a full gear by rotating a single tooth profile.

    This function generates the complete geometry of a gear by taking a single
    tooth profile, applying an initial alignment rotation, and then repeatedly
    rotating it to create a circular pattern of teeth.

    Args:
        X_tooth: A NumPy array of x-coordinates for a single tooth.
        Y_tooth: A NumPy array of y-coordinates for a single tooth.
        Z: The total number of teeth on the gear.
        P_ANGLE: The pitch angle (angle between teeth) in radians.
        ALIGN_ANGLE: An initial alignment angle to orient the first tooth correctly.

    Returns:
        A tuple of two lists, where each list contains NumPy arrays of the
        x and y coordinates for each tooth in the full gear.
    """
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