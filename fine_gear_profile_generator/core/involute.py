# -*- coding: utf-8 -*-

"""
This module contains utility functions for calculating involute curve coordinates.
"""

import numpy as np


def involute_polar_angle(r, rb):
    """
    Calculates the polar angle (involute function) of an involute curve at a given radius.
    The angle is relative to the starting point of the involute on the base circle.

    This is equivalent to the involute function, inv(alpha) = tan(alpha) - alpha.

    Args:
        r (float or np.ndarray): Radius at which to calculate the involute angle.
        rb (float): Base circle radius.

    Returns:
        float or np.ndarray: The polar angle in radians. Returns np.nan for r < rb.
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