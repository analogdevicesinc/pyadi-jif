"""OR-Tools translator for pysym."""

from fractions import Fraction
from typing import Any, Dict, Optional, Tuple, Union

from adijif.pysym.constraints import ConditionalConstraint, Constraint
from adijif.pysym.expressions import Expression, Intermediate
from adijif.pysym.model import Model
from adijif.pysym.solution import Solution
from adijif.pysym.translators.base import BaseTranslator
from adijif.pysym.variables import BinaryVar, Constant, IntegerVar, Variable
from adijif.solvers import ortools_solver

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
    - Integer-only solver. Rational arithmetic is used to handle float constants.
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
        for _var_name, (native_var, domain) in self._non_contiguous_vars.items():
            native_model.AddAllowedAssignments([native_var], [(v,) for v in domain])

        # Translate intermediates
        self.intermediate_map = {}  # intermediate name -> native variable/expression
        for inter in model.intermediates:
            # Intermediates are translated as expressions (rational tuples)
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
                    # Objective translation returns (num, den)
                    num, den = self._translate_objective_expr(
                        first_obj.expr, self.native_var_map, self.intermediate_map
                    )
                    # We minimize/maximize the numerator.
                    # Denominator is assumed positive and constant for comparison,
                    # but if it's variable, it's complex.
                    # Usually objectives are linear or simple.
                    # If den is not 1, we should be careful.
                    # For now, assume den is 1 or constant positive.
                    if first_obj.minimize:
                        native_model.Minimize(num)
                    else:
                        native_model.Maximize(num)
                    break
        elif model.objectives:
            # Use single objective
            obj = model.objectives[0]
            num, den = self._translate_objective_expr(
                obj.expr, self.native_var_map, self.intermediate_map
            )
            if obj.minimize:
                native_model.Minimize(num)
            else:
                native_model.Maximize(num)

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
            Native expression for intermediate (tuple of num, den)

        """
        return self._translate_expression_tree(inter.left, var_map)

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
        # Reify condition to boolean variable
        b = self._reify_condition(cond.condition, var_map, inter_map)

        # Apply consequent with implication
        # Translate the consequent constraint expression
        # We need to construct the constraint manually to apply OnlyEnforceIf
        
        # Consequent is a comparison (left OP right)
        # Handle both Constraint (has .expr) and Expression directly
        consequent_expr = cond.consequent.expr if isinstance(cond.consequent, Constraint) else cond.consequent
        left_r, right_r, op = self._translate_comparison_parts(
            consequent_expr, var_map, inter_map
        )
        
        # Cross multiply: n1/d1 OP n2/d2 -> n1*d2 OP n2*d1
        n1, d1 = left_r
        n2, d2 = right_r
        
        # Handle multiplication with intermediates if needed
        lhs = self._mul_exprs(n1, d2)
        rhs = self._mul_exprs(n2, d1)

        if op == "==":
            self._native_model.Add(lhs == rhs).OnlyEnforceIf(b)
        elif op == "!=":
            self._native_model.Add(lhs != rhs).OnlyEnforceIf(b)
        elif op == "<=":
            self._native_model.Add(lhs <= rhs).OnlyEnforceIf(b)
        elif op == ">=":
            self._native_model.Add(lhs >= rhs).OnlyEnforceIf(b)
        elif op == "<":
            self._native_model.Add(lhs < rhs).OnlyEnforceIf(b)
        elif op == ">":
            self._native_model.Add(lhs > rhs).OnlyEnforceIf(b)
        else:
            raise ValueError(f"Unsupported operator for consequent: {op}")

        return None

    def _reify_condition(
        self,
        cond_expr: Union[Constraint, Expression],
        var_map: Dict[str, Any],
        inter_map: Dict[str, Any],
    ) -> Any:
        """Reify a condition expression into a boolean variable.

        Returns:
             Bool var (or literal) that is true <=> cond_expr is true.
        """
        # Create bool var
        b = self._native_model.NewBoolVar(f"reify_{id(cond_expr)}")

        # Extract the Expression - handle both Constraint and Expression
        if isinstance(cond_expr, Constraint):
            expr = cond_expr.expr
        else:
            expr = cond_expr

        # Translate left and right
        left_r, right_r, op = self._translate_comparison_parts(
            expr, var_map, inter_map
        )
        
        n1, d1 = left_r
        n2, d2 = right_r
        
        lhs = self._mul_exprs(n1, d2)
        rhs = self._mul_exprs(n2, d1)

        # Add reified constraints
        if op == "==":
            self._native_model.Add(lhs == rhs).OnlyEnforceIf(b)
            self._native_model.Add(lhs != rhs).OnlyEnforceIf(b.Not())
        elif op == "!=":
            self._native_model.Add(lhs != rhs).OnlyEnforceIf(b)
            self._native_model.Add(lhs == rhs).OnlyEnforceIf(b.Not())
        elif op == "<=":
            self._native_model.Add(lhs <= rhs).OnlyEnforceIf(b)
            self._native_model.Add(lhs > rhs).OnlyEnforceIf(b.Not())
        elif op == ">=":
            self._native_model.Add(lhs >= rhs).OnlyEnforceIf(b)
            self._native_model.Add(lhs < rhs).OnlyEnforceIf(b.Not())
        elif op == "<":
            self._native_model.Add(lhs < rhs).OnlyEnforceIf(b)
            self._native_model.Add(lhs >= rhs).OnlyEnforceIf(b.Not())
        elif op == ">":
            self._native_model.Add(lhs > rhs).OnlyEnforceIf(b)
            self._native_model.Add(lhs <= rhs).OnlyEnforceIf(b.Not())
        else:
            raise ValueError(f"Unsupported operator for reification: {op}")

        return b

    def _translate_objective_expr(
        self,
        expr: Any,
        var_map: Dict[str, Any],
        inter_map: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Translate an objective expression.

        Returns:
            (num, den) tuple
        """
        return self._translate_expression_tree(expr, var_map, inter_map)

    def _translate_comparison_parts(
        self, 
        expr: Expression, 
        var_map: Dict[str, Any], 
        inter_map: Dict[str, Any]
    ) -> Tuple[Any, Any, str]:
        """Translate comparison expression parts without forming a constraint."""
        left = self._translate_expression_tree(expr.left, var_map, inter_map)
        right = self._translate_expression_tree(expr.right, var_map, inter_map)
        return left, right, expr.operator

    def _to_rational(self, val: Any) -> Tuple[Any, Any]:
        """Convert a value to (num, den)."""
        if isinstance(val, tuple) and len(val) == 2:
            return val
        if isinstance(val, float):
            if val.is_integer():
                return int(val), 1
            # Use Fraction to limit denominator size and avoid overflow
            f = Fraction(val).limit_denominator(100000)
            return f.numerator, f.denominator
        return val, 1

    def _mul_exprs(self, e1: Any, e2: Any) -> Any:
        """Multiply two linear expressions/vars/ints."""
        if isinstance(e1, int) and isinstance(e2, int):
            return e1 * e2
        if isinstance(e1, int) and e1 == 1:
            return e2
        if isinstance(e2, int) and e2 == 1:
            return e1
        if isinstance(e1, int) and e1 == 0:
            return 0
        if isinstance(e2, int) and e2 == 0:
            return 0

        # If one is constant int, it works directly in OR-Tools (LinearExpr * int)
        if isinstance(e1, int) or isinstance(e2, int):
            return e1 * e2

        # Both are non-constant expressions/vars
        # Use AddMultiplicationEquality
        # Use reasonable bounds for clock frequency calculations
        # Clock rates are typically in range [1e6, 1e12] Hz
        # Products can be up to 1e24 which still fits in int64 (9e18)
        # But we need to be careful - use bounds that are reasonable for the domain
        # Using -(10^14) to +(10^14) should cover most practical cases
        min_val = -(10**14)
        max_val = 10**14

        prod = self._native_model.NewIntVar(min_val, max_val, f"prod_{id(e1)}_{id(e2)}")
        self._native_model.AddMultiplicationEquality(prod, [e1, e2])
        return prod

    def _translate_expression_tree(
        self,
        expr: Any,
        var_map: Dict[str, Any],
        inter_map: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Translate an expression tree recursively.

        Returns:
            (numerator, denominator) tuple where each is an OR-Tools expression or int
        """
        if inter_map is None:
            inter_map = {}

        # Handle constants
        if isinstance(expr, (int, float)):
            return self._to_rational(expr)

        # Handle variables
        if isinstance(expr, Variable):
            if isinstance(expr, Constant):
                return self._to_rational(expr.value)
            var_name = expr.name
            if var_name not in var_map:
                # Should have been added to model and var_map
                raise ValueError(f"Variable {var_name} not in variable map")
            return var_map[var_name], 1

        # Handle intermediates
        if isinstance(expr, Intermediate):
            if expr.name in inter_map:
                return inter_map[expr.name]
            # Recursively translate
            return self._translate_expression_tree(expr.left, var_map, inter_map)

        # Handle expressions (operators)
        if isinstance(expr, Expression):
            if expr.left is None:
                # Unary operator (negation)
                r_n, r_d = self._translate_expression_tree(
                    expr.right, var_map, inter_map
                )
                if expr.operator == "-":
                    return -r_n, r_d
                else:
                    raise ValueError(f"Unknown unary operator: {expr.operator}")

            l_n, l_d = self._translate_expression_tree(
                expr.left, var_map, inter_map
            )
            r_n, r_d = self._translate_expression_tree(
                expr.right, var_map, inter_map
            )

            # Arithmetic operators
            if expr.operator == "+":
                # n1/d1 + n2/d2 = (n1*d2 + n2*d1) / (d1*d2)
                term1 = self._mul_exprs(l_n, r_d)
                term2 = self._mul_exprs(r_n, l_d)
                num = term1 + term2 # OR-Tools supports adding linear exprs
                den = self._mul_exprs(l_d, r_d)
                return num, den
                
            elif expr.operator == "-":
                # n1/d1 - n2/d2 = (n1*d2 - n2*d1) / (d1*d2)
                term1 = self._mul_exprs(l_n, r_d)
                term2 = self._mul_exprs(r_n, l_d)
                num = term1 - term2
                den = self._mul_exprs(l_d, r_d)
                return num, den
                
            elif expr.operator == "*":
                # (n1/d1) * (n2/d2) = (n1*n2) / (d1*d2)
                num = self._mul_exprs(l_n, r_n)
                den = self._mul_exprs(l_d, r_d)
                return num, den
                
            elif expr.operator == "/":
                # (n1/d1) / (n2/d2) = (n1*d2) / (d1*n2)
                num = self._mul_exprs(l_n, r_d)
                den = self._mul_exprs(l_d, r_n)
                return num, den

            # Comparison operators (returns constraint, not rational)
            elif expr.operator in ["==", "<=", ">=", "<", ">", "!="]:
                # n1/d1 OP n2/d2 -> n1*d2 OP n2*d1
                # Assumes positive denominators!
                # If den can be negative, inequality direction flips.
                # Usually dens are constants > 0 or products of positive vars.
                # If den involves vars, we assume they are positive (dividers, freqs).
                
                lhs = self._mul_exprs(l_n, r_d)
                rhs = self._mul_exprs(r_n, l_d)
                
                if expr.operator == "==":
                    return lhs == rhs
                elif expr.operator == "<=":
                    return lhs <= rhs
                elif expr.operator == ">=":
                    return lhs >= rhs
                elif expr.operator == "<":
                    return lhs < rhs
                elif expr.operator == ">":
                    return lhs > rhs
                elif expr.operator == "!=":
                    return lhs != rhs

            else:
                raise ValueError(f"Unknown operator: {expr.operator}")

        raise TypeError(f"Unknown expression type: {type(expr)}")