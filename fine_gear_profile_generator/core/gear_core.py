"""Core calculation orchestrator for the Fine Gear Profile Generator."""

from __future__ import annotations

from typing import Dict, Union

from . import gear_math, geometry_generator
from .models import (
    GearPairAnalysis,
    GearPairParameters,
    GearPairResult,
    GearProfileGeometry,
)


def _resolve_parameters(
    params: Union[GearPairParameters, Dict[str, float]],
) -> GearPairParameters:
    """Normalize legacy dictionaries into ``GearPairParameters`` instances."""

    if isinstance(params, GearPairParameters):
        return params
    return GearPairParameters.from_dict(params)


def _describe_undercut(geometry_status: str) -> str:
    """Translate the geometry generator status into a user-facing message.

    The geometry generator detects undercut exactly (the fillet intersects the
    involute instead of joining it tangentially), so its result is used rather
    than the approximate ``x_min`` rule of :func:`gear_math.check_undercut`.
    """

    return "OK" if geometry_status == "OK" else "Undercut (profile corrected)"


def generate_gear_pair(
    params: Union[GearPairParameters, Dict[str, float]],
) -> GearPairResult:
    """Compute all derived geometry and analysis data for the supplied gear pair."""

    normalized_params = _resolve_parameters(params)
    calc_params = normalized_params.to_calculation_dict()

    contact_ratio, center_dist = gear_math.calculate_contact_ratio(
        calc_params['M'],
        calc_params['Z'],
        calc_params['z2'],
        calc_params['X'],
        calc_params['x2'],
        calc_params['ALPHA'],
        calc_params['A']
    )

    # Pass the full parameter object to the geometry generator
    gear1_profile_data = geometry_generator.generate_tooth_profile(
        params=normalized_params, gear_type='driver'
    )

    gear2_profile_data = geometry_generator.generate_tooth_profile(
        params=normalized_params, gear_type='driven'
    )

    return GearPairResult(
        analysis=GearPairAnalysis(
            contact_ratio=contact_ratio,
            center_distance=center_dist,
        ),
        gear1=GearProfileGeometry(
            profile=gear1_profile_data[0],
            teeth=int(gear1_profile_data[1]),
            pitch_angle=float(gear1_profile_data[2]),
            alignment_angle=float(gear1_profile_data[3]),
            undercut_status=_describe_undercut(gear1_profile_data[4]),
        ),
        gear2=GearProfileGeometry(
            profile=gear2_profile_data[0],
            teeth=int(gear2_profile_data[1]),
            pitch_angle=float(gear2_profile_data[2]),
            alignment_angle=float(gear2_profile_data[3]),
            undercut_status=_describe_undercut(gear2_profile_data[4]),
        ),
    )
