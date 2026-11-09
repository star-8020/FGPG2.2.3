# Fine Gear Profile Generator (FGPG) 2.2.3

FGPG generates precise 2D tooth profiles of spur gear pairs (external, and internal with the
rack method) and exports them as DXF (CAD) and PNG (preview). Each tooth is assembled from
exact primitives: involute flanks and root fillets as fit-point SPLINEs, and the tip and root
circles as ARCs.

The root fillet can be generated in two ways:

| Method | Model | When to use |
|---|---|---|
| `rack_trochoid` (default) | Fillet cut by a rack / hob with tip radius `c·m` | Hobbed gears |
| `shaper_trochoid` | Fillet cut by a pinion-type shaper cutter with `n0` teeth (gear–gear generation, Lian 2006) | Shaped gears, internal-gear cutters, small cutters |

---

## Getting started

### Windows (easiest)

1. Download the repository (green **Code** button → *Download ZIP*) and unzip it, or `git clone` it.
2. Double-click **`install_windows.bat`** (once). It
   - looks for Python 3.12 or newer. If Python is missing or older than 3.15, it offers to
     install Python 3.15 with `winget`,
   - creates a private environment in `.venv` and installs the packages,
   - runs a quick test generation into `result/`.
3. Double-click **`run_fgpg.bat`** to start the GUI.

### Any OS (manual)

Requirements: **Python 3.12 or newer** (tested on 3.12, 3.14 and 3.15; numpy/scipy require
3.12+) and the packages in `fine_gear_profile_generator/requirements.txt`. Tkinter is needed
only for the GUI.

```bash
python -m venv .venv
.venv/bin/pip install -r fine_gear_profile_generator/requirements.txt   # Windows: .venv\Scripts\pip
```

Run everything from the repository root (the folder that holds `config.json`).

**GUI**

```bash
python -m fine_gear_profile_generator.main
```

**Headless** (no display or Tk needed)

```bash
python -m fine_gear_profile_generator.main --headless
python -m fine_gear_profile_generator.main --headless --fillet-method shaper_trochoid --cutter-teeth 30 --output-dir out
```

### Output files

Every run writes three files with the same, unique base name that holds the main gear data
and a time stamp:

```
FGPG_m2_z21x0.2_z36x0_rack_20261109-153012.png    preview
FGPG_m2_z21x0.2_z36x0_rack_20261109-153012.dxf    CAD geometry (mm)
FGPG_m2_z21x0.2_z36x0_rack_20261109-153012.json   inputs + results of this run
```

Pattern: `FGPG_m<module>_z<z1>x<x1>_z<z2>x<x2>_<rack | shaper-n<n0>>_<date-time>`. Earlier
results are never overwritten. If two runs fall in the same second, `_2`, `_3` … is
appended. Headless runs can choose the name with `--name`.

In the GUI:
- **Load** opens a parameter file or any result `.json`, so a result's inputs can be
  restored. Old `Inputs.dat` files also load.
- **Save** asks for a file name and suggests one from the gear data.
- **Open Folder** shows the result folder.

A relative working directory is resolved against the repository root, for both GUI and
headless runs.

**Tests**

```bash
pip install pytest
python -m pytest            # GUI tests are skipped when no display is available
xvfb-run -a python -m pytest   # Linux without a desktop: include the GUI tests
```

CI runs the tests on Linux (Python 3.12, 3.14 and 3.15, including the real Tk GUI under
Xvfb). It also runs `install_windows.bat` on a Windows runner.

---

## Configuration (`config.json`)

`defaults` holds the gear parameters (module, teeth, pressure angle, profile shift, backlash,
addendum/dedendum factors, hob edge radius `c`, tip edge radius `e`, mating gear, segment
counts, working directory) and `root_fillet_method`. Gear 2 can use its own method with
`root_fillet_method_2` (`null` = same as gear 1). In the GUI it is the *Fillet Method*
field of the mating gear.

`shaper_cutter_defaults` is used when `root_fillet_method` is `shaper_trochoid`:

```json
"shaper_cutter_defaults": {
  "n0": 50,
  "tip_radius_factor": null,
  "protuberance_factor": 0.0,
  "profile_shift_x0": 0.0
}
```

| Key | Meaning |
|---|---|
| `n0` | Number of cutter teeth (>= 5). |
| `tip_radius_factor` | Cutter tip radius `rho0 / m`. `null` uses the hob edge radius factor `c`, so both methods use the same tool tip radius. |
| `protuberance_factor` | Protuberance `delta0 / m` (0 = plain cutter). |
| `profile_shift_x0` | Profile shift of the cutter. |

The cutter has the module and pressure angle of the gear. Its outside diameter is derived
so that it cuts the gear's root circle `m·(z/2 + x − d)`. The pre-2.2.3 inch-based keys
(`Pnd0`, `da0`, `sn0`, …) are no longer used.

