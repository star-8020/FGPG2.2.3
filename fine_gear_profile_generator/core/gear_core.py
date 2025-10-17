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
    """Normalize legacy dictionaries into ``GearPairParameters`` instances.

    This function ensures that the gear parameters are always represented by a
    ``GearPairParameters`` object, allowing for consistent access to parameter
    values throughout the calculation pipeline. It handles both modern
    ``GearPairParameters`` objects and older dictionary-based parameter sets.

    Args:
        params: The gear parameters, which can be either a ``GearPairParameters``
            object or a dictionary mapping parameter names to float values.

    Returns:
        A ``GearPairParameters`` instance containing the normalized gear parameters.
    """
    if isinstance(params, GearPairParameters):
        return params
    return GearPairParameters.from_dict(params)


def generate_gear_pair(
    params: Union[GearPairParameters, Dict[str, float]],
) -> GearPairResult:
    """Compute all derived geometry and analysis data for the supplied gear pair.

    This is the main entry point for generating a pair of gears. It takes a set of
    gear parameters, calculates key performance metrics like contact ratio and
    center distance, checks for undercut conditions, and generates the tooth
    profile geometry for both the driver and driven gears.

    Args:
        params: The gear parameters, which can be provided as a
            ``GearPairParameters`` object or a dictionary.

    Returns:
        A ``GearPairResult`` object containing the complete analysis and
        geometric data for the gear pair, including the tooth profiles for
        both gears.
    """
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

    undercut_status1 = gear_math.check_undercut(
        calc_params['Z'], calc_params['ALPHA'], calc_params['X'], calc_params['A']
    )
    undercut_status2 = gear_math.check_undercut(
        calc_params['z2'], calc_params['ALPHA'], calc_params['x2'], calc_params['A']
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
            undercut_status=undercut_status1,
        ),
        gear2=GearProfileGeometry(
            profile=gear2_profile_data[0],
            teeth=int(gear2_profile_data[1]),
            pitch_angle=float(gear2_profile_data[2]),
            alignment_angle=float(gear2_profile_data[3]),
            undercut_status=undercut_status2,
        ),
    )
