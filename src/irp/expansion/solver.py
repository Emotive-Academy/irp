"""Solver abstraction interface for Linear Programming (LP) and Mixed-Integer

Linear Programming (MILP) using SciPy HiGHS and extensible backend solvers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import linprog, OptimizeResult

from irp.core.exceptions import InfeasibleModelError


@dataclass
class OptimizationResult:
    """Standardized optimization solution container."""

    status: str
    success: bool
    objective_value: float
    variable_values: np.ndarray
    variable_names: List[str]
    solution_dict: Dict[str, float]
    shadow_prices: Optional[Dict[str, float]] = None

    def get(self, var_name: str, default: float = 0.0) -> float:
        """Lookup variable value by name."""
        return self.solution_dict.get(var_name, default)


class LinearSolver:
    """Wrapper around SciPy's HiGHS solver engine."""

    @classmethod
    def solve(
        cls,
        c: np.ndarray,
        a_ub: Optional[np.ndarray] = None,
        b_ub: Optional[np.ndarray] = None,
        a_eq: Optional[np.ndarray] = None,
        b_eq: Optional[np.ndarray] = None,
        bounds: Optional[List[Tuple[Optional[float], Optional[float]]]] = None,
        variable_names: Optional[List[str]] = None,
    ) -> OptimizationResult:
        """Solve min c^T x subject to A_ub x <= b_ub and A_eq x == b_eq.

        Uses SciPy's high-performance HiGHS interior-point and simplex routines.
        """
        res: OptimizeResult = linprog(
            c=c,
            A_ub=a_ub if (a_ub is not None and a_ub.size > 0) else None,
            b_ub=b_ub if (b_ub is not None and b_ub.size > 0) else None,
            A_eq=a_eq if (a_eq is not None and a_eq.size > 0) else None,
            b_eq=b_eq if (b_eq is not None and b_eq.size > 0) else None,
            bounds=bounds,
            method="highs",
        )

        if not res.success:
            raise InfeasibleModelError(
                f"Optimization failed with message: {res.message} (status={res.status})"
            )

        var_names = variable_names or [f"x_{i}" for i in range(len(c))]
        sol_dict = {name: float(res.x[i]) for i, name in enumerate(var_names)}

        # Extract dual variables / shadow prices if available
        shadow_prices = None
        if hasattr(res, "ineqlin") and hasattr(res.ineqlin, "marginals"):
            shadow_prices = {"ineq": res.ineqlin.marginals}

        return OptimizationResult(
            status=str(res.message),
            success=bool(res.success),
            objective_value=float(res.fun),
            variable_values=res.x,
            variable_names=var_names,
            solution_dict=sol_dict,
            shadow_prices=shadow_prices,
        )
