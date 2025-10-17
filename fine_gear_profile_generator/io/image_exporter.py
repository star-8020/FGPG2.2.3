"""Utilities for exporting gear pair previews as images."""

from __future__ import annotations

import os
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np

from ..core import transformations
from ..core.models import Arc, GearProfileGeometry, Spline, StructuredToothProfile

# A constant for the number of segments to approximate an arc for plotting
ARC_PLOT_SEGMENTS = 20


def _structured_profile_to_polyline(profile: StructuredToothProfile) -> Tuple[np.ndarray, np.ndarray]:
    """Convert a structured tooth profile into a single, continuous polyline.

    This helper function takes a ``StructuredToothProfile`` and converts its
    constituent arcs and splines into a single sequence of x and y coordinates,
    suitable for plotting with libraries like Matplotlib.

    Args:
        profile: The structured tooth profile to convert.

    Returns:
        A tuple of two NumPy arrays: the x and y coordinates of the polyline.
    """
    all_x, all_y = [], []

    # The elements are already in a continuous order, so we just concatenate them.
    for element in profile.elements:
        if isinstance(element, Spline):
            if not element.vertices:
                continue
            # Unzip the vertices into x and y coordinates
            x_coords, y_coords = zip(*element.vertices)
            all_x.extend(x_coords)
            all_y.extend(y_coords)
        elif isinstance(element, Arc):
            # Generate points along the arc for plotting
            # The angles need to be ordered correctly, linspace handles this.
            angles = np.linspace(element.start_angle, element.end_angle, ARC_PLOT_SEGMENTS)
            x_coords = element.center[0] + element.radius * np.cos(angles)
            y_coords = element.center[1] + element.radius * np.sin(angles)
            all_x.extend(x_coords)
            all_y.extend(y_coords)

    return np.array(all_x), np.array(all_y)


def export_gear_pair_to_image(
    working_dir: str,
    gear1: GearProfileGeometry,
    gear2: GearProfileGeometry,
    center_dist: float,
    module_value: float,
    gear1_teeth: int,
    gear2_teeth: int,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> None:
    """Generate and save a PNG preview for the supplied gear pair.

    This function uses Matplotlib to create a 2D plot of the meshing gear
    pair and saves it as a PNG image. It handles the positioning and rotation
    of each tooth for both gears to create a complete visual representation.

    Args:
        working_dir: The directory where the image file will be saved.
        gear1: The geometric data for the first gear (driver).
        gear2: The geometric data for the second gear (driven).
        center_dist: The center distance between the two gears.
        module_value: The module of the gears.
        gear1_teeth: The number of teeth on the first gear.
        gear2_teeth: The number of teeth on the second gear.
        x_offset: The global x-coordinate offset for the gear pair.
        y_offset: The global y-coordinate offset for the gear pair.
    """
    if 'DISPLAY' not in os.environ and 'XDG_SESSION_TYPE' not in os.environ:
        plt.switch_backend('Agg')

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111)
    ax.set_aspect('equal')
    ax.set_title('Fine Gear Profile Generator - Gear Pair Preview')
    ax.grid(True)

    # Convert the structured profiles from both gears into plottable polylines
    x_tooth1, y_tooth1 = _structured_profile_to_polyline(gear1.profile)
    x_tooth2, y_tooth2 = _structured_profile_to_polyline(gear2.profile)

    # Plot gear 1
    z1, pitch_angle1 = gear1.teeth, gear1.pitch_angle
    for i in range(int(z1)):
        x_temp, y_temp = transformations.rotate(x_tooth1, y_tooth1, pitch_angle1 * i)
        x_final, y_final = transformations.translate(x_temp, y_temp, x_offset, y_offset)
        ax.plot(x_final, y_final, '-', linewidth=1.5, color='blue')

    # Plot gear 2
    z2, pitch_angle2 = gear2.teeth, gear2.pitch_angle
    initial_rotation2 = np.pi + (np.pi / z2)
    for i in range(int(z2)):
        x_temp, y_temp = transformations.rotate(x_tooth2, y_tooth2, initial_rotation2 + (pitch_angle2 * i))
        x_final, y_final = transformations.translate(x_temp, y_temp, x_offset + center_dist, y_offset)
        ax.plot(x_final, y_final, '-', linewidth=1.5, color='red')

    ax.set_xlim(-module_value * gear1_teeth / 1.5, center_dist + module_value * gear2_teeth / 1.5)
    max_teeth = max(gear1_teeth, gear2_teeth)
    ax.set_ylim(-module_value * max_teeth * 1.2, module_value * max_teeth * 1.2)

    output_path = os.path.join(working_dir, 'Result1.png')
    try:
        fig.savefig(output_path, dpi=100)
    except OSError as error:  # pragma: no cover - filesystem errors
        print(f"Error saving image: {error}")
    finally:
        plt.close(fig)