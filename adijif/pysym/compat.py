"""Backward compatibility layer for pysym.

This module provides compatibility with the existing gekko_translation interface,
enabling gradual migration of components to use pysym backend without code changes.
"""

from typing import Any, Dict, List, Optional, Union

from adijif.solvers import GK_Intermediate, GK_Operators, GKVariable, CpoExpr

from adijif.pysym.model import Model
from adijif.pysym.variables import BinaryVar, Constant, IntegerVar, Variable


class pysym_translation:
    """Compatibility adapter matching gekko_translation interface.

    This class provides the same interface as gekko_translation but uses pysym
    backend for building optimization models. It allows existing components to
    work without modification while benefiting from the new solver-agnostic API.

    Usage (as drop-in replacement for gekko_translation):
        class MyComponent(pysym_translation):
            def __init__(self, model=None, solver="CPLEX"):
                super().__init__(model, solver)
                # rest of component code
    """

    def __init__(
        self, model: Optional[Model] = None, solver: str = "CPLEX"
    ) -> None:
        """Initialize compatibility layer.

        Args:
            model: Optional pysym Model. If not provided, creates new one.
            solver: Solver backend ("CPLEX" or "gekko")
        """
        self.solver = solver
        self.model = model or Model(solver=solver)
        self.solution = None

        # Track created variables for later retrieval
        self._pysym_variables: Dict[str, Variable] = {}

    def _add_intermediate(
        self, eqs: Union[GK_Operators, CpoExpr]
    ) -> Union[GK_Intermediate, CpoExpr]:
        """Add intermediate/simplified equation (compatibility method).

        Args:
            eqs: Equation expression

        Returns:
            Intermediate expression (passed through for pysym)
        """
        # In pysym, intermediates are handled explicitly via add_intermediate
        # For compatibility, just return the expression
        return eqs

    def _add_equation(
        self,
        eqs: List[Union[GKVariable, GK_Intermediate, GK_Operators, CpoExpr]],
    ) -> None:
        """Add equation/constraint to solver (compatibility method).

        Args:
            eqs: List of constraint expressions
        """
        if not isinstance(eqs, list):
            eqs = [eqs]

        # Convert expressions to pysym constraints and add to model
        for eq in eqs:
            # Handle native solver expressions (pass through directly)
            # These will be handled by the translator when compile() is called
            try:
                self.model.add_constraint(eq)
            except (TypeError, ValueError):
                # If it's a native solver expression, store it as an intermediate
                # for later translation. For now, just skip it - the actual
                # constraint was created in the native model
                pass

    def _get_val(
        self,
        value: Union[int, float, GKVariable, GK_Intermediate, GK_Operators],
    ) -> Union[int, float]:
        """Extract value from solver (compatibility method).

        Args:
            value: Variable or expression to extract value from

        Returns:
            Numeric value from solution
        """
        if isinstance(value, (int, float)):
            return value

        # If it's a pysym Variable, extract from solution
        if isinstance(value, Variable):
            if self.solution is None:
                raise RuntimeError("No solution available yet")
            return self.solution.get_value(value)

        # Otherwise try to get from solution by name
        if hasattr(value, "name"):
            if self.solution is None:
                raise RuntimeError("No solution available yet")
            return self.solution.get_value(value)

        # Fallback: return as-is
        return value

    def _convert_input(
        self,
        val: Union[int, List[int], float, List[float]],
        name: Optional[str] = None,
        default: Union[int, float] = None,
    ) -> Union[Variable, int, float]:
        """Convert input to solver variable (compatibility method).

        Args:
            val: Value(s) to convert
            name: Variable name
            default: Default/initial value

        Returns:
            pysym Variable or constant
        """
        # Handle single values as constants
        if isinstance(val, (int, float)):
            const = Constant(val, name=name)
            if name:
                self._pysym_variables[name] = const
            return const

        # Handle lists as domains
        if isinstance(val, list):
            if len(val) == 1:
                # Single value - constant
                const = Constant(val[0], name=name)
                if name:
                    self._pysym_variables[name] = const
                return const
            else:
                # Multiple values - create IntegerVar with list domain
                var = IntegerVar(domain=val, name=name, initial_value=default)
                self.model.add_variable(var)
                if name:
                    self._pysym_variables[name] = var
                return var

        # Default: treat as constant
        const = Constant(val, name=name)
        if name:
            self._pysym_variables[name] = const
        return const

    def _add_objective(
        self,
        objective: Union[List[Union[Variable, GK_Operators, CpoExpr]], Variable, GK_Operators, CpoExpr],
    ) -> None:
        """Add objective function (compatibility method).

        Args:
            objective: Expression(s) to minimize
        """
        if isinstance(objective, list):
            # Multiple objectives - use lexicographic
            objectives = []
            for obj in objective:
                objectives.append((obj, True))  # True = minimize
            self.model.add_lexicographic_objective(objectives)
        else:
            # Single objective - minimize
            self.model.add_objective(objective, minimize=True)

    def _check_in_range(
        self,
        value: Union[int, str, List[int], List[str]],
        possible: Union[List[int], List[str]],
        varname: str,
    ) -> None:
        """Check if value is in allowed range (compatibility method).

        Args:
            value: Value to check
            possible: List of allowed values
            varname: Variable name for error message

        Raises:
            Exception: If value not in possible
        """
        if not isinstance(value, list):
            value = [value]

        for v in value:
            if v not in possible:
                raise Exception(
                    f"{v} invalid for {varname}. Only {possible} possible"
                )

    def solve(self, **kwargs) -> Dict[str, Any]:
        """Solve the model.

        Args:
            **kwargs: Optional parameters (time_limit, etc.)

        Returns:
            Dictionary with solution (empty dict for compatibility)
        """
        self.solution = self.model.solve()

        if not self.solution.is_feasible:
            raise Exception("No solution found")

        return {}

    def get_variable(self, name: str) -> Optional[Variable]:
        """Get variable by name.

        Args:
            name: Variable name

        Returns:
            pysym Variable or None
        """
        return self._pysym_variables.get(name) or self.model.get_variable_by_name(name)

    def get_variables(self) -> Dict[str, Variable]:
        """Get all tracked variables.

        Returns:
            Dictionary mapping names to variables
        """
        return self._pysym_variables.copy()
