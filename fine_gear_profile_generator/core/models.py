"""Data models for the Fine Gear Profile Generator core layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Union

import numpy as np


@dataclass
class Arc:
    """Represents a circular arc segment.

    This class is used to define a portion of a circle, which can be a
    component of a gear tooth profile, such as the top land or root arc.

    Attributes:
        center: A tuple ``(x, y)`` representing the center of the arc.
        radius: The radius of the arc.
        start_angle: The starting angle of the arc in radians.
        end_angle: The ending angle of the arc in radians.
    """
    center: Tuple[float, float]
    radius: float
    start_angle: float
    end_angle: float


@dataclass
class Spline:
    """Represents a spline curve defined by its vertices.

    This class holds the vertices of a spline, which is used to represent the
    more complex, non-circular parts of a gear tooth, like the involute flank
    and the root fillet.

    Attributes:
        vertices: A list of ``(x, y)`` tuples that define the control points
            or vertices of the spline.
    """
    vertices: List[Tuple[float, float]]


@dataclass
class StructuredToothProfile:
    """A structured representation of a single tooth profile.

    This class aggregates the various geometric primitives (arcs and splines)
    that together form the complete profile of a single gear tooth.

    Attributes:
        elements: A list of ``Arc`` and ``Spline`` objects that describe the
            tooth's geometry in a structured way.
    """
    elements: List[Union[Arc, Spline]]


@dataclass
class GearSpec:
    """Specification for a single gear.

    This class holds the fundamental defining parameters for a single gear
    within a gear pair.

    Attributes:
        teeth: The number of teeth on the gear. This value must be non-zero to
            allow for the derivation of the pitch angle.
        profile_shift: The profile shift coefficient for the gear, which
            modifies the tooth thickness and addendum/dedendum.
    """
    teeth: int
    profile_shift: float

    def __post_init__(self) -> None:
        """Validate that the gear specification is internally consistent."""

        if self.teeth == 0:
            raise ValueError("Gear teeth count must be non-zero.")


@dataclass
class SegmentationSettings:
    """Rendering segmentation resolution for generated tooth geometry.

    This class defines how many points should be used to approximate the
    different curves that make up the gear tooth profile. Higher values result
    in a smoother, more accurate representation, at the cost of increased
    computation time and file size.

    Attributes:
        involute: The number of segments to use for the involute flank of the
            tooth.
        edge: The number of segments for the rounded edge at the tooth tip.
        root_round: The number of segments for the trochoidal root fillet.
    """
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
    """Parameters for the shaper cutter tool, based on Lian (2006).

    This class holds the geometric and manufacturing parameters of a shaper
    cutter tool, which is used for generating the root fillet of the gear.
    The parameters are based on the model described in "Computerized design
    and generation of cycloidal gear drives" by T. L. Lian (2006).

    Attributes:
        Pnd0: Diametral pitch of the shaper cutter.
        n0: Number of teeth of the shaper cutter.
        phi_n0_deg: Normal pressure angle of the shaper cutter in degrees.
        psi0_deg: Helix angle of the shaper cutter in degrees.
        sn0: Normal tooth thickness of the shaper cutter.
        da0: Addendum of the shaper cutter.
        rho0: Edge radius of the shaper cutter.
        delta0: Rake angle of the shaper cutter.
    """
    Pnd0: float
    n0: int
    phi_n0_deg: float
    psi0_deg: float
    sn0: float
    da0: float
    rho0: float
    delta0: float


@dataclass
class GearPairParameters:
    """Aggregate configuration required to generate a meshing gear pair.

    This class serves as the main container for all the parameters needed to
    define and generate a pair of meshing gears. It includes geometric
    parameters, manufacturing details, and settings for the generation process.

    Attributes:
        module: The module of the gear pair.
        pressure_angle_deg: The nominal pressure angle in degrees.
        backlash_factor: A factor to introduce backlash (clearance) between teeth.
        addendum_factor: The factor for calculating the addendum height.
        dedendum_factor: The factor for calculating the dedendum depth.
        hob_edge_radius: The radius of the hob cutter's edge.
        tooth_edge_radius: The radius of the tooth's edge rounding.
        driver: A ``GearSpec`` object for the driving gear.
        driven: A ``GearSpec`` object for the driven gear.
        segmentation: ``SegmentationSettings`` for the geometry generation.
        root_fillet_method: The method to use for generating the root fillet
            (e.g., 'rack_trochoid' or 'shaper_trochoid').
        shaper_cutter: An optional ``ShaperCutterParameters`` object, required
            if the ``root_fillet_method`` is 'shaper_trochoid'.
        center_x: The x-coordinate of the gear pair's center.
        center_y: The y-coordinate of the gear pair's center.
    """
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
        """Translate the dataclass into the dictionary form used by the engine.

        This method provides backward compatibility with older parts of the
        codebase that expect gear parameters to be in a dictionary format.

        Returns:
            A dictionary mapping the legacy parameter names to their
            corresponding float values.
        """
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
        """Build an instance from the legacy dictionary representation.

        This class method allows for the creation of a ``GearPairParameters``
        object from an older, dictionary-based representation of the parameters.

        Args:
            params: A dictionary containing the gear parameters with legacy
                key names.

        Returns:
            A new instance of ``GearPairParameters`` populated with the data
            from the input dictionary.
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
            center_x=float(params.get("X_0", 0.0)),
            center_y=float(params.get("Y_0", 0.0)),
        )


