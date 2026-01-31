"""Expression building with operator overloading."""

from typing import Any, List, Optional, Union

from adijif.pysym.variables import Constant, Variable


class Expression:
    """Expression combining variables with operators.

    Expressions are the building blocks of constraints and objectives.
    They support arithmetic and comparison operators, which return new
    Expression objects until a constraint (comparison) is made.

    The expression tree is preserved for later translation to native
    solver expressions.

    Examples:
        x = IntegerVar(range(1, 10), "x")
        y = IntegerVar(range(1, 10), "y")

        # Arithmetic expressions
        sum_expr = x + y
        product_expr = x * 5

        # Comparison constraints (return Expression)
        constraint = sum_expr >= 10
        equality = x == 5

        # Nested expressions
        complex_expr = (x + y) * 2 <= (x - y) + 100
    """

    def __init__(
        self,
        left: Any,
        operator: str,
        right: Any,
    ):
        """Initialize expression.

        Args:
            left: Left operand (Variable, Expression, or constant)
            operator: Operator string ("+", "-", "*", "/", "==", "<=", etc.)
            right: Right operand (Variable, Expression, or constant)
        """
        self.left = left
        self.operator = operator
        self.right = right

    def __repr__(self) -> str:
        """Return string representation."""
        left_str = repr(self.left) if not isinstance(self.left, Variable) else self.left.name
        right_str = repr(self.right) if not isinstance(self.right, Variable) else self.right.name
        if self.left is None:
            return f"({self.operator}{right_str})"
        return f"({left_str} {self.operator} {right_str})"

    def __add__(self, other: Any) -> "Expression":
        """Addition operator."""
        return Expression(self, "+", other)

    def __sub__(self, other: Any) -> "Expression":
        """Subtraction operator."""
        return Expression(self, "-", other)

    def __mul__(self, other: Any) -> "Expression":
        """Multiplication operator."""
        return Expression(self, "*", other)

    def __truediv__(self, other: Any) -> "Expression":
        """Division operator."""
        return Expression(self, "/", other)

    def __eq__(self, other: Any) -> "Expression":
        """Equality constraint."""
        return Expression(self, "==", other)

    def __le__(self, other: Any) -> "Expression":
        """Less than or equal constraint."""
        return Expression(self, "<=", other)

    def __ge__(self, other: Any) -> "Expression":
        """Greater than or equal constraint."""
        return Expression(self, ">=", other)

    def __lt__(self, other: Any) -> "Expression":
        """Less than constraint."""
        return Expression(self, "<", other)

    def __gt__(self, other: Any) -> "Expression":
        """Greater than constraint."""
        return Expression(self, ">", other)

    def __radd__(self, other: Any) -> "Expression":
        """Right addition."""
        return Expression(other, "+", self)

    def __rsub__(self, other: Any) -> "Expression":
        """Right subtraction."""
        return Expression(other, "-", self)

    def __rmul__(self, other: Any) -> "Expression":
        """Right multiplication."""
        return Expression(other, "*", self)

    def __rtruediv__(self, other: Any) -> "Expression":
        """Right division."""
        return Expression(other, "/", self)

    def __neg__(self) -> "Expression":
        """Negation operator."""
        return Expression(None, "-", self)

    def is_constraint(self) -> bool:
        """Check if expression is a constraint (comparison)."""
        return self.operator in ["==", "<=", ">=", "<", ">", "!="]

    def is_arithmetic(self) -> bool:
        """Check if expression is purely arithmetic (no comparison)."""
        return self.operator in ["+", "-", "*", "/"]

    def collect_variables(self) -> List[Variable]:
        """Collect all variables in this expression.

        Returns:
            List of unique Variable objects in order of appearance
        """
        variables = []
        seen = set()

        def _collect(expr: Any) -> None:
            if isinstance(expr, Variable):
                if expr.name not in seen:
                    variables.append(expr)
                    seen.add(expr.name)
            elif isinstance(expr, Expression):
                if expr.left is not None:
                    _collect(expr.left)
                _collect(expr.right)

        _collect(self)
        return variables


class Intermediate(Expression):
    """Intermediate expression (auxiliary variable).

    Intermediate expressions are used to simplify complex expressions
    by introducing auxiliary variables that represent sub-expressions.
    This is useful for:
    - Breaking down complex constraints
    - Improving solver readability
    - Enabling certain constraint patterns

    Examples:
        vco = Intermediate(vcxo * n / r, name="vco")
        model.add_constraint(vco >= vco_min)
        model.add_constraint(vco <= vco_max)
    """

    def __init__(
        self,
        expr: Union[Variable, Expression],
        name: str,
    ):
        """Initialize intermediate expression.

        Args:
            expr: The expression this intermediate represents
            name: Name of the auxiliary variable
        """
        super().__init__(expr, "intermediate", None)
        self.name = name
        self._aux_var = None  # Will be set by translator

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Intermediate({self.name})"
