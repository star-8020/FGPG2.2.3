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

    p = _resolve_parameters(params)

    profiles = {
        gear_type: geometry_generator.generate_tooth_profile(params=p, gear_type=gear_type)
        for gear_type in ('driver', 'driven')
    }

    def actual_tip(gear_type: str, teeth: int):
        # External gears: use the tip radius actually drawn (it may have been
        # topped because the tooth was pointed).  Internal gears: nominal.
        return profiles[gear_type][0].tip_radius if teeth > 0 else None

    contact_ratio, center_dist = gear_math.calculate_contact_ratio(
        p.module, p.driver.teeth, p.driven.teeth,
        p.driver.profile_shift, p.driven.profile_shift,
        p.pressure_angle_deg, p.addendum_factor,
        tip_radius1=actual_tip('driver', p.driver.teeth),
        tip_radius2=actual_tip('driven', p.driven.teeth),
    )

    def geometry(gear_type: str) -> GearProfileGeometry:
        profile, teeth, pitch, align, status = profiles[gear_type]
        return GearProfileGeometry(
            profile=profile,
            teeth=int(teeth),
            pitch_angle=float(pitch),
            alignment_angle=float(align),
            undercut_status=_describe_undercut(status),
            notes=list(profile.notes),
        )

    return GearPairResult(
        analysis=GearPairAnalysis(contact_ratio=contact_ratio, center_distance=center_dist),
        gear1=geometry('driver'),
        gear2=geometry('driven'),
    )
