"""Data models for the Fine Gear Profile Generator core layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Union

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


@dataclass
class ShaperCutterParameters:
    """Parameters for the shaper cutter tool, based on Lian (2006)."""

    Pnd0: float
    n0: int
    phi_n0_deg: float
    psi0_deg: float
    sn0: float
    da0: float
    rho0: float
    delta0: float
    ellipse_a: float
    ellipse_b: float
    ellipse_orientation_deg: float


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
    root_fillet_method: str
    shaper_cutter: ShaperCutterParameters | None = None
    center_x: float = 0.0
    center_y: float = 0.0

    def __post_init__(self) -> None:
        """Validate scalar configuration values."""

        if self.module <= 0:
            raise ValueError("Module must be positive.")
        if not 0 < self.pressure_angle_deg < 90:
            raise ValueError("Pressure angle must be between 0 and 90 degrees.")

    def to_calculation_dict(self) -> Dict[str, float]:
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
        }

    @classmethod
    def from_dict(cls, params: Dict[str, float]) -> "GearPairParameters":
        """Build an instance from the legacy dictionary representation."""

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
            center_x=float(params.get("X_0", 0.0)),
            center_y=float(params.get("Y_0", 0.0)),
        )


@dataclass
class GearPairAnalysis:
    """Calculated metrics that describe a gear pair's performance."""

    contact_ratio: float
    center_distance: float


@dataclass
class GearProfileGeometry:
    """Generated geometric information for a single gear."""

    profile: Union[StructuredToothProfile, Tuple[np.ndarray, np.ndarray]]
    teeth: int
    pitch_angle: float
    alignment_angle: float
    undercut_status: str


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

