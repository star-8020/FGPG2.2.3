# -*- coding: utf-8 -*-

"""
This module provides a generic Newton-Raphson solver for single or multi-variable systems.
It is designed to solve non-linear systems of equations of the form F(X) = 0.
"""

import numpy as np

def newton_raphson_solver(f, x0, tol=1e-10, max_iter=30, h=1e-6):
    """A generic Newton-Raphson solver for single or multi-variable systems.

    This function finds the root of a system of non-linear equations, F(X) = 0,
    using the Newton-Raphson iterative method. It can handle both single-variable
    and multi-variable (vector) functions. The derivative (for single-variable)
    or the Jacobian matrix (for multi-variable) is approximated using a
    forward finite difference method.

    Args:
        f: The function F(X) for which to find the root. It must take a
            scalar or NumPy array `X` and return a scalar or NumPy array of
            the same dimension.
        x0: The initial guess for the solution `X`. Can be a float or a
            NumPy array.
        tol: The convergence tolerance. The solver stops when the absolute
            value (for scalar) or the L2 norm (for vector) of F(X) is below
            this value.
        max_iter: The maximum number of iterations to perform before raising
            an error.
        h: The step size used for the finite difference approximation of the
            derivative or Jacobian.

    Returns:
        The solution `X` that satisfies F(X) ≈ 0. The return type (float or
        NumPy array) matches the type of `x0`.

    Raises:
        RuntimeError: If the solver fails to converge within `max_iter`
            iterations, or if the derivative or Jacobian is found to be
            zero or singular, which prevents the next step from being computed.
    """
    x = np.asarray(x0, dtype=float)
    is_scalar = x.ndim == 0

    if is_scalar:
        # Handle single-variable case
        x_val = x.item()
        for i in range(max_iter):
            fx = f(x_val)
            if abs(fx) < tol:
                return x_val

            # Approximate derivative f'(x)
            f_prime = (f(x_val + h) - fx) / h
            if abs(f_prime) < 1e-14:
                raise RuntimeError("Derivative is close to zero. Cannot solve.")

            # Update solution
            x_val -= fx / f_prime

        raise RuntimeError(f"Solver did not converge within {max_iter} iterations. "
                           f"Final value of F(X) is {abs(f(x_val))}.")
    else:
        # Handle multi-variable case (original logic)
        n = len(x)
        for i in range(max_iter):
            fx = f(x)
            norm_fx = np.linalg.norm(fx)

            if norm_fx < tol:
                return x

            # Approximate Jacobian using forward finite differences
            J = np.zeros((n, n))
            for j in range(n):
                x_plus_h = x.copy()
                x_plus_h[j] += h
                J[:, j] = (f(x_plus_h) - fx) / h

            # Solve the linear system J * delta_x = -fx
            try:
                delta_x = np.linalg.solve(J, -fx)
            except np.linalg.LinAlgError:
                raise RuntimeError("Singular Jacobian matrix encountered. Cannot solve.")

            # Update solution
            x += delta_x

        raise RuntimeError(f"Solver did not converge within {max_iter} iterations. "
                           f"Final norm of F(X) is {np.linalg.norm(f(x))}.")