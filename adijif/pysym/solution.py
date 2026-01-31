"""Unified solution interface for all solvers."""

from typing import Any, Dict, Optional

from adijif.pysym.variables import Variable


class Solution:
    """Unified interface for solution results across all solvers.

    Wraps solver-specific solution objects and provides a common API
    for extracting variable values and checking solution status.

    Attributes:
        is_feasible: Whether a feasible solution was found
        is_optimal: Whether the solution is proven optimal
        objective_value: Value of the objective function(s)
        solver_name: Name of solver that produced this solution
        native_solution: Raw solution object from underlying solver
    """

    def __init__(
        self,
        native_solution: Any,
        solver_name: str,
        var_map: Dict[str, Variable],
        native_var_map: Dict[str, Any],
    ):
        """Initialize solution wrapper.

        Args:
            native_solution: Native solver solution object
            solver_name: Name of the solver (CPLEX, gekko, ortools)
            var_map: Map of variable names to pysym Variable objects
            native_var_map: Map of variable names to native solver variables
        """
        self.native_solution = native_solution
        self.solver_name = solver_name
        self.var_map = var_map
        self.native_var_map = native_var_map

        # These will be set by the translator
        self._is_feasible = None
        self._is_optimal = None
        self._objective_value = None

    def __repr__(self) -> str:
        """Return string representation."""
        status = "feasible" if self.is_feasible else "infeasible"
        return f"Solution({self.solver_name}, {status})"

    @property
    def is_feasible(self) -> bool:
        """Check if solution is feasible."""
        if self._is_feasible is None:
            raise ValueError("Solution status not set by translator")
        return self._is_feasible

    @property
    def is_optimal(self) -> bool:
        """Check if solution is proven optimal."""
        if self._is_optimal is None:
            return False
        return self._is_optimal

    @property
    def objective_value(self) -> Optional[float]:
        """Get objective function value."""
        return self._objective_value

    def get_value(self, var: Variable) -> Any:
        """Extract value of a variable from the solution.

        Args:
            var: The Variable to extract value for

        Returns:
            The numeric value of the variable in this solution

        Raises:
            ValueError: If variable not in solution
            RuntimeError: If solution is infeasible
        """
        if not self.is_feasible:
            raise RuntimeError("Cannot extract values from infeasible solution")

        if var.name not in self.var_map:
            raise ValueError(f"Variable {var.name} not in solution")

        # This method signature is common; implementation is solver-specific
        # and must be provided by the translator
        raise NotImplementedError(
            "get_value() must be implemented by solver translator"
        )

    def get_values(self, variables: list) -> Dict[str, Any]:
        """Extract values of multiple variables.

        Args:
            variables: List of Variable objects

        Returns:
            Dictionary mapping variable names to values
        """
        return {var.name: self.get_value(var) for var in variables}
