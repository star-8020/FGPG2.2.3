> **Status (FGPG 2.2.3):** this was an early sketch and is **not** the implemented algorithm.
> Known problems: residual `F4` is identically zero, and the "involute" in section 3
> (`r = rb·sqrt(1+tan²φ)` at polar angle `φ`) is the straight line `x = rb`.
> The implemented shaper-cutter fillet is documented in `README.md` and
> `fine_gear_profile_generator/core/shaper_fillet.py`.

# Newton–Elliptical Shaper Solver Implementation Guide

> **Goal:** A simple but plausible, standard shaper-cutter based, ready-to-implement blueprint for solving elliptical cutter tip geometry using a vectorized Newton solver.

---

## 1️⃣ Unknowns and Constraints
We define the 4-vector of unknowns as:
\[ x = [r_{S0}, \lambda_{S0}, \theta_{Pn0}, \theta_{En0}]^T \]

### Constraints (F = 0)
| Equation | Description | Purpose |
|-----------|--------------|----------|
| F₁ | Tangency between tip and involute at P₀ | Ensure correct slope alignment |
| F₂ | Tangency between tip and OD at E₀ | Ensure OD contact consistency |
| F₃ | Arc-thickness / radial closure | Maintain geometric closure |
| F₄ | Orientation and position closure | Stabilize tip pose |

> Minimal system (for early testing): Use two tangency (P₀/E₀) and two radial consistency equations.

---

## 2️⃣ Elliptical Tip Geometry (Local Frame)

The cutter tip ellipse is defined in its normal plane:

\[
X_{tip}(\theta_n) = (a \cos \theta_n, b \sin \theta_n)
\]
\[
T_{tip}(\theta_n) = (-a \sin \theta_n, b \cos \theta_n)
\]
\[
N_{tip}(\theta_n) = (-b \cos \theta_n, -a \sin \theta_n)
\]

Transform into the tool transverse plane using the cutter’s center position S₀ and orientation λₛ₀:

\[
X_0 = S_0 + R(\psi_0) X_{tip}(\theta_n)
\]
where \(R(\psi_0)\) is the rotation matrix of the helix projection (identity for spur gears).

---

## 3️⃣ Involute Geometry (for Tangency at P₀)

Transverse-plane involute of base circle:
\[
r(\phi) = r_b \sqrt{1 + \tan^2 \phi}
\]
\[
\vec{r}(\phi) = [r(\phi)\cos(\phi),\; r(\phi)\sin(\phi)]
\]

Thickness offset: apply ±Δφ about base circle corresponding to base circular thickness.

Use numerical derivative to compute tangent:
```python
def involute_tangent(rb, phi):
    eps = 1e-6
    r0 = rb * np.sqrt(1 + np.tan(phi)**2)
    p0 = np.array([r0*np.cos(phi), r0*np.sin(phi)])
    p1 = np.array([(rb*np.sqrt(1 + np.tan(phi+eps)**2))*np.cos(phi+eps),
                   (rb*np.sqrt(1 + np.tan(phi+eps)**2))*np.sin(phi+eps)])
    t = p1 - p0
    return t / np.linalg.norm(t)
```

---

## 4️⃣ Tangency and Radial Residuals

**Angle residual:**
\[
f_{angle}(u,v) = \operatorname{atan2}(u_y,u_x) - \operatorname{atan2}(v_y,v_x)
\]
**Cross-product residual:**
\[
f_{cross}(u,v) = \frac{u_x v_y - u_y v_x}{\|u\|\,\|v\|}
\]
**Radial constraint:**
\[
f_{rad} = \|X_E\| - d_{a0}/2
\]

---

## 5️⃣ Newton–Raphson Solver (Vector Form)

```python
import numpy as np

def newton_solve(F, x0, tol=1e-10, maxit=30, h=1e-6):
    x = np.array(x0, dtype=float)
    for k in range(maxit):
        r = F(x)
        nr = np.linalg.norm(r)
        print(f"Iter {k}: ||F||={nr:.3e}, x={x}")
        if nr < tol:
            return x, True, k, nr
        n = len(x)
        J = np.zeros((n, n))
        for j in range(n):
            xj = x.copy(); xj[j] += h
            J[:, j] = (F(xj) - r) / h
        try:
            dx = np.linalg.solve(J + 1e-12*np.eye(n), -r)
        except np.linalg.LinAlgError:
            dx = np.linalg.lstsq(J, -r, rcond=None)[0]
        x += dx
    return x, False, maxit, np.linalg.norm(F(x))
```

---

## 6️⃣ Example Residual Function
```python
def residuals(x, tool):
    rS0, lamS0, thP, thE = x
    S0 = np.array([rS0*np.cos(lamS0), rS0*np.sin(lamS0)])
    a, b = tool['a'], tool['b']
    rb0, da0 = tool['rb0'], tool['da0']

    XP = S0 + np.array([a*np.cos(thP), b*np.sin(thP)])
    XE = S0 + np.array([a*np.cos(thE), b*np.sin(thE)])

    TP = np.array([-a*np.sin(thP), b*np.cos(thP)])
    TE = np.array([-a*np.sin(thE), b*np.cos(thE)])
    TP /= np.linalg.norm(TP); TE /= np.linalg.norm(TE)

    rE = np.linalg.norm(XE)
    rhatE = XE / rE
    F2 = rE - da0/2.0               # OD contact
    F3 = np.dot(TE, rhatE)          # tangency

    phi = np.sqrt((np.linalg.norm(XP)/rb0)**2 - 1.0)
    tinv = involute_tangent(rb0, phi)
    F1 = TP[0]*tinv[1] - TP[1]*tinv[0]  # tangency

    F4 = np.linalg.norm(XP - S0) - np.linalg.norm([a*np.cos(thP), b*np.sin(thP)])
    return np.array([F1, F2, F3, F4])
```

---

## 7️⃣ Example Call
```python
x0 = np.array([tool['r0']-tool['rho0'], 0.0, -np.radians(tool['phi_n0']), -1.2])
x, ok, iters, nrm = newton_solve(lambda x: residuals(x, tool), x0)
print("Solution:", x, "Converged:", ok, "||F||=", nrm)
```

---

## 8️⃣ Tips for Stability
- Normalize tangents and normals before use.
- Apply small damping to Jacobian if near-singular.
- Use `backtracking` if residual increases.
- If initial guesses fail, try: \(θ_{Pn0}≈−φ_{n0}, θ_{En0}≈−1.5\text{ rad}\).

---

## 9️⃣ Next Steps
1. Add arc-thickness constraint for full 4-equation system.
2. Integrate with the shaper trochoid path generator.
3. Validate with Lian (2006) Table 1 benchmark.

---

**Summary:**  
This blueprint defines a Newton–Raphson vector solver and elliptical cutter-tip geometry framework that is *mechanically grounded yet simple enough to execute immediately*.  It provides a working foundation for the shaper-cutter trochoid algorithm in FGPG 2.x.

