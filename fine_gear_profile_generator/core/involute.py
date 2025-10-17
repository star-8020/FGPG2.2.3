# -*- coding: utf-8 -*-

"""
This module contains utility functions for calculating involute curve coordinates.
"""

import numpy as np


def involute_polar_angle(r, rb):
    """Calculates the polar angle of an involute curve.

    This function computes the polar angle (often denoted as the involute
    function, inv(α)) for a point on an involute curve at a specified radius.
    The angle is measured from the starting point of the involute on the base
    circle.

    The formula used is: inv(α) = tan(α) - α, where α = arccos(rb / r).

    Args:
        r: The radius (or radii) at which to calculate the involute angle.
           Can be a float or a NumPy array.
        rb: The base circle radius of the gear.

    Returns:
        The polar angle in radians. Returns ``np.nan`` for any radius `r` that
        is less than the base radius `rb`, as the involute is not defined in
        that region. The return type will be a float if `r` is a scalar, or a
        NumPy array if `r` is an array.
    """
    # Use np.errstate to avoid warnings for invalid values (e.g., r < rb),
    # which will result in np.nan.
    with np.errstate(invalid='ignore'):
        # Ensure r is a numpy array for vectorized operations
        r_arr = np.asarray(r)
        # alpha is the pressure angle at radius r
        alpha = np.arccos(rb / r_arr)
        # The polar angle is tan(alpha) - alpha
        angle = np.tan(alpha) - alpha

    # If the original input was a scalar, return a scalar.
    return angle.item() if np.isscalar(r) else angle