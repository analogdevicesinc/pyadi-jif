"""OR-Tools translator for pysym."""

from typing import Any, Dict, Optional

from importlib.util import find_spec

from adijif.pysym.model import Model
from adijif.pysym.solution import Solution
from adijif.pysym.translators.base import BaseTranslator
from adijif.pysym.variables import BinaryVar, Constant, IntegerVar, Variable
from adijif.pysym.expressions import Expression
from adijif.pysym.constraints import Constraint
from adijif.pysym.objectives import Objective

ortools_available = find_spec("ortools") is not None

if ortools_available:
    from ortools.sat.python import cp_model  # type: ignore


class ORToolsSolution(Solution):
    """Solution wrapper for OR-Tools CP-SAT solver."""

    def __init__(self, solver: Any, status: Any, variable_map: Dict[str, Any]):
        """Initialize solution from OR-Tools CpSolver.

        Args:
            solver: OR-Tools CpSolver instance (after Solve() called)
            status: Status returned from solver.Solve()
            variable_map: Mapping from pysym variables to OR-Tools variables
        """
        self.solver = solver
        self.status = status
        self.variable_map = variable_map

        # Check feasibility
        # Status can be OPTIMAL (4) or FEASIBLE (3)
        status_int = int(status)
        self._feasible = status_int in [3, 4]  # FEASIBLE=3, OPTIMAL=4
        self._optimal = status_int == 4  # OPTIMAL=4

    @property
    def is_feasible(self) -> bool:
        """Check if solution is feasible."""
        return self._feasible

    @property
    def is_optimal(self) -> bool:
        """Check if solution is optimal."""
        return self._optimal

    def get_value(self, var: Variable) -> int:
        """Extract variable value from solution.

        Args:
            var: pysym Variable

        Returns:
            Variable value from solution
        """
        if isinstance(var, Constant):
            return var.value

        native_var = self.variable_map.get(id(var))
        if native_var is None:
            raise ValueError(f"Variable {var.name} not in solution map")

        return int(self.solver.Value(native_var))


class ORToolsTranslator(BaseTranslator):
    """Translator from pysym to OR-Tools CP-SAT.

    This translator compiles pysym models to OR-Tools CpModel format.
    """

    def __init__(self):
        """Initialize OR-Tools translator."""
        super().__init__("ortools")

    def check_availability(self) -> bool:
        """Check if OR-Tools is installed."""
        return ortools_available

    def build_native_model(self, model: Model) -> Any:
        """Build native OR-Tools CpModel from pysym model.

        Args:
            model: pysym Model to translate

        Returns:
            OR-Tools CpModel instance
        """
        if not ortools_available:
            raise RuntimeError("OR-Tools not installed")

        # Create native model
        native_model = cp_model.CpModel()

        # Track variable mapping
        self.variable_map = {}

        # Translate all variables
        for var in model.variables:
            self._translate_variable(native_model, var)

        # Translate all constraints
        for constraint in model.constraints:
            self._translate_constraint(native_model, constraint)

        # Translate objective
        if model.objectives:
            self._translate_objective(native_model, model.objectives[0])

        return native_model

    def _translate_variable(self, native_model: Any, var: Variable) -> Any:
        """Translate pysym variable to OR-Tools variable.

        Args:
            native_model: OR-Tools CpModel
            var: pysym Variable

        Returns:
            OR-Tools IntVar or BoolVar
        """
        if isinstance(var, Constant):
            # Constants don't need OR-Tools variables
            return var.value

        elif isinstance(var, BinaryVar):
            native_var = native_model.NewBoolVar(var.name or "bvar")
            self.variable_map[id(var)] = native_var
            return native_var

        elif isinstance(var, IntegerVar):
            if isinstance(var.domain, range):
                # Contiguous domain
                lb = var.domain.start
                ub = var.domain.stop - 1
                native_var = native_model.NewIntVar(lb, ub, var.name or "ivar")
                self.variable_map[id(var)] = native_var
                return native_var

            elif isinstance(var.domain, list):
                # List domain
                if len(var.domain) == 1:
                    # Single value - treat as constant
                    return var.domain[0]
                else:
                    # Discrete domain - create var with range, then add allowed values constraint
                    lb = min(var.domain)
                    ub = max(var.domain)
                    native_var = native_model.NewIntVar(lb, ub, var.name or "ivar")

                    # Add constraint to restrict to allowed values
                    native_model.AddAllowedAssignments(
                        [native_var], [(v,) for v in var.domain]
                    )

                    self.variable_map[id(var)] = native_var
                    return native_var
            else:
                raise ValueError(f"Invalid domain for {var.name}: {var.domain}")

        else:
            raise ValueError(f"Unsupported variable type: {type(var)}")

    def _translate_expression(
        self, native_model: Any, expr: Any
    ) -> Any:
        """Translate pysym expression to OR-Tools expression.

        Args:
            native_model: OR-Tools CpModel
            expr: Expression to translate

        Returns:
            OR-Tools expression
        """
        if isinstance(expr, (int, float)):
            return int(expr)

        if isinstance(expr, Variable):
            if isinstance(expr, Constant):
                return expr.value
            return self.variable_map.get(id(expr))

        if isinstance(expr, Expression):
            # Recursively translate operands
            left = self._translate_expression(native_model, expr.left)
            right = self._translate_expression(native_model, expr.right)
            op = expr.operator

            if op == "+":
                return left + right
            elif op == "-":
                return left - right
            elif op == "*":
                return left * right
            elif op == "/":
                # Integer division
                return left // right
            else:
                raise ValueError(f"Unsupported operator: {op}")

        raise ValueError(f"Unable to translate expression: {expr}")

    def _translate_constraint(self, native_model: Any, constraint: Constraint):
        """Translate pysym constraint to OR-Tools constraint.

        Args:
            native_model: OR-Tools CpModel
            constraint: Constraint to translate
        """
        expr = constraint.expr

        if isinstance(expr, Expression):
            left = self._translate_expression(native_model, expr.left)
            right = self._translate_expression(native_model, expr.right)
            op = expr.operator

            if op == "==":
                native_model.Add(left == right)
            elif op == "<=":
                native_model.Add(left <= right)
            elif op == ">=":
                native_model.Add(left >= right)
            elif op == "<":
                native_model.Add(left < right)
            elif op == ">":
                native_model.Add(left > right)
            elif op == "!=":
                native_model.Add(left != right)
            else:
                raise ValueError(f"Unsupported constraint operator: {op}")
        else:
            raise ValueError(f"Invalid constraint expression: {expr}")

    def _translate_objective(self, native_model: Any, objective: Objective):
        """Translate pysym objective to OR-Tools objective.

        Args:
            native_model: OR-Tools CpModel
            objective: Objective to translate
        """
        if objective.expr is None:
            return

        obj_expr = self._translate_expression(native_model, objective.expr)

        if objective.minimize:
            native_model.Minimize(obj_expr)
        else:
            native_model.Maximize(obj_expr)

    def solve(
        self,
        native_model: Any,
        pysym_model: Model,
        time_limit: Optional[float] = None,
    ) -> Solution:
        """Solve OR-Tools model.

        Args:
            native_model: OR-Tools CpModel
            pysym_model: Original pysym Model
            time_limit: Optional time limit in seconds

        Returns:
            ORToolsSolution instance
        """
        if not ortools_available:
            raise RuntimeError("OR-Tools not installed")

        solver = cp_model.CpSolver()

        if time_limit:
            solver.parameters.max_time_in_seconds = time_limit

        # Solve the model
        status = solver.Solve(native_model)

        return ORToolsSolution(solver, status, self.variable_map)
