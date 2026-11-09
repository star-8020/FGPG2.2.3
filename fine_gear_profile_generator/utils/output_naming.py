"""File naming and run records for generated results.

Every run gets its own base name built from the main gear data and a time
stamp, e.g. ``FGPG_m2_z21x0.2_z36x0_rack_20261109-153012``, so results never
overwrite each other and the file name tells which gear pair it holds.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Dict, Iterable, Optional

from ..core.models import GearPairParameters, GearPairResult

RESULT_EXTENSIONS = ('.png', '.dxf', '.json')


def _num(value: float) -> str:
    """Compact number for file names: 2.0 -> '2', 0.25 -> '0.25', -0.1 -> '-0.1'."""
    text = f"{float(value):g}"
    return "0" if text == "-0" else text


def describe_parameters(params: GearPairParameters) -> str:
    """Short, file-name safe description of a gear pair, e.g. ``m2_z21x0.2_z36x0_rack``."""

    method = "rack"
    if params.root_fillet_method == 'shaper_trochoid':
        teeth = params.shaper_cutter.teeth if params.shaper_cutter else 50
        method = f"shaper-n{teeth}"
    text = (
        f"m{_num(params.module)}"
        f"_z{params.driver.teeth}x{_num(params.driver.profile_shift)}"
        f"_z{params.driven.teeth}x{_num(params.driven.profile_shift)}"
        f"_{method}"
    )
    return re.sub(r'[^A-Za-z0-9._+-]', '_', text)


def unique_basename(
    working_dir: str,
    params: GearPairParameters,
    now: Optional[datetime] = None,
    extensions: Iterable[str] = RESULT_EXTENSIONS,
) -> str:
    """Return a base name (without extension) that no existing result file uses."""

    stamp = (now or datetime.now()).strftime('%Y%m%d-%H%M%S')
    base = f"FGPG_{describe_parameters(params)}_{stamp}"
    candidate, counter = base, 2
    while any(os.path.exists(os.path.join(working_dir, candidate + ext)) for ext in extensions):
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def write_run_record(
    path: str,
    inputs: Dict[str, object],
    result: GearPairResult,
    files: Dict[str, str],
) -> None:
    """Write the inputs and key results of one run as JSON.

    The ``inputs`` block uses the same keys as the GUI, so the file can be
    opened again with *Load*.
    """

    record = {
        "fgpg_record": 1,
        "created": datetime.now().isoformat(timespec='seconds'),
        "inputs": inputs,
        "results": {
            "contact_ratio": result.analysis.contact_ratio,
            "center_distance_mm": result.analysis.center_distance,
            "gear1_undercut": result.gear1.undercut_status,
            "gear2_undercut": result.gear2.undercut_status,
        },
        "files": files,
    }
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)


def inputs_from_parameters(params: GearPairParameters) -> Dict[str, object]:
    """GUI-style input values for a parameter object (used by the headless mode)."""

    values: Dict[str, object] = {
        'module_m': params.module,
        'teeth_number_z': params.driver.teeth,
        'pressure_angle_alpha': params.pressure_angle_deg,
        'offset_factor_x': params.driver.profile_shift,
        'backlash_factor_b': params.backlash_factor,
        'addendum_factor_a': params.addendum_factor,
        'dedendum_factor_d': params.dedendum_factor,
        'hob_edge_radius_c': params.hob_edge_radius,
        'tooth_edge_radius_e': params.tooth_edge_radius,
        'root_fillet_method': params.root_fillet_method,
        'teeth_number_z2': params.driven.teeth,
        'offset_factor_x2': params.driven.profile_shift,
        'x_0': params.center_x,
        'y_0': params.center_y,
        'seg_involute': params.segmentation.involute,
        'seg_edge_r': params.segmentation.edge,
        'seg_root_r': params.segmentation.root_round,
    }
    if params.shaper_cutter is not None:
        cutter = params.shaper_cutter
        values.update({
            'shaper_n0': cutter.teeth,
            'shaper_tip_radius_factor': '' if cutter.tip_radius_factor is None else cutter.tip_radius_factor,
            'shaper_protuberance_factor': cutter.protuberance_factor,
            'shaper_profile_shift_x0': cutter.profile_shift,
        })
    return values
