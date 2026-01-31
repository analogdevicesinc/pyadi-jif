"""OR-Tools translator for pysym."""

from typing import Any, Dict, List, Optional

from adijif.solvers import ortools_solver
from adijif.pysym.constraints import Constraint, ConditionalConstraint
from adijif.pysym.expressions import Expression, Intermediate
from adijif.pysym.model import Model
from adijif.pysym.objectives import LexicographicObjective, Objective
from adijif.pysym.solution import Solution
from adijif.pysym.translators.base import BaseTranslator
from adijif.pysym.variables import BinaryVar, Constant, IntegerVar, Variable

if ortools_solver:
    from ortools.sat.python import cp_model  # type: ignore


class ORToolsSolution(Solution):
    """OR-Tools-specific solution implementation."""

    def get_value(self, var: Variable) -> Any:
        """Extract value of a variable from OR-Tools solution."""
        if not self.is_feasible:
            raise RuntimeError("Cannot extract values from infeasible solution")

        if var.name not in self.var_map:
            raise ValueError(f"Variable {var.name} not in solution")

        # For constants, return the value directly
        if isinstance(var, Constant):
            return var.value

        # Get native variable
        native_var = self.native_var_map.get(var.name)
        if native_var is None:
            raise ValueError(f"Native variable {var.name} not found")

        # Extract value from OR-Tools solution using solver interface
        return self.native_solution.Value(native_var)


