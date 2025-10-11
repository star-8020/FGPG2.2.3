"""Helpers for loading and persisting Fine Gear Profile Generator settings."""

from __future__ import annotations

import json
import os
from typing import Dict, Tuple

from ..core.models import (
    GearPairParameters,
    GearSpec,
    SegmentationSettings,
    ShaperCutterParameters,
)

DEFAULT_CONFIG_FILENAME = 'config.json'

FALLBACK_DEFAULTS = {
    'module_m': 1.0,
    'teeth_number_z': 18,
    'pressure_angle_alpha': 20.0,
    'offset_factor_x': 0.2,
    'backlash_factor_b': 0.05,
    'addendum_factor_a': 1.0,
    'dedendum_factor_d': 1.25,
    'hob_edge_radius_c': 0.2,
    'tooth_edge_radius_e': 0.1,
    'teeth_number_z2': 36,
    'offset_factor_x2': 0.0,
    'x_0': 0.0,
    'y_0': 0.0,
    'seg_involute': 15,
    'seg_edge_r': 15,
    'seg_root_r': 15,
    'working_directory': './result/',
    'current_image_path': 'Result1.png'
}

UI_TO_CALCULATION_MAP = {
    'module_m': 'M',
    'teeth_number_z': 'Z',
    'pressure_angle_alpha': 'ALPHA',
    'offset_factor_x': 'X',
    'backlash_factor_b': 'B',
    'addendum_factor_a': 'A',
    'dedendum_factor_d': 'D',
    'hob_edge_radius_c': 'C',
    'tooth_edge_radius_e': 'E',
    'x_0': 'X_0',
    'y_0': 'Y_0',
    'seg_involute': 'SEG_INVOLUTE',
    'seg_edge_r': 'SEG_EDGE_R',
    'seg_root_r': 'SEG_ROOT_R',
    'teeth_number_z2': 'z2',
    'offset_factor_x2': 'x2'
}

INT_PARAM_KEYS = {
    'Z', 'SEG_INVOLUTE', 'SEG_EDGE_R', 'SEG_ROOT_R', 'z2'
}


def get_config_path(filename: str = DEFAULT_CONFIG_FILENAME) -> str:
    """Return the absolute path to the application configuration file."""

    package_root = os.path.dirname(os.path.dirname(__file__))
    project_root = os.path.dirname(package_root)
    return os.path.join(project_root, filename)


def load_app_config(path: str | None = None) -> Dict[str, object]:
    """Load application configuration data from JSON."""

    config_path = path or get_config_path()
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}


def get_defaults(config_data: Dict[str, object] | None = None) -> Dict[str, object]:
    """Return merged default values using configuration data with fallbacks."""

    config = config_data or load_app_config()
    defaults = dict(FALLBACK_DEFAULTS)
    defaults.update(config.get('defaults', {}))
    return defaults


def _build_segmentation(defaults: Dict[str, object]) -> SegmentationSettings:
    """Construct segmentation settings from the defaults table."""

    return SegmentationSettings(
        involute=int(defaults.get('seg_involute', FALLBACK_DEFAULTS['seg_involute'])),
        edge=int(defaults.get('seg_edge_r', FALLBACK_DEFAULTS['seg_edge_r'])),
        root_round=int(defaults.get('seg_root_r', FALLBACK_DEFAULTS['seg_root_r'])),
    )


def _build_gear_specs(defaults: Dict[str, object]) -> Tuple[GearSpec, GearSpec]:
    """Return driver and driven gear specifications."""

    driver = GearSpec(
        teeth=int(defaults.get('teeth_number_z', FALLBACK_DEFAULTS['teeth_number_z'])),
        profile_shift=float(defaults.get('offset_factor_x', FALLBACK_DEFAULTS['offset_factor_x'])),
    )
    driven = GearSpec(
        teeth=int(defaults.get('teeth_number_z2', FALLBACK_DEFAULTS['teeth_number_z2'])),
        profile_shift=float(defaults.get('offset_factor_x2', FALLBACK_DEFAULTS['offset_factor_x2'])),
    )
    return driver, driven


