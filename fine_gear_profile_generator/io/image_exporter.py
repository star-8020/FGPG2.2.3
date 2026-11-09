"""Utilities for exporting gear pair previews as images."""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np
from matplotlib.figure import Figure

from ..core import transformations
from ..core.models import GearProfileGeometry, Spline, StructuredToothProfile

# A constant for the number of segments to approximate an arc for plotting
ARC_PLOT_SEGMENTS = 20
DEFAULT_IMAGE_FILENAME = 'Result1.png'


def _element_points(element) -> np.ndarray:
    """Return the points of a profile element as an ``(N, 2)`` array."""
    if isinstance(element, Spline):
        return np.asarray(element.vertices, dtype=float).reshape(-1, 2)
    angles = np.linspace(element.start_angle, element.end_angle, ARC_PLOT_SEGMENTS)
    return np.column_stack((
        element.center[0] + element.radius * np.cos(angles),
        element.center[1] + element.radius * np.sin(angles),
    ))


def _structured_profile_to_polyline(profile: StructuredToothProfile) -> Tuple[np.ndarray, np.ndarray]:
    """Convert a structured tooth profile into a single, continuous polyline for plotting.

    Elements may be stored in either direction (arcs are always counter-clockwise
    and reflected splines are reversed), so each element is flipped when needed
    to start at the end of the previous one.
    """
    chunks = [pts for pts in (_element_points(e) for e in profile.elements) if len(pts)]
    if not chunks:
        return np.array([]), np.array([])

    def dist(p, q):
        return float(np.hypot(*(p - q)))

    if len(chunks) > 1:
        nxt = chunks[1]
        first = chunks[0]
        if min(dist(first[0], nxt[0]), dist(first[0], nxt[-1])) < min(dist(first[-1], nxt[0]), dist(first[-1], nxt[-1])):
            chunks[0] = first[::-1]
    ordered = [chunks[0]]
    for pts in chunks[1:]:
        end = ordered[-1][-1]
        ordered.append(pts[::-1] if dist(end, pts[-1]) < dist(end, pts[0]) else pts)

    poly = np.vstack(ordered)
    return poly[:, 0], poly[:, 1]


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
    filename: str = DEFAULT_IMAGE_FILENAME,
) -> str:
    """Generate and save a PNG preview for the supplied gear pair.

    A standalone :class:`matplotlib.figure.Figure` is used so no GUI backend
    (and no display) is required.

    Returns:
        The path of the written image.

    Raises:
        OSError: If the image cannot be written.
    """

    fig = Figure(figsize=(8, 8))
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

    # Fit the view to the drawn gears with a small margin.
    xs = np.concatenate([line.get_xdata() for line in ax.get_lines()])
    ys = np.concatenate([line.get_ydata() for line in ax.get_lines()])
    margin = 0.05 * max(np.ptp(xs), np.ptp(ys))
    ax.set_xlim(xs.min() - margin, xs.max() + margin)
    ax.set_ylim(ys.min() - margin, ys.max() + margin)
    width = 10.0
    fig.set_size_inches(width, max(4.0, width * (np.ptp(ys) + 2 * margin) / (np.ptp(xs) + 2 * margin) + 0.6))
    fig.tight_layout()

    output_path = os.path.join(working_dir, filename)
    fig.savefig(output_path, dpi=100)
    return output_path