---

## Shaper-cutter fillet: how it works

Implemented in `fine_gear_profile_generator/core/shaper_fillet.py`. Everything is in mm, in the
transverse plane.

1. **Generating mesh.** Gear and cutter mesh without backlash. The operating pressure
   angle follows in closed form from the gear space width (including profile shift and
   backlash) and the cutter tooth thickness:
   `inv αw = (n0·ψb0 − z·ηb) / (z + n0)`, `C = (rb + rb0) / cos αw`.
2. **Tool tip.** The tip round (radius `rho0`) touches the cutter outside circle and its
   involute flank. Its centre lies on the flank involute offset by `rho0 − delta0`, which is
   the same involute rotated by `(rho0 − delta0)/rb0`.
3. **Fillet.** While the gears roll, the tip-round centre traces a trochoid in the gear
   frame. The fillet is the envelope of the tip round, from the root circle up to the point
   where the contact reaches the flank tangency point. There it joins the involute
   tangentially. This point is the start of involute (SOI).
4. **Undercut and protuberance.** If the fillet cuts into the involute, the profile follows
   the fillet up to its intersection with the involute and is reported as
   "Undercut (profile corrected)". This is the same treatment as the rack method.

Only external spur gears are supported by this method. If an internal gear is set to
`shaper_trochoid`, the rack fillet is used for it and a warning is shown.

### Validation (measured by `tests/test_shaper_fillet.py`)

As `n0 → ∞` the shaper cutter becomes a rack, so the fillet must converge to the rack
fillet. Example: z = 18, x = 0.2, m = 1 mm, α = 20°, c = 0.2, b = 0.05. The rack SOI
diameter is 16.9327 mm.

| Cutter teeth `n0` | Max fillet deviation from rack fillet [mm] | SOI diameter [mm] | SOI − rack SOI [µm] |
|---|---|---|---|
| 20 | 8.80e-02 | 17.0287 | +95.9 |
| 50 | 4.04e-02 | 16.9735 | +40.8 |
| 100 | 2.14e-02 | 16.9530 | +20.3 |
| 1 000 | 2.26e-03 | 16.9347 | +1.9 |
| 10 000 | 2.28e-04 | 16.9329 | +0.2 |

The deviation falls as `1/n0`. The tests also check four more properties:
- The fillet starts exactly on the root circle and ends on the involute (to 1e-9 mm).
- The SOI rises as the cutter gets smaller.
- For undercut gears (z = 10) the SOI converges to the rack method's undercut intersection.
- The whole tooth outline is continuous (all element end points meet within 1e-9 mm).

---

## Project structure

```
fine_gear_profile_generator/
  main.py                 entry point (GUI / --headless)
  core/
    models.py             dataclasses: GearPairParameters, ShaperCutterParameters, results
    gear_math.py          involute function, contact ratio, tooth angles, rack curves
    geometry_generator.py assembles one tooth (fillet, involute, tip round, arcs)
    shaper_fillet.py      shaper-cutter fillet (see above)
    transformations.py    mirror / rotate / translate helpers
    gear_core.py          orchestrates a gear pair
  io/                     DXF (ezdxf) and PNG (matplotlib) export
  gui/fgpg_gui.py         Tkinter GUI
  utils/config_manager.py config.json and parameter files
  utils/output_naming.py  unique result file names and run records
  tests/                  pytest / unittest suite
docs/                     design notes
```

## Tooth tip, internal gears and warnings

- **Tip round:** the tip round (`e·m`) is exported as a true ARC, tangent to the involute and
  the tip circle.
- **Narrow or pointed tips** are corrected automatically, and the change is reported as a
  warning (orange text in the GUI, `Warning:` lines in headless mode, `gearN_notes` in the
  run record):
  - If the tip round does not fit on a narrow tip, its radius is reduced until the two rounds
    meet on the tooth centre line.
  - If the flanks cross before the tip circle (a pointed tooth), the tip circle is reduced to
    the point where they meet, and the tip round is removed. The contact ratio then uses the
    reduced tip.
- **Internal gears** use a negative tooth number for the ring gear, with the signed
  convention of ISO 21771. The ring tip radius is `m·(|z|/2 − a − x)`.
  - The contact ratio uses the internal-pair path of contact. Example: z1 = 18 with
    z2 = −60 at x = 0 gives 1.9361.
  - The centre distance is shown as a positive value marked "internal".
  - Profile-shift combinations that cannot mesh raise a clear error.

## Known limitations

- Spur gears only (no helix angle).
- The shaper-cutter fillet is not available for internal gears yet (the rack fillet is used).
- Protuberance is modelled as a tip round shifted towards the flank. The finite length of a
  real protuberance flank is not modelled.

## Reference

Lian, G. (2006). *Determining the Shaper Cut Helical Gear Fillet Profile.* Gear Technology,
Sep/Oct 2006.