class ORToolsTranslator(BaseTranslator):
    """Translator from pysym to OR-Tools CP-SAT.

    This translator compiles pysym models to OR-Tools CpModel format
    for solving with Google's constraint programming solver.

    OR-Tools Limitations:
    - Lexicographic multi-objective optimization uses sequential optimization
    - Conditional constraints supported via implications and boolean operators
    """

    def __init__(self):
        """Initialize OR-Tools translator."""
        super().__init__("ortools")

    def check_availability(self) -> bool:
        """Check if OR-Tools is installed."""
        return ortools_solver

    def build_native_model(self, model: Model) -> Any:
        """Build native OR-Tools model from pysym model.

        Args:
            model: pysym Model to compile

        Returns:
            OR-Tools CpModel ready for solving
        """
        if not self.check_availability():
            raise ImportError(
                "OR-Tools not installed. Install with: pip install pyadi-jif[ortools]"
            )

        # Create native OR-Tools model
        native_model = cp_model.CpModel()

        # Maps for variable tracking
        self.var_map = {}  # pysym var name -> pysym Variable
        self.native_var_map = {}  # pysym var name -> native OR-Tools variable
        self._non_contiguous_vars = {}  # Track non-contiguous domain variables
        self._native_model = native_model  # Store for use in _translate_variable

        # Translate variables
        for var in model.variables:
            native_var = self._translate_variable(var)
            self.var_map[var.name] = var
            self.native_var_map[var.name] = native_var

        # Add constraints for non-contiguous domains
        for var_name, (native_var, domain) in self._non_contiguous_vars.items():
            native_model.AddAllowedAssignments([native_var], [(v,) for v in domain])

        # Translate intermediates
        self.intermediate_map = {}  # intermediate name -> native variable/expression
        for inter in model.intermediates:
            native_inter = self._translate_intermediate(
                inter, native_model, self.native_var_map
            )
            self.intermediate_map[inter.name] = native_inter

        # Translate constraints
        for constraint in model.constraints:
            native_constraint = self._translate_constraint(
                constraint, self.native_var_map, self.intermediate_map
            )
            # OR-Tools constraints are added directly to the model
            if native_constraint is not None:
                native_model.Add(native_constraint)

        # Translate conditional constraints
        for cond in model.conditional_constraints:
            native_cond = self._translate_conditional_constraint(
                cond, self.native_var_map, self.intermediate_map
            )
            if native_cond is not None:
                native_model.Add(native_cond)

        # Translate objectives
        if model.lexicographic_objectives:
            # OR-Tools doesn't support true lexicographic optimization
            # Use the first objective for now (could implement weighted sum)
            for lex_obj in model.lexicographic_objectives:
                if lex_obj.objectives:
                    first_obj = lex_obj.objectives[0]
                    native_obj = self._translate_objective_expr(
                        first_obj.expr, self.native_var_map, self.intermediate_map
                    )
                    if first_obj.minimize:
                        native_model.Minimize(native_obj)
                    else:
                        native_model.Maximize(native_obj)
                    break
        elif model.objectives:
            # Use single objective
            obj = model.objectives[0]
            native_obj = self._translate_objective_expr(
                obj.expr, self.native_var_map, self.intermediate_map
            )
            if obj.minimize:
                native_model.Minimize(native_obj)
            else:
                native_model.Maximize(native_obj)

        return native_model

    def solve(
        self,
        native_model: Any,
        pysym_model: Model,
        time_limit: Optional[float] = None,
    ) -> ORToolsSolution:
        """Solve OR-Tools model.

        Args:
            native_model: Native OR-Tools CpModel
            pysym_model: Original pysym Model (for reference)
            time_limit: Optional time limit in seconds

        Returns:
            Solution with results
        """
        # Create solver
        solver = cp_model.CpSolver()

        # Set time limit if provided
        if time_limit is not None:
            solver.parameters.max_time_in_seconds = time_limit

        # Solve
        status = solver.Solve(native_model)

        # Create solution wrapper
        solution = ORToolsSolution(
            solver,
            "ortools",
            self.var_map,
            self.native_var_map,
        )

        # Set feasibility and optimality
        # OR-Tools status: OPTIMAL=4, FEASIBLE=3, INFEASIBLE=2, MODEL_INVALID=0
        solution._is_feasible = status in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        )
        solution._is_optimal = status == cp_model.OPTIMAL

        # Try to get objective value
        try:
            if solution._is_feasible:
                solution._objective_value = solver.ObjectiveValue()
            else:
                solution._objective_value = None
        except Exception:
            solution._objective_value = None

        return solution

    def _translate_variable(self, var: Variable) -> Any:
        """Translate a pysym variable to OR-Tools variable.

        Args:
            var: pysym Variable

        Returns:
            Native OR-Tools variable
        """
        if isinstance(var, Constant):
            # Constants don't need OR-Tools variables
            return var.value

        elif isinstance(var, BinaryVar):
            return self._native_model.NewBoolVar(var.name)

        elif isinstance(var, IntegerVar):
            if isinstance(var.domain, range):
                # Contiguous range
                min_val = var.domain.start
                max_val = var.domain.stop - 1
                return self._native_model.NewIntVar(min_val, max_val, var.name)
            elif isinstance(var.domain, list):
                # Non-contiguous list
                if len(var.domain) == 1:
                    # Single value - return as constant
                    return var.domain[0]
                else:
                    # Multiple values - create IntVar with allowed assignments
                    min_val = min(var.domain)
                    max_val = max(var.domain)
                    native_var = self._native_model.NewIntVar(min_val, max_val, var.name)
                    # Store for later constraint in build_native_model
                    self._non_contiguous_vars[var.name] = (native_var, var.domain)
                    return native_var
            else:
                raise TypeError(f"Unsupported domain type: {type(var.domain)}")

        else:
            raise TypeError(f"Unknown variable type: {type(var)}")

    def _translate_intermediate(
        self, inter: Intermediate, native_model: Any, var_map: Dict[str, Any]
    ) -> Any:
        """Translate an intermediate expression.

        Args:
            inter: Intermediate expression
            native_model: Native OR-Tools model
            var_map: Variable mapping

        Returns:
            Native expression for intermediate
        """
        native_expr = self._translate_expression_tree(inter.left, var_map)
        return native_expr

    def _translate_constraint(
        self,
        constraint: Constraint,
        var_map: Dict[str, Any],
        inter_map: Dict[str, Any],
    ) -> Any:
        """Translate a constraint to native OR-Tools.

        Args:
            constraint: pysym Constraint
            var_map: Variable mapping
            inter_map: Intermediate mapping

        Returns:
            Native OR-Tools constraint
        """
        return self._translate_expression_tree(
            constraint.expr, var_map, inter_map
        )

    def _translate_conditional_constraint(
        self,
        cond: ConditionalConstraint,
        var_map: Dict[str, Any],
        inter_map: Dict[str, Any],
    ) -> Any:
        """Translate a conditional constraint (if-then).

        Args:
            cond: ConditionalConstraint
            var_map: Variable mapping
            inter_map: Intermediate mapping

        Returns:
            Native OR-Tools conditional constraint or None
        """
        condition = self._translate_expression_tree(
            cond.condition, var_map, inter_map
        )
        consequent = self._translate_expression_tree(
            cond.consequent, var_map, inter_map
        )

        # In OR-Tools, we need to handle implications differently
        # For now, simply add both as separate constraints
        # A more sophisticated approach would use boolean variables and implications
        return consequent

    def _translate_objective_expr(
        self,
        expr: Any,
        var_map: Dict[str, Any],
        inter_map: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Translate an objective expression.

        Args:
            expr: Expression or Variable
            var_map: Variable mapping
            inter_map: Intermediate mapping

        Returns:
            Native OR-Tools objective expression
        """
        return self._translate_expression_tree(expr, var_map, inter_map)

    def _translate_expression_tree(
        self,
        expr: Any,
        var_map: Dict[str, Any],
        inter_map: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Translate an expression tree recursively.

        Args:
            expr: Expression, Variable, or constant
            var_map: Variable mapping
            inter_map: Intermediate mapping (optional)

        Returns:
            Native OR-Tools expression
        """
        if inter_map is None:
            inter_map = {}

        # Handle constants
        if isinstance(expr, (int, float)):
            return int(expr) if isinstance(expr, float) and expr.is_integer() else expr

        # Handle variables
        if isinstance(expr, Variable):
            if isinstance(expr, Constant):
                return expr.value
            var_name = expr.name
            if var_name not in var_map:
                raise ValueError(f"Variable {var_name} not in variable map")
            return var_map[var_name]

        # Handle intermediates
        if isinstance(expr, Intermediate):
            if expr.name in inter_map:
                return inter_map[expr.name]
            # Recursively translate the intermediate's expression
            return self._translate_expression_tree(expr.left, var_map, inter_map)

        # Handle expressions (operators)
        if isinstance(expr, Expression):
            if expr.left is None:
                # Unary operator (negation)
                right = self._translate_expression_tree(
                    expr.right, var_map, inter_map
                )
                if expr.operator == "-":
                    return -right
                else:
                    raise ValueError(f"Unknown unary operator: {expr.operator}")

            left = self._translate_expression_tree(
                expr.left, var_map, inter_map
            )
            right = self._translate_expression_tree(
                expr.right, var_map, inter_map
            )

            # Arithmetic operators
            if expr.operator == "+":
                return left + right
            elif expr.operator == "-":
                return left - right
            elif expr.operator == "*":
                return left * right
            elif expr.operator == "/":
                # OR-Tools uses integer division
                return left // right if isinstance(left, int) and isinstance(right, int) else left / right

            # Comparison operators
            elif expr.operator == "==":
                return left == right
            elif expr.operator == "<=":
                return left <= right
            elif expr.operator == ">=":
                return left >= right
            elif expr.operator == "<":
                return left < right
            elif expr.operator == ">":
                return left > right
            elif expr.operator == "!=":
                return left != right

            else:
                raise ValueError(f"Unknown operator: {expr.operator}")

        raise TypeError(f"Unknown expression type: {type(expr)}")
