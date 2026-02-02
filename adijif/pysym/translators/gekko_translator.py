"""GEKKO translator for pysym."""

from typing import Any, Dict, Optional

from adijif.pysym.constraints import Constraint
from adijif.pysym.expressions import Expression, Intermediate
from adijif.pysym.model import Model
from adijif.pysym.solution import Solution
from adijif.pysym.translators.base import BaseTranslator
from adijif.pysym.variables import BinaryVar, Constant, IntegerVar, Variable
from adijif.solvers import GEKKO, gekko_solver


class GEKKOSolution(Solution):
    """GEKKO-specific solution implementation."""

    def get_value(self, var: Variable) -> Any:
        """Extract value of a variable from GEKKO solution."""
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

        # Extract value from GEKKO variable
        # GEKKO stores values in .value[0] for single values
        if hasattr(native_var, "value"):
            value = native_var.value
            if isinstance(value, list) and len(value) > 0:
                value = value[0]

            # Round integer variables to handle GEKKO's numerical tolerance
            if isinstance(var, (IntegerVar, BinaryVar)):
                value = round(value)

            return value
        else:
            raise ValueError(f"Cannot extract value from {type(native_var)}")


class GEKKOTranslator(BaseTranslator):
    """Translator from pysym to GEKKO.

    This translator compiles pysym models to GEKKO format for solving.

    GEKKO Limitations:
    - Conditional constraints (if_then) are not supported
    - Lexicographic multi-objective optimization not supported
    - Non-contiguous integer domains use SOS1 constraints (workaround)
    """

    def __init__(self):
        """Initialize GEKKO translator."""
        super().__init__("gekko")

    def check_availability(self) -> bool:
        """Check if GEKKO is installed."""
        return gekko_solver

    def build_native_model(self, model: Model) -> GEKKO:
        """Build native GEKKO model from pysym model.

        Args:
            model: pysym Model to compile

        Returns:
            GEKKO model ready for solving

        """
        if not self.check_availability():
            raise ImportError(
                "GEKKO not installed. Install with: pip install pyadi-jif[gekko]"
            )

        # Check for unsupported features
        if model.conditional_constraints:
            raise NotImplementedError(
                "GEKKO translator does not support conditional constraints (if_then). "
                "Use CPLEX solver instead."
            )

        if model.lexicographic_objectives:
            raise NotImplementedError(
                "GEKKO translator does not support lexicographic objectives. "
                "Use CPLEX solver instead."
            )

        # Create native GEKKO model
        native_model = GEKKO(remote=False)

        # Maps for variable tracking
        self.var_map = {}  # pysym var name -> pysym Variable
        self.native_var_map = {}  # pysym var name -> native GEKKO variable

        # Translate variables
        for var in model.variables:
            native_var = self._translate_variable(native_model, var)
            self.var_map[var.name] = var
            self.native_var_map[var.name] = native_var

        # Translate intermediates
        self.intermediate_map = {}  # intermediate name -> native variable
        for inter in model.intermediates:
            native_inter = self._translate_intermediate(
                native_model, inter, self.native_var_map
            )
            self.intermediate_map[inter.name] = native_inter

        # Translate constraints
        constraints = []
        for constraint in model.constraints:
            native_constraint = self._translate_constraint(
                constraint, self.native_var_map, self.intermediate_map
            )
            constraints.append(native_constraint)

        # Add all constraints at once
        if constraints:
            native_model.Equations(constraints)

        # Translate objectives
        if model.objectives:
            # GEKKO only supports single objective
            obj = model.objectives[0]
            native_obj = self._translate_expression_tree(
                obj.expr, self.native_var_map, self.intermediate_map
            )

            if obj.minimize:
                native_model.Minimize(native_obj)
            else:
                native_model.Maximize(native_obj)

        return native_model

    def solve(
        self,
        native_model: GEKKO,
        pysym_model: Model,
        time_limit: Optional[float] = None,
    ) -> GEKKOSolution:
        """Solve GEKKO model.

        Args:
            native_model: Native GEKKO model
            pysym_model: Original pysym Model (for reference)
            time_limit: Optional time limit in seconds

        Returns:
            Solution with results

        """
        # Set options
        native_model.options.IMODE = 3  # Static optimization
        native_model.options.SOLVER = 2  # IPOPT (for mixed-integer use 1 for APOPT)

        if time_limit is not None:
            native_model.options.MAX_TIME = time_limit

        try:
            native_model.solve(disp=False)
            is_feasible = True
        except Exception:
            # GEKKO raises exception if no solution found
            is_feasible = False

        # Create solution wrapper
        solution = GEKKOSolution(
            native_model,
            "gekko",
            self.var_map,
            self.native_var_map,
        )

        solution._is_feasible = is_feasible
        solution._is_optimal = is_feasible

        return solution

    def _translate_variable(self, native_model: GEKKO, var: Variable) -> Any:
        """Translate a pysym variable to GEKKO variable.

        Args:
            native_model: GEKKO model
            var: pysym Variable

        Returns:
            Native GEKKO variable

        """
        if isinstance(var, Constant):
            # Constants don't need GEKKO variables
            return var.value

        elif isinstance(var, BinaryVar):
            # Binary variable: 0 or 1
            return native_model.Var(lb=0, ub=1, integer=True, name=var.name)

        elif isinstance(var, IntegerVar):
            if isinstance(var.domain, range):
                # Contiguous range
                min_val = var.domain.start
                max_val = var.domain.stop - 1
                return native_model.Var(
                    lb=min_val, ub=max_val, integer=True, name=var.name
                )
            elif isinstance(var.domain, list):
                # Non-contiguous list
                if len(var.domain) == 1:
                    # Single value - constant
                    return var.domain[0]
                else:
                    # Non-contiguous domain
                    # Create a variable with wide bounds and apply SOS1 constraint
                    min_val = min(var.domain)
                    max_val = max(var.domain)

                    # Create auxiliary binary variables for SOS1
                    aux_vars = [
                        native_model.Var(lb=0, ub=1, integer=True) for _ in var.domain
                    ]

                    # Create main variable with wide bounds
                    main_var = native_model.Var(
                        lb=min_val, ub=max_val, integer=True, name=var.name
                    )

                    # Add constraint: main_var = sum(domain[i] * aux_vars[i])
                    native_model.Equation(
                        main_var
                        == sum(val * aux for val, aux in zip(var.domain, aux_vars))
                    )

                    # Add SOS1 constraint: sum(aux_vars) == 1
                    native_model.Equation(sum(aux_vars) == 1)

                    return main_var
            else:
                raise TypeError(f"Unsupported domain type: {type(var.domain)}")

        else:
            raise TypeError(f"Unknown variable type: {type(var)}")

    def _translate_intermediate(
        self,
        native_model: GEKKO,
        inter: Intermediate,
        var_map: Dict[str, Any],
    ) -> Any:
        """Translate an intermediate expression.

        Args:
            native_model: GEKKO model
            inter: Intermediate expression
            var_map: Variable mapping

        Returns:
            Native GEKKO intermediate

        """
        native_expr = self._translate_expression_tree(inter.left, var_map, {})
        return native_model.Intermediate(native_expr, name=inter.name)

    def _translate_constraint(
        self,
        constraint: Constraint,
        var_map: Dict[str, Any],
        inter_map: Dict[str, Any],
    ) -> Any:
        """Translate a constraint to native GEKKO.

        Args:
            constraint: pysym Constraint
            var_map: Variable mapping
            inter_map: Intermediate mapping

        Returns:
            Native GEKKO constraint

        """
        return self._translate_expression_tree(constraint.expr, var_map, inter_map)

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
            Native GEKKO expression

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