def get_default_gear_pair_parameters(config_data: Dict[str, object] | None = None) -> GearPairParameters:
    """Build a ``GearPairParameters`` instance populated with default values."""

    config = config_data or load_app_config()
    defaults = get_defaults(config)
    segmentation = _build_segmentation(defaults)
    driver, driven = _build_gear_specs(defaults)

    root_fillet_method = str(defaults.get('root_fillet_method', 'rack_trochoid'))

    shaper_cutter_params = None
    if root_fillet_method == 'shaper_trochoid':
        shaper_defaults = config.get('shaper_cutter_defaults', {})
        shaper_cutter_params = ShaperCutterParameters(
            Pnd0=float(shaper_defaults.get('Pnd0', 12)),
            n0=int(shaper_defaults.get('n0', 1000)),
            phi_n0_deg=float(shaper_defaults.get('phi_n0_deg', 20.0)),
            psi0_deg=float(shaper_defaults.get('psi0_deg', 22.1)),
            sn0=float(shaper_defaults.get('sn0', 0.13)),
            da0=float(shaper_defaults.get('da0', 9.23)),
            rho0=float(shaper_defaults.get('rho0', 0.01)),
            delta0=float(shaper_defaults.get('delta0', 0.0025)),
            ellipse_a=float(shaper_defaults.get('ellipse_a', 0.01)),
            ellipse_b=float(shaper_defaults.get('ellipse_b', 0.01)),
            ellipse_orientation_deg=float(shaper_defaults.get('ellipse_orientation_deg', 0.0)),
        )

    return GearPairParameters(
        module=float(defaults.get('module_m', FALLBACK_DEFAULTS['module_m'])),
        pressure_angle_deg=float(defaults.get('pressure_angle_alpha', FALLBACK_DEFAULTS['pressure_angle_alpha'])),
        backlash_factor=float(defaults.get('backlash_factor_b', FALLBACK_DEFAULTS['backlash_factor_b'])),
        addendum_factor=float(defaults.get('addendum_factor_a', FALLBACK_DEFAULTS['addendum_factor_a'])),
        dedendum_factor=float(defaults.get('dedendum_factor_d', FALLBACK_DEFAULTS['dedendum_factor_d'])),
        hob_edge_radius=float(defaults.get('hob_edge_radius_c', FALLBACK_DEFAULTS['hob_edge_radius_c'])),
        tooth_edge_radius=float(defaults.get('tooth_edge_radius_e', FALLBACK_DEFAULTS['tooth_edge_radius_e'])),
        driver=driver,
        driven=driven,
        segmentation=segmentation,
        root_fillet_method=root_fillet_method,
        shaper_cutter=shaper_cutter_params,
        center_x=float(defaults.get('x_0', FALLBACK_DEFAULTS['x_0'])),
        center_y=float(defaults.get('y_0', FALLBACK_DEFAULTS['y_0'])),
    )


def get_default_calculation_params(config_data: Dict[str, object] | None = None) -> Dict[str, object]:
    """Expose defaults using the legacy dictionary schema."""

    params = get_default_gear_pair_parameters(config_data)
    return params.to_calculation_dict()


def get_default_working_directory(config_data: Dict[str, object] | None = None) -> str:
    """Return the default working directory specified in the configuration."""

    defaults = get_defaults(config_data)
    return str(defaults.get('working_directory', FALLBACK_DEFAULTS['working_directory']))


def save_params(working_dir: str, params_dict: Dict[str, object]) -> Tuple[bool, str]:
    """Persist UI parameters to ``Inputs.dat`` in the specified directory."""

    os.makedirs(working_dir, exist_ok=True)
    filepath = os.path.join(working_dir, 'Inputs.dat')
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(params_dict, file, indent=4)
        return True, f"Parameters saved to {filepath}"
    except OSError as error:
        return False, f"Error saving parameters: {error}"


def load_params(working_dir: str) -> Tuple[bool, Dict[str, object] | str]:
    """Load parameters from ``Inputs.dat`` within the given directory."""

    filepath = os.path.join(working_dir, 'Inputs.dat')
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            loaded_data = json.load(file)
        return True, loaded_data
    except json.JSONDecodeError:
        return False, f"Error: The file {filepath} is not a valid JSON file."
    except OSError as error:
        return False, f"Failed to load parameters: {error}"
