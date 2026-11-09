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
    'root_fillet_method': 'rack_trochoid',
    'root_fillet_method_2': None,
    'working_directory': './result/',
}

SHAPER_FALLBACK_DEFAULTS = {
    'n0': 50,
    'tip_radius_factor': None,
    'protuberance_factor': 0.0,
    'profile_shift_x0': 0.0,
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

    config = load_app_config() if config_data is None else config_data
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


def get_shaper_defaults(config_data: Dict[str, object] | None = None) -> Dict[str, object]:
    """Return the shaper cutter defaults merged with the built-in fallbacks."""

    config = load_app_config() if config_data is None else config_data
    merged = dict(SHAPER_FALLBACK_DEFAULTS)
    merged.update(config.get('shaper_cutter_defaults', {}) or {})
    return merged


def build_shaper_cutter_parameters(values: Dict[str, object]) -> ShaperCutterParameters:
    """Create :class:`ShaperCutterParameters` from config/UI style values.

    ``tip_radius_factor`` may be ``None`` or an empty string, meaning "use the
    hob edge radius factor c".
    """

    tip = values.get('tip_radius_factor', SHAPER_FALLBACK_DEFAULTS['tip_radius_factor'])
    if tip is not None and str(tip).strip() == '':
        tip = None
    return ShaperCutterParameters(
        teeth=int(float(values.get('n0', SHAPER_FALLBACK_DEFAULTS['n0']))),
        tip_radius_factor=None if tip is None else float(tip),
        protuberance_factor=float(values.get('protuberance_factor', 0.0) or 0.0),
        profile_shift=float(values.get('profile_shift_x0', 0.0) or 0.0),
    )


def get_default_gear_pair_parameters(config_data: Dict[str, object] | None = None) -> GearPairParameters:
    """Build a ``GearPairParameters`` instance populated with default values."""

    config = load_app_config() if config_data is None else config_data
    defaults = get_defaults(config)
    segmentation = _build_segmentation(defaults)
    driver, driven = _build_gear_specs(defaults)

    root_fillet_method = str(defaults.get('root_fillet_method', 'rack_trochoid'))
    driven_method = defaults.get('root_fillet_method_2')
    if driven_method in (None, '', 'same', 'same as gear 1'):
        driven_method = None

    shaper_cutter_params = None
    if 'shaper_trochoid' in (root_fillet_method, driven_method):
        shaper_cutter_params = build_shaper_cutter_parameters(get_shaper_defaults(config))

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
        driven_fillet_method=driven_method,
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


def resolve_working_directory(path: str) -> str:
    """Resolve a working directory; relative paths are relative to the project root.

    The project root is the folder that holds ``config.json``.  Using it for
    both the GUI and the headless mode makes the output location independent
    of the directory the program was started from.
    """

    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(os.path.dirname(get_config_path()), path))


def save_params(path: str, params_dict: Dict[str, object]) -> Tuple[bool, str]:
    """Save GUI parameter values as JSON to ``path``."""

    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(params_dict, file, indent=4, ensure_ascii=False)
        return True, f"Parameters saved to {path}"
    except OSError as error:
        return False, f"Error saving parameters: {error}"


def load_params(path: str) -> Tuple[bool, Dict[str, object] | str]:
    """Load GUI parameter values from ``path``.

    Accepts a parameter file written by *Save* (including the old
    ``Inputs.dat``) and the ``.json`` record written next to every result,
    whose values are stored under ``"inputs"``.
    """

    if not os.path.exists(path):
        return False, f"File not found: {path}"

    try:
        with open(path, 'r', encoding='utf-8') as file:
            loaded_data = json.load(file)
    except json.JSONDecodeError:
        return False, f"Error: The file {path} is not a valid JSON file."
    except OSError as error:
        return False, f"Failed to load parameters: {error}"

    if not isinstance(loaded_data, dict):
        return False, f"Error: The file {path} does not contain FGPG parameters."
    if isinstance(loaded_data.get('inputs'), dict):
        loaded_data = loaded_data['inputs']
    if 'shaper_teeth_n0' in loaded_data:  # key used by FGPG 2.2.x files
        loaded_data.setdefault('shaper_n0', loaded_data.pop('shaper_teeth_n0'))
    return True, loaded_data
