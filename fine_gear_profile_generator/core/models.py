"""Data models for the Fine Gear Profile Generator core layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np


@dataclass
class Arc:
    """Represents a circular arc segment."""

    center: Tuple[float, float]
    radius: float
    start_angle: float
    end_angle: float


@dataclass
class Spline:
    """Represents a spline curve defined by its vertices."""

    vertices: List[Tuple[float, float]]


@dataclass
class StructuredToothProfile:
    """A structured representation of a single tooth profile using geometric primitives."""

    elements: List[Union[Arc, Spline]]
    notes: List[str] = field(default_factory=list)
    tip_radius: Optional[float] = None


@dataclass
class GearSpec:
    """Specification for a single gear.

    Attributes:
        teeth: Number of teeth on the gear. The value must be non-zero so the
            pitch angle can be derived.
        profile_shift: Profile shift coefficient for the gear.
    """

    teeth: int
    profile_shift: float

    def __post_init__(self) -> None:
        """Validate that the gear specification is internally consistent."""

        if self.teeth == 0:
            raise ValueError("Gear teeth count must be non-zero.")


@dataclass
class SegmentationSettings:
    """Rendering segmentation resolution for generated tooth geometry."""

    involute: int
    edge: int
    root_round: int

    def __post_init__(self) -> None:
        """Ensure that the segmentation counts are strictly positive integers."""

        for name, value in (
            ("involute", self.involute),
            ("edge", self.edge),
            ("root_round", self.root_round),
        ):
            if value <= 0:
                raise ValueError(f"Segmentation value '{name}' must be positive.")


FILLET_METHODS = ("rack_trochoid", "shaper_trochoid")


@dataclass
class ShaperCutterParameters:
    """Pinion-type shaper cutter used by the ``shaper_trochoid`` fillet method.

    The cutter shares the module and pressure angle of the work gear.  Its
    outside diameter is derived so that it cuts the gear's root circle
    ``m * (z/2 + x - d)``; lengths are expressed as factors of the module.

    Attributes:
        teeth: Number of cutter teeth ``n0`` (>= 5).
        tip_radius_factor: Tip-round radius ``rho0 / m``.  ``None`` uses the
            gear's hob edge radius factor ``c`` so that the result is directly
            comparable with the rack method.
        protuberance_factor: Protuberance ``delta0 / m`` (0 for a plain cutter).
        profile_shift: Profile shift coefficient ``x0`` of the cutter.
    """

    teeth: int = 50
    tip_radius_factor: Optional[float] = None
    protuberance_factor: float = 0.0
    profile_shift: float = 0.0

    def __post_init__(self) -> None:
        if int(self.teeth) != self.teeth or self.teeth < 5:
            raise ValueError("Shaper cutter teeth must be an integer >= 5.")
        self.teeth = int(self.teeth)
        if self.tip_radius_factor is not None and self.tip_radius_factor < 0:
            raise ValueError("Shaper cutter tip radius factor must be non-negative.")
        if self.protuberance_factor < 0:
            raise ValueError("Shaper cutter protuberance factor must be non-negative.")


@dataclass
class GearPairParameters:
    """Aggregate configuration required to generate a meshing gear pair."""

    module: float
    pressure_angle_deg: float
    backlash_factor: float
    addendum_factor: float
    dedendum_factor: float
    hob_edge_radius: float
    tooth_edge_radius: float
    driver: GearSpec
    driven: GearSpec
    segmentation: SegmentationSettings
    root_fillet_method: str = "rack_trochoid"
    shaper_cutter: Optional[ShaperCutterParameters] = None
    driven_fillet_method: Optional[str] = None  # None = same as root_fillet_method
    center_x: float = 0.0
    center_y: float = 0.0

    def __post_init__(self) -> None:
        """Validate scalar configuration values."""

        if self.module <= 0:
            raise ValueError("Module must be positive.")
        if not 0 < self.pressure_angle_deg < 90:
            raise ValueError("Pressure angle must be between 0 and 90 degrees.")
        if self.driven_fillet_method is not None and self.driven_fillet_method not in FILLET_METHODS:
            raise ValueError(
                f"Unknown root fillet method '{self.driven_fillet_method}' for gear 2. "
                f"Expected one of {', '.join(FILLET_METHODS)}."
            )
        if self.root_fillet_method not in FILLET_METHODS:
            raise ValueError(
                f"Unknown root fillet method '{self.root_fillet_method}'. "
                f"Expected one of {', '.join(FILLET_METHODS)}."
            )

    def fillet_method_for(self, gear_type: str) -> str:
        """Fillet method requested for ``'driver'`` (gear 1) or ``'driven'`` (gear 2)."""

        if gear_type == 'driven' and self.driven_fillet_method is not None:
            return self.driven_fillet_method
        return self.root_fillet_method

    def to_calculation_dict(self) -> Dict[str, object]:
        """Translate the dataclass into the dictionary form used by the engine."""

        return {
            "M": self.module,
            "Z": self.driver.teeth,
            "ALPHA": self.pressure_angle_deg,
            "X": self.driver.profile_shift,
            "B": self.backlash_factor,
            "A": self.addendum_factor,
            "D": self.dedendum_factor,
            "C": self.hob_edge_radius,
            "E": self.tooth_edge_radius,
            "SEG_INVOLUTE": self.segmentation.involute,
            "SEG_EDGE_R": self.segmentation.edge,
            "SEG_ROOT_R": self.segmentation.root_round,
            "z2": self.driven.teeth,
            "x2": self.driven.profile_shift,
            "X_0": self.center_x,
            "Y_0": self.center_y,
            "FILLET_METHOD": self.root_fillet_method,
            "FILLET_METHOD_2": self.driven_fillet_method,
        }

    @classmethod
    def from_dict(cls, params: Dict[str, object]) -> "GearPairParameters":
        """Build an instance from the legacy dictionary representation.

        ``FILLET_METHOD`` is optional and defaults to ``rack_trochoid``.
        """

        segmentation = SegmentationSettings(
            involute=int(params["SEG_INVOLUTE"]),
            edge=int(params["SEG_EDGE_R"]),
            root_round=int(params["SEG_ROOT_R"]),
        )
        return cls(
            module=float(params["M"]),
            pressure_angle_deg=float(params["ALPHA"]),
            backlash_factor=float(params["B"]),
            addendum_factor=float(params["A"]),
            dedendum_factor=float(params["D"]),
            hob_edge_radius=float(params["C"]),
            tooth_edge_radius=float(params["E"]),
            driver=GearSpec(teeth=int(params["Z"]), profile_shift=float(params["X"])),
            driven=GearSpec(teeth=int(params["z2"]), profile_shift=float(params["x2"])),
            segmentation=segmentation,
            root_fillet_method=str(params.get("FILLET_METHOD", "rack_trochoid")),
            driven_fillet_method=params.get("FILLET_METHOD_2"),
            center_x=float(params.get("X_0", 0.0)),
            center_y=float(params.get("Y_0", 0.0)),
        )


@dataclass
class GearPairAnalysis:
    """Calculated metrics that describe a gear pair's performance."""

    contact_ratio: float
    center_distance: float  # signed: negative for an internal pair (ISO 21771)

    @property
    def is_internal(self) -> bool:
        """True for a pinion meshing with an internal (ring) gear."""
        return self.center_distance < 0


@dataclass
class GearProfileGeometry:
    """Generated geometric information for a single gear."""

    profile: Union[StructuredToothProfile, Tuple[np.ndarray, np.ndarray]]
    teeth: int
    pitch_angle: float
    alignment_angle: float
    undercut_status: str
    notes: List[str] = field(default_factory=list)


@dataclass
class GearPairResult:
    """Container bundling the geometry and analysis for a gear pair."""

    analysis: GearPairAnalysis
    gear1: GearProfileGeometry
    gear2: GearProfileGeometry

    def to_dict(self) -> Dict[str, Dict[str, object]]:
        """Expose the result as a dictionary for backward compatibility."""

        return {
            "analysis": {
                "contact_ratio": self.analysis.contact_ratio,
                "center_distance": self.analysis.center_distance,
            },
            "gear1": {"undercut_status": self.gear1.undercut_status},
            "gear2": {"undercut_status": self.gear2.undercut_status},
        }

