"""Tkinter based user interface for the Fine Gear Profile Generator."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..core import gear_core
from ..core.models import FILLET_METHODS, GearPairParameters, GearSpec, SegmentationSettings
from ..io import dxf_exporter, image_exporter
from ..utils import config_manager, output_naming

SPEC_FIELDS = [
    ("module_m", "Module, m", "[mm], (>0)"),
    ("teeth_number_z", "Teeth Number, z1", "[ea], (+/-)"),
    ("pressure_angle_alpha", "Pressure Angle, alpha", "[deg]"),
    ("offset_factor_x", "Offset Factor, x1", "(-1~+1)"),
    ("backlash_factor_b", "Backlash Factor, b", "(0~1)"),
    ("addendum_factor_a", "Addendum Factor, a", "(e.g. 1.0)"),
    ("dedendum_factor_d", "Dedendum Factor, d", "(e.g. 1.25)"),
    ("hob_edge_radius_c", "Hob Edge Radius, c", ""),
    ("tooth_edge_radius_e", "Tooth Edge Radius, e", "")
]

MATING_FIELDS = [
    ("teeth_number_z2", "Teeth Number, z2", "[ea]"),
    ("offset_factor_x2", "Offset Factor, x2", "")
]

SHAPER_FIELDS = [
    ("n0", "Shaper Teeth, n0", "[ea], (>=5)"),
    ("tip_radius_factor", "Tip Radius, rho0/m", "(blank = c)"),
    ("protuberance_factor", "Protuberance, delta0/m", "(0 = none)"),
    ("profile_shift_x0", "Cutter Offset, x0", ""),
]

GRAPHIC_FIELDS = [
    ("x_0", "Center, x_0", "[mm]"),
    ("y_0", "Center, y_0", "[mm]"),
    ("seg_involute", "Seg, involute", "[ea]"),
    ("seg_edge_r", "Seg, edge_r", "[ea]"),
    ("seg_root_r", "Seg, root_r", "[ea]")
]

PREVIEW_SIZE = 600  # pixels


class GearApp(tk.Tk):
    """Main Tkinter window hosting all application widgets."""

    def __init__(self) -> None:
        super().__init__()
        self.config_data = config_manager.load_app_config()
        self.defaults = config_manager.get_defaults(self.config_data)

        window_config = self.config_data.get('window', {})
        self.title(window_config.get('title', "FGPG - Fine Gear Profile Generator"))
        if window_config.get('geometry'):
            self.geometry(window_config['geometry'])
        # Otherwise Tk sizes the window to fit all widgets.

        self.vars: Dict[str, tk.StringVar] = {}
        self.logo_image: Optional[ImageTk.PhotoImage] = None
        self.result_image: Optional[ImageTk.PhotoImage] = None
        self.last_output_base: Optional[str] = None

        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        left_frame = ttk.Frame(main_frame, padding="10")
        left_frame.grid(row=0, column=0, sticky="ns")
        right_frame = ttk.Frame(main_frame, padding="10")
        right_frame.grid(row=0, column=1, sticky="ns")
        main_frame.grid_columnconfigure(1, weight=1)

        self.create_spec_widgets(left_frame)
        self.create_shaper_cutter_widgets(left_frame) # New frame for shaper params
        self.create_mating_gear_widgets(left_frame)
        self.create_analysis_widgets(left_frame)
        self.create_graphics_widgets(left_frame)
        self.create_control_widgets(right_frame)
        self.load_logo_image()

        # Set initial visibility of the shaper frame
        self._toggle_shaper_widgets()

    def create_entry(
        self,
        parent: ttk.Frame,
        row: int,
        key: str,
        label: str,
        default_val: object,
        unit: str,
    ) -> None:
        """Create a labeled entry widget and store its variable."""

        ttk.Label(parent, text=f"{label} =").grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(default_val))
        self.vars[key] = var
        ttk.Entry(parent, textvariable=var, width=10).grid(row=row, column=1, padx=5)
        ttk.Label(parent, text=unit).grid(row=row, column=2, sticky="w")

    def create_spec_widgets(self, parent: ttk.Frame) -> None:
        """Create widgets that capture the first gear's specification."""

        frame = ttk.LabelFrame(parent, text="1. Gear Spec (Gear 1)", padding="10")
        frame.grid(row=0, column=0, sticky="ew", pady=5)
        for i, (key, label, unit) in enumerate(SPEC_FIELDS):
            default_val = self.defaults.get(key)
            self.create_entry(frame, i, key, label, default_val, unit)

        # Add root fillet method dropdown
        row_index = len(SPEC_FIELDS)
        ttk.Label(frame, text="Fillet Method =").grid(row=row_index, column=0, sticky="w", pady=5)
        var = tk.StringVar(value=self.defaults.get('root_fillet_method', 'rack_trochoid'))
        self.vars['root_fillet_method'] = var
        fillet_options = list(FILLET_METHODS)
        fillet_combo = ttk.Combobox(frame, textvariable=var, values=fillet_options, state="readonly", width=15)
        fillet_combo.grid(
            row=row_index, column=1, columnspan=2, padx=5, sticky="w"
        )
        fillet_combo.bind("<<ComboboxSelected>>", self._toggle_shaper_widgets)

    def create_shaper_cutter_widgets(self, parent: ttk.Frame) -> None:
        """Create widgets for shaper cutter parameters."""
        self.shaper_frame = ttk.LabelFrame(parent, text="1.2. Shaper Cutter Spec", padding="10")
        # Grid placement is handled by _toggle_shaper_widgets

        shaper_defaults = config_manager.get_shaper_defaults(self.config_data)
        for i, (key, label, unit) in enumerate(SHAPER_FIELDS):
            default_val = shaper_defaults.get(key)
            self.create_entry(
                self.shaper_frame, i, f"shaper_{key}", label,
                "" if default_val is None else default_val, unit,
            )

    def _toggle_shaper_widgets(self, event=None) -> None:
        """Show or hide the shaper cutter widgets based on the selected fillet method."""
        if self.vars['root_fillet_method'].get() == 'shaper_trochoid':
            self.shaper_frame.grid(row=1, column=0, sticky="ew", pady=5)
        else:
            self.shaper_frame.grid_remove()

    def create_mating_gear_widgets(self, parent: ttk.Frame) -> None:
        """Create widgets that capture the mating gear specification."""

        frame = ttk.LabelFrame(parent, text="1.5. Mating Gear Spec (Gear 2)", padding="10")
        frame.grid(row=2, column=0, sticky="ew", pady=5)
        for i, (key, label, unit) in enumerate(MATING_FIELDS):
            default_val = self.defaults.get(key)
            self.create_entry(frame, i, key, label, default_val, unit)

    def create_analysis_widgets(self, parent: ttk.Frame) -> None:
        """Create static fields for presenting calculation results."""

        frame = ttk.LabelFrame(parent, text="Analysis", padding="10")
        frame.grid(row=3, column=0, sticky="ew", pady=5)
        ttk.Label(frame, text="Contact Ratio:").grid(row=0, column=0, sticky="w")
        self.vars['contact_ratio'] = tk.StringVar(value="--")
        ttk.Label(
            frame,
            textvariable=self.vars['contact_ratio'],
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=1, sticky="w")
        ttk.Label(frame, text="Center Distance:").grid(row=1, column=0, sticky="w")
        self.vars['center_distance'] = tk.StringVar(value="--")
        ttk.Label(frame, textvariable=self.vars['center_distance']).grid(row=1, column=1, sticky="w")

    def create_graphics_widgets(self, parent: ttk.Frame) -> None:
        """Create widgets for graphics and miscellaneous settings."""

        frame = ttk.LabelFrame(parent, text="2. Graphics & Misc.", padding="10")
        frame.grid(row=4, column=0, sticky="ew", pady=5)
        for i, (key, label, unit) in enumerate(GRAPHIC_FIELDS):
            default_val = self.defaults.get(key)
            self.create_entry(frame, i, key, label, default_val, unit)

    def create_control_widgets(self, parent: ttk.Frame) -> None:
        """Create save/load/run controls and the preview panel."""

        dir_frame = ttk.Frame(parent)
        dir_frame.grid(row=0, column=0, sticky="ew", pady=5)
        ttk.Label(dir_frame, text="Working Directory:").grid(row=0, column=0, sticky="w")
        default_working_dir = self.defaults.get('working_directory', "./result/")
        self.vars['working_directory'] = tk.StringVar(value=default_working_dir)
        ttk.Entry(dir_frame, textvariable=self.vars['working_directory'], width=40).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(dir_frame, text="Browse...", command=self.browse_dir).grid(row=0, column=2)
        dir_frame.columnconfigure(1, weight=1)

        # Buttons sit directly under the working directory so they stay visible
        # on small screens.
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        ttk.Button(btn_frame, text="Load", command=self.load_params_from_file).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Run", command=self.run_calculation).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_params_to_file).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Open Folder", command=self.open_working_directory).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Exit", command=self.quit).pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="Welcome to the Fine Gear Profile Generator!")
        ttk.Label(parent, textvariable=self.status_var, wraplength=600).grid(row=2, column=0, sticky="ew", pady=5)

        self.image_label = ttk.Label(parent, text="Image will be displayed here.")
        self.image_label.grid(row=3, column=0, pady=5, sticky="nsew")
        parent.rowconfigure(3, weight=1)

    def load_logo_image(self) -> None:
        """Load the application logo if Pillow is available."""

        if not PIL_AVAILABLE:
            self.image_label.config(text="Pillow library not found. Image preview is disabled.")
            return
        logo_path = os.path.join(os.path.dirname(config_manager.get_config_path()), 'FGPG2-05', 'FGPG2.png')
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE))
                self.logo_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.logo_image)
            except Exception as exc:  # pragma: no cover - UI feedback
                self.status_var.set(f"Info: Could not load logo. {exc}")
        # A missing logo is not an error: the preview area simply stays empty.

    def browse_dir(self) -> None:
        """Prompt the user to choose a working directory."""

        dir_name = filedialog.askdirectory()
        if dir_name:
            self.vars['working_directory'].set(dir_name)

    def _params_from_ui(self) -> Optional[GearPairParameters]:
        """Parse UI fields into a ``GearPairParameters`` instance."""

        try:
            segmentation = SegmentationSettings(
                involute=int(self.vars['seg_involute'].get()),
                edge=int(self.vars['seg_edge_r'].get()),
                root_round=int(self.vars['seg_root_r'].get()),
            )
            driver = GearSpec(
                teeth=int(self.vars['teeth_number_z'].get()),
                profile_shift=float(self.vars['offset_factor_x'].get()),
            )
            driven = GearSpec(
                teeth=int(self.vars['teeth_number_z2'].get()),
                profile_shift=float(self.vars['offset_factor_x2'].get()),
            )
            shaper_params = None
            root_fillet_method = self.vars['root_fillet_method'].get()
            if root_fillet_method == 'shaper_trochoid':
                shaper_params = config_manager.build_shaper_cutter_parameters(
                    {key: self.vars[f"shaper_{key}"].get() for key, _, _ in SHAPER_FIELDS}
                )

            params = GearPairParameters(
                module=float(self.vars['module_m'].get()),
                pressure_angle_deg=float(self.vars['pressure_angle_alpha'].get()),
                backlash_factor=float(self.vars['backlash_factor_b'].get()),
                addendum_factor=float(self.vars['addendum_factor_a'].get()),
                dedendum_factor=float(self.vars['dedendum_factor_d'].get()),
                hob_edge_radius=float(self.vars['hob_edge_radius_c'].get()),
                tooth_edge_radius=float(self.vars['tooth_edge_radius_e'].get()),
                driver=driver,
                driven=driven,
                segmentation=segmentation,
                center_x=float(self.vars['x_0'].get()),
                center_y=float(self.vars['y_0'].get()),
                root_fillet_method=root_fillet_method,
                shaper_cutter=shaper_params
            )
            return params
        except (ValueError, KeyError) as error:
            messagebox.showerror("Input Error", f"Invalid or missing input value: {error}")
            return None

    def run_calculation(self) -> None:
        """Execute the gear generation engine with the current inputs."""

        params = self._params_from_ui()
        if not params:
            return

        working_dir = self._working_dir()

        try:
            os.makedirs(working_dir, exist_ok=True)
            result = gear_core.generate_gear_pair(params)

            analysis = result.analysis
            gear1 = result.gear1
            gear2 = result.gear2

            # Every run gets its own file names (gear data + time stamp), so
            # earlier results are never overwritten.
            base = output_naming.unique_basename(working_dir, params)
            image_path = image_exporter.export_gear_pair_to_image(
                working_dir,
                gear1,
                gear2,
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
                gear1,
                gear2,
                analysis.center_distance,
                params.center_x,
                params.center_y,
                filename=base + '.dxf',
            )
            output_naming.write_run_record(
                os.path.join(working_dir, base + '.json'),
                self._ui_values(),
                result,
                {'png': os.path.basename(image_path), 'dxf': os.path.basename(dxf_path)},
            )
            self.last_output_base = base

            self.vars['contact_ratio'].set(f"{analysis.contact_ratio:.4f}")
            self.vars['center_distance'].set(f"{analysis.center_distance:.4f} mm")
            self.status_var.set(
                f"Run: OK. Saved {base} (.png .dxf .json)\n"
                f"G1 Undercut: {gear1.undercut_status}. G2 Undercut: {gear2.undercut_status}"
            )
            self.display_result_image(image_path)

        except Exception as exc:  # pragma: no cover - UI feedback
            messagebox.showerror("Calculation Error", f"An error occurred: {exc}")
            self.status_var.set(f"Run: Failed. {exc}")

    def _working_dir(self) -> str:
        return config_manager.resolve_working_directory(self.vars['working_directory'].get())

    def _ui_values(self) -> Dict[str, str]:
        """Current input values (without results and the working directory)."""
        skip = {'working_directory', 'contact_ratio', 'center_distance'}
        return {key: var.get() for key, var in self.vars.items() if key not in skip}

    def open_working_directory(self) -> None:
        """Open the result folder in the system file browser."""
        working_dir = self._working_dir()
        os.makedirs(working_dir, exist_ok=True)
        try:
            if sys.platform.startswith('win'):
                os.startfile(working_dir)  # type: ignore[attr-defined]
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', working_dir])
            else:
                subprocess.Popen(['xdg-open', working_dir])
        except OSError as exc:  # pragma: no cover - depends on the desktop
            messagebox.showerror("Open Folder", f"Could not open {working_dir}: {exc}")

    def display_result_image(self, img_path: str) -> None:
        """Show the generated preview image, if possible."""

        if not PIL_AVAILABLE:
            self.status_var.set("Run: OK. Install Pillow (pip install Pillow) for image preview.")
            return
        try:
            if os.path.exists(img_path):
                img = Image.open(img_path)
                img.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE))
                self.result_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.result_image)
            else:
                self.image_label.config(image=self.logo_image)
                self.status_var.set(f"Image not found: {img_path}")
        except Exception as exc:  # pragma: no cover - UI feedback
            self.status_var.set(f"Error displaying image: {exc}")

    def save_params_to_file(self, path: Optional[str] = None) -> None:
        """Save the current inputs to a parameter file chosen by the user."""

        if path is None:
            working_dir = self._working_dir()
            os.makedirs(working_dir, exist_ok=True)
            suggested = "FGPG_params.json"
            params = self._params_from_ui()
            if params is not None:
                suggested = f"FGPG_{output_naming.describe_parameters(params)}_params.json"
            path = filedialog.asksaveasfilename(
                title="Save parameters",
                initialdir=working_dir,
                initialfile=suggested,
                defaultextension=".json",
                filetypes=[("FGPG parameters", "*.json"), ("All files", "*.*")],
            )  # the dialog itself asks before overwriting an existing file
            if not path:
                return
        success, message = config_manager.save_params(path, self._ui_values())
        self.status_var.set(message)
        if not success:
            messagebox.showerror("Save Error", message)

    def load_params_from_file(self, path: Optional[str] = None) -> None:
        """Load inputs from a parameter file or from a result's .json record."""

        if path is None:
            path = filedialog.askopenfilename(
                title="Load parameters",
                initialdir=self._working_dir(),
                filetypes=[("FGPG parameters / results", "*.json *.dat"), ("All files", "*.*")],
            )
            if not path:
                return
        success, data_or_error = config_manager.load_params(path)
        if success and isinstance(data_or_error, dict):
            for key, value in data_or_error.items():
                if key in self.vars:
                    self.vars[key].set(value)
            self._toggle_shaper_widgets()
            self.status_var.set(f"Loaded {os.path.basename(path)}")
        else:
            messagebox.showerror("Load Error", data_or_error)
            self.status_var.set(f"Load failed: {data_or_error}")
