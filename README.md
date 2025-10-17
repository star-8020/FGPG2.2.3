# Fine Gear Profile Generator (FGPG)

## 🧭 Overview

The Fine Gear Profile Generator (FGPG) is a Python-based tool for generating high-precision 2D profiles of spur and internal gears. It provides a flexible and powerful engine for calculating gear geometry, including the involute tooth flanks and the critical root fillet curve.

This project features:
-   A user-friendly GUI built with Tkinter.
-   A core engine for generating gear tooth profiles based on standard gear parameters.
-   Two methods for root fillet generation:
    -   **Rack Trochoid:** A classic and widely-used method that simulates a rack-shaped cutter.
    -   **Shaper Trochoid:** An advanced method that simulates a gear-like shaper cutter, providing more realistic geometry for certain manufacturing processes.
-   Export capabilities for both DXF (for CAD applications) and PNG (for visual previews).
-   A headless mode for running generations from the command line.
-   A modular structure that separates the core logic, GUI, and I/O operations.

## 🚀 Getting Started

### Prerequisites

-   Python 3.6+
-   The required Python packages can be installed via `pip`:
    ```bash
    pip install numpy scipy ezdxf matplotlib Pillow
    ```

### Running the Application

There are two ways to run the Fine Gear Profile Generator:

**1. GUI Mode (Recommended)**

To launch the graphical user interface, run the `main.py` script as a module from the project's root directory:

```bash
python -m fine_gear_profile_generator.main
```

This will open the main application window, where you can input gear parameters, generate profiles, and save the results.

**2. Headless Mode**

For automated workflows or running in environments without a graphical display, you can use the headless mode. This will generate a gear pair using the default parameters specified in `config.json` and save the output files to the default working directory.

```bash
python -m fine_gear_profile_generator.main --headless
```

## ⚙️ Configuration

The application's default settings can be customized through the `config.json` file located in the project's root directory.

### Main Defaults

The `defaults` section contains the primary parameters for the gear generation:

```json
{
  "defaults": {
    "module_m": 1.0,
    "teeth_number_z": 18,
    "pressure_angle_alpha": 20.0,
    "offset_factor_x": 0.2,
    "backlash_factor_b": 0.05,
    "root_fillet_method": "rack_trochoid",
    ...
  }
}
```

### Root Fillet Method

You can choose between two algorithms for generating the root fillet by setting the `root_fillet_method` property:
-   `"rack_trochoid"`: The classic method using a rack cutter approximation (default).
-   `"shaper_trochoid"`: A more advanced method that simulates a shaper cutter, which can produce more accurate root geometry.

### Shaper Cutter Parameters

If you select the `"shaper_trochoid"` method, you can also configure the parameters of the virtual shaper cutter tool in the `shaper_cutter_defaults` section:

```json
{
  "shaper_cutter_defaults": {
    "Pnd0": 12,
    "n0": 1000,
    "phi_n0_deg": 20.0,
    ...
  }
}
```

## 📁 Project Structure

The project is organized into several key directories:

-   `fine_gear_profile_generator/`: The main package directory.
    -   `core/`: Contains the core logic for gear calculations, including geometry generation, mathematical functions, and data models.
    -   `gui/`: Contains the Tkinter-based graphical user interface.
    -   `io/`: Contains modules for exporting the generated profiles to DXF and image files.
    -   `utils/`: Contains utility functions, such as the configuration manager.
    -   `tests/`: Contains unit and integration tests for the various components of the application.
-   `debug_shaper_error.py`: A script for debugging the shaper fillet generation without the GUI.
-   `config.json`: The main configuration file for default parameters.
-   `README.md`: This file.

## 🧪 Running Tests

The project includes a suite of tests to ensure the correctness of the calculations and the stability of the application. To run the tests, you can use Python's built-in `unittest` module from the project's root directory:

```bash
python -m unittest discover fine_gear_profile_generator/tests
```

This will automatically discover and run all the tests in the `tests` directory.

---

**FGPG — bridging analytical design and manufacturing precision.**