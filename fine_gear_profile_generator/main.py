"""Entry point module for the Fine Gear Profile Generator application."""

from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk

from typing import Optional

# By using relative imports, we treat this project as a package.
# This script should be run as a module from the parent directory, e.g.:
# python -m fine_gear_profile_generator.main
try:
    from .gui.fgpg_gui import GearApp
    from .core import gear_core
    from .io import dxf_exporter, image_exporter
    from .utils import config_manager
except ImportError:
    print("Error: Failed to import application modules.", file=sys.stderr)
    print("Please run this script as a module from the project's parent directory.", file=sys.stderr)
    print("Example: python -m fine_gear_profile_generator.main", file=sys.stderr)
    sys.exit(1)

def run_headless_mode() -> None:
    """Generate gears using default parameters without launching the GUI."""

    print("Running in headless mode with default parameters...")

    config_data = config_manager.load_app_config()
    params = config_manager.get_default_gear_pair_parameters(config_data)

    working_dir_default = config_manager.get_default_working_directory(config_data)
    if os.path.isabs(working_dir_default):
        working_dir = working_dir_default
    else:
        working_dir = os.path.join(os.path.dirname(__file__), working_dir_default)
    os.makedirs(working_dir, exist_ok=True)

    try:
        result = gear_core.generate_gear_pair(params)
        analysis = result.analysis

        image_exporter.export_gear_pair_to_image(
            working_dir,
            result.gear1.as_tuple(),
            result.gear2.as_tuple(),
            analysis.center_distance,
            params.module,
            params.driver.teeth,
            params.driven.teeth,
            params.center_x,
            params.center_y,
        )

        dxf_exporter.export_gear_pair_to_dxf(
            working_dir,
            result.gear1.as_tuple(),
            result.gear2.as_tuple(),
            analysis.center_distance,
            params.center_x,
            params.center_y,
        )

        print(f"Headless run complete. Files saved in {working_dir}")

    except Exception as exc:
        print(f"An error occurred during the headless run: {exc}", file=sys.stderr)
        sys.exit(1)


def main(argv: Optional[list[str]] = None) -> None:
    """Parse command-line arguments and execute the requested mode."""

    parser = argparse.ArgumentParser(
        description="A fine gear profile generator for spur and internal gears."
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run the application in headless mode without a GUI.'
    )
    # Future arguments for headless mode would be defined here.
    # e.g., parser.add_argument('--module', type=float, help='Set the gear module.')

    args = parser.parse_args(argv)

    if args.headless:
        run_headless_mode()
    else:
        # Launch the GUI application
        try:
            app = GearApp()
            app.mainloop()
        except tk.TclError as e:
            print(f"Error: Could not start the GUI. This may be because no display is available.", file=sys.stderr)
            print(f"({e})", file=sys.stderr)
            print("You can try running in headless mode with the --headless flag.", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    main()