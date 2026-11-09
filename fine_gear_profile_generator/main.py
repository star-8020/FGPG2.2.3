"""Entry point module for the Fine Gear Profile Generator application.

Run it as a module from the project root::

    python -m fine_gear_profile_generator.main             # GUI
    python -m fine_gear_profile_generator.main --headless  # no GUI

The GUI (Tkinter) is imported only when it is needed, so the headless mode
also works on machines without Tk.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from typing import Optional

from .core import gear_core
from .core.models import FILLET_METHODS, ShaperCutterParameters
from .io import dxf_exporter, image_exporter
from .utils import config_manager, output_naming


def run_headless_mode(
    output_dir: Optional[str] = None,
    fillet_method: Optional[str] = None,
    cutter_teeth: Optional[int] = None,
    name: Optional[str] = None,
) -> int:
    """Generate the default gear pair without a GUI.

    Args:
        output_dir: Output directory.  Defaults to ``working_directory`` from
            ``config.json``; relative paths are resolved against the project root.
        fillet_method: Overrides ``root_fillet_method`` from the configuration.
        cutter_teeth: Overrides the shaper cutter tooth count.
        name: Base name of the output files.  By default a unique name with the
            gear data and a time stamp is used, so earlier results are kept.

    Returns:
        Process exit code (0 on success).
    """

    print("Running in headless mode...")

    config_data = config_manager.load_app_config()
    params = config_manager.get_default_gear_pair_parameters(config_data)

    try:
        if fillet_method is not None:
            shaper = params.shaper_cutter
            if fillet_method == 'shaper_trochoid' and shaper is None:
                shaper = config_manager.build_shaper_cutter_parameters(
                    config_manager.get_shaper_defaults(config_data)
                )
            params = replace(params, root_fillet_method=fillet_method, shaper_cutter=shaper)
        if cutter_teeth is not None:
            base = params.shaper_cutter or ShaperCutterParameters()
            # dataclasses.replace re-runs __post_init__, so the value is validated.
            params = replace(params, shaper_cutter=replace(base, teeth=cutter_teeth))

        working_dir = config_manager.resolve_working_directory(
            output_dir or config_manager.get_default_working_directory(config_data)
        )
        os.makedirs(working_dir, exist_ok=True)

        result = gear_core.generate_gear_pair(params)
        analysis = result.analysis
        base = name or output_naming.unique_basename(working_dir, params)

        image_path = image_exporter.export_gear_pair_to_image(
            working_dir,
            result.gear1,
            result.gear2,
            analysis.center_distance,
            params.module,
            params.driver.teeth,
            params.driven.teeth,
            params.center_x,
            params.center_y,
            filename=base + '.png',
        )
        dxf_path = dxf_exporter.export_gear_pair_to_dxf(
            working_dir,
            result.gear1,
            result.gear2,
            analysis.center_distance,
            params.center_x,
            params.center_y,
            filename=base + '.dxf',
        )
        record_path = os.path.join(working_dir, base + '.json')
        output_naming.write_run_record(
            record_path,
            output_naming.inputs_from_parameters(params),
            result,
            {'png': os.path.basename(image_path), 'dxf': os.path.basename(dxf_path)},
        )
    except Exception as exc:  # report any failure as a non-zero exit code
        print(f"An error occurred during the headless run: {exc}", file=sys.stderr)
        return 1

    print(f"Fillet method   : {params.root_fillet_method}")
    print(f"Contact ratio   : {analysis.contact_ratio:.4f}")
    internal = " (internal pair)" if analysis.is_internal else ""
    print(f"Center distance : {abs(analysis.center_distance):.4f} mm{internal}")
    print(f"Gear 1 undercut : {result.gear1.undercut_status}")
    print(f"Gear 2 undercut : {result.gear2.undercut_status}")
    for label, gear in (("Gear 1", result.gear1), ("Gear 2", result.gear2)):
        for note in gear.notes:
            print(f"Warning ({label}): {note}")
    print(f"Wrote {image_path}")
    print(f"Wrote {dxf_path}")
    print(f"Wrote {record_path}")
    return 0


def main(argv: Optional[list[str]] = None) -> None:
    """Parse command-line arguments and execute the requested mode."""

    parser = argparse.ArgumentParser(
        description="A fine gear profile generator for spur and internal gears."
    )
    parser.add_argument('--headless', action='store_true',
                        help='Run without a GUI using the defaults from config.json.')
    parser.add_argument('--output-dir', help='Headless output directory.')
    parser.add_argument('--fillet-method', choices=FILLET_METHODS,
                        help='Headless: root fillet method (overrides config.json).')
    parser.add_argument('--cutter-teeth', type=int,
                        help='Headless: shaper cutter tooth count (overrides config.json).')
    parser.add_argument('--name',
                        help='Headless: base name of the output files '
                             '(default: gear data + time stamp, never overwrites).')

    args = parser.parse_args(argv)

    if args.headless:
        sys.exit(run_headless_mode(args.output_dir, args.fillet_method, args.cutter_teeth, args.name))

    try:
        import tkinter as tk
        from .gui.fgpg_gui import GearApp
    except ImportError as exc:
        print(f"Error: the GUI requires Tkinter ({exc}).", file=sys.stderr)
        print("Install Tk for your Python or use --headless.", file=sys.stderr)
        sys.exit(1)

    try:
        app = GearApp()
        app.mainloop()
    except tk.TclError as exc:
        print("Error: Could not start the GUI. This may be because no display is available.",
              file=sys.stderr)
        print(f"({exc})", file=sys.stderr)
        print("You can try running in headless mode with the --headless flag.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
