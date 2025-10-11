"""DXF export utilities for the Fine Gear Profile Generator."""

from __future__ import annotations

import os
from typing import Union

import ezdxf
import numpy as np
from ezdxf.layouts import Modelspace
from ezdxf.math import Vec3

from ..core import transformations
from ..core.models import Arc, GearProfileGeometry, Spline, StructuredToothProfile


def rad2deg(rad: float) -> float:
    """Convert radians to degrees."""
    return rad * 180.0 / np.pi


def _render_tooth_profile(
    msp: Modelspace,
    profile: StructuredToothProfile,
    color: int,
    rotation_angle: float,
    x_offset: float,
    y_offset: float,
) -> None:
    """Render a single structured tooth profile into the modelspace."""
    for element in profile.elements:
        if isinstance(element, Spline):
            vertices = np.array(element.vertices)
            if vertices.size == 0:
                continue

            x_rot, y_rot = transformations.rotate(vertices[:, 0], vertices[:, 1], rotation_angle)
            x_final, y_final = transformations.translate(x_rot, y_rot, x_offset, y_offset)

            points = [Vec3(x, y, 0) for x, y in zip(x_final, y_final)]
            if len(points) > 1:
                msp.add_spline(fit_points=points, dxfattribs={'color': color})

        elif isinstance(element, Arc):
            center_x, center_y = element.center
            center_vec = np.array([center_x, center_y])

            center_x_rot, center_y_rot = transformations.rotate(center_vec[0], center_vec[1], rotation_angle)
            center_x_final, center_y_final = transformations.translate(
                center_x_rot, center_y_rot, x_offset, y_offset
            )

            start_angle_deg = rad2deg(element.start_angle + rotation_angle)
            end_angle_deg = rad2deg(element.end_angle + rotation_angle)

            msp.add_arc(
                center=(center_x_final, center_y_final),
                radius=element.radius,
                start_angle=start_angle_deg,
                end_angle=end_angle_deg,
                dxfattribs={'color': color},
            )


def export_gear_pair_to_dxf(
    working_dir: str,
    gear1: GearProfileGeometry,
    gear2: GearProfileGeometry,
    center_dist: float,
    x_offset: float,
    y_offset: float,
) -> None:
    """Export the supplied gear pair geometry to a DXF file."""
    doc = ezdxf.new('R2000')
    msp = doc.modelspace()

    # Process Gear 1
    profile1 = gear1.profile
    if isinstance(profile1, StructuredToothProfile):
        for i in range(gear1.teeth):
            rotation = gear1.pitch_angle * i
            _render_tooth_profile(
                msp, profile1, color=5, rotation_angle=rotation, x_offset=x_offset, y_offset=y_offset
            )

    # Process Gear 2
    profile2 = gear2.profile
    if isinstance(profile2, StructuredToothProfile):
        initial_rotation2 = np.pi + (np.pi / gear2.teeth)
        for i in range(gear2.teeth):
            rotation = initial_rotation2 + (gear2.pitch_angle * i)
            _render_tooth_profile(
                msp,
                profile2,
                color=1,
                rotation_angle=rotation,
                x_offset=x_offset + center_dist,
                y_offset=y_offset,
            )

    output_path = os.path.join(working_dir, 'Result_Gear_Pair.dxf')
    try:
        doc.saveas(output_path)
    except IOError:  # pragma: no cover - filesystem errors
        print(f"Error: Could not save DXF file to {output_path}.")