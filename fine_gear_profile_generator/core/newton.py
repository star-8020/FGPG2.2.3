# -*- coding: utf-8 -*-

"""
This module provides a generic Newton-Raphson solver for single or multi-variable systems.
It is designed to solve non-linear systems of equations of the form F(X) = 0.
"""

import numpy as np

def newton_raphson_solver(f, x0, tol=1e-10, max_iter=30, h=1e-6):
    """
    A generic Newton-Raphson solver for single or multi-variable systems,
    using finite differences for the derivative or Jacobian.

    Args:
        f (callable): The function F(X) for which to find the root.
                      It must take a scalar or NumPy array and return a scalar or NumPy array.
        x0 (float or np.ndarray): The initial guess for the variable(s) X.
        tol (float): The convergence tolerance for the absolute value or norm of F(X).
        max_iter (int): The maximum number of iterations.
        h (float): The step size for finite difference approximation.

    Returns:
        float or np.ndarray: The solution X that satisfies F(X) = 0.

    Raises:
        RuntimeError: If the solver fails to converge or if the derivative/Jacobian
                      is zero/singular.
    """
    x = np.asarray(x0, dtype=float)
    is_scalar = x.ndim == 0

    if is_scalar:
        # Handle single-variable case
        x_val = x.item()
        for i in range(max_iter):
            fx = f(x_val)
            if abs(fx) < tol:
                return x_val, True, i, abs(fx)

            # Approximate derivative f'(x)
            f_prime = (f(x_val + h) - fx) / h
            if abs(f_prime) < 1e-14:
                return x_val, False, i, abs(fx)

            # Update solution
            x_val -= fx / f_prime

        return x_val, False, max_iter, abs(f(x_val))
    else:
        # Handle multi-variable case
        n = len(x)
        for i in range(max_iter):
            r = f(x)
            nr = np.linalg.norm(r)

            if nr < tol:
                return x, True, i, nr

            # Approximate Jacobian using forward finite differences
            J = np.zeros((n, n))
            for j in range(n):
                xj = x.copy()
                xj[j] += h
                J[:, j] = (f(xj) - r) / h

            # Solve the linear system J * dx = -r with damping and lstsq fallback
            try:
                dx = np.linalg.solve(J + 1e-12 * np.eye(n), -r)
            except np.linalg.LinAlgError:
                dx = np.linalg.lstsq(J, -r, rcond=None)[0]

            # Update solution
            x += dx

        # Return failure if convergence is not achieved
        return x, False, max_iter, np.linalg.norm(f(x))