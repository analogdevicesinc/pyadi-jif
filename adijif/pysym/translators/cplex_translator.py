"""CPLEX (docplex) translator for pysym."""

from typing import Any, Dict, Optional

from docplex.cp.modeler import if_then  # type: ignore

from adijif.pysym.constraints import ConditionalConstraint, Constraint
from adijif.pysym.expressions import Expression, Intermediate
from adijif.pysym.model import Model
from adijif.pysym.solution import Solution
from adijif.pysym.translators.base import BaseTranslator
from adijif.pysym.variables import BinaryVar, Constant, IntegerVar, Variable
from adijif.solvers import (
    CpoModel,
    binary_var,
    cplex_solver,
    integer_var,
)


class CPLEXSolution(Solution):
    """CPLEX-specific solution implementation."""

    def get_value(self, var: Variable) -> Any:
        """Extract value of a variable from CPLEX solution."""
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

        # Extract value from solution using variable name
        return self.native_solution.get_value(native_var)


class CPLEXTranslator(BaseTranslator):
    """Translator from pysym to CPLEX/docplex.

    This translator compiles pysym models to docplex CpoModel format
    for solving with CPLEX.
    """

    def __init__(self):
        """Initialize CPLEX translator."""
        super().__init__("CPLEX")

    def check_availability(self) -> bool:
        """Check if CPLEX is installed."""
        return cplex_solver

    def build_native_model(self, model: Model) -> CpoModel:
        """Build native CPLEX model from pysym model.

        Args:
            model: pysym Model to compile

        Returns:
            CpoModel ready for solving

        """
        if not self.check_availability():
            raise ImportError(
                "CPLEX not installed. Install with: pip install pyadi-jif[cplex]"
            )

        # Create native CPLEX model
        native_model = CpoModel(name=f"pysym_{model.solver}")

        # Maps for variable tracking
        self.var_map = {}  # pysym var name -> pysym Variable
        self.native_var_map = {}  # pysym var name -> native CPLEX variable

        # Translate variables
        for var in model.variables:
            native_var = self._translate_variable(var)
            self.var_map[var.name] = var
            self.native_var_map[var.name] = native_var

        # Translate intermediates
        self.intermediate_map = {}  # intermediate name -> native variable
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
            native_model.add_constraint(native_constraint)

        # Translate conditional constraints
        for cond in model.conditional_constraints:
            native_cond = self._translate_conditional_constraint(
                cond, self.native_var_map, self.intermediate_map
            )
            native_model.add_constraint(native_cond)

        # Translate objectives
        if model.lexicographic_objectives:
            # Use lexicographic (multi-level) optimization
            objectives = []
            for lex_obj in model.lexicographic_objectives:
                for obj in lex_obj.objectives:
                    native_obj = self._translate_objective_expr(
                        obj.expr, self.native_var_map, self.intermediate_map
                    )
                    if not obj.minimize:
                        native_obj = -native_obj
                    objectives.append(native_obj)
            native_model.add(native_model.minimize_static_lex(objectives))
        elif model.objectives:
            # Use single objective (with weights if multiple)
            # CPLEX doesn't natively support weighted objectives, so take first
            obj = model.objectives[0]
            native_obj = self._translate_objective_expr(
                obj.expr, self.native_var_map, self.intermediate_map
            )
            if obj.minimize:
                native_model.minimize(native_obj)
            else:
                native_model.maximize(native_obj)

        return native_model

    def solve(
        self,
        native_model: CpoModel,
        pysym_model: Model,
        time_limit: Optional[float] = None,
    ) -> CPLEXSolution:
        """Solve CPLEX model.

        Args:
            native_model: Native CPLEX CpoModel
            pysym_model: Original pysym Model (for reference)
            time_limit: Optional time limit in seconds

        Returns:
            Solution with results

        """
        # Solve with optional time limit
        if time_limit is not None:
            native_solution = native_model.solve(TimeLimit=int(time_limit))
        else:
            native_solution = native_model.solve()

        # Create solution wrapper
        solution = CPLEXSolution(
            native_solution,
            "CPLEX",
            self.var_map,
            self.native_var_map,
        )

        # Set feasibility and optimality
        solution._is_feasible = native_solution.is_solution()
        solution._is_optimal = (
            native_solution.is_feasible_solution()
            if hasattr(native_solution, "is_feasible_solution")
            else False
        )

        # Try to get objective value
        try:
            solution._objective_value = native_solution.get_objective_value()
        except Exception:
            solution._objective_value = None

        return solution

    def _translate_variable(self, var: Variable) -> Any:
        """Translate a pysym variable to CPLEX variable.

        Args:
            var: pysym Variable

        Returns:
            Native CPLEX variable

        """
        if isinstance(var, Constant):
            # Constants don't need CPLEX variables, return the value
            return var.value

        elif isinstance(var, BinaryVar):
            return binary_var(name=var.name)

        elif isinstance(var, IntegerVar):
            if isinstance(var.domain, range):
                # Contiguous range
                min_val = var.domain.start
                max_val = var.domain.stop - 1
                return integer_var(min_val, max_val, name=var.name)
            elif isinstance(var.domain, list):
                # Non-contiguous list
                if len(var.domain) == 1:
                    # Single value - constant
                    return var.domain[0]
                else:
                    # Multiple values - use domain
                    return integer_var(var.domain, name=var.name)
            else:
                raise TypeError(f"Unsupported domain type: {type(var.domain)}")

        else:
            raise TypeError(f"Unknown variable type: {type(var)}")

    def _translate_intermediate(
        self, inter: Intermediate, native_model: CpoModel, var_map: Dict[str, Any]
    ) -> Any:
        """Translate an intermediate expression.

        Args:
            inter: Intermediate expression
            native_model: Native CPLEX model
            var_map: Variable mapping

        Returns:
            Native expression for intermediate

        """
        native_expr = self._translate_expression_tree(inter.left, var_map)
        # In CPLEX, intermediates are typically just expressions
        # We could use Intermediate() but for simplicity just return the expr
        return native_expr

    def _translate_constraint(
        self,
        constraint: Constraint,
        var_map: Dict[str, Any],
        inter_map: Dict[str, Any],
    ) -> Any:
        """Translate a constraint to native CPLEX.

        Args:
            constraint: pysym Constraint
            var_map: Variable mapping
            inter_map: Intermediate mapping

        Returns:
            Native CPLEX constraint

        """
        return self._translate_expression_tree(constraint.expr, var_map, inter_map)

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
            Native CPLEX conditional constraint

        """
        condition = self._translate_expression_tree(cond.condition, var_map, inter_map)
        consequent = self._translate_expression_tree(
            cond.consequent, var_map, inter_map
        )
        return if_then(condition, consequent)

    def _translate_objective_expr(
        self,
        expr: Any,
        var_map: Dict[str, Any],
        inter_map: Dict[str, Any],
    ) -> Any:
        """Translate an objective expression.

        Args:
            expr: Expression or Variable
            var_map: Variable mapping
            inter_map: Intermediate mapping

        Returns:
            Native CPLEX objective expression

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
            Native CPLEX expression

        """
        if inter_map is None:
            inter_map = {}

        # Handle constants
        if isinstance(expr, (int, float)):
            return expr

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
                right = self._translate_expression_tree(expr.right, var_map, inter_map)
                if expr.operator == "-":
                    return -right
                else:
                    raise ValueError(f"Unknown unary operator: {expr.operator}")

            left = self._translate_expression_tree(expr.left, var_map, inter_map)
            right = self._translate_expression_tree(expr.right, var_map, inter_map)

            # Arithmetic operators
            if expr.operator == "+":
                return left + right
            elif expr.operator == "-":
                return left - right
            elif expr.operator == "*":
                return left * right
            elif expr.operator == "/":
                return left / right

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
