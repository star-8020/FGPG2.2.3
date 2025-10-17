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
    """Convert an angle from radians to degrees.

    Args:
        rad: The angle in radians.

    Returns:
        The angle in degrees.
    """
    return rad * 180.0 / np.pi


def _render_tooth_profile(
    msp: Modelspace,
    profile: StructuredToothProfile,
    color: int,
    rotation_angle: float,
    x_offset: float,
    y_offset: float,
) -> None:
    """Render a single structured tooth profile into the modelspace.

    This helper function takes a ``StructuredToothProfile``, which is composed
    of splines and arcs, and adds its geometric elements to the DXF modelspace.
    It applies the necessary rotation and translation to position the tooth
    correctly within the gear.

    Args:
        msp: The ezdxf modelspace to draw on.
        profile: The structured tooth profile to render.
        color: The DXF color code for the tooth profile.
        rotation_angle: The angle (in radians) to rotate the tooth.
        x_offset: The x-coordinate offset for the gear's center.
        y_offset: The y-coordinate offset for the gear's center.
    """
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
    """Export the supplied gear pair geometry to a DXF file.

    This function creates a new DXF document and populates it with the geometry
    of a meshing gear pair. It iterates through each tooth of both gears,
    rendering them in their correct positions and orientations.

    Args:
        working_dir: The directory where the DXF file will be saved.
        gear1: The geometric data for the first gear (driver).
        gear2: The geometric data for the second gear (driven).
        center_dist: The center distance between the two gears.
        x_offset: The global x-coordinate offset for the gear pair.
        y_offset: The global y-coordinate offset for the gear pair.
    """
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