@dataclass
class GearPairAnalysis:
    """Calculated metrics that describe a gear pair's performance.

    This class stores the results of performance analysis for a generated
    gear pair.

    Attributes:
        contact_ratio: The contact ratio of the gear pair, which indicates the
            average number of teeth in contact at any given time.
        center_distance: The operational center distance between the two gears.
    """
    contact_ratio: float
    center_distance: float


@dataclass
class GearProfileGeometry:
    """Generated geometric information for a single gear.

    This class holds the generated geometric data for a single gear, including
    the tooth profile and other key angular parameters.

    Attributes:
        profile: The geometric representation of the tooth profile. This can be
            a ``StructuredToothProfile`` for a detailed, primitive-based
            description, or a tuple of NumPy arrays for raw vertex data.
        teeth: The number of teeth on the gear.
        pitch_angle: The angle between corresponding points on adjacent teeth.
        alignment_angle: An angle used for correctly orienting the gear.
        undercut_status: A string indicating the undercut status (e.g., "OK",
            "Warning", "Corrected").
    """
    profile: Union[StructuredToothProfile, Tuple[np.ndarray, np.ndarray]]
    teeth: int
    pitch_angle: float
    alignment_angle: float
    undercut_status: str


@dataclass
class GearPairResult:
    """Container bundling the geometry and analysis for a gear pair.

    This class is the final output of the gear generation process. It contains
    the performance analysis and the geometric data for both gears in the pair.

    Attributes:
        analysis: A ``GearPairAnalysis`` object with performance metrics.
        gear1: A ``GearProfileGeometry`` object for the first gear (driver).
        gear2: A ``GearProfileGeometry`` object for the second gear (driven).
    """
    analysis: GearPairAnalysis
    gear1: GearProfileGeometry
    gear2: GearProfileGeometry

    def to_dict(self) -> Dict[str, Dict[str, object]]:
        """Expose the result as a dictionary for backward compatibility.

        This method provides a way to access the results in a dictionary
        format, which may be required for interfacing with other systems or
        for serialization.

        Returns:
            A dictionary containing the analysis and undercut status for the
            gear pair.
        """
        return {
            "analysis": {
                "contact_ratio": self.analysis.contact_ratio,
                "center_distance": self.analysis.center_distance,
            },
            "gear1": {"undercut_status": self.gear1.undercut_status},
            "gear2": {"undercut_status": self.gear2.undercut_status},
        }

