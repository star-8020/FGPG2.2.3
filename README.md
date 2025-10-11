# FGPG 2.2.1
# Fine Gear Profile Generator (FGPG)

### 🧭 Overview
This version of FGPG introduces a major new feature: the **Shaper-Cutter Root Fillet Algorithm**. Based on the analytical work of George Lian (2006), this advanced modeling capability replaces the traditional rack-based trochoid approximation with a realistic gear–gear conjugate model. This allows for the generation of gear profiles with higher precision and improved structural reliability, especially at the tooth root.

This feature is implemented as an optional setting, allowing users to choose between the classic rack generation method and the new shaper-based algorithm.

---

### ⚙️ How to Use the Shaper-Cutter Fillet Option

To enable the shaper-cutter algorithm, modify the `config.json` file in the project's root directory.

1.  **Set the fillet method:**
    In the `defaults` section, set the `root_fillet_method` property to `"shaper_trochoid"`.

    ```json
    {
      "defaults": {
        "root_fillet_method": "shaper_trochoid",
        ...
      }
    }
    ```
    The available options are:
    - `"rack_trochoid"`: The classic method using a rack cutter approximation (default).
    - `"shaper_trochoid"`: The new, more accurate method using a shaper cutter model.

2.  **Configure the shaper cutter tool (optional):**
    You can customize the parameters of the virtual shaper cutter tool by editing the `shaper_cutter_defaults` section in `config.json`.

    ```json
    {
      "shaper_cutter_defaults": {
        "Pnd0": 12,
        "n0": 1000,
        "phi_n0_deg": 20.0,
        "psi0_deg": 22.1,
        "sn0": 0.13,
        "da0": 9.23,
        "rho0": 0.01,
        "delta0": 0.0025,
        "ellipse_a": 0.012,
        "ellipse_b": 0.009,
        "ellipse_orientation_deg": 5.0
      }
    }
    ```

    The `delta0` parameter now directly offsets the cutter center when solving the tool placement. Increasing `delta0` pushes t
    he cutter outward, enlarging the resulting fillet and Start-of-Involute (SOI) diameter as described in Lian's protuberance f
    ormulation. The new `ellipse_a`, `ellipse_b`, and `ellipse_orientation_deg` fields define the semi-axes and in-plane orienta
    tion of the shaper tip ellipse, enabling Newton-based solutions for non-circular cutter tips.

---

### 🧩 Core Implementation
The new algorithm is implemented in the following core modules:
```
/fine_gear_profile_generator/core/
  ├── shaper_fillet.py  # Main shaper-cutter trochoid algorithm
  ├── newton.py         # Multi-variable Newton-Raphson solver
  ├── involute.py       # Involute curve utilities
  ├── geometry_generator.py # Integrates the new method
  └── ...
```

---

### 🧮 Algorithm Workflow
1.  **Configuration:** The application reads the `root_fillet_method` from `config.json`.
2.  **Parameter Calculation:** It computes the base geometry for the gear and, if selected, the shaper tool.
3.  **Fillet Generation:**
    - If `shaper_trochoid` is selected, `shaper_fillet.py` solves the non-linear system for the cutter tip and traces its path to generate the root trochoid.
    - Otherwise, the classic rack-based trochoid is generated.
4.  **SOI Detection:** The Start of Involute (SOI) is calculated by finding the intersection of the fillet and the involute profile.
5.  **Profile Assembly:** The final gear profile is assembled and exported.

---

### 📈 Validation
The algorithm's accuracy is validated by observing its convergence towards the traditional hobbed trochoid as the shaper cutter's number of teeth approaches infinity.

| Cutter Teeth | Max Fillet Deviation (vs. Rack) | SOI Difference (vs. Rack) |
|--------------|---------------------------------|---------------------------|
| 100          | 0.001901 in                     | 0.0102 in                 |
| 1000         | 0.000111 in                     | 0.0011 in                 |
| 10000        | 0.000011 in                     | 0.0001 in                 |

These results confirm that the shaper-based model is a correct generalization of the rack-based limit.

---

### 💡 Benefits
- **Realistic Geometry:** Simulates true gear–gear contact instead of a rack approximation.
- **Improved Strength:** Produces a smoother root curvature, leading to better stress distribution.
- **Advanced Control:** Allows direct control over protuberance and tool-tip radius.
- **FEA-Ready:** Generates high-fidelity profiles suitable for CAE/FEA analysis.

---

### 📚 Reference
Lian, G. (2006). *Determining the Shaper Cut Helical Gear Fillet Profile.* Gear Technology, Sep/Oct 2006.

---

**FGPG — bridging analytical design and manufacturing precision.**
